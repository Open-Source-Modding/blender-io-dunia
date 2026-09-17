"""FC6 / New Dawn XBG mesh parser.

FC6 (version 0x00130049) uses the same HSEM chunk-based format as FC5.
Chunk order: LTMR → LEKS → EDON → MB2O → KSRP → DIKS → DNKS → ITOM
→ SDOL → DHRM → ZNRM → XOBB → HPSB → FIKS → SDPD → [PMCP] → [PMCU]

SDOL format identical to FC2-FC5 (verified: FC4 Blender importer +
Noesis plugin + FC6 binary analysis):
  lod_count(u32) → per LOD: dist(f32) + vbc(u32)
    → per VB: flag/stride/vcount/offset (4×u32, 16B)
    → sm_count(u32) → per submesh: 7×u32 (28B)
    → vb_size(u32) → align(16) → vertex data → align(16) → index data

FC6 differences from FC5: version 0x00130049, DHRM v2, n_chunks at
offset 28. Chunk walker ignores n_chunks (unreliable); walks by fourcc+size.
"""

import struct

from . import import_xbg_fc5 as _fc5

# FC6 version marker
VERSION_FC6 = 0x00130049

# Header layout (32 bytes, same total as FC5 but different field positions):
#   + 0: HSEM magic (4B)
#   + 4: version u32 (0x00130049)
#   + 8: hash1 u32 (zero observed)
#   +12: hash2 u32 (zero observed)
#   +16: unknown u32 (zero observed)
#   +20: filesize_minus_12 u32
#   +24: reserved u32 (zero)
#   +28: n_chunks u32 (unreliable — walk by fourcc instead)
#   +32: first chunk

_HEADER_SIZE = 32


def detect_fc6(data):
    """Return True if data is an FC6 XBG (HSEM + version 0x00130049)."""
    return (len(data) >= 8
            and data[:4] == b'HSEM'
            and struct.unpack_from('<I', data, 4)[0] == VERSION_FC6)


def parse_fc6(path_or_bytes):
    """Parse an FC6 .xbg file.

    Returns dict with same structure as import_xbg_fc5.parse_xbg():
        version, materials, bones, skinning, clusters, lods,
        pos_scale, chunks, file_size
    """
    if isinstance(path_or_bytes, (bytes, bytearray)):
        data = bytes(path_or_bytes)
    else:
        with open(path_or_bytes, 'rb') as f:
            data = f.read()

    if not detect_fc6(data):
        raise ValueError("not an FC6 XBG (expected HSEM + version 0x00130049)")

    # Walk chunks starting at _HEADER_SIZE
    p = _HEADER_SIZE
    chunks = []  # [(name, offset, ck_size, dsize), ...]
    while p + 20 <= len(data):
        fourcc = data[p:p+4]
        if not all(0x20 <= b < 0x7f for b in fourcc):
            break
        ck_ver = struct.unpack_from('<I', data, p + 4)[0]
        ck_size = struct.unpack_from('<I', data, p + 8)[0]
        ck_dsize = struct.unpack_from('<I', data, p + 12)[0]
        if ck_size < 20 or p + ck_size > len(data):
            break
        name = fourcc.decode('ascii', errors='replace')
        chunks.append((name, p, ck_ver, ck_size, ck_dsize))
        p += ck_size

    # Delegate to FC5 parser's chunk decoders — the chunk formats are
    # compatible (LTMR, EDON, DNKS/SULC, SDOL, etc.).
    # Build a fake stream that the FC5 helpers can consume.
    materials = []
    lods = []
    bones = []
    skinning = None
    clusters = []
    pos_scale = 1.0

    for name, coff, cver, csize, cdsize in chunks:
        # Create a lightweight stream slice for this chunk's payload
        payload = data[coff + 20: coff + csize]
        s = _fc5._Stream(payload)

        if name == 'LTMR':
            n_mats = s.u32()
            s.u32()  # unknown
            for _ in range(n_mats):
                mp = s.strex()  # path
                mn = s.strex()  # name
                materials.append((mn, mp))
        elif name == 'EDON':
            bones = _fc5._read_edon(s, cdsize)
        elif name == 'DNKS':
            skinning = _fc5._read_dnks_sulc(data, coff)
            clusters = _fc5._read_dnks_clusters(data, coff, csize)
        elif name == 'SDOL':
            # FC6 SDOL format = FC2-FC5 (Noesis/FC4 Blender confirmed):
            # lod_count(u32) → per LOD: dist(f32) + vbc(u32) + VB descriptors + ...
            # Use _read_lod (FC3/FC4) which starts at lod_dist, not _read_lod_fc5
            # which expects an extra u32 before lod_dist.
            try:
                n_lods = struct.unpack_from('<I', data, coff + 20)[0]
                s2 = _fc5._Stream(data)
                s2.setpos(coff + 28)  # skip chunk header(20) + n_lods(4) + unk(4)
                for _ in range(n_lods):
                    try:
                        lods.append(_fc5._read_lod(s2))
                    except Exception:
                        break
            except Exception:
                pass
        elif name == 'PMCP':
            try:
                s2 = _fc5._Stream(data)
                s2.setpos(coff + 20)
                _pmcp_unk = s2.f32()
                raw_scale = s2.f32()
                baseline = 1.0 / 16384.0
                if abs(raw_scale - baseline) > 1e-6 and raw_scale > 0.0:
                    pos_scale = raw_scale * 16384.0
            except Exception:
                pass

    # Apply PMCP scale
    if pos_scale != 1.0:
        for lod in lods:
            for vb in lod['vbs']:
                scaled = []
                for v in vb['verts']:
                    px, py, pz = v['p']
                    scaled.append({**v, 'p': (px * pos_scale, py * pos_scale, pz * pos_scale)})
                vb['verts'] = scaled

    # Resolve SULC palettes
    if skinning and bones and lods:
        try:
            _fc5._assign_sulc_palettes(data, skinning, bones, lods)
        except Exception:
            pass

    return {
        'version': VERSION_FC6,
        'materials': materials,
        'bones': bones,
        'skinning': skinning,
        'clusters': clusters,
        'lods': lods,
        'pos_scale': pos_scale,
        'chunks': chunks,
        'file_size': len(data),
    }

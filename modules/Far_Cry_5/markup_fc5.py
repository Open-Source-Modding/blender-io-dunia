"""FC5/FC6 .markup.bin parser — cinematic trigger events.

Markup files define time-stamped gameplay events (footsteps, sounds,
dialog triggers, camera shakes) that play during animations. The binary
format is: version(u16) + 5 group_counts(u16 each) + per group: entries
of f32(time) + u32(fcb_len) + u64(frame_crc64) + bytes(fcb_data).

FC6 uses dialog trigger IDs instead of names (unlike FC5 which used names
in the FCB data). See dialog-trigger-ids.md for the ID→name mapping.

References:
- MabTools (Jakub Mareček) — FCBConverter fork with markup.bin support
- Disrupt markup-format.md — WDL markup XML structure
- legendhavoc175 / BIRDdude12 — FC6 dialog trigger ID mapping
"""

import struct


# Known FCB object hashes (from MabTools OffsetsHashesArray.ParamNames)
PARAM_HASHES = {
    0xC61F1FC7: 'ANIMPARAM',
    0x29A8E908: 'POSEANIMPARAM',
    0x8ED0A244: 'MOTIONMATCHINGPARAM',
    0x5FE8B8CB: 'BLENDPARAM',
    0xB40D7E9A: 'CURVEPARAM',
    0x1A23F841: 'CLIPPARAM',
    0x4DC6103D: 'LAYERPARAM',
    0xB92B4424: 'LOOKATPARAM',
    0x5FBCE41E: 'MOVEBLENDPARAM',
    0xB917B418: 'MOVESTATEPARAM',
    0xA7180A3D: 'PMSVALUEPARAM',
    0x68F54F2E: 'RAGDOLLPARAM',
    0x27F5B59A: 'SECONDARYMOTIONPARAM',
    0x52ABD0AC: 'BLENDADJUSTPARAM',
    0xA0B744E0: 'MOTIONMATCHINGANIMSPEEDPARAM',
    0x89A7B434: 'MOTIONMATCHINGANIMMOTIONPARAM',
}


def parse_markup_bin(path_or_bytes):
    """Parse a .markup.bin file into a list of frame events.

    Returns dict:
        version     : int
        groups      : list of (group_index, entries)
        entries     : list of {time, frame_crc64, fcb_data, group}
    """
    if isinstance(path_or_bytes, (bytes, bytearray)):
        data = bytes(path_or_bytes)
    else:
        with open(path_or_bytes, 'rb') as f:
            data = f.read()

    if len(data) < 12:
        return {'version': 0, 'groups': [], 'entries': []}

    off = 0
    version = struct.unpack_from('<H', data, off)[0]; off += 2

    # Read 5 group counts
    group_counts = []
    for _ in range(5):
        gc = struct.unpack_from('<H', data, off)[0]; off += 2
        group_counts.append(gc)

    groups = []
    all_entries = []

    for gi, count in enumerate(group_counts):
        entries = []
        for _ in range(count):
            if off + 16 > len(data):
                break
            time = struct.unpack_from('<f', data, off)[0]; off += 4
            fcb_len = struct.unpack_from('<I', data, off)[0]; off += 4
            frame_crc64 = struct.unpack_from('<Q', data, off)[0]; off += 8

            fcb_data = data[off:off + fcb_len] if fcb_len > 0 else b''
            off += fcb_len

            entry = {
                'time': time,
                'frame_crc64': frame_crc64,
                'fcb_data': fcb_data,
                'group': gi,
            }
            entries.append(entry)
            all_entries.append(entry)

        groups.append((gi, entries))

    return {
        'version': version,
        'groups': groups,
        'entries': all_entries,
    }


def parse_fcb_event(fcb_data):
    """Parse a single FCB event object from raw bytes.

    Returns dict with event type and fields, or None if unparseable.
    FCB format: nbCF header → type_hash(u32) → fields.
    """
    if len(fcb_data) < 8:
        return None

    # nbCF header
    if fcb_data[:4] != b'nbCF':
        return None

    off = 8  # skip nbCF + version(4)
    result = {'type_hash': 0, 'fields': {}}

    # Read type hash (first u32 after header)
    if off + 4 <= len(fcb_data):
        result['type_hash'] = struct.unpack_from('<I', fcb_data, off)[0]
        off += 4

    # Read field count
    if off + 4 <= len(fcb_data):
        n_fields = struct.unpack_from('<I', fcb_data, off)[0]
        off += 4
    else:
        return result

    # Read fields (simplified — full FCB parsing needs the binary object format)
    # For now, extract string-like values
    for _ in range(min(n_fields, 20)):
        if off + 8 > len(fcb_data):
            break
        field_hash = struct.unpack_from('<I', fcb_data, off)[0]
        field_type = struct.unpack_from('<I', fcb_data, off + 4)[0]
        off += 8

        if field_type == 0x02:  # String
            str_len = struct.unpack_from('<I', fcb_data, off)[0]
            off += 4
            if off + str_len <= len(fcb_data):
                s = fcb_data[off:off + str_len].decode('ascii', errors='replace').rstrip('\0')
                result['fields'][f'0x{field_hash:08X}'] = s
                off += str_len
        elif field_type == 0x01:  # Int32
            val = struct.unpack_from('<i', fcb_data, off)[0]
            result['fields'][f'0x{field_hash:08X}'] = val
            off += 4
        elif field_type == 0x05:  # Float
            val = struct.unpack_from('<f', fcb_data, off)[0]
            result['fields'][f'0x{field_hash:08X}'] = val
            off += 4
        elif field_type == 0x06:  # Float4/Vector4
            vals = struct.unpack_from('<4f', fcb_data, off)
            result['fields'][f'0x{field_hash:08X}'] = vals
            off += 16
        elif field_type == 0x08:  # BinHex/blob
            blob_len = struct.unpack_from('<I', fcb_data, off)[0]
            off += 4 + blob_len
        else:
            # Unknown type — skip
            off += 4

    return result


def markup_to_blender_markers(blender_obj, markup_data):
    """Create Blender timeline markers from parsed markup data.

    Creates a marker for each event with the time and event type info.
    """
    import bpy

    for entry in markup_data.get('entries', []):
        time = entry['time']
        frame_crc = entry['frame_crc64']

        # Create marker
        marker_name = f"markup_{frame_crc:016X}"
        marker = bpy.context.scene.timeline_markers.new(marker_name, frame=int(time * 24))

        # Try to parse the FCB event for a better name
        if entry.get('fcb_data'):
            event = parse_fcb_event(entry['fcb_data'])
            if event and event.get('fields'):
                # Use first string field as the marker name
                for k, v in event['fields'].items():
                    if isinstance(v, str) and len(v) > 3:
                        marker.name = v[:64]
                        break

    return len(markup_data.get('entries', []))

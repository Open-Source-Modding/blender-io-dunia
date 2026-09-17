"""FC5 .material.bin parser — extracts texture paths for auto-loading.

FC5 material.bin format (reverse-engineered from io_scene_FarCry5 by Volfin):
    Header: 4B version + 4B unknown
    Length-prefixed strings: opaque_type, material_type, then texture paths
    Texture paths are length-prefixed strings found at known offsets.

This module extracts the texture map paths (diffuse, normal, specular, etc.)
so the importer can auto-load them into Blender materials.
"""

import struct
import os


def _read_str(data, offset):
    """Read a length-prefixed string from data at offset.

    Returns (string, new_offset) or ('', new_offset) on failure.
    """
    if offset + 1 > len(data):
        return '', offset
    length = data[offset]
    offset += 1
    if offset + length > len(data):
        return '', offset
    s = data[offset:offset + length].decode('latin-1', errors='replace')
    return s, offset + length


def _read_u32(data, offset):
    """Read a u32 from data at offset."""
    if offset + 4 > len(data):
        return 0, offset
    v = struct.unpack_from('<I', data, offset)[0]
    return v, offset + 4


def _read_u8(data, offset):
    """Read a u8 from data at offset."""
    if offset >= len(data):
        return 0, offset
    return data[offset], offset + 1


def parse_material_bin(path):
    """Parse an FC5 .material.bin file and extract texture paths.

    Returns dict:
        opaque      : str — opaque type (e.g. 'opaquealpha', 'emissivealpha')
        textures    : list of (map_type, path) tuples
                      map_type is one of: 'diffuse', 'normal', 'specular',
                      'emissive', 'unknown'
        raw_paths   : list of all texture paths found (for fallback)
    """
    if not os.path.isfile(path):
        return None

    with open(path, 'rb') as f:
        data = f.read()

    if len(data) < 10:
        return None

    result = {
        'opaque': '',
        'textures': [],
        'raw_paths': [],
    }

    try:
        p = 0
        # Skip header (4B version + 4B unknown)
        p += 8

        # Read opaque type string
        opaque, p = _read_str(data, p)
        result['opaque'] = opaque

        # Skip some bytes depending on opaque type
        if opaque in ('opaquealpha', 'DISABLE_ALBEDO', 'ANIMATED_WRINKLES_V0'):
            # Skip descriptor blocks (layout varies by opaque type)
            # We just scan for length-prefixed paths after this
            pass

        # Scan for texture paths — they appear as length-prefixed strings
        # at predictable offsets.  Rather than hardcode offsets (which vary
        # across materials), we scan for plausible path patterns.
        i = p
        while i < len(data) - 2:
            # Look for length-prefixed strings that look like texture paths
            length = data[i]
            if length < 8 or length > 200:
                i += 1
                continue
            if i + 1 + length > len(data):
                break
            s = data[i+1:i+1+length].decode('latin-1', errors='replace')
            # Check if it looks like a texture path (contains backslash + extension)
            if '\\' in s and ('.' in s.split('\\')[-1]):
                result['raw_paths'].append(s)
                # Classify by suffix
                base = s.split('\\')[-1].lower()
                if '_d.' in base or '_diffuse' in base:
                    result['textures'].append(('diffuse', s))
                elif '_n.' in base or '_normal' in base:
                    result['textures'].append(('normal', s))
                elif '_s.' in base or '_specular' in base:
                    result['textures'].append(('specular', s))
                elif '_e.' in base or '_emissive' in base:
                    result['textures'].append(('emissive', s))
                else:
                    result['textures'].append(('unknown', s))
                i += 1 + length
            else:
                i += 1

    except Exception:
        pass

    return result


def resolve_texture_path(mat_path, tex_rel_path, xbg_path):
    """Resolve a texture path relative to the XBG file location.

    FC5 stores textures relative to the 'graphics' folder.  Given:
        mat_path  : material path from LTMR (e.g. 'graphics\\_materials\\X.material.bin')
        tex_rel_path : texture path from material.bin (e.g. 'graphics\\textures\\X_d.xbt')
        xbg_path : full path to the .xbg file

    Returns the absolute path to the texture file, or None.
    """
    if not tex_rel_path or not xbg_path:
        return None

    # XBG is typically at e.g. '.../graphics/weapons/xxx.xbg'
    # Textures are at '.../graphics/textures/xxx.xbt'
    # Walk up from xbg until we find the 'graphics' folder
    xbg_dir = os.path.dirname(os.path.abspath(xbg_path))

    # Try relative to the XBG's parent directories
    # Convert backslashes to forward slashes for cross-platform
    tex_rel = tex_rel_path.replace('\\', '/')

    # Walk up to find the common root
    parts = tex_rel.split('/')
    for depth in range(len(parts)):
        candidate = os.path.join(xbg_dir, *(['..'] * depth), *parts)
        candidate = os.path.normpath(candidate)
        if os.path.isfile(candidate):
            return candidate

    # Fallback: try relative to xbg directory directly
    candidate = os.path.join(xbg_dir, parts[-1])
    if os.path.isfile(candidate):
        return candidate

    return None

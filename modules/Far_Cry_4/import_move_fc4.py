"""Far Cry 4/5/6 .move.bin parser — minimal header + metadata.

The move.bin format is a custom binary container (NOT nbCF/FCbn):
  u16 version     (22093=FC4 "MV", 65=ND, 85=FC6)
  u16 unknown
  byte[] data     (custom binary object format — not standard FCB)

The data defines animation state machines: blend trees, state transitions,
locomotion graphs, and procedural animation parameters.

Full parsing requires RE of the binary object container, which uses
hash-based field identifiers. MabTools (Jakub Mareček) has ConvertFCB
support for this format via Gibbed.Dunia2.

Source: MabTools-main/FCBConverter/Program.cs, samir (Discord),
sharp_razor8 (Discord), MoveBin Research/ samples.
"""

import struct
import os

from . import move_values


# Version magic values
VER_FC4 = 22093    # 0x564D "MV"
VER_ND = 65
VER_FC6 = 85


def parse_move_header(data):
    """Parse the 4-byte move.bin header.

    Returns:
        dict with 'version', 'unknown', 'game' keys
    """
    if len(data) < 4:
        return None

    ver = struct.unpack_from('<H', data, 0)[0]
    unk = struct.unpack_from('<H', data, 2)[0]

    if ver == VER_FC4:
        game = "Far Cry 4"
    elif ver == VER_ND:
        game = "Far Cry New Dawn"
    elif ver == VER_FC6:
        game = "Far Cry 6"
    else:
        game = f"Unknown (0x{ver:04x})"

    return {
        'version': ver,
        'unknown': unk,
        'game': game,
    }


def parse_move_file(path_or_bytes):
    """Parse a .move.bin file.

    Args:
        path_or_bytes: file path or raw bytes

    Returns:
        dict with header info and raw data, or None on error
    """
    if isinstance(path_or_bytes, (str, bytes)):
        if isinstance(path_or_bytes, str):
            with open(path_or_bytes, 'rb') as f:
                data = f.read()
        else:
            data = path_or_bytes
    else:
        return None

    header = parse_move_header(data)
    if header is None:
        return None

    # The binary object data starts at offset 4
    # Format: custom container (not nbCF/FCbn)
    # Full parsing needs the Gibbed.Dunia2 BinaryObjectFile deserializer
    raw_data = data[4:]

    return {
        'header': header,
        'raw_data': raw_data,
        'size': len(data),
        'param_definitions': move_values.MOVE_VALUE_DEFINITIONS,
    }


def get_param_name(index):
    """Get human-readable name for a move value index."""
    return move_values.get_param_name(index)


def get_param_type(index):
    """Get type string for a move value index."""
    return move_values.get_param_type(index)

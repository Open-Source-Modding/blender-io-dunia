"""Far Cry 5 .move.bin parser — minimal header + metadata.

The combinedmovefile.bin is the FC5 root state machine.
Format: u16 version (64=FC5) + u16 unknown + binary object data.

Full parsing requires RE of the binary object container.
"""

import struct

from .. import move_values


VER_FC5 = 64


def parse_move_header(data):
    """Parse the 4-byte move.bin header."""
    if len(data) < 4:
        return None

    ver = struct.unpack_from('<H', data, 0)[0]
    unk = struct.unpack_from('<H', data, 2)[0]

    if ver == VER_FC5:
        game = "Far Cry 5"
    else:
        game = f"Unknown (0x{ver:04x})"

    return {
        'version': ver,
        'unknown': unk,
        'game': game,
    }


def parse_move_file(path_or_bytes):
    """Parse a .move.bin file."""
    if isinstance(path_or_bytes, str):
        with open(path_or_bytes, 'rb') as f:
            data = f.read()
    elif isinstance(path_or_bytes, bytes):
        data = path_or_bytes
    else:
        return None

    header = parse_move_header(data)
    if header is None:
        return None

    return {
        'header': header,
        'raw_data': data[4:],
        'size': len(data),
        'param_definitions': move_values.MOVE_VALUE_DEFINITIONS,
    }

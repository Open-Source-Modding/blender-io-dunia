"""Far Cry 5 .move.bin parser — binary animation state machine.

Same parser as FC4 — auto-detects format.
"""

import struct

from . import move_values

# Import core parser from FC4
from ..Far_Cry_4.import_move_fc4 import (
    MoveNode, MoveFile, CLASS_NAMES,
    _parse_tree_nodes, _parse_combined_move, _parse_movedef,
    get_class_name,
    VER_FC4, VER_FC5, VER_ND, VER_FC6,
)


def parse_move_file(path_or_bytes, sizes=None, offsets_array=None):
    """Parse a .move.bin file (FC5/ND/FC6).

    Args:
        path_or_bytes: file path or raw bytes
        sizes: optional list of tree sizes from PerMoveResourceInfo
        offsets_array: optional byte positions array from ANIMPARAM_FIXUPS
    """
    if isinstance(path_or_bytes, str):
        with open(path_or_bytes, 'rb') as f:
            data = f.read()
    elif isinstance(path_or_bytes, bytes):
        data = path_or_bytes
    else:
        return None

    if len(data) < 4:
        return None

    first_u32 = struct.unpack_from('<I', data, 0)[0]
    if first_u32 in (VER_FC5, VER_ND, VER_FC6):
        return _parse_combined_move(data, sizes, offsets_array)
    else:
        return _parse_movedef(data)

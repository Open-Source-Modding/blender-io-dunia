"""Far Cry 4/5/6 .move.bin parser — binary animation state machine.

Two file formats:
1. movedef.move.bin (FC4): u16 ver + u16 unk + raw animation tree
2. combinedmovefile.bin (FC5/ND/FC6): u32 ver + u32 moveDataSize + u32 fcbDataSize
   + moveData (animation trees) + fcbData (FCbn: PerMoveResourceInfo + OffsetsHashesArray)

Animation tree nodes use classNameType bytes (7-47) to determine structure.
Children are referenced by u16 offsets (×4 for byte position from data start).

Source: MabTools-main/FCBConverter/CombinedMoveFile.cs (GPL, Jakub Mareček)
"""

import struct
import os

try:
    from . import move_values
except ImportError:
    import move_values


VER_FC4 = 22093    # 0x564D "MV"
VER_FC5 = 64
VER_ND = 65
VER_FC6 = 85

# classNameType → human-readable name
CLASS_NAMES = {
    7: "CMoveState",
    8: "CMoveBranch",
    9: "CMoveBracket",
    10: "CMoveComparisonOpe",
    11: "CMoveIntervalOpe",
    12: "CMoveBlendRef",
    13: "CMoveMultiBlendRef",
    14: "CMoveSuspendLayer",
    15: "CMoveStateRef",
    16: "CMoveSingleAnim",
    17: "CMoveSpeedScaledAnim",
    18: "CMoveRandomOffsetAnim",
    19: "CMoveTimeControlledAnim",
    20: "CMoveDoNothing",
    21: "CMoveMotionMatching",
    22: "CMoveMotionMatchingList",
    23: "CMoveMotionMatchingAnim",
    24: "CMoveMotionMatchingPartialAnim",
    25: "CMoveMotionMatchingAnimGroup",
    26: "CMoveFacialAnim",
    27: "CMoveProcedural",
    28: "CMoveRandomSelector",
    29: "CMovePMSSelector",
    30: "CMoveSequence",
    31: "CMoveRangeBlend",
    32: "CMoveAxialBlend",
    34: "CMoveMultiBlend",
    37: "CMoveSetGameParams",
    38: "CMoveAnimTechSetPMS",
    39: "CMoveAnimTechProgressToPMS",
    40: "CMoveAnimTechAnchor",
    41: "CMoveAnimTechIKPath",
    43: "CMoveTransition",
    44: "CMoveTransitionContainer",
}


class MoveNode:
    """A single node in the animation state machine tree."""
    __slots__ = ('class_type', 'class_name', 'header_a', 'header_b',
                 'children', 'params', 'data')

    def __init__(self, class_type):
        self.class_type = class_type
        self.class_name = CLASS_NAMES.get(class_type, f"Unknown_{class_type}")
        self.header_a = 0
        self.header_b = 0
        self.children = []
        self.params = {}
        self.data = b''

    def __repr__(self):
        return f"MoveNode({self.class_name}, children={len(self.children)})"


class MoveFile:
    """Parsed move.bin file with header info and animation tree."""
    __slots__ = ('version', 'unknown', 'game', 'file_type',
                 'root_hash', 'nodes', 'resource_infos', 'param_definitions')

    def __init__(self):
        self.version = 0
        self.unknown = 0
        self.game = ""
        self.file_type = ""  # "movedef" or "combined"
        self.root_hash = 0
        self.nodes = []
        self.resource_infos = []
        self.param_definitions = move_values.MOVE_VALUE_DEFINITIONS

    def get_param_name(self, index):
        return move_values.get_param_name(index)

    def get_param_type(self, index):
        return move_values.get_param_type(index)


def _read_node_data(data, pos, class_type):
    """Read node-specific data based on classNameType.

    Different class types have different binary layouts.
    Returns (new_pos, params_dict).

    Source: MabTools/CombinedMoveFile.cs ChildDeserialize()
    """
    params = {}

    if class_type in (10, 11):
        # ComparisonOpe / IntervalOpe: single byte value
        if pos < len(data):
            params['header_value'] = struct.unpack_from('<B', data, pos)[0]
            pos += 1
        return pos, params

    # Standard header: children_count, headerA, headerB
    if pos + 3 > len(data):
        return pos, params

    children_count = struct.unpack_from('<B', data, pos)[0]
    pos += 1
    header_a = struct.unpack_from('<B', data, pos)[0]
    pos += 1
    header_b = struct.unpack_from('<B', data, pos)[0]
    pos += 1

    # For blend/layer types, children_count and headerA are swapped
    if class_type in (12, 13, 14, 44):
        children_count, header_a = header_a, children_count

    params['children_count'] = children_count
    params['header_a'] = header_a
    params['header_b'] = header_b

    # Read child offsets (u16 each)
    child_offsets = []
    for _ in range(children_count):
        if pos + 2 > len(data):
            break
        offset_val = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        if offset_val != 0:
            child_offsets.append(offset_val)
    params['child_offsets'] = child_offsets

    # Padding to 4-byte alignment
    padding = (4 - (children_count % 4)) % 4
    pos += padding * 2

    # Node-specific data after header
    if class_type in (16, 17, 18, 19):
        # Animation nodes: u32 animId + u32 animParam
        if pos + 8 <= len(data):
            params['anim_id'] = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            params['anim_param'] = struct.unpack_from('<I', data, pos)[0]
            pos += 4
    elif class_type == 12:
        # BlendRef: no extra data (children already read)
        pass
    elif class_type == 13:
        # MultiBlendRef: no extra data
        pass
    elif class_type == 14:
        # SuspendLayer: no extra data
        pass
    elif class_type == 15:
        # StateRef: no extra data
        pass
    elif class_type == 21:
        # MotionMatching: u32 + u32 + data
        if pos + 8 <= len(data):
            pos += 8
    elif class_type == 22:
        # MotionMatchingList: u32 count + data
        if pos + 4 <= len(data):
            pos += 4
    elif class_type in (30, 31, 32, 34):
        # RangeBlend/AxialBlend/MultiBlend: u32 blendParam
        if pos + 4 <= len(data):
            params['blend_param'] = struct.unpack_from('<I', data, pos)[0]
            pos += 4
    elif class_type == 43:
        # Transition: u32 transitionParam
        if pos + 4 <= len(data):
            params['transition_param'] = struct.unpack_from('<I', data, pos)[0]
            pos += 4

    return pos, params


def _parse_tree_nodes(data, pos, depth=0, max_depth=50, visited=None, max_nodes=100000):
    """Parse animation tree nodes from binary data."""
    if visited is None:
        visited = set()

    nodes = []
    if depth > max_depth or pos >= len(data) or pos in visited or len(nodes) >= max_nodes:
        return nodes

    visited.add(pos)

    while pos < len(data):
        class_type = struct.unpack_from('<b', data, pos)[0]
        pos += 1

        node = MoveNode(class_type)
        pos, params = _read_node_data(data, pos, class_type)
        node.params = params
        node.header_a = params.get('header_a', 0)
        node.header_b = params.get('header_b', 0)

        # Read children recursively
        child_offsets = params.get('child_offsets', [])
        for offset_val in child_offsets:
            child_pos = offset_val * 4
            if child_pos < len(data) and child_pos not in visited:
                children = _parse_tree_nodes(data, child_pos, depth + 1, max_depth, visited, max_nodes)
                node.children.extend(children)

        nodes.append(node)
        if depth == 0:
            break
        if len(nodes) >= max_nodes:
            break

    return nodes


def _parse_combined_move(data):
    """Parse combinedmovefile.bin format.

    Format: u32 ver + u32 moveDataSize + u32 fcbDataSize + moveData + fcbData
    The moveData has: u64 filename_hash + tree nodes
    Tree child offsets are relative to moveData start (after filename hash).
    """
    if len(data) < 12:
        return None

    result = MoveFile()
    result.file_type = "combined"
    result.version = struct.unpack_from('<I', data, 0)[0]
    move_data_size = struct.unpack_from('<I', data, 4)[0]
    fcb_data_size = struct.unpack_from('<I', data, 8)[0]

    if result.version == VER_FC5:
        result.game = "Far Cry 5"
    elif result.version == VER_ND:
        result.game = "Far Cry New Dawn"
    elif result.version == VER_FC6:
        result.game = "Far Cry 6"
    else:
        result.game = f"Unknown (0x{result.version:08x})"

    # Extract move data (animation trees)
    move_data = data[12:12 + move_data_size]

    # Tree starts after 8-byte filename hash
    # Child offsets are relative to move_data start (after filename hash)
    if move_data and len(move_data) > 8:
        tree_data = move_data[8:]  # skip filename hash
        result.nodes = _parse_tree_nodes(tree_data, 0)

    return result


def _parse_movedef(data):
    """Parse movedef.move.bin format.

    Format: u16 ver + u16 unk + header + tree data.
    The header structure is NOT the same as combinedmovefile.bin.
    Tree data starts after a variable-length header (found via classNameType scan).

    TODO: Full header format RE needed. The header contains:
    - u32 count (21 objects?)
    - u32 size (327680?)
    - u32 count (2?)
    - Array of small u32 values (0-6, likely counts/indices)
    - ASCII-like strings ("gVMv", "CVmV")
    - Tree data follows after header (classNameType bytes found at 0x523+)
    """
    if len(data) < 4:
        return None

    result = MoveFile()
    result.file_type = "movedef"
    result.version = struct.unpack_from('<H', data, 0)[0]
    result.unknown = struct.unpack_from('<H', data, 2)[0]

    if result.version == VER_FC4:
        result.game = "Far Cry 4"
    elif result.version == VER_FC5:
        result.game = "Far Cry 5"
    elif result.version == VER_ND:
        result.game = "Far Cry New Dawn"
    elif result.version == VER_FC6:
        result.game = "Far Cry 6"
    else:
        result.game = f"Unknown (0x{result.version:04x})"

    # Scan for first classNameType (7-47) to find tree data start
    tree_start = 4
    for i in range(4, min(len(data), 10000)):
        ct = struct.unpack_from('<b', data, i)[0]
        if 7 <= ct <= 47:
            tree_start = i
            break

    # Parse tree nodes from data after header
    if tree_start < len(data):
        result.nodes = _parse_tree_nodes(data, tree_start)

    return result


def parse_move_file(path_or_bytes):
    """Parse a .move.bin file (auto-detect format).

    Returns MoveFile or None on error.
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

    # Auto-detect: combinedmovefile.bin starts with u32 version (64/65/85)
    # movedef.move.bin starts with u16 version (22093) + u16 unk
    first_u32 = struct.unpack_from('<I', data, 0)[0]
    first_u16 = struct.unpack_from('<H', data, 0)[0]

    if first_u32 in (VER_FC5, VER_ND, VER_FC6):
        return _parse_combined_move(data)
    elif first_u16 == VER_FC4:
        return _parse_movedef(data)
    else:
        # Try combined format first (u32 version)
        return _parse_combined_move(data)


def get_class_name(class_type):
    """Get human-readable name for a classNameType value."""
    return CLASS_NAMES.get(class_type, f"Unknown_{class_type}")

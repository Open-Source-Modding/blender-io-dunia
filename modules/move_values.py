"""MoveValueDefinitions — animation state machine parameter mappings.

Source: samir (Discord), MabTools CombinedMoveFile.cs
Games: FC4, FC5, ND, FC6 (indices may vary per game)
"""

# index → (name, type)
# Types: angle (radians), float, enum (indexed), bool (0/1)
MOVE_VALUE_DEFINITIONS = {
    5:   ("HeadingAngle", "angle"),
    6:   ("FacingAngle", "angle"),
    7:   ("Speed", "float"),
    12:  ("AimStance", "enum"),
    21:  ("EquippedWeapon", "enum"),
    47:  ("MentalState", "enum"),
    58:  ("IsSprinting", "bool"),
    60:  ("IronSightTransition", "float"),
    82:  ("LastHitDirection", "angle"),
    83:  ("SpeedWhenHurt", "float"),
    86:  ("PGM_TargetPlantAngle", "angle"),
    87:  ("CoverHidingBehind", "bool"),
    91:  ("PGM_TargetSpeed", "float"),
    93:  ("PGM_TargetMoveDirection", "angle"),
    94:  ("PGM_TargetFaceDirection", "angle"),
    101: ("Identity_AnimationSet", "enum"),
    175: ("Identity_MetaAnimationSet", "enum"),
    225: ("TurnAngle", "angle"),
}

# Reverse lookup: name → index
MOVE_VALUE_NAMES = {name: idx for idx, (name, _) in MOVE_VALUE_DEFINITIONS.items()}


def get_param_name(index):
    """Get human-readable name for a move value index."""
    if index in MOVE_VALUE_DEFINITIONS:
        return MOVE_VALUE_DEFINITIONS[index][0]
    return f"Param_{index}"


def get_param_type(index):
    """Get type string for a move value index."""
    if index in MOVE_VALUE_DEFINITIONS:
        return MOVE_VALUE_DEFINITIONS[index][1]
    return "unknown"

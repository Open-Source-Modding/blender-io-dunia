# Far Cry XBG Importer for Blender

Blender 5.0 add-on for importing, editing, and re-exporting 3D models from
Far Cry and Avatar games. Originally Szkaradek123's Blender 2.49b script,
rewritten for modern Blender.

## Features

- **Eight games, one add-on** — Avatar, Far Cry 1 through 5/New Dawn, Primal,
  and Instincts, each self-contained with a game-picker UI.
- **Full geometry editing** — add/delete vertices, join foreign meshes, re-skin
  from vertex groups, then inject back into the game file.
- **Animations** — import .mab skeletal animations for six games, facial pose
  libraries and expression curves for Avatar/FC2, full cinematic scene import.
- **Skeletons and collision** — import .skeleton rigs, import HKX collision for
  five games, export edited collision with MOPP rebuild for Avatar/FC2.
- **Custom materials** — bake Blender materials to .xbt textures and .xbm files
  (Avatar/FC2 only).
- **LOD control** — import specific or all LODs, peek LOD count, edit switch
  distances.
- **Byte-exact round-trips** — unedited re-exports are bit-identical to the
  original. Oversized geometry auto-expands bounds instead of clamping.

## Supported Games

| Game | Import | Materials | Inject | Add/Delete | Animation | Skeleton | Collision |
|------|--------|-----------|--------|------------|-----------|----------|-----------|
| Avatar | Full (LODs, skin, damage) | auto-load + export | Yes | Yes | .mab + facial + scenes | import+export | import+export (MOPP) |
| Far Cry 2 | Full | auto-load* + export | Yes | Yes | .mab + facial + scenes | import+export | import+export |
| Far Cry 3 | Full | slot names | Yes | Yes | partial .mab | import | import |
| Far Cry 4 | Full | slot names | Yes | Yes | .mab | rig from model | import |
| Far Cry 5 / ND | 8-influence skin | slot names | same-count | No | .mab + root motion | rig from model | — |
| Far Cry Primal | Full | slot names | Yes | Yes | coming soon | rig from model | — |
| Far Cry 1 | per-face materials | .dds auto-load | — | — | — | — | — |
| FC Instincts | Yes | .xbt auto-decode | — | — | — | — | — |
| Far Cry 6 | coming soon | | | | | | |

Inject writes to a new copy, never the original. Add/Delete means full
vertex/triangle count rebuild. Same-count inject preserves edits at the
original vertex count.

*FC2 texture auto-load shares Avatar's data-folder preference.

## Requirements

- Blender 5.0+
- Extracted game files (Avatar `Data/`, FC Instincts `.fat/.dat` dumps, etc.)

## Installation

1. Download the release `.zip` from [Releases](../../releases).
2. Blender Edit > Preferences > Add-ons > Install, pick the zip, enable.
3. Set data-folder paths in add-on preferences (powers texture auto-load).

Upgrading from v2.x: remove the old add-on first, then install the new zip.

## Usage

N-panel > XBG Import tab > pick your game. Panels:

| Panel | What it does |
|-------|-------------|
| Import | Data folder, texture options, LOD peek, import button |
| Advanced Mode | Toggle to reveal inject, animation, skeleton, editors |
| Inject / Export | Source file status, bounds check, inject button |
| Animation | .mab import with resampling and helper-bone options |
| Skeleton / HKX | Standalone skeleton import, collision import/export |
| Editors | LOD distances, bounding volumes, jiggle bones, materials |

### Edit and inject

1. Import with Separate Primitives ON (Advanced > import options).
2. Edit in Blender: sculpt, UVs, vertex colors, weights. Games with rebuild
   support accept extrude/delete/join operations.
3. Press Inject. A patched copy appears next to the source file.

### Animation

Import the model first (armature created automatically). Advanced > Animation
> pick the .mab. Bones match by name hash. Avatar/FC2 cinematic scenes use the
Scene Viewer for cameras, anchors, and timeline markers.

### Custom materials (Avatar/FC2)

Set up materials on the imported mesh. Advanced > Export Custom Materials,
pick a template. The add-on bakes .xbt + .xbm files.

## Layout

```
__init__.py
modules/
  Core/              preferences, logging, settings
  UI/                game picker + per-game panels
  Avatar/            per-game modules, self-contained
  Far_Cry_1/  Far_Cry_2/  Far_Cry_3/  Far_Cry_4/  Far_Cry_5/
  Far_Cry_Primal/  Far_Cry_Instincts/  Far_Cry_6/ (WIP)
```

No cross-game imports. A fix in one game never breaks another.

## Credits

**Authors:** Selene0623, Quiet Joker

**Special thanks:** EncryptedStudios, Jasper_Zebra, legendhavoc175, qstlijku

**Original script:** Szkaradek123 (Blender 2.49b era, Avatar modding community)

## Contributing

Bug reports, broken files the importer doesn't handle, feature requests, and
pull requests all welcome.

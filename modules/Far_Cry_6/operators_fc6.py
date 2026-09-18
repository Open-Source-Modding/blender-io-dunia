"""Far Cry 6 — operators (import).

Self-contained: every import below resolves inside the Far_Cry_6 folder or
shared infra — no cross-game imports.
"""
import os

import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper

from ..Core.debug import VerboseLogger as vlog
from . import import_xbg_fc6


class XBG_OT_ImportFC6(bpy.types.Operator, ImportHelper):
    """Import a Far Cry 6 .xbg model"""
    bl_idname = "import_scene.xbg_fc6"
    bl_label = "Far Cry 6 Importer (.xbg)"
    bl_description = "Import a Far Cry 6 compiled XBG mesh file"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".xbg"
    filter_glob: StringProperty(default="*.xbg", options={'HIDDEN'})

    import_lod: EnumProperty(
        name="LOD",
        description="Which LOD to import",
        items=[
            ('0', "LOD0 (highest detail)", "Import the highest detail LOD"),
            ('ALL', "All LODs", "Import all LODs as separate objects"),
        ],
        default='0',
    )

    mesh_scale: bpy.props.FloatProperty(
        name="Scale",
        description="Import scale factor",
        default=1.0, min=0.001, max=1000.0,
    )

    def execute(self, context):
        return import_fc6_model(context, self.filepath, self.import_lod, self.mesh_scale)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def import_fc6_model(context, filepath, import_lod='0', mesh_scale=1.0):
    """Import an FC6 XBG file into Blender."""
    import math
    from mathutils import Vector, Matrix

    vlog.reset()
    vlog.log(f"FC6 XBG Import: {os.path.basename(filepath)}")

    try:
        result = import_xbg_fc6.parse_fc6(filepath)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return {'CANCELLED'}

    vlog.log(f"  Version: 0x{result['version']:08x}")
    vlog.log(f"  Materials: {len(result['materials'])}")
    vlog.log(f"  Bones: {len(result['bones'])}")
    vlog.log(f"  LODs: {len(result['lods'])}")

    # Pick LODs to import
    lods = result['lods']
    if import_lod == '0' and lods:
        lods = [lods[0]]

    if not lods:
        vlog.log("  No LODs to import")
        return {'CANCELLED'}

    created_objects = []

    for lod_idx, lod in enumerate(lods):
        vbc = lod['vbc']
        vbs = lod['vbs']
        lod_dist = lod['dist']

        vlog.log(f"\n  LOD[{lod_idx}] dist={lod_dist:.2f} vbc={vbc}")

        # Collect all vertices, UVs, normals, faces across VBs
        positions = []
        uvs = []
        normals = []
        faces = []
        vert_offset = 0

        for vb in vbs:
            flag = vb['flag']
            stride = vb['stride']
            verts = vb.get('verts', [])
            vb_faces = vb.get('faces', [])

            vlog.log(f"    VB: flags=0x{flag:04x} stride={stride} vcount={len(verts)} faces={len(vb_faces)}")

            for v in verts:
                positions.append(v['p'])
                uvs.append(v.get('uv', (0, 0)))
                normals.append(v.get('n', (0, 0, 1)))

            # Offset face indices to be global across VBs
            for a, b, c in vb_faces:
                faces.append((a + vert_offset, b + vert_offset, c + vert_offset))

            vert_offset += len(verts)

        if not positions:
            vlog.log("  No vertices")
            continue

        # Create Blender mesh
        mesh_name = f"{os.path.splitext(os.path.basename(filepath))[0]}_LOD{lod_idx}"
        mesh = bpy.data.meshes.new(mesh_name)
        mesh.from_pydata(positions, [], faces)
        mesh.update()

        obj = bpy.data.objects.new(mesh_name, mesh)
        context.collection.objects.link(obj)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # Set scale
        obj.scale = (mesh_scale, mesh_scale, mesh_scale)

        created_objects.append(obj)
        vlog.log(f"  Created: {mesh_name} ({len(positions)} verts)")

    # Build armature if bones present
    if result['bones'] and created_objects:
        arm_name = f"{os.path.splitext(os.path.basename(filepath))[0]}_armature"
        arm_data = bpy.data.armatures.new(arm_name)
        arm_obj = bpy.data.objects.new(arm_name, arm_data)
        context.collection.objects.link(arm_obj)

        # Parent all imported objects to armature
        for obj in created_objects:
            obj.parent = arm_obj

        vlog.log(f"\n  Armature: {arm_name} ({len(result['bones'])} bones)")

    vlog.log(f"\nImport complete: {len(created_objects)} object(s)")
    return {'FINISHED'}


classes = (
    XBG_OT_ImportFC6,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


def menu_func_import(self, context):
    self.layout.operator(XBG_OT_ImportFC6.bl_idname, text="Far Cry 6 Model (.xbg)")

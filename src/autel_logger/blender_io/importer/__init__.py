_needs_reload = "bpy" in locals()

import bpy

from . import props, operators, ui
if _needs_reload:
    import importlib
    importlib.reload(props)
    importlib.reload(operators)
    importlib.reload(ui)


bl_info = {
    "name": "Autel Flight Log Importer",
    "author": "Matt Reid",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "File > Import > Autel Flight Log (.json)",
    "description": "Import Autel flight log data and visualize in 3D view",
    "warning": "",
    "wiki_url": "",
    "category": "Import-Export",
}





def is_registered() -> bool:
    op_name = operators.IMPORT_SCENE_OT_autel_flight_log.bl_idname.split('.')[-1]
    return hasattr(bpy.ops.import_scene, op_name)


def register() -> None:
    props.register_classes()
    operators.register_classes()
    ui.register_classes()


def unregister() -> None:
    try:
        ui.unregister_classes()
        operators.unregister_classes()
        props.unregister_classes()
    except Exception as e:
        print(f"Error during unregister: {e}")


if __name__ == "__main__":
    if is_registered():
        unregister()
    register()

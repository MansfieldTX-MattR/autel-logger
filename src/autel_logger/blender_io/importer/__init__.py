
import bpy


from .props import (
    FlightProperties, TrackItemProperties, VideoItemProperties, FlightPathVertexProperties,
)
from .operators import (
    IMPORT_SCENE_OT_autel_flight_log,
    SCENE_OT_autel_flight_log_update_animation,
    SCENE_OT_autel_flight_log_next_item,
    SCENE_OT_autel_flight_log_prev_item,
    SCENE_OT_autel_flight_log_next_video_item,
    SCENE_OT_autel_flight_log_prev_video_item,
)
from .ui import OBJECT_PT_flight_log_panel

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


def menu_func_import(self, context: bpy.types.Context) -> None:
    self.layout.operator(IMPORT_SCENE_OT_autel_flight_log.bl_idname, text="Autel Flight Log (.json)")



def is_registered() -> bool:
    op_name = IMPORT_SCENE_OT_autel_flight_log.bl_idname.split('.')[-1]
    return hasattr(bpy.ops.import_scene, op_name)


def register() -> None:
    FlightPathVertexProperties._register_cls()
    TrackItemProperties._register_cls()
    VideoItemProperties._register_cls()
    FlightProperties._register_cls()
    IMPORT_SCENE_OT_autel_flight_log._register_cls()
    SCENE_OT_autel_flight_log_update_animation._register_cls()
    SCENE_OT_autel_flight_log_next_item._register_cls()
    SCENE_OT_autel_flight_log_prev_item._register_cls()
    SCENE_OT_autel_flight_log_next_video_item._register_cls()
    SCENE_OT_autel_flight_log_prev_video_item._register_cls()
    OBJECT_PT_flight_log_panel._register_cls()
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    try:
        OBJECT_PT_flight_log_panel._unregister_cls()
        SCENE_OT_autel_flight_log_update_animation._unregister_cls()
        IMPORT_SCENE_OT_autel_flight_log._unregister_cls()
        FlightProperties._unregister_cls()
        TrackItemProperties._unregister_cls()
        VideoItemProperties._unregister_cls()
        FlightPathVertexProperties._unregister_cls()
        SCENE_OT_autel_flight_log_next_item._unregister_cls()
        SCENE_OT_autel_flight_log_prev_item._unregister_cls()
        SCENE_OT_autel_flight_log_next_video_item._unregister_cls()
        SCENE_OT_autel_flight_log_prev_video_item._unregister_cls()
    except Exception as e:
        print(f"Error during unregister: {e}")


if __name__ == "__main__":
    if is_registered():
        unregister()
    register()

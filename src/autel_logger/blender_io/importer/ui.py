from __future__ import annotations
from typing import TYPE_CHECKING

import bpy
from bl_ui.generic_ui_list import draw_ui_list

if TYPE_CHECKING:
    from ..types import *

from .props import FlightProperties
from .operators import (
    IMPORT_SCENE_OT_autel_flight_log,
    SCENE_OT_autel_flight_log_update_animation,
    SCENE_OT_autel_flight_log_next_item,
    SCENE_OT_autel_flight_log_prev_item,
    SCENE_OT_autel_flight_log_next_video_item,
    SCENE_OT_autel_flight_log_prev_video_item,
    SCENE_OT_autel_flight_log_import_video,
)


class OBJECT_PT_flight_log_panel(bpy.types.Panel):
    """Panel to display flight log information"""
    bl_label = "Autel Flight Log"
    bl_idname = "OBJECT_PT_flight_log_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Autel'

    def draw(self, context: bpy.types.Context) -> None:
        assert self.layout is not None
        scene = context.scene
        assert scene is not None
        layout = self.layout
        box = layout.box()
        box.label(text="Import Flight Log:")
        box.operator(IMPORT_SCENE_OT_autel_flight_log.bl_idname)
        box = layout.box()
        box.label(text="Update Animation Keyframes:")
        box.operator(SCENE_OT_autel_flight_log_update_animation.bl_idname)
        box = layout.box()
        box.label(text="Select Flight Log:")
        draw_ui_list(
            box,
            context,
            list_path="scene.autel_flight_logs",
            active_index_path="scene.autel_flight_logs_index",
            unique_id="SCENE_UL_autel_flight_logs",
        )
        selected_flight = FlightProperties.get_selected_flight(context)
        if selected_flight is None:
            pass
        else:
            box = layout.box()
            box.label(text=f"Flight: {selected_flight.name}")
            box.prop(selected_flight, "start_time")
            box.prop(selected_flight, "start_latitude")
            box.prop(selected_flight, "start_longitude")
            box.prop(selected_flight, "duration")
            box.prop(selected_flight, "distance")
            box.prop(selected_flight, "max_altitude")


class OBJECT_PT_flight_log_video_panel(bpy.types.Panel):
    """Panel to display flight log video information"""
    bl_label = "Flight Log Video"
    bl_idname = "OBJECT_PT_flight_log_video_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Autel'

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        scene = context.scene
        if scene is None or layout is None:
            return
        selected_flight = FlightProperties.get_selected_flight(context)
        if selected_flight is None:
            return
        box = layout.box()
        box.label(text="Selected Video Item:")
        row = box.row()
        row.operator(SCENE_OT_autel_flight_log_prev_video_item.bl_idname, text="Previous")
        row.operator(SCENE_OT_autel_flight_log_next_video_item.bl_idname, text="Next")
        video_item = selected_flight.get_current_video_item(context)
        if video_item is None:
            return
        box.separator()
        box.prop(video_item, "src_filename")
        box.prop(video_item, "filename")
        box.prop(video_item, "image_object")
        box.prop(video_item, "start_time")
        box.prop(video_item, "end_time")
        box.prop(video_item, "duration")
        box.prop(video_item, "frame_rate")
        box.prop(video_item, "exists_locally")
        box.prop(video_item, "latitude")
        box.prop(video_item, "longitude")
        box.prop(video_item, "start_frame")
        box.prop(video_item, "end_frame")
        box.prop(video_item, "current_frame")
        box.operator(SCENE_OT_autel_flight_log_import_video.bl_idname, text="Import Video")


class OBJECT_PT_flight_log_track_panel(bpy.types.Panel):
    """Panel to display flight log track information"""
    bl_label = "Flight Log Track"
    bl_idname = "OBJECT_PT_flight_log_track_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Autel'

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        scene = context.scene
        if scene is None or layout is None:
            return
        selected_flight = FlightProperties.get_selected_flight(context)
        if selected_flight is None:
            return
        item = selected_flight.get_current_track_item(context)
        box = layout.box()
        box.label(text="Selected Track Item:")
        row = box.row()
        row.operator(SCENE_OT_autel_flight_log_prev_item.bl_idname, text="Previous")
        row.operator(SCENE_OT_autel_flight_log_next_item.bl_idname, text="Next")
        if item is None:
            return
        box.separator()
        box.prop(item, "index")
        box.prop(item, "scene_time")
        box.prop(item, "latitude")
        box.prop(item, "longitude")
        box.prop(item, "altitude")
        box.prop(item, "drone_orientation")
        box.prop(item, "gimbal_orientation")
        box.prop(item, "gimbal_orientation_relative")
        box.prop(item, "speed")
        box.prop(item, "relative_location")
        box.prop(item, "relative_height")
        box.prop(item, "distance")



def register_classes() -> None:
    bpy.utils.register_class(OBJECT_PT_flight_log_panel)
    bpy.utils.register_class(OBJECT_PT_flight_log_video_panel)
    bpy.utils.register_class(OBJECT_PT_flight_log_track_panel)


def unregister_classes() -> None:
    bpy.utils.unregister_class(OBJECT_PT_flight_log_panel)
    bpy.utils.unregister_class(OBJECT_PT_flight_log_video_panel)
    bpy.utils.unregister_class(OBJECT_PT_flight_log_track_panel)

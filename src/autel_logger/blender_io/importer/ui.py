from __future__ import annotations
from typing import Self, Literal, Iterable, TYPE_CHECKING, cast, overload
import json
import datetime
from pathlib import Path
import math

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
        # layout.template_list(
        #     "SCENE_UL_autel_flight_logs",
        #     "",
        #     scene,
        #     "autel_flight_logs",
        #     scene,
        #     "autel_flight_logs_index",
        #     rows=3,
        # )
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
        # flight_logs = scene.autel_flight_logs # type: ignore[attr-defined]
        selected_flight_name = scene.autel_flight_logs_selected_name # type: ignore[assigned]
        selected_flight = FlightProperties.get_flight_by_name(context, selected_flight_name) if selected_flight_name else None
        # selected_flight = scene.autel_flight_log_selected_item # type: ignore[assigned]
        if selected_flight is None:
            pass
        #     layout.template_list(
        #         "SCENE_UL_autel_flight_logs",
        #         "",
        #         scene,
        #         "autel_flight_logs",
        #         scene,
        #         "autel_flight_logs_index",
        #         rows=3,
        #     )
        #     # if len(flight_logs) == 0:
        #     #     layout.label(text="No flight logs imported")
        #     # else:
        #     #     layout.label(text="Select a flight log:")
        #     #     for flight in flight_logs:
        #     #         op = layout.operator(IMPORT_SCENE_OT_autel_flight_log.bl_idname, text=flight.name)
        #     #         op.filepath = flight.name  # type: ignore[attr-defined]
        else:
            box = layout.box()
            box.label(text=f"Flight: {selected_flight.name}")
            box.prop(selected_flight, "start_time")
            box.prop(selected_flight, "start_latitude")
            box.prop(selected_flight, "start_longitude")
            box.prop(selected_flight, "duration")
            box.prop(selected_flight, "distance")
            box.prop(selected_flight, "max_altitude")
            # box.label(text="Track Items:")
            # row = layout.row()
            # row.template_list(
            #     "UI_UL_list",
            #     "track_items",
            #     selected_flight,
            #     "track_items",
            #     selected_flight,
            #     "track_items_index",
            #     rows=3,
            # )
            box = layout.box()
            box.label(text="Current Video Item:")
            row = box.row()
            row.operator(SCENE_OT_autel_flight_log_prev_video_item.bl_idname, text="Previous")
            row.operator(SCENE_OT_autel_flight_log_next_video_item.bl_idname, text="Next")
            video_item = selected_flight.get_current_video_item(context)
            if video_item is not None:
                box.prop(video_item, "src_filename")
                box.prop(video_item, "filename")
                box.prop(video_item, "start_time")
                box.prop(video_item, "end_time")
                box.prop(video_item, "duration")
                box.prop(video_item, "latitude")
                box.prop(video_item, "longitude")
                box.prop(video_item, "start_frame")
                box.prop(video_item, "end_frame")
                box.prop(video_item, "current_frame")
                # row = box.row()
                # row.label(text='Current Frame:')
                # cur_frame = video_item.get_current_frame(context)
                # # cur_frame = context.scene.frame_current
                # row.label(text=f'{cur_frame}')
            item = selected_flight.get_current_track_item(context)
            box = layout.box()
            box.label(text="Selected Track Item:")
            row = box.row()
            row.operator(SCENE_OT_autel_flight_log_prev_item.bl_idname, text="Previous")
            row.operator(SCENE_OT_autel_flight_log_next_item.bl_idname, text="Next")
            if item is not None:
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

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)

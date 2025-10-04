from __future__ import annotations
from typing import Literal, TYPE_CHECKING
import json
from pathlib import Path
import math

import bpy

if TYPE_CHECKING:
    from ..types import *

from .props import (
    FlightProperties, CAMERA_FOCAL_LENGTH, CAMERA_SENSOR_WIDTH,
)



def animate_objects(
    flight_props: FlightProperties,
    context: bpy.types.Context,
    initial: bool,
) -> None:
    def set_active_object(obj: bpy.types.Object) -> None:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        assert context.view_layer is not None
        context.view_layer.objects.active = obj
    def clear_all_keyframes(obj: bpy.types.Object) -> None:
        if obj.animation_data is not None and obj.animation_data.action is not None:
            obj.animation_data_clear()

    scene = context.scene
    assert scene is not None
    current_frame = scene.frame_current
    scene.frame_start = 1
    scene.frame_end = max((item.frame for item in flight_props.track_items), default=1)
    drone_obj = flight_props.drone_object
    gimbal_obj = flight_props.gimbal_object
    assert drone_obj is not None
    assert gimbal_obj is not None
    if not initial:
        clear_all_keyframes(flight_props.drone_object)
        clear_all_keyframes(flight_props.gimbal_object)
    try:
        for item in flight_props.track_items:
            frame = item.frame
            scene.frame_set(frame=int(frame), subframe=frame % 1)
            if item.has_location:
                drone_obj.location.x = item.relative_location[0]
                drone_obj.location.y = item.relative_location[1]
                gimbal_obj.location.x = item.relative_location[0]
                gimbal_obj.location.y = item.relative_location[1]
                drone_obj.location.z = item.relative_height
                gimbal_obj.location.z = item.relative_height
            drone_obj.rotation_euler = item.drone_orientation
            gimbal_obj.rotation_euler = item.gimbal_orientation
            set_active_object(drone_obj)
            if item.has_location:
                bpy.ops.anim.keyframe_insert(type='Location')
            bpy.ops.anim.keyframe_insert(type='Rotation')
            set_active_object(gimbal_obj)
            if item.has_location:
                bpy.ops.anim.keyframe_insert(type='Location')
            bpy.ops.anim.keyframe_insert(type='Rotation')
    finally:
        scene.frame_set(current_frame)


def next_prev_item_helper(context: bpy.types.Context, item_type: Literal['TRACK', 'VIDEO'], direction: Literal['NEXT', 'PREV']) -> set[str]:
    selected_flight_name = context.scene.autel_flight_logs_selected_name # type: ignore[assigned]
    selected_flight = FlightProperties.get_flight_by_name(context, selected_flight_name)
    if selected_flight is None:
        return {'CANCELLED'}
    if item_type == 'TRACK':
        if direction == 'NEXT':
            item = selected_flight.get_next_track_item(context)
        else:
            item = selected_flight.get_previous_track_item(context)
        frame = item.frame if item is not None else None
    else:
        if direction == 'NEXT':
            item = selected_flight.get_next_video_item(context)
        else:
            item = selected_flight.get_previous_video_item(context)
        frame = item.get_start_frame(context) if item is not None else None
        if frame is not None:
            frame = math.ceil(frame)
    if item is None:
        return {'CANCELLED'}
    if context.scene is not None and frame is not None:
        context.scene.frame_set(frame=frame)
        return {'FINISHED'}
    return {'CANCELLED'}


class SCENE_OT_autel_flight_log_next_item(bpy.types.Operator):
    """Go to the next track item in the selected flight log"""
    bl_idname = "scene.autel_flight_log_next_item"
    bl_label = "Next Track Item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        scene = context.scene
        if scene is None:
            return False
        selected_flight_name = scene.autel_flight_logs_selected_name # type: ignore[assigned]
        selected_flight = FlightProperties.get_flight_by_name(context, selected_flight_name)
        return selected_flight is not None

    def execute(self, context: bpy.types.Context) -> set[str]:
        return next_prev_item_helper(context, 'TRACK', 'NEXT')

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)

class SCENE_OT_autel_flight_log_prev_item(bpy.types.Operator):
    """Go to the previous track item in the selected flight log"""
    bl_idname = "scene.autel_flight_log_prev_item"
    bl_label = "Previous Track Item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        scene = context.scene
        if scene is None:
            return False
        selected_flight_name = scene.autel_flight_logs_selected_name # type: ignore[assigned]
        selected_flight = FlightProperties.get_flight_by_name(context, selected_flight_name)
        return selected_flight is not None

    def execute(self, context: bpy.types.Context) -> set[str]:
        return next_prev_item_helper(context, 'TRACK', 'PREV')

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)


class SCENE_OT_autel_flight_log_next_video_item(bpy.types.Operator):
    """Go to the next video item in the selected flight log"""
    bl_idname = "scene.autel_flight_log_next_video_item"
    bl_label = "Next Video Item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        scene = context.scene
        if scene is None:
            return False
        selected_flight_name = scene.autel_flight_logs_selected_name # type: ignore[assigned]
        selected_flight = FlightProperties.get_flight_by_name(context, selected_flight_name)
        return selected_flight is not None

    def execute(self, context: bpy.types.Context) -> set[str]:
        return next_prev_item_helper(context, 'VIDEO', 'NEXT')

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)


class SCENE_OT_autel_flight_log_prev_video_item(bpy.types.Operator):
    """Go to the previous video item in the selected flight log"""
    bl_idname = "scene.autel_flight_log_prev_video_item"
    bl_label = "Previous Video Item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        scene = context.scene
        if scene is None:
            return False
        selected_flight_name = scene.autel_flight_logs_selected_name # type: ignore[assigned]
        selected_flight = FlightProperties.get_flight_by_name(context, selected_flight_name)
        return selected_flight is not None

    def execute(self, context: bpy.types.Context) -> set[str]:
        return next_prev_item_helper(context, 'VIDEO', 'PREV')

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)



class SCENE_OT_autel_flight_log_update_animation(bpy.types.Operator):
    """Update flight log animation keyframes"""
    bl_idname = "scene.autel_flight_log_update_animation"
    bl_label = "Update Flight Log Animation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        scene = context.scene
        if scene is None:
            return False
        selected_flight_name = scene.autel_flight_logs_selected_name # type: ignore[assigned]
        selected_flight = FlightProperties.get_flight_by_name(context, selected_flight_name)
        return selected_flight is not None

    def execute(self, context: bpy.types.Context) -> set[str]:
        selected_flight_name = context.scene.autel_flight_logs_selected_name # type: ignore[assigned]
        selected_flight = FlightProperties.get_flight_by_name(context, selected_flight_name)
        if selected_flight is None:
            self.report({'WARNING'}, "No flight log selected")
            return {'CANCELLED'}
        selected_flight.update_item_times(context)
        animate_objects(selected_flight, context, initial=False)
        self.report({'INFO'}, f"Updated animation for flight log: {selected_flight.name}")
        return {'FINISHED'}

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)



class IMPORT_SCENE_OT_autel_flight_log(bpy.types.Operator):
    """Import flight log data into Blender"""
    bl_idname = "import_scene.autel_flight_log"
    bl_label = "Import Autel Flight Log"
    bl_options = {'REGISTER', 'UNDO'}

    if TYPE_CHECKING:
        filepath: str
    else:
        filepath: bpy.props.StringProperty(
            name="File Path",
            description="Filepath used for importing the flight log file",
            maxlen=1024,
            subtype='FILE_PATH',
        )

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)

    def _get_fps(self, ctx: bpy.types.Context) -> int:
        assert ctx.scene is not None
        return ctx.scene.render.fps

    def _get_scene(self, ctx: bpy.types.Context) -> bpy.types.Scene:
        assert ctx.scene is not None
        return ctx.scene

    def execute(self, context: bpy.types.Context) -> set[str]:
        p = Path(self.filepath)
        s = p.read_text()
        data: BlExportData = json.loads(s)
        flight_props = FlightProperties.import_from_data(context, data)
        scene = self._get_scene(context)
        scene.frame_start = 1
        scene.frame_end = int(data['duration'] * self._get_fps(context)) + 1
        parent_object = self._create_object('EMPTY', f'Flight_{flight_props.name}_Parent')
        flight_path = self.build_flight_path(data['flight_path'], context, parent_object)
        drone_empty = self._create_object('EMPTY', 'Drone_Empty')
        drone_empty.empty_display_type = 'ARROWS'
        drone_empty.parent = parent_object
        gimbal_empty = self._create_object('EMPTY', 'Gimbal_Empty')
        gimbal_empty.empty_display_type = 'ARROWS'
        gimbal_empty.parent = parent_object
        self._setup_camera(gimbal_empty, context)
        flight_props.parent_object = parent_object
        flight_props.drone_object = drone_empty
        flight_props.gimbal_object = gimbal_empty
        flight_props.flight_path_object = flight_path
        bpy.ops.scene.autel_flight_log_update_animation() # type: ignore[attr-defined]
        return {'FINISHED'}

    def _setup_camera(self, gimbal_empty: bpy.types.Object, context: bpy.types.Context) -> bpy.types.Object:
        camera = self._create_object('CAMERA', 'Drone_Camera')#, parent=gimbal_empty)
        assert isinstance(camera.data, bpy.types.Camera)
        camera.data.lens = CAMERA_FOCAL_LENGTH
        camera.data.sensor_width = CAMERA_SENSOR_WIDTH
        camera.data.sensor_fit = 'HORIZONTAL'
        camera.rotation_euler = (math.radians(90), 0, 0)
        bpy.ops.object.constraint_add(type='COPY_LOCATION')
        loc_constraint = camera.constraints['Copy Location']
        assert isinstance(loc_constraint, bpy.types.CopyLocationConstraint)
        loc_constraint.target = gimbal_empty
        bpy.ops.object.constraint_add(type='COPY_ROTATION')
        rot_constraint = camera.constraints['Copy Rotation']
        assert isinstance(rot_constraint, bpy.types.CopyRotationConstraint)
        rot_constraint.target = gimbal_empty
        # rot_constraint.invert_x = True
        # rot_constraint.invert_z = True
        rot_constraint.mix_mode = 'ADD'
        return camera

    def build_flight_path(self, data: BlObjectWithVerticesData, context: bpy.types.Context, parent: bpy.types.Object) -> bpy.types.Object:
        bpy.ops.curve.primitive_bezier_curve_add()
        obj = context.active_object
        assert obj is not None
        assert obj.type == 'CURVE'
        obj.parent = parent
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.curve.delete(type='VERT')
        # bpy.ops.curve.vertex_add(location=(0, 0, 0))
        for vert in data['vertices']:
            bpy.ops.curve.vertex_add(location=vert)
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.name = data['name']
        assert obj.data is not None
        obj.data.name = data['name']
        return obj

    def _create_object(self, obj_type: BlObjectType, name: str, parent: bpy.types.Object|None = None) -> bpy.types.Object:
        if obj_type == 'MESH':
            bpy.ops.mesh.primitive_cube_add()
        elif obj_type == 'EMPTY':
            bpy.ops.object.empty_add(type='PLAIN_AXES')
        elif obj_type == 'CAMERA':
            bpy.ops.object.camera_add()
        else:
            raise ValueError(f"Unsupported object type: {obj_type}")
        obj = bpy.context.active_object
        assert obj is not None
        assert obj.type == obj_type
        if parent is not None:
            obj.parent = parent
        obj.name = name
        if obj_type != 'EMPTY':
            assert obj.data is not None
            obj.data.name = name
        return obj

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        assert context is not None
        assert context.window_manager is not None
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

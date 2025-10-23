from __future__ import annotations
from typing import Literal, TYPE_CHECKING
import json
from pathlib import Path
import math

import bpy

if TYPE_CHECKING:
    from ..types import *

from .props import (
    FlightProperties, VideoItemProperties, FlightPathVertexProperties,
    FlightStickProperties,
    CAMERA_FOCAL_LENGTH, CAMERA_SENSOR_WIDTH,
)



def animate_objects(
    flight_props: FlightProperties,
    context: bpy.types.Context,
    initial: bool,
) -> None:
    def clear_all_keyframes(obj: bpy.types.Object) -> None:
        if obj.animation_data is not None and obj.animation_data.action is not None:
            obj.animation_data_clear()

    scene = context.scene
    assert scene is not None
    current_frame = scene.frame_current
    scene.frame_start = 0
    scene.frame_end = max((item.frame for item in flight_props.track_items), default=1)
    drone_obj = flight_props.drone_object
    gimbal_obj = flight_props.gimbal_object
    left_stick_obj = flight_props.left_stick
    right_stick_obj = flight_props.right_stick
    assert drone_obj is not None
    assert gimbal_obj is not None
    assert left_stick_obj is not None
    assert right_stick_obj is not None
    if not initial:
        clear_all_keyframes(flight_props.drone_object)
        clear_all_keyframes(flight_props.gimbal_object)
        clear_all_keyframes(flight_props.left_stick)
        clear_all_keyframes(flight_props.right_stick)
    left_stick_props = FlightStickProperties.get_from_object(left_stick_obj)
    right_stick_props = FlightStickProperties.get_from_object(right_stick_obj)
    try:
        for item in flight_props.track_items:
            frame = item.frame
            if item.has_location:
                drone_obj.location.x = item.relative_location[0]
                drone_obj.location.y = item.relative_location[1]
                gimbal_obj.location.x = item.relative_location[0]
                gimbal_obj.location.y = item.relative_location[1]
                drone_obj.location.z = item.relative_height
                gimbal_obj.location.z = item.relative_height
            drone_obj.rotation_euler = item.drone_orientation
            gimbal_obj.rotation_euler = item.gimbal_orientation
            left_prop = left_stick_props[item.name]
            right_prop = right_stick_props[item.name]
            left_stick_obj.delta_location.x = left_prop.position[0]
            left_stick_obj.delta_location.y = left_prop.position[1]
            right_stick_obj.delta_location.x = right_prop.position[0]
            right_stick_obj.delta_location.y = right_prop.position[1]

            if item.has_location:
                drone_obj.keyframe_insert('location', frame=frame)
            drone_obj.keyframe_insert('rotation_euler', frame=frame)
            if item.has_location:
                gimbal_obj.keyframe_insert('location', frame=frame)
            gimbal_obj.keyframe_insert('rotation_euler', frame=frame)
            left_stick_obj.keyframe_insert('delta_location', index=-1, frame=frame)
            right_stick_obj.keyframe_insert('delta_location', index=-1, frame=frame)
    finally:
        scene.frame_set(current_frame)


def next_prev_item_helper(context: bpy.types.Context, item_type: Literal['TRACK', 'VIDEO'], direction: Literal['NEXT', 'PREV']) -> set[str]:
    selected_flight = FlightProperties.get_selected_flight(context)
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
        selected_flight = FlightProperties.get_selected_flight(context)
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
        selected_flight = FlightProperties.get_selected_flight(context)
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
        selected_flight = FlightProperties.get_selected_flight(context)
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
        selected_flight = FlightProperties.get_selected_flight(context)
        return selected_flight is not None

    def execute(self, context: bpy.types.Context) -> set[str]:
        return next_prev_item_helper(context, 'VIDEO', 'PREV')

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)

class SCENE_OT_autel_flight_log_import_video(bpy.types.Operator):
    """Import video files for the selected flight log"""
    bl_idname = "scene.autel_flight_log_import_video"
    bl_label = "Import Flight Log Video"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        current_video, err_msg = cls._get_current_video(context)
        if current_video is None:
            return False
        if not current_video.exists_locally:
            return False
        if current_video.image_object is not None:
            return False
        return True

    @classmethod
    def _get_current_video(cls, context: bpy.types.Context) -> tuple[VideoItemProperties | None, str]:
        selected_flight = FlightProperties.get_selected_flight(context)
        if selected_flight is None:
            return None, "No flight log selected"
        current_video = selected_flight.get_current_video_item(context)
        if current_video is None:
            return None, "No video item at current frame"
        return current_video, ""

    @classmethod
    def _can_import_video(cls, context: bpy.types.Context, current_video: VideoItemProperties) -> tuple[bool, str]:
        if not current_video.exists_locally:
            return False, "Video item does not exist locally"
        if current_video.image_object is not None:
            return False, "Video item already has an image object"
        assert context.scene is not None
        if current_video.frame_rate != context.scene.render.fps:
            return False, "Video item frame rate does not match scene frame rate"
        video_path = Path(current_video.src_filename)
        if not video_path.exists():
            return False, f"Video file does not exist: {video_path}"
        scene = context.scene
        if scene is None:
            return False, "No active scene"
        if current_video.frame_rate != scene.render.fps:
            return False, "Video item frame rate does not match scene frame rate"
        return True, ""

    def execute(self, context: bpy.types.Context) -> set[str]:
        current_video, err_msg = self._get_current_video(context)
        if current_video is None:
            self.report({'WARNING'}, err_msg)
            return {'CANCELLED'}
        can_import, err_msg = self._can_import_video(context, current_video)
        if not can_import:
            self.report({'WARNING'}, err_msg)
            return {'CANCELLED'}
        video_path = Path(current_video.src_filename)
        assert video_path.exists()
        selected_flight = FlightProperties.get_selected_flight(context)
        assert selected_flight is not None
        try:
            image = bpy.data.images.load(filepath=str(video_path), check_existing=True)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load video file: {e}")
            return {'CANCELLED'}
        current_video.image_object = image
        self.report({'INFO'}, f"Imported video file: {video_path.name}")

        camera = selected_flight.camera_object
        if camera is None:
            self.report({'WARNING'}, "No camera object found in flight properties")
            return {'CANCELLED'}
        assert isinstance(camera.data, bpy.types.Camera)
        camera.data.show_background_images = True
        bg = camera.data.background_images.new()
        bg.image = image
        bg.display_depth = 'FRONT'
        bg.frame_method = 'CROP'
        bg.alpha = 0.5
        start_frame = current_video.get_start_frame(context)
        end_frame = current_video.get_end_frame(context)
        num_frames = end_frame - start_frame
        if num_frames <= 0:
            self.report({'WARNING'}, "Video item has invalid frame range")
            return {'CANCELLED'}
        bg.image_user.frame_start = int(round(start_frame))
        bg.image_user.frame_duration = int(round(num_frames))
        bg.image_user.frame_offset = 0
        return {'FINISHED'}

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
        selected_flight = FlightProperties.get_selected_flight(context)
        return selected_flight is not None

    def execute(self, context: bpy.types.Context) -> set[str]:
        selected_flight = FlightProperties.get_selected_flight(context)
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
        left_stick, right_stick = self._build_flight_controls_objects(context, parent_object)
        flight_props.left_stick = left_stick
        flight_props.right_stick = right_stick
        flight_props.add_flight_stick_data(context, data)
        drone_empty = self._create_object('EMPTY', 'Drone_Empty')
        drone_empty.empty_display_type = 'ARROWS'
        drone_empty.parent = parent_object
        gimbal_empty = self._create_object('EMPTY', 'Gimbal_Empty')
        gimbal_empty.empty_display_type = 'ARROWS'
        gimbal_empty.parent = parent_object
        camera = self._setup_camera(gimbal_empty, context)
        flight_props.parent_object = parent_object
        flight_props.drone_object = drone_empty
        flight_props.gimbal_object = gimbal_empty
        flight_props.flight_path_object = flight_path
        flight_props.camera_object = camera
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

    def build_flight_path(self, data: BlFlightPathData, context: bpy.types.Context, parent: bpy.types.Object) -> bpy.types.Object:
        bpy.ops.curve.primitive_bezier_curve_add()
        obj = context.active_object
        assert obj is not None
        assert obj.type == 'CURVE'
        assert isinstance(obj.data, bpy.types.Curve)
        obj.parent = parent
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.curve.delete(type='VERT')
        path_props = FlightPathVertexProperties.get_from_object(obj)
        assert len(path_props) == 0
        # bpy.ops.curve.vertex_add(location=(0, 0, 0))
        for i, vert in enumerate(data['vertices']):
            bpy.ops.curve.vertex_add(location=vert)
            prop = path_props.add()
            prop.vertex_index = i
            prop.flight_time = data['vertex_times'][i]
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.name = data['name']
        assert obj.data is not None
        obj.data.name = data['name']
        return obj

    def _build_flight_controls_objects(
        self,
        context: bpy.types.Context,
        parent: bpy.types.Object|None
    ) -> tuple[bpy.types.Object, bpy.types.Object]:
        stick_parent = self._create_object('EMPTY', 'Flight Controls', parent=parent)
        bpy.ops.mesh.primitive_circle_add(vertices=32, radius=1.0)
        left_stick_circle = context.active_object
        assert left_stick_circle is not None
        left_stick_circle.name = 'Left_Stick_Circle'
        left_stick_circle.parent = stick_parent
        circle_mesh = left_stick_circle.data
        assert circle_mesh is not None
        assert isinstance(circle_mesh, bpy.types.Mesh)
        right_stick_circle = left_stick_circle.copy()
        right_stick_circle.name = 'Right_Stick_Circle'

        left_stick = left_stick_circle.copy()
        left_stick.name = 'Left_Stick'
        left_stick.scale = (0.3, 0.3, 0.3)
        left_stick.location.z += 0.3

        right_stick = right_stick_circle.copy()
        right_stick.name = 'Right_Stick'
        right_stick.scale = (0.3, 0.3, 0.3)
        right_stick.location.z += 0.3

        assert context.collection is not None
        context.collection.objects.link(right_stick_circle)
        context.collection.objects.link(left_stick)
        context.collection.objects.link(right_stick)

        left_stick.parent = left_stick_circle
        right_stick.parent = right_stick_circle

        left_stick_circle.location.x = -2.0
        right_stick_circle.location.x = 2.0
        left_stick_circle.parent = stick_parent
        right_stick_circle.parent = stick_parent

        return left_stick, right_stick

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




def menu_func_import(self, context: bpy.types.Context) -> None:
    self.layout.operator(IMPORT_SCENE_OT_autel_flight_log.bl_idname, text="Autel Flight Log (.json)")


def register_classes() -> None:
    IMPORT_SCENE_OT_autel_flight_log._register_cls()
    SCENE_OT_autel_flight_log_update_animation._register_cls()
    SCENE_OT_autel_flight_log_next_item._register_cls()
    SCENE_OT_autel_flight_log_prev_item._register_cls()
    SCENE_OT_autel_flight_log_next_video_item._register_cls()
    SCENE_OT_autel_flight_log_prev_video_item._register_cls()
    SCENE_OT_autel_flight_log_import_video._register_cls()
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister_classes() -> None:
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    SCENE_OT_autel_flight_log_update_animation._unregister_cls()
    IMPORT_SCENE_OT_autel_flight_log._unregister_cls()
    SCENE_OT_autel_flight_log_next_item._unregister_cls()
    SCENE_OT_autel_flight_log_prev_item._unregister_cls()
    SCENE_OT_autel_flight_log_next_video_item._unregister_cls()
    SCENE_OT_autel_flight_log_prev_video_item._unregister_cls()
    SCENE_OT_autel_flight_log_import_video._unregister_cls()

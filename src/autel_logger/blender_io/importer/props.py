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



CAMERA_FOCAL_LENGTH = 10.57  # mm, Autel EVO II Pro
CAMERA_SENSOR_WIDTH = 13.2  # mm, Autel EVO II Pro
CAMERA_SENSOR_HEIGHT = 8.8  # mm, Autel EVO II Pro
CAMERA_ASPECT_RATIO = CAMERA_SENSOR_WIDTH / CAMERA_SENSOR_HEIGHT
CAMERA_FOV = 2 * math.degrees(math.atan((CAMERA_SENSOR_WIDTH / 2) / CAMERA_FOCAL_LENGTH))  # degrees, horizontal FOV



# class LatLonProp(bpy.types.PropertyGroup):
#     latitude: bpy.props.FloatProperty(
#         name="Latitude",
#         description="Latitude in decimal degrees",
#         default=0.0,
#     )
#     longitude: bpy.props.FloatProperty(
#         name="Longitude",
#         description="Longitude in decimal degrees",
#         default=0.0,
#     )

@overload
def timestamp_to_frame(timestamp: float|datetime.datetime, context: bpy.types.Context|None = None, as_int: Literal[False] = ...) -> float: ...
@overload
def timestamp_to_frame(timestamp: float|datetime.datetime, context: bpy.types.Context|None = None, as_int: Literal[True] = ...) -> int: ...
def timestamp_to_frame(timestamp: float|datetime.datetime, context: bpy.types.Context|None = None, as_int: bool = False) -> float|int:
    """Convert a UNIX timestamp to a Blender frame number."""
    if isinstance(timestamp, datetime.datetime):
        timestamp = timestamp.timestamp()
    if context is None or context.scene is None:
        fps, fps_base = None, None
    else:
        fps = context.scene.render.fps
        fps_base = context.scene.render.fps_base
    delta = bpy.utils.time_to_frame(timestamp, fps=fps, fps_base=fps_base)
    if isinstance(delta, datetime.timedelta):
        delta = delta.total_seconds()
    if as_int:
        return int(round(delta))
    return delta


def frame_to_timestamp(frame: int|float, context: bpy.types.Context|None = None) -> float:
    """Convert a Blender frame number to a UNIX timestamp."""
    if context is None or context.scene is None:
        fps, fps_base = None, None
    else:
        fps = context.scene.render.fps
        fps_base = context.scene.render.fps_base
    delta = bpy.utils.time_from_frame(frame, fps=fps, fps_base=fps_base)
    assert delta is not None
    if isinstance(delta, datetime.timedelta):
        return delta.total_seconds()
    return delta



class TrackItemProperties(bpy.types.PropertyGroup):
    index: bpy.props.IntProperty(
        name="Index",
        description="Index of the track item in the flight",
        default=0,
    ) # type: ignore[call-arg]
    # def _get_frame(self) -> int:
    #     return timestamp_to_frame(self.scene_time, as_int=True)
    frame: bpy.props.IntProperty(
        name="Frame",
        description="Frame number in the Blender timeline",
        default=0,
    ) # type: ignore[call-arg]
    scene_time: bpy.props.FloatProperty(
        name="Scene Time",
        description="Time offset from the start of the flight in seconds",
        subtype='TIME',
        unit='TIME',
        default=0.0,
    ) # type: ignore[call-arg]
    latitude: bpy.props.FloatProperty(
        name="Latitude",
        description="Latitude in decimal degrees",
        default=0.0,
        precision=6,
        min=-90.0,
        max=90.0,
    ) # type: ignore[call-arg]
    longitude: bpy.props.FloatProperty(
        name="Longitude",
        description="Longitude in decimal degrees",
        default=0.0,
        precision=6,
        min=-180.0,
        max=180.0,
    ) # type: ignore[call-arg]
    altitude: bpy.props.FloatProperty(
        name="Altitude",
        description="Altitude in meters",
        subtype='DISTANCE',
        unit='LENGTH',
        default=0.0,
    ) # type: ignore[call-arg]
    drone_orientation: bpy.props.FloatVectorProperty(
        name="Drone Orientation",
        description="Orientation of the drone as (pitch, roll, yaw) in degrees",
        size=3,
        default=(0.0, 0.0, 0.0),
        subtype='EULER',
        unit='ROTATION',
    ) # type: ignore[call-arg]
    gimbal_orientation: bpy.props.FloatVectorProperty(
        name="Gimbal Orientation",
        description="Orientation of the gimbal as (pitch, roll, yaw) in degrees",
        size=3,
        default=(0.0, 0.0, 0.0),
        subtype='EULER',
        unit='ROTATION',
    ) # type: ignore[call-arg]
    gimbal_orientation_relative: bpy.props.FloatVectorProperty(
        name="Gimbal Orientation Relative",
        description="Relative orientation of the gimbal as (pitch, roll, yaw) in degrees",
        size=3,
        default=(0.0, 0.0, 0.0),
        subtype='EULER',
        unit='ROTATION',
    ) # type: ignore[call-arg]
    speed: bpy.props.FloatVectorProperty(
        name="Speed",
        description="Speed in meters per second",
        unit='VELOCITY',
        size=3,
        default=(0.0, 0.0, 0.0),
    ) # type: ignore[call-arg]
    relative_location: bpy.props.FloatVectorProperty(
        name="Relative Location",
        description="Relative location from the start of the flight in meters (X, Y, Z)",
        size=2,
        default=(0.0, 0.0),
        subtype='TRANSLATION',
        unit='LENGTH',
    ) # type: ignore[call-arg]
    has_location: bpy.props.BoolProperty(
        name="Has Location",
        description="Whether the track item has a location",
        default=False,
    ) # type: ignore[call-arg]
    relative_height: bpy.props.FloatProperty(
        name="Relative Height",
        description="Relative height from the start of the flight in meters",
        subtype='DISTANCE',
        unit='LENGTH',
        default=0.0,
    ) # type: ignore[call-arg]
    distance: bpy.props.FloatProperty(
        name="Distance",
        description="Distance from the start of the flight in meters",
        subtype='DISTANCE',
        unit='LENGTH',
        default=0.0,
    ) # type: ignore[call-arg]

    def update_frame(self, context: bpy.types.Context) -> None:
        """Update the frame number based on the scene fps"""
        self.frame = timestamp_to_frame(self.scene_time, context, as_int=True)

    @classmethod
    def from_track_item_data(
        cls,
        item_data: BlTrackItemData,
        flight: FlightProperties,
        context: bpy.types.Context
    ) -> Self:
        item = flight.track_items.add()
        item = cast(Self, item)
        # item.index = data['index']
        # item.scene_time = data['time']
        # item.update_frame(context)
        # if data['location'] is not None:
        #     item.latitude = data['location']['latitude']
        #     item.longitude = data['location']['longitude']
        #     item.has_location = True
        # else:
        #     item.has_location = False
        # item.altitude = data['altitude']
        # item.drone_orientation = data['drone_orientation']
        # item.gimbal_orientation = data['gimbal_orientation']
        # item.gimbal_orientation_relative = data['gimbal_orientation_relative']
        # item.speed = data['speed']
        # rel_loc_xy = data['relative_location']
        # if rel_loc_xy is not None:
        #     item.relative_location = (rel_loc_xy[0], rel_loc_xy[1])
        #     item.has_location = True
        # else:
        #     item.has_location = False
        # # item.relative_location = data['relative_location']
        # item.relative_height = data['relative_height']
        # if data['distance'] is not None:
        #     item.distance = data['distance']

        item.index = item_data['index']
        item.update_frame(context)
        item.scene_time = item_data['time']
        if item_data['location'] is not None:
            item.latitude = item_data['location']['latitude']
            item.longitude = item_data['location']['longitude']
            item.has_location = True
        else:
            item.has_location = False
        item.altitude = item_data['altitude']
        item.drone_orientation = item_data['drone_orientation']
        item.gimbal_orientation = item_data['gimbal_orientation']
        item.gimbal_orientation_relative = item_data['gimbal_orientation_relative']
        item.speed = item_data['speed']
        rel_loc_xy = item_data['relative_location']
        if rel_loc_xy is not None:
            item.relative_location = (rel_loc_xy[0], rel_loc_xy[1])
            item.has_location = True
        else:
            item.has_location = False
        # item.relative_location = item_data['relative_location']
        item.relative_height = item_data['relative_height']
        if item_data['distance'] is not None:
            item.distance = item_data['distance']
        return item

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)


class VideoItemProperties(bpy.types.PropertyGroup):
    src_filename: bpy.props.StringProperty(
        name="Source Filename",
        description="Original filename of the video",
        default="",
    ) # type: ignore
    filename: bpy.props.StringProperty(
        name="Filename",
        description="Filename of the video",
        subtype='FILE_NAME',
        default="",
    ) # type: ignore
    start_time: bpy.props.FloatProperty(
        name="Start Time",
        description="Start time of the video in seconds",
        default=0.0,
    ) # type: ignore
    end_time: bpy.props.FloatProperty(
        name="End Time",
        description="End time of the video in seconds",
        default=0.0,
    ) # type: ignore[call-arg]
    duration: bpy.props.FloatProperty(
        name="Duration",
        description="Duration of the video in seconds",
        default=0.0,
    ) # type: ignore[call-arg]
    latitude: bpy.props.FloatProperty(
        name="Latitude",
        description="Latitude of the video location",
        default=0.0,
        precision=6,
        min=-90.0,
        max=90.0,
    ) # type: ignore[call-arg]
    longitude: bpy.props.FloatProperty(
        name="Longitude",
        description="Longitude of the video location",
        default=0.0,
        precision=6,
        min=-180.0,
        max=180.0,
    ) # type: ignore[call-arg]
    def _get_start_frame(self) -> int:
        context = bpy.context
        return int(round(self.get_start_frame(context)))
    def _get_end_frame(self) -> int:
        context = bpy.context
        return int(round(self.get_end_frame(context)))
    def _get_current_frame(self) -> int:
        context = bpy.context
        return int(round(self.get_current_frame(context)))
    # def _set_current_frame(self, value: int) -> None:
    #     pass
    start_frame: bpy.props.IntProperty(
        name="Start Frame",
        description="Start frame of the video",
        get=_get_start_frame,
        # set=_set_current_frame,
    ) # type: ignore[call-arg]
    end_frame: bpy.props.IntProperty(
        name="End Frame",
        description="End frame of the video",
        get=_get_end_frame,
    ) # type: ignore[call-arg]
    current_frame: bpy.props.IntProperty(
        name="Current Frame",
        description="Current frame of the video",
        get=_get_current_frame,
    ) # type: ignore[call-arg]
    # start_frame: bpy.props.IntProperty(
    #     name="Start Frame",
    #     description="Start frame of the video",
    #     default=0,
    # ) # type: ignore
    # end_frame: bpy.props.IntProperty(
    #     name="End Frame",
    #     description="End frame of the video",
    #     default=0,
    # ) # type: ignore
    def get_start_frame(self, context: bpy.types.Context) -> float:
        return timestamp_to_frame(self.start_time, context)
        # # fps = context.scene.render.fps if context.scene is not None else 24
        # # return int(self.start_time * fps) + 1
        # delta = bpy.utils.time_to_frame(self.start_time)
        # if isinstance(delta, datetime.timedelta):
        #     return delta.total_seconds()
        # return delta

    def get_end_frame(self, context: bpy.types.Context) -> float:
        return timestamp_to_frame(self.end_time, context)
        # # fps = context.scene.render.fps if context.scene is not None else 24
        # # return int(self.end_time * fps) + 1
        # delta = bpy.utils.time_to_frame(self.end_time)
        # if isinstance(delta, datetime.timedelta):
        #     return delta.total_seconds()
        # return delta

    def get_current_frame(self, context: bpy.types.Context) -> float:
        """Return the current video frame based on the scene frame."""
        if context.scene is None:
            return 0
        current_scene_time = frame_to_timestamp(context.scene.frame_current, context)
        # current_scene_time = bpy.utils.time_from_frame(context.scene.frame_current)
        # if isinstance(current_scene_time, datetime.timedelta):
        #     current_scene_time = current_scene_time.total_seconds()
        if current_scene_time < self.start_time:
            return 0
        if current_scene_time > self.end_time:
            return 0
        offset_time = current_scene_time - self.start_time
        # return bpy.utils.time_to_frame(offset_time)
        return timestamp_to_frame(offset_time, context)
        # if context.scene is None:
        #     return 0
        # scene_frame = context.scene.frame_current
        # start_frame = self.get_start_frame(context)
        # if scene_frame < start_frame:
        #     return -1
        # end_frame = self.get_end_frame(context)
        # if end_frame > scene_frame:
        #     return -1
        # return scene_frame - start_frame + 1

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)


class FlightProperties(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Flight Name",
        description="Name of the flight",
        default="",
    ) # type: ignore
    start_timestamp: bpy.props.FloatProperty(
        name="Start Timestamp",
        description="Start time of the flight as a UNIX timestamp",
        default=0.0,
    ) # type: ignore
    start_time: bpy.props.StringProperty(
        name="Start Time",
        description="Start time of the flight as an ISO 8601 string",
        default="",
    ) # type: ignore
    duration: bpy.props.FloatProperty(
        name="Duration",
        description="Duration of the flight in seconds",
        default=0.0,
    ) # type: ignore
    distance: bpy.props.FloatProperty(
        name="Distance",
        description="Total distance of the flight in meters",
        subtype='DISTANCE',
        unit='LENGTH',
        default=0.0,
    ) # type: ignore
    max_altitude: bpy.props.FloatProperty(
        name="Max Altitude",
        description="Maximum altitude reached during the flight in meters",
        subtype='DISTANCE',
        unit='LENGTH',
        default=0.0,
    ) # type: ignore
    start_latitude: bpy.props.FloatProperty(
        name="Start Latitude",
        description="Starting latitude of the flight",
        default=0.0,
        precision=6,
        min=-90.0,
        max=90.0,
    ) # type: ignore
    start_longitude: bpy.props.FloatProperty(
        name="Start Longitude",
        description="Starting longitude of the flight",
        default=0.0,
        precision=6,
        min=-180.0,
        max=180.0,
    ) # type: ignore
    track_items: bpy.props.CollectionProperty(
        type=TrackItemProperties,
        name="Track Items",
        description="Collection of track items in the flight",
    ) # type: ignore
    video_items: bpy.props.CollectionProperty(
        type=VideoItemProperties,
        name="Video Items",
        description="Collection of video items in the flight",
    ) # type: ignore
    # track_items_index: bpy.props.IntProperty(
    #     name="Track Items Index",
    #     description="Index of the active track item",
    #     default=0,
    # ) # type: ignore
    parent_object: bpy.props.PointerProperty(
        name="Parent Object",
        description="Blender object representing the parent of the flight",
        type=bpy.types.Object,
    ) # type: ignore
    drone_object: bpy.props.PointerProperty(
        name="Drone Object",
        description="Blender object representing the drone",
        type=bpy.types.Object,
    ) # type: ignore
    gimbal_object: bpy.props.PointerProperty(
        name="Gimbal Object",
        description="Blender object representing the gimbal",
        type=bpy.types.Object,
    ) # type: ignore
    flight_path_object: bpy.props.PointerProperty(
        name="Flight Path Object",
        description="Blender object representing the flight path",
        type=bpy.types.Object,
    ) # type: ignore

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)
        bpy.types.Scene.autel_flight_logs = bpy.props.CollectionProperty(type=cls) # type: ignore[assign]
        bpy.types.Scene.autel_flight_logs_index = bpy.props.IntProperty( # type: ignore[assign]
            name="Selected Flight Log Index",
            description="Index of the currently selected flight log",
            default=0,
        )
        def _get_selected_name(self) -> str:
            try:
                flight = self.autel_flight_logs[self.autel_flight_logs_index]
                return flight.name
            except IndexError:
                return ""

        bpy.types.Scene.autel_flight_logs_selected_name = bpy.props.StringProperty( # type: ignore[assign]
            name="Selected Flight Log Name",
            description="Name of the currently selected flight log",
            default="",
            get=_get_selected_name,
        )
        # bpy.types.Scene.autel_flight_log_selected_item = bpy.props.PointerProperty( # type: ignore[assign]
        #     name="Selected Flight Log",
        #     description="Currently selected flight log",
        #     type=cls,
        # )

    @classmethod
    def _unregister_cls(cls) -> None:
        del bpy.types.Scene.autel_flight_logs_selected_name # type: ignore[assign]
        del bpy.types.Scene.autel_flight_logs_index # type: ignore[assign]
        # del bpy.types.Scene.autel_flight_log_selected_item # type: ignore[assign]
        del bpy.types.Scene.autel_flight_logs # type: ignore[assign]
        bpy.utils.unregister_class(cls)

    @classmethod
    def get_flight_by_name(cls, context: bpy.types.Context, name: str) -> FlightProperties | None:
        for flight in context.scene.autel_flight_logs: # type: ignore[attr-defined]
            if flight.name == name:
                return flight
        return None

    @classmethod
    def flight_exists(cls, context: bpy.types.Context, name: str) -> bool:
        return cls.get_flight_by_name(context, name) is not None

    @classmethod
    def import_from_data(cls, context: bpy.types.Context, data: BlExportData) -> FlightProperties:
        stem = Path(data['filename']).stem
        name = stem
        name_suffix = ''
        i = 0
        while cls.flight_exists(context, name):
            if name_suffix != '':
                name_suffix = f'{i:03d}'
                name = f'{stem}.{name_suffix}'
            else:
                name_suffix = '001'
                name = f'{stem}.{name_suffix}'
            i += 1
            if i > 999:
                raise RuntimeError("Too many flights with the same name")
        assert context.scene is not None
        flight = context.scene.autel_flight_logs.add() # type: ignore[attr-defined]
        flight = cast(FlightProperties, flight)
        flight.name = name
        flight.start_timestamp = data['start_timestamp']
        flight.start_time = data['start_time']
        flight.duration = data['duration']
        flight.distance = data['distance']
        flight.max_altitude = data['max_altitude']
        flight.start_latitude = data['start_location']['latitude']
        flight.start_longitude = data['start_location']['longitude']
        for item_data in data['track_items']:
            flight.add_track_item(item_data, context)
        for item_data in data['video_items']:
            flight.add_video_item(item_data)
        # context.scene.autel_flight_logs_selected_name = flight.name # type: ignore[assigned]
        context.scene.autel_flight_logs_index = len(context.scene.autel_flight_logs) - 1 # type: ignore[assigned]
        # context.scene.autel_flight_log_selected_item = flight # type: ignore[assigned]
        return flight

    def add_track_item(self, item_data: BlTrackItemData, context: bpy.types.Context) -> TrackItemProperties:
        return TrackItemProperties.from_track_item_data(item_data, self, context)
        # # fps = context.scene.render.fps if context.scene is not None else 24
        # # item_data_frame = int(item_data['time'] * fps) + 1
        # item_data_frame = timestamp_to_frame(self.start_timestamp + item_data['time'], context, as_int=True)
        # item = self.track_items.add() # type: ignore[call-arg]
        # item = cast(TrackItemProperties, item)
        # item.index = item_data['index']
        # item.frame = item_data_frame
        # item.scene_time = item_data['time']
        # if item_data['location'] is not None:
        #     item.latitude = item_data['location']['latitude']
        #     item.longitude = item_data['location']['longitude']
        #     item.has_location = True
        # else:
        #     item.has_location = False
        # item.altitude = item_data['altitude']
        # item.drone_orientation = item_data['drone_orientation']
        # item.gimbal_orientation = item_data['gimbal_orientation']
        # item.gimbal_orientation_relative = item_data['gimbal_orientation_relative']
        # item.speed = item_data['speed']
        # rel_loc_xy = item_data['relative_location']
        # if rel_loc_xy is not None:
        #     item.relative_location = (rel_loc_xy[0], rel_loc_xy[1])
        #     item.has_location = True
        # else:
        #     item.has_location = False
        # # item.relative_location = item_data['relative_location']
        # item.relative_height = item_data['relative_height']
        # if item_data['distance'] is not None:
        #     item.distance = item_data['distance']
        # return item

    def add_video_item(self, item_data: BlVideoItemData) -> VideoItemProperties:
        item = self.video_items.add() # type: ignore[call-arg]
        item = cast(VideoItemProperties, item)
        item.src_filename = item_data.get('src_filename', item_data['filename'])
        # item.filename = item_data['filename']
        item.start_time = item_data['start_time']
        item.end_time = item_data['end_time']
        item.duration = item_data['duration']
        item.latitude = item_data['location']['latitude']
        item.longitude = item_data['location']['longitude']
        return item

    def update_item_times(self, context: bpy.types.Context) -> None:
        # self._items_by_frame = None
        for item in self.track_items:
            item.update_frame(context)

    @property
    def items_by_frame(self) -> dict[int, TrackItemProperties]:
        r = getattr(self, '_items_by_frame', None)
        if r is None:
            r = {item.frame: item for item in self.track_items}
            # self._items_by_frame = r
        return r

    def get_current_track_item(self, context: bpy.types.Context) -> TrackItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        items_by_frame = self.items_by_frame
        return items_by_frame.get(current_frame, None)

    def get_next_track_item(self, context: bpy.types.Context) -> TrackItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        items_by_frame = self.items_by_frame
        items_by_frame = {k: v for k, v in items_by_frame.items() if k > current_frame}
        if not items_by_frame:
            return None
        next_frame = min(items_by_frame.keys())
        return items_by_frame.get(next_frame, None)

    def get_previous_track_item(self, context: bpy.types.Context) -> TrackItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        items_by_frame = self.items_by_frame
        items_by_frame = {k: v for k, v in items_by_frame.items() if k < current_frame}
        if not items_by_frame:
            return None
        prev_frame = max(items_by_frame.keys())
        return items_by_frame.get(prev_frame, None)

    def get_current_video_item(self, context: bpy.types.Context) -> VideoItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        for item in self.video_items:
            item = cast(VideoItemProperties, item)
            start_frame = round(item.get_start_frame(context))
            end_frame = round(item.get_end_frame(context))
            if start_frame <= current_frame <= end_frame:
                return item
        return None

    def get_next_video_item(self, context: bpy.types.Context) -> VideoItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        video_items = cast(Iterable[VideoItemProperties], self.video_items)
        future_items = [item for item in video_items if item.get_start_frame(context) > current_frame]
        if not future_items:
            return None
        next_item = min(future_items, key=lambda item: item.get_start_frame(context))
        return next_item

    def get_previous_video_item(self, context: bpy.types.Context) -> VideoItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        video_items = cast(Iterable[VideoItemProperties], self.video_items)
        past_items = [item for item in video_items if item.get_end_frame(context) < current_frame]
        if not past_items:
            return None
        prev_item = max(past_items, key=lambda item: item.get_end_frame(context))
        return prev_item


# class OBJECT_OT_flight_log_properties(bpy.types.Operator):
#     """Operator to to display selected flight log properties"""
#     bl_idname = "object.flight_log_properties"
#     bl_label = "Flight Log Properties"
#     bl_options = {'REGISTER', 'UNDO'}

#     selected_flight: bpy.props.PointerProperty(
#         name="Selected Flight",
#         description="Selected flight log",
#         type=FlightProperties,
#     ) # type: ignore

#     def execute(self, context: bpy.types.Context) -> set[str]:
#         if self.selected_flight is None:
#             self.report({'WARNING'}, "No flight log selected")
#             return {'CANCELLED'}
#         self.report({'INFO'}, f"Selected flight log: {self.selected_flight.name}")
#         return {'FINISHED'}

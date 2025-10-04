from __future__ import annotations
from typing import Self, Literal, Iterable, TYPE_CHECKING, cast, overload
import json
import datetime
from pathlib import Path
import math

import bpy
from bl_ui.generic_ui_list import draw_ui_list

if TYPE_CHECKING:
    from .types import *

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
            item = cast(TrackItemProperties, item)
            frame = item.frame
            scene.frame_set(frame=int(frame), subframe=frame % 1)
            if item.has_location:
                drone_obj.location.x = item.relative_location[0]
                drone_obj.location.y = item.relative_location[1]
                gimbal_obj.location.x = item.relative_location[0]
                gimbal_obj.location.y = item.relative_location[1]
                drone_obj.location.z = item.relative_height
                gimbal_obj.location.z = item.relative_height
            # drone_obj.rotation_euler = (
            #     math.radians(item.drone_orientation[0]),
            #     math.radians(item.drone_orientation[1]),
            #     math.radians(item.drone_orientation[2]),
            # )
            # gimbal_obj.rotation_euler = (
            #     math.radians(item.gimbal_orientation[0]),
            #     math.radians(item.gimbal_orientation[1]),
            #     math.radians(item.gimbal_orientation[2]),
            # )
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

    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Filepath used for importing the flight log file",
        maxlen=1024,
        subtype='FILE_PATH',
    )   # type: ignore

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
        # self._animate_object(data['drone'], drone_empty, context)
        gimbal_empty = self._create_object('EMPTY', 'Gimbal_Empty')
        gimbal_empty.empty_display_type = 'ARROWS'
        gimbal_empty.parent = parent_object
        self._setup_camera(gimbal_empty, context)
        # self._animate_object(data['gimbal'], gimbal_empty, context)
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

    # def build_drone(self, data: BlObjectWithAnimationData, context: bpy.types.Context) -> bpy.types.Object:

    # def _set_active_object(self, obj: bpy.types.Object, context: bpy.types.Context) -> None:
    #     bpy.ops.object.select_all(action='DESELECT')
    #     obj.select_set(True)
    #     assert context.view_layer is not None
    #     context.view_layer.objects.active = obj

    # def _animate_object(self, flight_props: FlightProperties, context: bpy.types.Context) -> None:
    #     animate_objects(flight_props, context)

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        assert context is not None
        assert context.window_manager is not None
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def menu_func_import(self, context: bpy.types.Context) -> None:
    self.layout.operator(IMPORT_SCENE_OT_autel_flight_log.bl_idname, text="Autel Flight Log (.json)")

def is_registered() -> bool:
    op_name = IMPORT_SCENE_OT_autel_flight_log.bl_idname.split('.')[-1]
    return hasattr(bpy.ops.import_scene, op_name)
    # return hasattr(bpy.types, IMPORT_SCENE_OT_autel_flight_log.__name__)

def register() -> None:
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

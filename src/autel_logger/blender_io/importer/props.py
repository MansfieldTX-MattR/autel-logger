from __future__ import annotations
from typing import TypeVar, Generic, Self, Literal, TYPE_CHECKING, overload
import datetime
from pathlib import Path
import math

import bpy
from bpy.app.handlers import persistent

T = TypeVar("T")

if TYPE_CHECKING:
    from ..types import *

    class CollectionProp(bpy.types.bpy_prop_collection[T], Generic[T]):
        def add(self) -> T: ...
        def remove(self, obj: T) -> None: ...



CAMERA_FOCAL_LENGTH = 10.57  # mm, Autel EVO II Pro
CAMERA_SENSOR_WIDTH = 13.2  # mm, Autel EVO II Pro
CAMERA_SENSOR_HEIGHT = 8.8  # mm, Autel EVO II Pro
CAMERA_ASPECT_RATIO = CAMERA_SENSOR_WIDTH / CAMERA_SENSOR_HEIGHT
CAMERA_FOV = 2 * math.degrees(math.atan((CAMERA_SENSOR_WIDTH / 2) / CAMERA_FOCAL_LENGTH))  # degrees, horizontal FOV



@overload
def timestamp_to_frame(
    timestamp: float|datetime.datetime,
    context: bpy.types.Context|bpy.types.Scene|None = None,
    as_int: Literal[False] = ...
) -> float: ...
@overload
def timestamp_to_frame(
    timestamp: float|datetime.datetime,
    context: bpy.types.Context|bpy.types.Scene|None = None,
    as_int: Literal[True] = ...
) -> int: ...
def timestamp_to_frame(
    timestamp: float|datetime.datetime,
    context: bpy.types.Context|bpy.types.Scene|None = None,
    as_int: bool = False
) -> float|int:
    """Convert a UNIX timestamp to a Blender frame number."""
    if isinstance(timestamp, datetime.datetime):
        timestamp = timestamp.timestamp()
    if isinstance(context, bpy.types.Scene):
        scene = context
    elif context is not None:
        scene = context.scene
    if scene is not None:
        fps = scene.render.fps
        fps_base = scene.render.fps_base
    else:
        fps, fps_base = None, None
    delta = bpy.utils.time_to_frame(timestamp, fps=fps, fps_base=fps_base)
    if isinstance(delta, datetime.timedelta):
        delta = delta.total_seconds()
    if as_int:
        return int(round(delta))
    return delta


def frame_to_timestamp(
    frame: int|float,
    context: bpy.types.Context|bpy.types.Scene|None = None
) -> float:
    """Convert a Blender frame number to a UNIX timestamp."""
    if isinstance(context, bpy.types.Scene):
        scene = context
    elif context is not None:
        scene = context.scene
    if scene is not None:
        fps = scene.render.fps
        fps_base = scene.render.fps_base
    else:
        fps, fps_base = None, None
    delta = bpy.utils.time_from_frame(frame, fps=fps, fps_base=fps_base)
    assert delta is not None
    if isinstance(delta, datetime.timedelta):
        return delta.total_seconds()
    return delta


class FlightPathVertexProperties(bpy.types.PropertyGroup):
    _DATA_PROPERTY_NAME = "autel_flight_path_vertex_props"
    if TYPE_CHECKING:
        vertex_index: int
        flight_time: float
        frame: float
    else:
        def _get_frame(self) -> float:
            return timestamp_to_frame(self.flight_time, None)
        vertex_index: bpy.props.IntProperty(
            name="Vertex Index",
            description="Index of the vertex in the flight path",
            default=0,
        )
        flight_time: bpy.props.FloatProperty(
            name="Flight Time",
            description="Time of the flight in seconds",
            default=0.0,
        )
        frame: bpy.props.FloatProperty(
            name="Frame",
            description="Frame number in the Blender timeline",
            default=0.0,
            get=_get_frame,
        )

    @classmethod
    def get_from_object(cls, obj: bpy.types.Object) -> CollectionProp[Self]:
        props = obj.autel_flight_path_vertex_props # type: ignore[assignment]
        return props

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)
        bpy.types.Object.autel_flight_path_vertex_props = bpy.props.CollectionProperty(type=cls) # type: ignore[assign]

    @classmethod
    def _unregister_cls(cls) -> None:
        del bpy.types.Object.autel_flight_path_vertex_props # type: ignore[assign]
        bpy.utils.unregister_class(cls)


class TrackItemProperties(bpy.types.PropertyGroup):
    if TYPE_CHECKING:
        name: str
        index: int
        frame: int
        scene_time: float
        latitude: float
        longitude: float
        altitude: float
        drone_orientation: tuple[float, float, float]
        gimbal_orientation: tuple[float, float, float]
        gimbal_orientation_relative: tuple[float, float, float]
        speed: tuple[float, float, float]
        relative_location: tuple[float, float]
        has_location: bool
        relative_height: float
        distance: float
    else:
        name: bpy.props.StringProperty(
            name="Name",
            description="Name of the track item. This is str(self.frame)",
            default="",
        )
        index: bpy.props.IntProperty(
            name="Index",
            description="Index of the track item in the flight",
            default=0,
        )
        frame: bpy.props.IntProperty(
            name="Frame",
            description="Frame number in the Blender timeline",
            default=0,
        )
        scene_time: bpy.props.FloatProperty(
            name="Scene Time",
            description="Time offset from the start of the flight in seconds",
            subtype='TIME',
            unit='TIME',
            default=0.0,
        )
        latitude: bpy.props.FloatProperty(
            name="Latitude",
            description="Latitude in decimal degrees",
            default=0.0,
            precision=6,
            min=-90.0,
            max=90.0,
        )
        longitude: bpy.props.FloatProperty(
            name="Longitude",
            description="Longitude in decimal degrees",
            default=0.0,
            precision=6,
            min=-180.0,
            max=180.0,
        )
        altitude: bpy.props.FloatProperty(
            name="Altitude",
            description="Altitude in meters",
            subtype='DISTANCE',
            unit='LENGTH',
            default=0.0,
        )
        drone_orientation: bpy.props.FloatVectorProperty(
            name="Drone Orientation",
            description="Orientation of the drone as (pitch, roll, yaw) in degrees",
            size=3,
            default=(0.0, 0.0, 0.0),
            subtype='EULER',
            unit='ROTATION',
        )
        gimbal_orientation: bpy.props.FloatVectorProperty(
            name="Gimbal Orientation",
            description="Orientation of the gimbal as (pitch, roll, yaw) in degrees",
            size=3,
            default=(0.0, 0.0, 0.0),
            subtype='EULER',
            unit='ROTATION',
        )
        gimbal_orientation_relative: bpy.props.FloatVectorProperty(
            name="Gimbal Orientation Relative",
            description="Relative orientation of the gimbal as (pitch, roll, yaw) in degrees",
            size=3,
            default=(0.0, 0.0, 0.0),
            subtype='EULER',
            unit='ROTATION',
        )
        speed: bpy.props.FloatVectorProperty(
            name="Speed",
            description="Speed in meters per second",
            unit='VELOCITY',
            size=3,
            default=(0.0, 0.0, 0.0),
        )
        relative_location: bpy.props.FloatVectorProperty(
            name="Relative Location",
            description="Relative location from the start of the flight in meters (X, Y, Z)",
            size=2,
            default=(0.0, 0.0),
            subtype='TRANSLATION',
            unit='LENGTH',
        )
        has_location: bpy.props.BoolProperty(
            name="Has Location",
            description="Whether the track item has a location",
            default=False,
        )
        relative_height: bpy.props.FloatProperty(
            name="Relative Height",
            description="Relative height from the start of the flight in meters",
            subtype='DISTANCE',
            unit='LENGTH',
            default=0.0,
        )
        distance: bpy.props.FloatProperty(
            name="Distance",
            description="Distance from the start of the flight in meters",
            subtype='DISTANCE',
            unit='LENGTH',
            default=0.0,
        )

    def on_scene_fps_change(self, context: bpy.types.Context|bpy.types.Scene) -> None:
        """Update the frame number based on the scene fps"""
        self.frame = timestamp_to_frame(self.scene_time, context, as_int=True)
        self.name = str(self.frame)

    @classmethod
    def from_track_item_data(
        cls,
        item_data: BlTrackItemData,
        flight: FlightProperties,
        context: bpy.types.Context
    ) -> Self:
        item = flight.track_items.add()
        assert isinstance(item, cls)
        item.index = item_data['index']
        item.on_scene_fps_change(context)
        # note: item.name is already set in on_scene_fps_change
        item.scene_time = item_data['time']
        if item_data['location'] is not None:
            item.latitude = item_data['location']['latitude']
            item.longitude = item_data['location']['longitude']
            item.has_location = True
        else:
            item.has_location = False
        if item_data['altitude'] is not None:
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
    if TYPE_CHECKING:
        name: str
        src_filename: str
        filename: str
        start_time: float
        end_time: float
        duration: float
        latitude: float
        longitude: float
        start_frame: int
        end_frame: int
        current_frame: int
        frame_rate: float|None
        exists_locally: bool
        image_object: bpy.types.Image|None
    else:
        name: bpy.props.StringProperty(
            name="Name",
            description="Name of the video item. This is str(self.start_frame)",
            default="",
        )
        src_filename: bpy.props.StringProperty(
            name="Source Filename",
            description="Original filename of the video",
            default="",
        )
        filename: bpy.props.StringProperty(
            name="Filename",
            description="Filename of the video",
            subtype='FILE_NAME',
            default="",
        )
        start_time: bpy.props.FloatProperty(
            name="Start Time",
            description="Start time of the video in seconds",
            default=0.0,
        )
        end_time: bpy.props.FloatProperty(
            name="End Time",
            description="End time of the video in seconds",
            default=0.0,
        )
        duration: bpy.props.FloatProperty(
            name="Duration",
            description="Duration of the video in seconds",
            default=0.0,
        )
        latitude: bpy.props.FloatProperty(
            name="Latitude",
            description="Latitude of the video location",
            default=0.0,
            precision=6,
            min=-90.0,
            max=90.0,
        )
        longitude: bpy.props.FloatProperty(
            name="Longitude",
            description="Longitude of the video location",
            default=0.0,
            precision=6,
            min=-180.0,
            max=180.0,
        )
        def _get_current_frame(self) -> int:
            context = bpy.context
            return int(round(self.get_current_frame(context)))
        start_frame: bpy.props.IntProperty(
            name="Start Frame",
            description="Start frame of the video",
        )
        end_frame: bpy.props.IntProperty(
            name="End Frame",
            description="End frame of the video",
        )
        current_frame: bpy.props.IntProperty(
            name="Current Frame",
            description="Current frame of the video",
            get=_get_current_frame,
        )
        frame_rate: bpy.props.FloatProperty(
            name="Frame Rate",
            description="Frame rate of the video in frames per second",
            default=0.0,
        )
        exists_locally: bpy.props.BoolProperty(
            name="Exists Locally",
            description="Whether the video file exists locally",
            default=False,
        )
        image_object: bpy.props.PointerProperty(
            name="Image Object",
            description="Blender object representing the video image",
            type=bpy.types.Image,
        )

    def on_scene_fps_change(self, context: bpy.types.Context|bpy.types.Scene) -> None:
        """Update start_frame and end_frame when scene fps changes"""
        self.start_frame = int(round(self.get_start_frame(context)))
        self.end_frame = int(round(self.get_end_frame(context)))
        self.name = str(self.start_frame)

    def get_start_frame(self, context: bpy.types.Context|bpy.types.Scene) -> float:
        return timestamp_to_frame(self.start_time, context)

    def get_end_frame(self, context: bpy.types.Context|bpy.types.Scene) -> float:
        return timestamp_to_frame(self.end_time, context)

    def get_current_frame(self, context: bpy.types.Context) -> float:
        """Return the current video frame based on the scene frame."""
        if context.scene is None:
            return 0
        current_scene_time = frame_to_timestamp(context.scene.frame_current, context)
        if current_scene_time < self.start_time:
            return 0
        if current_scene_time > self.end_time:
            return 0
        offset_time = current_scene_time - self.start_time
        return timestamp_to_frame(offset_time, context)

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)


class FlightProperties(bpy.types.PropertyGroup):
    if TYPE_CHECKING:
        name: str
        start_timestamp: float
        start_time: str
        duration: float
        distance: float
        max_altitude: float
        start_latitude: float
        start_longitude: float
        track_items: CollectionProp[TrackItemProperties]
        video_items: CollectionProp[VideoItemProperties]
        parent_object: bpy.types.Object
        drone_object: bpy.types.Object
        gimbal_object: bpy.types.Object
        flight_path_object: bpy.types.Object
        camera_object: bpy.types.Object
    else:
        name: bpy.props.StringProperty(
            name="Flight Name",
            description="Name of the flight",
            default="",
        )
        start_timestamp: bpy.props.FloatProperty(
            name="Start Timestamp",
            description="Start time of the flight as a UNIX timestamp",
            default=0.0,
        )
        start_time: bpy.props.StringProperty(
            name="Start Time",
            description="Start time of the flight as an ISO 8601 string",
            default="",
        )
        duration: bpy.props.FloatProperty(
            name="Duration",
            description="Duration of the flight in seconds",
            default=0.0,
        )
        distance: bpy.props.FloatProperty(
            name="Distance",
            description="Total distance of the flight in meters",
            subtype='DISTANCE',
            unit='LENGTH',
            default=0.0,
        )
        max_altitude: bpy.props.FloatProperty(
            name="Max Altitude",
            description="Maximum altitude reached during the flight in meters",
            subtype='DISTANCE',
            unit='LENGTH',
            default=0.0,
        )
        start_latitude: bpy.props.FloatProperty(
            name="Start Latitude",
            description="Starting latitude of the flight",
            default=0.0,
            precision=6,
            min=-90.0,
            max=90.0,
        )
        start_longitude: bpy.props.FloatProperty(
            name="Start Longitude",
            description="Starting longitude of the flight",
            default=0.0,
            precision=6,
            min=-180.0,
            max=180.0,
        )
        track_items: bpy.props.CollectionProperty(
            type=TrackItemProperties,
            name="Track Items",
            description="Collection of track items in the flight",
        )
        video_items: bpy.props.CollectionProperty(
            type=VideoItemProperties,
            name="Video Items",
            description="Collection of video items in the flight",
        )
        parent_object: bpy.props.PointerProperty(
            name="Parent Object",
            description="Blender object representing the parent of the flight",
            type=bpy.types.Object,
        )
        drone_object: bpy.props.PointerProperty(
            name="Drone Object",
            description="Blender object representing the drone",
            type=bpy.types.Object,
        )
        gimbal_object: bpy.props.PointerProperty(
            name="Gimbal Object",
            description="Blender object representing the gimbal",
            type=bpy.types.Object,
        )
        flight_path_object: bpy.props.PointerProperty(
            name="Flight Path Object",
            description="Blender object representing the flight path",
            type=bpy.types.Object,
        )
        camera_object: bpy.props.PointerProperty(
            name="Camera Object",
            description="Blender object representing the camera",
            type=bpy.types.Object,
        )

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

    @classmethod
    def _unregister_cls(cls) -> None:
        del bpy.types.Scene.autel_flight_logs_selected_name # type: ignore[assign]
        del bpy.types.Scene.autel_flight_logs_index # type: ignore[assign]
        del bpy.types.Scene.autel_flight_logs # type: ignore[assign]
        bpy.utils.unregister_class(cls)

    @classmethod
    def get_flight_by_name(cls, context: bpy.types.Context, name: str) -> FlightProperties | None:
        for flight in context.scene.autel_flight_logs: # type: ignore[attr-defined]
            if flight.name == name:
                return flight
        return None

    @classmethod
    def get_selected_flight(cls, context: bpy.types.Context) -> FlightProperties | None:
        scene = context.scene
        if scene is None:
            return None
        selected_flight_name = scene.autel_flight_logs_selected_name # type: ignore[attr-defined]
        selected_flight = cls.get_flight_by_name(context, selected_flight_name) if selected_flight_name else None
        return selected_flight

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
        assert isinstance(flight, FlightProperties)
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
        context.scene.autel_flight_logs_index = len(context.scene.autel_flight_logs) - 1 # type: ignore[assigned]
        flight.subscribe_to_scene_fps(context.scene)
        return flight

    def add_track_item(self, item_data: BlTrackItemData, context: bpy.types.Context) -> TrackItemProperties:
        return TrackItemProperties.from_track_item_data(item_data, self, context)

    def add_video_item(self, item_data: BlVideoItemData) -> VideoItemProperties:
        item = self.video_items.add()
        item.name = str(item_data['start_time'])
        item.src_filename = item_data.get('src_filename', item_data['filename'])
        item.start_time = item_data['start_time']
        item.end_time = item_data['end_time']
        item.duration = item_data['duration']
        item.latitude = item_data['location']['latitude']
        item.longitude = item_data['location']['longitude']
        item.frame_rate = item_data['frame_rate'] or 0.0
        item.exists_locally = item_data['exists_locally']
        return item

    @staticmethod
    def subscribe_all_flights_to_scene_fps(scene: bpy.types.Scene) -> None:
        for flight in scene.autel_flight_logs: # type: ignore[attr-defined]
            flight.subscribe_to_scene_fps(scene)

    def subscribe_to_scene_fps(self, scene: bpy.types.Scene) -> None:
        if scene is None:
            return
        # Unsubscribe first to avoid duplicate subscriptions
        bpy.msgbus.clear_by_owner(self)
        # Subscribe to changes in scene.render.fps
        key = scene.render.path_resolve("fps", False)
        bpy.msgbus.subscribe_rna(
            key=key,
            owner=self,
            args=(self, scene),
            notify=self.on_scene_fps_changed,
        )

    @staticmethod
    def on_scene_fps_changed(instance: FlightProperties, scene: bpy.types.Scene) -> None:
        instance.update_item_times(scene)

    def update_item_times(self, context: bpy.types.Context|bpy.types.Scene) -> None:
        for item in self.track_items:
            item.on_scene_fps_change(context)
        for item in self.video_items:
            item.on_scene_fps_change(context)

    @property
    def items_by_frame(self) -> dict[int, TrackItemProperties]:
        return {item.frame: item for item in self.track_items}

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
            start_frame = round(item.get_start_frame(context))
            end_frame = round(item.get_end_frame(context))
            if start_frame <= current_frame <= end_frame:
                return item
        return None

    def get_next_video_item(self, context: bpy.types.Context) -> VideoItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        video_items = self.video_items
        future_items = [item for item in video_items if item.get_start_frame(context) > current_frame]
        if not future_items:
            return None
        next_item = min(future_items, key=lambda item: item.get_start_frame(context))
        return next_item

    def get_previous_video_item(self, context: bpy.types.Context) -> VideoItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        video_items = self.video_items
        past_items = [item for item in video_items if item.get_end_frame(context) < current_frame]
        if not past_items:
            return None
        prev_item = max(past_items, key=lambda item: item.get_end_frame(context))
        return prev_item



def register_classes() -> None:
    FlightPathVertexProperties._register_cls()
    TrackItemProperties._register_cls()
    VideoItemProperties._register_cls()
    FlightProperties._register_cls()
    @persistent
    def on_load_post(*args) -> None:
        for scene in bpy.data.scenes:
            FlightProperties.subscribe_all_flights_to_scene_fps(scene)
    bpy.app.handlers.load_post.append(on_load_post)



def unregister_classes() -> None:
    FlightProperties._unregister_cls()
    VideoItemProperties._unregister_cls()
    TrackItemProperties._unregister_cls()
    FlightPathVertexProperties._unregister_cls()

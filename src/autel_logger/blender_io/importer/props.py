from __future__ import annotations
from typing import TypeVar, Generic, Self, Literal, Callable, TYPE_CHECKING, overload
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


class FlightStickProperties(bpy.types.PropertyGroup):
    if TYPE_CHECKING:
        name: str
        index: int
        frame: int
        scene_time: float
        position: tuple[float, float]
        stick_type: Literal['LEFT', 'RIGHT']
    else:
        name: bpy.props.StringProperty(
            name="Name",
            description="Name of the flight stick. This is str(self.frame)",
            default="",
        )
        index: bpy.props.IntProperty(
            name="Index",
            description="Index of the flight stick",
            default=0,
        )
        frame: bpy.props.IntProperty(
            name="Frame",
            description="Frame number in the Blender timeline",
            default=0,
        )
        scene_time: bpy.props.FloatProperty(
            name="Scene Time",
            description="Time in the scene in seconds",
            default=0.0,
        )
        position: bpy.props.FloatVectorProperty(
            name="Stick Position",
            description="Position of the flight stick (X, Y) from -1.0 to 1.0",
            size=2,
            default=(0.0, 0.0),
            min=-1.0,
            max=1.0,
        )
        stick_type: bpy.props.EnumProperty(
            name="Stick Type",
            description="Type of flight stick (left or right)",
            items=[
                ('LEFT', "Left Stick", "Left flight stick"),
                ('RIGHT', "Right Stick", "Right flight stick"),
            ]
        )

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)
        bpy.types.Object.autel_flight_stick_props = bpy.props.CollectionProperty(type=cls) # type: ignore[assign]

    @classmethod
    def _unregister_cls(cls) -> None:
        del bpy.types.Object.autel_flight_stick_props # type: ignore[assign]
        bpy.utils.unregister_class(cls)

    @classmethod
    def get_from_object(cls, obj: bpy.types.Object) -> CollectionProp[Self]:
        props = obj.autel_flight_stick_props # type: ignore[assignment]
        return props

    @classmethod
    def from_track_item_data(
        cls,
        item_data: BlTrackItemData,
        flight: FlightProperties,
        context: bpy.types.Context,
        stick_type: Literal['LEFT', 'RIGHT']
    ) -> Self:
        obj = flight.left_stick if stick_type == 'LEFT' else flight.right_stick
        props = cls.get_from_object(obj)
        self = props.add()
        self.stick_type = stick_type
        self.index = item_data['index']
        self.scene_time = item_data['time']
        if stick_type == 'LEFT':
            stick_data = item_data['flight_controls']['left_stick']
            pos = (stick_data['x'], stick_data['y'])
        else:
            stick_data = item_data['flight_controls']['right_stick']
            # Right stick data is inverted
            pos = (-stick_data['x'], -stick_data['y'])
        self.position = pos
        self.on_scene_fps_change(context)
        return self

    def on_scene_fps_change(self, context: bpy.types.Context|bpy.types.Scene) -> None:
        """Update the frame number based on the scene fps"""
        self.frame = timestamp_to_frame(self.scene_time, context, as_int=True)
        self.name = str(self.frame)

    def on_scene_frame_change(self, scene: bpy.types.Scene, obj: bpy.types.Object) -> None:
        """Update any properties based on the scene frame change"""
        pass



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

    def on_scene_frame_change(self, context: bpy.types.Context|bpy.types.Scene, parent: FlightProperties) -> None:
        """Update any properties based on the scene frame change"""
        pass

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

    def get_camera_background(self, flight: FlightProperties) -> bpy.types.CameraBackgroundImage|None:
        if self.image_object is None:
            return None
        if flight.camera_object is None:
            return None
        camera = flight.camera_object.data
        if not isinstance(camera, bpy.types.Camera):
            return None
        for bg in camera.background_images:
            if bg.image == self.image_object:
                return bg
        return None

    def on_scene_fps_change(self, context: bpy.types.Context|bpy.types.Scene) -> None:
        """Update start_frame and end_frame when scene fps changes"""
        self.start_frame = int(round(self.get_start_frame(context)))
        self.end_frame = int(round(self.get_end_frame(context)))
        self.name = str(self.start_frame)

    def on_scene_frame_change(self, context: bpy.types.Context|bpy.types.Scene, parent: FlightProperties) -> None:
        """Update current_frame when scene frame changes"""
        scene = context.scene if isinstance(context, bpy.types.Context) else context
        if scene is None:
            return
        bg = self.get_camera_background(parent)
        if bg is None:
            return
        is_current = self.start_frame <= scene.frame_current <= self.end_frame
        if is_current:
            bg.alpha = 0.5
        else:
            bg.alpha = 0.0

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


class CameraInfoProperties(bpy.types.PropertyGroup):
    if TYPE_CHECKING:
        focal_length: float
        sensor_width: float
        sensor_height: float
        fov: float
    else:
        focal_length: bpy.props.FloatProperty(
            name="Focal Length",
            description="Focal length of the camera in mm",
            default=CAMERA_FOCAL_LENGTH,
        )
        sensor_width: bpy.props.FloatProperty(
            name="Sensor Width",
            description="Width of the camera sensor in mm",
            default=CAMERA_SENSOR_WIDTH,
        )
        sensor_height: bpy.props.FloatProperty(
            name="Sensor Height",
            description="Height of the camera sensor in mm",
            default=CAMERA_SENSOR_HEIGHT,
        )
        fov: bpy.props.FloatProperty(
            name="Field of View",
            description="Horizontal field of view of the camera in degrees",
            default=CAMERA_FOV,
        )

    @classmethod
    def _register_cls(cls) -> None:
        bpy.utils.register_class(cls)

    @classmethod
    def _unregister_cls(cls) -> None:
        bpy.utils.unregister_class(cls)

    def import_from_data(self, data: BlCameraInfoData) -> None:
        self.focal_length = data['focal_length']
        self.sensor_width = data["sensor_width"]
        self.sensor_height = data['sensor_height']
        self.fov = 2 * math.degrees(
            math.atan((self.sensor_width / 2) / self.focal_length)
        )


class FlightProperties(bpy.types.PropertyGroup):
    if TYPE_CHECKING:
        name: str
        collection: bpy.types.Collection
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
        left_stick: bpy.types.Object
        right_stick: bpy.types.Object
        camera_info: CameraInfoProperties
    else:
        name: bpy.props.StringProperty(
            name="Flight Name",
            description="Name of the flight",
            default="",
        )
        collection: bpy.props.PointerProperty(
            name="Flight Collection",
            description="Blender collection containing all objects related to the flight",
            type=bpy.types.Collection,
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
        left_stick: bpy.props.PointerProperty(
            name="Left Stick Object",
            description="Blender object representing the left flight stick",
            type=bpy.types.Object,
        )
        right_stick: bpy.props.PointerProperty(
            name="Right Stick Object",
            description="Blender object representing the right flight stick",
            type=bpy.types.Object,
        )
        camera_info: bpy.props.PointerProperty(
            name="Camera Info",
            description="Camera information for the flight",
            type=CameraInfoProperties,
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
        if data['camera_info'] is not None:
            flight.camera_info.import_from_data(data['camera_info'])
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

    def add_flight_stick_data(self, context: bpy.types.Context, data: BlExportData) -> None:
        """Add :class:`FlightStickProperties` from the flight data"""
        for item_data in data['track_items']:
            FlightStickProperties.from_track_item_data(
                item_data, self, context, 'LEFT'
            )
            FlightStickProperties.from_track_item_data(
                item_data, self, context, 'RIGHT'
            )

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

    def on_scene_frame_change(self, scene: bpy.types.Scene) -> None:
        for item in self.track_items:
            item.on_scene_frame_change(scene, self)
        for item in self.video_items:
            item.on_scene_frame_change(scene, self)
        for stick in (self.left_stick, self.right_stick):
            props = FlightStickProperties.get_from_object(stick)
            for flight_stick in props:
                flight_stick.on_scene_frame_change(scene, stick)

    def update_item_times(self, context: bpy.types.Context|bpy.types.Scene) -> None:
        for item in self.track_items:
            item.on_scene_fps_change(context)
        for item in self.video_items:
            item.on_scene_fps_change(context)
        for stick in (self.left_stick, self.right_stick):
            props = FlightStickProperties.get_from_object(stick)
            for flight_stick in props:
                flight_stick.on_scene_fps_change(context)

    def get_items_by_frame(
        self, compare: Callable[[int], bool]|None = None
    ) -> dict[int, TrackItemProperties]:
        if compare is None:
            compare = lambda f: True
        return {
            int(key): value for key, value in self.track_items.items() if compare(int(key))
        }

    def get_video_items_by_start_frame(
        self, compare: Callable[[int], bool]|None = None
    ) -> dict[int, VideoItemProperties]:
        if compare is None:
            compare = lambda f: True
        return {
            round(float(key)): value for key, value in self.video_items.items()
            if compare(round(float(key)))
        }

    def get_current_track_item(self, context: bpy.types.Context) -> TrackItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        items_by_frame = self.get_items_by_frame()
        return items_by_frame.get(current_frame, None)

    def get_next_track_item(self, context: bpy.types.Context) -> TrackItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        items_by_frame = self.get_items_by_frame(lambda f: f > current_frame)
        if not items_by_frame:
            return None
        next_frame = min(items_by_frame.keys())
        return items_by_frame.get(next_frame, None)

    def get_previous_track_item(self, context: bpy.types.Context) -> TrackItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        items_by_frame = self.get_items_by_frame(lambda f: f < current_frame)
        if not items_by_frame:
            return None
        prev_frame = max(items_by_frame.keys())
        return items_by_frame.get(prev_frame, None)

    def get_current_video_item(self, context: bpy.types.Context) -> VideoItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        video_items = self.get_video_items_by_start_frame(lambda f: f <= current_frame)
        if not video_items:
            return None
        latest_start_frame = max(video_items.keys())
        item = video_items[latest_start_frame]
        end_frame = item.get_end_frame(context)
        if latest_start_frame <= current_frame <= end_frame:
            return item
        return None

    def get_next_video_item(self, context: bpy.types.Context) -> VideoItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        video_items = self.get_video_items_by_start_frame(lambda f: f > current_frame)
        if not video_items:
            return None
        next_start_frame = min(video_items.keys())
        return video_items[next_start_frame]

    def get_previous_video_item(self, context: bpy.types.Context) -> VideoItemProperties | None:
        if context.scene is None:
            return None
        current_frame = context.scene.frame_current
        video_items = self.get_video_items_by_start_frame(lambda f: f < current_frame)
        if not video_items:
            return None
        prev_start_frame = max(video_items.keys())
        return video_items[prev_start_frame]



def register_classes() -> None:
    FlightStickProperties._register_cls()
    FlightPathVertexProperties._register_cls()
    TrackItemProperties._register_cls()
    VideoItemProperties._register_cls()
    CameraInfoProperties._register_cls()
    FlightProperties._register_cls()
    @persistent
    def on_load_post(*args) -> None:
        for scene in bpy.data.scenes:
            FlightProperties.subscribe_all_flights_to_scene_fps(scene)
    bpy.app.handlers.load_post.append(on_load_post)

    @persistent
    def on_frame_change_post(scene: bpy.types.Scene) -> None:
        for flight in scene.autel_flight_logs: # type: ignore[attr-defined]
            flight.on_scene_frame_change(scene)
    bpy.app.handlers.frame_change_post.append(on_frame_change_post)


def unregister_classes() -> None:
    FlightProperties._unregister_cls()
    VideoItemProperties._unregister_cls()
    TrackItemProperties._unregister_cls()
    FlightPathVertexProperties._unregister_cls()
    FlightStickProperties._unregister_cls()
    CameraInfoProperties._unregister_cls()

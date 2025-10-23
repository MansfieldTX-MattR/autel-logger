from __future__ import annotations
from typing import TypedDict, NamedTuple, Literal

# from ..flight.flight import Flight, TrackItem

__all__ = [
    'BlVector2D',
    'BlVector3D',
    'BlObjectType',
    'BlObjectAnimationData',
    'BlObjectData',
    'BlObjectLatLonAltData',
    'BlObjectWithVerticesData',
    'BlFlightPathData',
    'BlFlightControlsData',
    'BlFlightStickData',
    'BlTrackItemData',
    'BlVideoItemData',
    'BlImageItemData',
    'BlCameraInfoData',
    'BlLatLon',
    'BlLatLonAlt',
    'BlExportData',
]

BlVector2D = tuple[float, float]
BlVector3D = tuple[float, float, float]

class BlLatLon(TypedDict):
    latitude: float
    longitude: float

class BlLatLonAlt(BlLatLon):
    altitude: float

type BlObjectType = Literal[
    'MESH', 'CURVE', 'EMPTY', 'CAMERA',
    # 'SURFACE', 'META', 'FONT', 'ARMATURE',
    # 'LATTICE', 'LIGHT', 'SPEAKER', 'LIGHT_PROBE'
]

class BlObjectAnimationData(TypedDict):
    time: float
    location: BlVector3D|None
    rotation: BlVector3D


class BlObjectLatLonAltData(TypedDict):
    time: float
    location: BlLatLonAlt


class BlObjectData(TypedDict):
    name: str
    type: BlObjectType



class BlObjectWithVerticesData(BlObjectData):
    vertices: list[BlVector3D]

class BlFlightPathData(BlObjectWithVerticesData):
    vertex_times: list[float]


class BlFlightStickData(TypedDict):
    x: float
    y: float

class BlFlightControlsData(TypedDict):
    left_stick: BlFlightStickData
    right_stick: BlFlightStickData
    is_calibrated: bool


class BlTrackItemData(TypedDict):
    index: int
    time: float
    location: BlLatLon|None
    altitude: float|None
    drone_orientation: BlVector3D  # pitch, roll, yaw in radians
    gimbal_orientation: BlVector3D  # pitch, roll, yaw in radians
    gimbal_orientation_relative: BlVector3D  # pitch, roll, yaw in radians
    speed: BlVector3D  # x, y, z in m/s
    relative_location: BlVector2D|None  # x, y in meters from start location
    relative_height: float  # z in meters from start location
    distance: float|None  # in meters from start location
    flight_controls: BlFlightControlsData


class BlVideoItemData(TypedDict):
    filename: str
    start_time: float  # seconds since start of flight
    end_time: float  # seconds since start of flight
    duration: float  # in seconds
    location: BlLatLon
    exists_locally: bool
    frame_rate: float|None

class BlImageItemData(TypedDict):
    filename: str
    time: float  # seconds since start of flight
    location: BlLatLon


class BlCameraInfoData(TypedDict):
    focal_length: float
    sensor_width: float
    sensor_height: float


class BlExportData(TypedDict):
    filename: str
    flight_path: BlFlightPathData
    track_items: list[BlTrackItemData]
    video_items: list[BlVideoItemData]
    image_items: list[BlImageItemData]
    start_timestamp: float
    start_time: str
    duration: float
    distance: float
    max_altitude: float
    start_location: BlLatLon
    camera_info: BlCameraInfoData|None

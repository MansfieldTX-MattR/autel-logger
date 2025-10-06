from __future__ import annotations
from typing import Literal, TypedDict, Sequence, NotRequired, get_args, cast
import enum


HeadKey = Literal[
    "aircraft_sn", "battery_sn", "location_name", "drone_type", "distance",
    "flight_time", "max_altitude", "video_time", "flight_at", "time_zone",
    "start_latitude", "start_longitude", "image_count", "video_count",
    "firmware_size", "firmware_info",
]
HeadKeys = cast(Sequence[HeadKey], get_args(HeadKey))

VideoKey = Literal[
    "media_filename", "media_timestamp", "latitude", "longitude", "duration",
]
VideoKeys = cast(Sequence[VideoKey], get_args(VideoKey))

ImageKey = Literal[
    "media_filename", "media_timestamp", "latitude", "longitude",
]
ImageKeys = cast(Sequence[ImageKey], get_args(ImageKey))

InBaseKey = Literal[
    "current_time", "drone_altitude", "x_speed", "y_speed", "z_speed",
    "gimbal_pitch", "gimbal_roll", "gimbal_yaw",
    "drone_pitch", "drone_roll", "drone_yaw",
    "m_left_horizontal", "m_left_vertical", "m_right_horizontal", "m_right_vertical",
    "rc_mode_state", "offline_duration", "rc_button_state", "phone_heading",
    "radar_info_timestamp", "front_radar_info", "rear_radar_info", "left_radar_info",
    "right_radar_info", "top_radar_info", "bottom_radar_info",
    "param_1", "param_2",
]
InBaseKeys = cast(Sequence[InBaseKey], get_args(InBaseKey))

InFullKey = Literal[
    "current_time", "drone_altitude", "x_speed", "y_speed", "z_speed",
    "gimbal_pitch", "gimbal_roll", "gimbal_yaw",
    "drone_pitch", "drone_roll", "drone_yaw",
    "m_left_horizontal", "m_left_vertical", "m_right_horizontal", "m_right_vertical",
    "rc_mode_state", "offline_duration", "rc_button_state", "phone_heading",
    "radar_info_timestamp", "front_radar_info", "rear_radar_info", "left_radar_info",
    "right_radar_info", "top_radar_info", "bottom_radar_info",
    "flight_mode", "camera_mode", "rcRSSI", "m_mode", "drone_warning", "drone_ext_warning",
    "gimbal_warning", "time_left", "design_volume", "full_charge_volume",
    "current_electricity", "current_voltage", "current_current", "remain_power_percent", "battery_temperature",
    "battery_state", "number_of_discharges", "cell_count", "cell_voltages",
    "vision_warning", "vision_ext_warning", "vision_error_code",
    "max_flight_altitude", "go_home_altitude", "beginner_mode_enable",
    "low_battery_warning_threshold", "serious_battery_warning_threshold",
    "max_flight_radius", "max_flight_horizontal_speed", "obstacle_avoidance_enabled",
    "radar_enabled", "max_error",
    "param_1", "param_2", "param_3", "param_4", "param_5",
]
InFullKeys = cast(Sequence[InFullKey], get_args(InFullKey))

OutBaseKey = Literal[
    "current_time", "drone_latitude", "drone_longitude", "drone_altitude",
    "x_speed", "y_speed", "z_speed",
    "gimbal_pitch", "gimbal_roll", "gimbal_yaw",
    "drone_pitch", "drone_roll", "drone_yaw",
    "m_left_horizontal", "m_left_vertical", "m_right_horizontal", "m_right_vertical",
    "rc_mode_state", "offline_duration", "rc_button_state", "phone_heading",
    "radar_info_timestamp", "front_radar_info", "rear_radar_info", "left_radar_info",
    "right_radar_info", "top_radar_info", "bottom_radar_info",
    "param_1", "param_2",
]
OutBaseKeys = cast(Sequence[OutBaseKey], get_args(OutBaseKey))

OutFullKey = Literal[
    "current_time", "drone_latitude", "drone_longitude", "drone_altitude",
    "x_speed", "y_speed", "z_speed",
    "gimbal_pitch", "gimbal_roll", "gimbal_yaw",
    "drone_pitch", "drone_roll", "drone_yaw",
    "m_left_horizontal", "m_left_vertical", "m_right_horizontal", "m_right_vertical",
    "rc_mode_state", "offline_duration", "rc_button_state", "phone_heading",
    "radar_info_timestamp", "front_radar_info", "rear_radar_info", "left_radar_info",
    "right_radar_info", "top_radar_info", "bottom_radar_info",
    "flight_mode", "camera_mode", "gps_signal_level", "rcRSSI", "m_mode",
    "home_latitude", "home_longitude", "distance_from_home", "current_journey",
    "drone_warning", "drone_ext_warning", "gimbal_warning", "time_left",
    "back_time", "satellite_count", "design_volume", "full_charge_volume",
    "current_electricity", "current_voltage", "current_current",
    "remain_power_percent", "battery_temperature", "battery_state",
    "number_of_discharges", "cell_count", "cell_voltages",
    "vision_warning", "vision_ext_warning", "vision_error_code",
    "max_flight_altitude", "go_home_altitude", "beginner_mode_enable",
    "low_battery_warning_threshold", "serious_battery_warning_threshold",
    "max_flight_radius", "max_flight_horizontal_speed", "obstacle_avoidance_enabled",
    "radar_enabled", "max_error",
    "param_1", "param_2", "param_3", "param_4", "param_5",
]
OutFullKeys = cast(Sequence[OutFullKey], get_args(OutFullKey))


type AllLogKey = InBaseKey | InFullKey | OutBaseKey | OutFullKey | VideoKey | ImageKey | HeadKey
# AllLogKeys = cast(Sequence[AllLogKey], get_args(AllLogKey))

type RecordTypeName = Literal[
    'head', 'video', 'image', 'in_base', 'in_full', 'out_base', 'out_full'
]
type FlightRecordTypeName = Literal[
    'in_base', 'in_full', 'out_base', 'out_full'
]
type MediaRecordTypeName = Literal[
    'video', 'image'
]

type ParseRecordTD = (
    ParsedHeadTD | ParsedVideoTD | ParsedImageTD |
    ParsedInBaseTD | ParsedInFullTD | ParsedOutBaseTD | ParsedOutFullTD
)

type ParseFlightRecordTD = (
    ParsedInBaseTD | ParsedInFullTD | ParsedOutBaseTD | ParsedOutFullTD
)
type ParseMediaTD = (
    ParsedVideoTD | ParsedImageTD
)


RECORD_TYPE_MAP: dict[int, RecordTypeName] = {
    0: 'out_full',
    1: 'out_base',
    2: 'in_full',
    3: 'in_base',
    6: 'head',
    15: 'video',
    14: 'image',

}

class RecordKeyMap(enum.Enum):
    head = HeadKeys
    video = VideoKeys
    image = ImageKeys
    in_base = InBaseKeys
    in_full = InFullKeys
    out_base = OutBaseKeys
    out_full = OutFullKeys




class ParsedRecordsTD(TypedDict):
    head: ParsedHeadTD
    video: list[ParsedVideoTD]
    image: list[ParsedImageTD]
    in_base: list[ParsedInBaseTD]
    in_full: list[ParsedInFullTD]
    out_base: list[ParsedOutBaseTD]
    out_full: list[ParsedOutFullTD]

# type ParseRecordKeyTup =

RECORD_SIZES: dict[AllLogKey, int] = {
    "aircraft_sn": 18,
    "battery_sn": 32,
    "location_name": 64,
    "drone_type": 1,
    "distance": 4,
    "flight_time": 4,
    "max_altitude": 4,
    "video_time": 4,
    "flight_at": 8,
    "time_zone": 4,
    "start_latitude": 4,
    "start_longitude": 4,
    "image_count": 2,
    "video_count": 2,
    "firmware_size": 2,
    "firmware_info": -1, # determined by firmware_size
    "current_time": 4,
    "drone_altitude": 4,
    "x_speed": 4,
    "y_speed": 4,
    "z_speed": 4,
    "gimbal_pitch": 4,
    "gimbal_roll": 4,
    "gimbal_yaw": 4,
    "drone_pitch": 4,
    "drone_roll": 4,
    "drone_yaw": 4,
    "m_left_horizontal": 2,
    "m_left_vertical": 2,
    "m_right_horizontal": 2,
    "m_right_vertical": 2,
    "rc_mode_state": 1,
    "offline_duration": 4,
    "rc_button_state": 1,
    "phone_heading": 8,
    "radar_info_timestamp": 8,
    "front_radar_info": 4,
    "rear_radar_info": 4,
    "left_radar_info": 4,
    "right_radar_info": 4,
    "top_radar_info": 4,
    "bottom_radar_info": 4,
    "param_1": 4,
    "param_2": 4,
    "flight_mode": 1,
    "camera_mode": 1,
    "rcRSSI": 1,
    "m_mode": 1,
    "drone_warning": 4,
    "drone_ext_warning": 4,
    "gimbal_warning": 4,
    "time_left": 4,
    "design_volume": 4,
    "full_charge_volume": 4,
    "current_electricity": 4,
    "current_voltage": 4,
    "current_current": 4,
    "remain_power_percent": 1,
    "battery_temperature": 4,
    "battery_state": 1,
    "number_of_discharges": 4,
    "cell_count": 1,
    "cell_voltages": 32, # comma-separated
    "vision_warning": 4,
    "vision_ext_warning": 4,
    "vision_error_code": 4,
    "max_flight_altitude": 4,
    "go_home_altitude": 4,
    "beginner_mode_enable": 1,
    "low_battery_warning_threshold": 1,
    "serious_battery_warning_threshold": 1,
    "max_flight_radius": 4,
    "max_flight_horizontal_speed": 4,
    "obstacle_avoidance_enabled": 1,
    "radar_enabled": 1,
    "max_error": 4,
    "param_3": 4,
    "param_4": 4,
    "param_5": 4,
    "media_filename": 64,
    "media_timestamp": 8,
    "latitude": 4,
    "longitude": 4,
    "duration": 4,
    "drone_latitude": 4,
    "drone_longitude": 4,
    "gps_signal_level": 1,
    "home_latitude": 4,
    "home_longitude": 4,
    "distance_from_home": 4,
    "current_journey": 4,
    "back_time": 4,
    "satellite_count": 1,
}


RECORD_FORMATS: dict[AllLogKey, str] = {
    "flight_time": "i",
    "time_zone": "i",
    "media_timestamp": "i",
    "current_time": "i",
    "duration": "i",
    "offline_duration": "i",
    "phone_heading": "d",
    "radar_info_timestamp": "d",
    "back_time": "i",
    "design_volume": "i",
    "drone_ext_warning": "h",
    "drone_warning": "h",
    "full_charge_volume": "i",
    "gimbal_warning": "h",
    "max_error": "i",
    "number_of_discharges": "i",
    "vision_ext_warning": "h",
    "vision_warning": "h",
    "cell_voltages": "[f",
}


class ParsedHeadTD(TypedDict):
    aircraft_sn: str
    battery_sn: str
    location_name: str
    drone_type: int
    distance: float
    flight_time: int        # seconds
    """Flight duration in seconds"""
    max_altitude: float
    video_time: int         # milliseconds
    flight_at: int          # milliseconds
    """Unix timestamp in milliseconds"""
    time_zone: int
    start_latitude: float
    start_longitude: float
    image_count: int
    video_count: int
    firmware_size: int
    firmware_info: str

class ParsedMediaTD(TypedDict):
    media_filename: str
    media_timestamp: float
    """Unix timestamp in milliseconds"""
    latitude: float
    longitude: float


class ParsedVideoTD(ParsedMediaTD):
    duration: float

class ParsedImageTD(ParsedMediaTD):
    pass



class HasXYZSpeedTD(TypedDict):
    x_speed: float
    y_speed: float
    z_speed: float


class HasGimbalTD(TypedDict):
    gimbal_roll: float
    gimbal_pitch: float
    gimbal_yaw: float


class HasDroneOrientationTD(TypedDict):
    drone_pitch: float
    drone_roll: float
    drone_yaw: float


class HasDronePositionTD(TypedDict):
    drone_latitude: float
    drone_longitude: float
    drone_altitude: float


class HasBatteryInfoTD(TypedDict):
    design_volume: float
    full_charge_volume: NotRequired[float]
    current_electricity: NotRequired[float]
    current_voltage: NotRequired[float]
    current_current: NotRequired[float]
    remain_power_percent: NotRequired[float]
    battery_temperature: NotRequired[float]
    battery_state: NotRequired[int]
    number_of_discharges: NotRequired[int]
    cell_count: int
    cell_voltages: NotRequired[list[float]]


class HasMLeftRightTD(TypedDict):
    m_left_horizontal: float
    m_left_vertical: float
    m_right_horizontal: float
    m_right_vertical: float


class HasRadarInfoTD(TypedDict):
    radar_info_timestamp: float
    front_radar_info: int
    rear_radar_info: int
    left_radar_info: int
    right_radar_info: int
    top_radar_info: int
    bottom_radar_info: int


class HasDroneWarningTD(TypedDict):
    drone_warning: str
    drone_ext_warning: str
    gimbal_warning: str
    vision_warning: str
    vision_ext_warning: str
    vision_error_code: int


class HasGoHomeInfoTD(TypedDict):
    home_latitude: float
    home_longitude: float
    distance_from_home: float
    current_journey: float
    time_left: float
    back_time: float
    satellite_count: int
    max_flight_altitude: float
    go_home_altitude: float
    low_battery_warning_threshold: float
    serious_battery_warning_threshold: float


class HasRCModeInfoTD(TypedDict):
    rc_mode_state: int
    offline_duration: float
    rc_button_state: int

class HasRCFullInfoTD(HasRCModeInfoTD):
    rcRSSI: int


class HasCurTimeTD(TypedDict):
    current_time: float
    """Milliseconds since flight start"""


class ParsedInBaseTD(
    HasCurTimeTD, HasXYZSpeedTD, HasGimbalTD, HasDroneOrientationTD,
    HasMLeftRightTD, HasRadarInfoTD, HasRCModeInfoTD
):
    drone_altitude: float
    phone_heading: float
    param_1: int
    param_2: int



class ParsedOutBaseTD(
    HasCurTimeTD, HasDronePositionTD, HasXYZSpeedTD, HasGimbalTD,
    HasDroneOrientationTD, HasMLeftRightTD, HasRadarInfoTD, HasRCModeInfoTD
):
    param_1: int
    param_2: int


class ParsedOutFullTD(
    HasCurTimeTD, HasDronePositionTD, HasXYZSpeedTD, HasGimbalTD,
    HasDroneOrientationTD, HasMLeftRightTD, HasRadarInfoTD,
    HasBatteryInfoTD, HasDroneWarningTD, HasGoHomeInfoTD, HasRCFullInfoTD
):
    phone_heading: float
    flight_mode: int
    camera_mode: int
    gps_signal_level: int
    m_mode: int
    beginner_mode_enable: int
    max_flight_radius: float
    max_flight_horizontal_speed: float
    obstacle_avoidance_enable: NotRequired[int]
    radar_enable: NotRequired[int]
    max_error: int
    param_1: int
    param_2: int
    param_3: int
    param_4: int
    param_5: int

class ParsedInFullTD(
    HasCurTimeTD, HasXYZSpeedTD, HasGimbalTD,
    HasDroneOrientationTD, HasMLeftRightTD, HasRadarInfoTD,
    HasBatteryInfoTD, HasDroneWarningTD, HasRCFullInfoTD
):
    drone_altitude: float
    phone_heading: float
    flight_mode: int
    camera_mode: int
    m_mode: int
    time_left: float
    max_flight_altitude: float
    go_home_altitude: float
    beginner_mode_enable: int
    low_battery_warning_threshold: float
    serious_battery_warning_threshold: float
    max_flight_radius: float
    max_flight_horizontal_speed: float
    obstacle_avoidance_enable: NotRequired[int]
    radar_enable: NotRequired[int]
    max_error: int
    param_1: int
    param_2: int
    param_3: int
    param_4: int
    param_5: int

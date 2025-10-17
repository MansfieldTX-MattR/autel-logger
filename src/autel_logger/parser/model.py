from __future__ import annotations
from typing import (
    NamedTuple, TypedDict, ClassVar, Literal, Iterable, Iterator, Self,
    TYPE_CHECKING
)
from abc import ABC, abstractmethod

import datetime
import dataclasses
from dataclasses import dataclass

from .types import (
    RecordTypeName, ParsedInBaseTD, ParsedInFullTD, ParsedOutBaseTD, ParsedOutFullTD,
    ParsedHeadTD, ParsedVideoTD, ParsedImageTD, ParseFlightRecordTD, ParseMediaTD,
    HasBatteryInfoTD, HasDroneWarningTD, HasGoHomeInfoTD, HasRadarInfoTD,
    HasRCFullInfoTD, HasMLeftRightTD,
    FlightRecordTypeName, MediaRecordTypeName,
)
from ..spatial import LatLon, LatLonAlt, Vector3D, Speed, Orientation
if TYPE_CHECKING:
    from .record_parser import ParseResult



class BatteryInfo(NamedTuple):
    """Battery information for the drone
    """
    state: int|None
    """Battery state"""
    design_volume: float
    """"""
    full_charge_volume: float
    """Full charge volume in mAh"""
    current_electricity: float
    """Current electricity use in Watts"""
    current_voltage: float
    """Current voltage in VDC"""
    current_current: float
    """Current current in Amps"""
    remain_power_percent: float
    """Remaining battery power percentage"""
    temperature: float
    """Battery temperature in Celsius"""
    discharge_count: int
    """Number of discharges"""
    cell_count: int
    """Number of cells in the battery"""
    cell_voltages: list[float]
    """Cell voltages in VDC"""

    class SerializeTD(TypedDict):
        """:meta private:"""
        state: int|None
        design_volume: float
        full_charge_volume: float
        current_electricity: float
        current_voltage: float
        current_current: float
        remain_power_percent: float
        temperature: float
        discharge_count: int
        cell_count: int
        cell_voltages: list[float]

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            state=self.state,
            design_volume=self.design_volume,
            full_charge_volume=self.full_charge_volume,
            current_electricity=self.current_electricity,
            current_voltage=self.current_voltage,
            current_current=self.current_current,
            remain_power_percent=self.remain_power_percent,
            temperature=self.temperature,
            discharge_count=self.discharge_count,
            cell_count=self.cell_count,
            cell_voltages=self.cell_voltages,
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            state=data['state'],
            design_volume=data['design_volume'],
            full_charge_volume=data['full_charge_volume'],
            current_electricity=data['current_electricity'],
            current_voltage=data['current_voltage'],
            current_current=data['current_current'],
            remain_power_percent=data['remain_power_percent'],
            temperature=data['temperature'],
            discharge_count=data['discharge_count'],
            cell_count=data['cell_count'],
            cell_voltages=data['cell_voltages'],
        )

    @classmethod
    def from_dict(cls, data: HasBatteryInfoTD) -> Self:
        count = data['cell_count']
        voltages = data['cell_voltages']
        if len(voltages) != count:
            voltages = voltages[:count]
        voltages = [v / 1000 for v in voltages]                     # mV to V
        return cls(
            state=data.get('battery_state'),
            design_volume=data['design_volume'],
            full_charge_volume=data['full_charge_volume'],
            current_electricity=data['current_electricity'] / 1000, # mW to W
            current_voltage=data['current_voltage'] / 1000,         # mV to V
            current_current=abs(data['current_current']) / 1000,    # mA to A
            remain_power_percent=data['remain_power_percent'],
            temperature=data['battery_temperature'],
            discharge_count=data['number_of_discharges'],
            cell_count=count,
            cell_voltages=voltages,
        )


class StickPosition(NamedTuple):
    """Position of a control stick on the RC"""
    horizontal: float
    """Horizontal position of the stick"""
    vertical: float
    """Vertical position of the stick"""

    class SerializeTD(TypedDict):
        """:meta private:"""
        horizontal: float
        vertical: float

    def normalize(self, calibration: StickCalibration) -> Self:
        """Normalize the stick position to the range of ``-1`` to ``1`` using
        the given calibration data
        """
        offset = calibration.center
        scale = StickPosition(
            calibration.negative_scale.horizontal if self.horizontal < calibration.center.horizontal
            else calibration.positive_scale.horizontal,
            calibration.negative_scale.vertical if self.vertical < calibration.center.vertical
            else calibration.positive_scale.vertical,
        )
        return (self - offset) * scale

    def serialize(self) -> SerializeTD:
        return {
            'horizontal': self.horizontal,
            'vertical': self.vertical,
        }

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            horizontal=data['horizontal'],
            vertical=data['vertical'],
        )

    def __add__(self, other: StickPosition|tuple[float, float]|float) -> Self:
        if isinstance(other, StickPosition):
            x, y = other.horizontal, other.vertical
        elif isinstance(other, tuple):
            x, y = other
        else:
            x = y = other
        return self.__class__(self.horizontal + x, self.vertical + y)

    def __sub__(self, other: StickPosition|tuple[float, float]|float) -> Self:
        if isinstance(other, StickPosition):
            x, y = other.horizontal, other.vertical
        elif isinstance(other, tuple):
            x, y = other
        else:
            x = y = other
        return self.__class__(self.horizontal - x, self.vertical - y)

    def __mul__(self, other: StickPosition|tuple[float, float]|float) -> Self:
        if isinstance(other, StickPosition):
            x, y = other.horizontal, other.vertical
        elif isinstance(other, tuple):
            x, y = other
        else:
            x = y = other
        return self.__class__(self.horizontal * x, self.vertical * y)

    def __truediv__(self, other: StickPosition|tuple[float, float]|float) -> Self:
        if isinstance(other, StickPosition):
            x, y = other.horizontal, other.vertical
        elif isinstance(other, tuple):
            x, y = other
        else:
            x = y = other
        return self.__class__(self.horizontal / x, self.vertical / y)

    def __rtruediv__(self, other: StickPosition|tuple[float, float]|float) -> Self:
        if isinstance(other, StickPosition):
            x, y = other.horizontal, other.vertical
        elif isinstance(other, tuple):
            x, y = other
        else:
            x = y = other
        return self.__class__(x / self.horizontal, y / self.vertical)

    def __abs__(self) -> float:
        return (self.horizontal**2 + self.vertical**2)**0.5


class StickCalibration(NamedTuple):
    """Calibration data for a control stick on the RC"""
    min: StickPosition
    """Minimum stick position"""
    max: StickPosition
    """Maximum stick position"""
    center: StickPosition = StickPosition(1024, 1024)
    """Center stick position"""

    class SerializeTD(TypedDict):
        """:meta private:"""
        min: StickPosition.SerializeTD
        max: StickPosition.SerializeTD
        center: StickPosition.SerializeTD

    @property
    def negative_divisor(self) -> StickPosition:
        """Divisors for negative stick movement"""
        return self.center - self.min

    @property
    def positive_divisor(self) -> StickPosition:
        """Divisors for positive stick movement"""
        return self.max - self.center

    @property
    def negative_scale(self) -> StickPosition:
        """Scale factors for negative stick movement"""
        return 1 / self.negative_divisor

    @property
    def positive_scale(self) -> StickPosition:
        """Scale factors for positive stick movement"""
        return 1 / self.positive_divisor

    @property
    def can_calibrate(self) -> bool:
        """Whether the calibration data is valid for normalizing stick positions"""
        neg_div = self.negative_divisor
        pos_div = self.positive_divisor
        return (
            neg_div.horizontal != 0 and neg_div.vertical != 0 and
            pos_div.horizontal != 0 and pos_div.vertical != 0
        )

    @classmethod
    def from_records(cls, *records: StickPosition) -> Self:
        """Create a StickCalibration from multiple StickPosition records
        """
        center = StickPosition(1024, 1024)
        min_pos = center
        max_pos = center
        for record in records:
            min_pos = StickPosition(
                min(min_pos.horizontal, record.horizontal),
                min(min_pos.vertical, record.vertical),
            )
            max_pos = StickPosition(
                max(max_pos.horizontal, record.horizontal),
                max(max_pos.vertical, record.vertical),
            )
        return cls(min=min_pos, max=max_pos, center=center)

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            min=self.min.serialize(),
            max=self.max.serialize(),
            center=self.center.serialize(),
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            min=StickPosition.deserialize(data['min']),
            max=StickPosition.deserialize(data['max']),
            center=StickPosition.deserialize(data['center']),
        )


class FlightControlsCalibration(NamedTuple):
    """Calibration data for both control sticks on the RC"""
    left_stick: StickCalibration
    """Left stick calibration"""
    right_stick: StickCalibration
    """Right stick calibration"""

    class SerializeTD(TypedDict):
        """:meta private:"""
        left_stick: StickCalibration.SerializeTD
        right_stick: StickCalibration.SerializeTD

    @property
    def can_calibrate(self) -> bool:
        """Whether the calibration data is valid for normalizing stick positions"""
        return self.left_stick.can_calibrate and self.right_stick.can_calibrate

    @classmethod
    def from_records(cls, *records: FlightControl) -> Self:
        """Create a FlightControlsCalibration from multiple FlightControl records
        """
        left_stick_records = [record.left_stick for record in records]
        right_stick_records = [record.right_stick for record in records]
        return cls(
            left_stick=StickCalibration.from_records(*left_stick_records),
            right_stick=StickCalibration.from_records(*right_stick_records),
        )

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            left_stick=self.left_stick.serialize(),
            right_stick=self.right_stick.serialize(),
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            left_stick=StickCalibration.deserialize(data['left_stick']),
            right_stick=StickCalibration.deserialize(data['right_stick']),
        )


class FlightControl(NamedTuple):
    """Positions of the left and right control sticks on the RC"""
    left_stick: StickPosition
    """Left stick position"""
    right_stick: StickPosition
    """Right stick position"""

    class SerializeTD(TypedDict):
        """:meta private:"""
        left_stick: StickPosition.SerializeTD
        right_stick: StickPosition.SerializeTD

    def serialize(self) -> SerializeTD:
        return {
            'left_stick': self.left_stick.serialize(),
            'right_stick': self.right_stick.serialize(),
        }

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            StickPosition.deserialize(data['left_stick']),
            StickPosition.deserialize(data['right_stick']),
        )

    @classmethod
    def from_dict(cls, data: HasMLeftRightTD) -> Self:
        return cls(
            StickPosition(data['m_left_horizontal'], data['m_left_vertical']),
            StickPosition(data['m_right_horizontal'], data['m_right_vertical']),
        )

    def normalize(self, calibration: FlightControlsCalibration) -> Self:
        """Normalize the flight control stick positions using the given calibration data"""
        if not calibration.can_calibrate:
            raise ValueError(f"Cannot normalize flight controls: invalid calibration data: {calibration}")
        return self.__class__(
            self.left_stick.normalize(calibration.left_stick),
            self.right_stick.normalize(calibration.right_stick),
        )

    def __add__(self, other: FlightControl|tuple[float, float]|float) -> Self:
        if isinstance(other, FlightControl):
            left, right = other.left_stick, other.right_stick
        elif isinstance(other, tuple) or isinstance(other, float) or isinstance(other, int):
            left = right = other
        else:
            raise TypeError(f"Unsupported type for addition: {type(other)}")
        return self.__class__(
            self.left_stick + left,
            self.right_stick + right,
        )

    def __sub__(self, other: FlightControl|tuple[float, float]|float) -> Self:
        if isinstance(other, FlightControl):
            left, right = other.left_stick, other.right_stick
        elif isinstance(other, tuple) or isinstance(other, float) or isinstance(other, int):
            left = right = other
        else:
            raise TypeError(f"Unsupported type for subtraction: {type(other)}")
        return self.__class__(
            self.left_stick - left,
            self.right_stick - right,
        )

    def __abs__(self) -> tuple[float, float]:
        return abs(self.left_stick), abs(self.right_stick)


class RadarInfo(NamedTuple):
    """Radar information from the drone's sensors."""
    timestamp: float
    front: int
    rear: int
    left: int
    right: int
    top: int
    bottom: int

    class SerializeTD(TypedDict):
        """:meta private:"""
        timestamp: float
        front: int
        rear: int
        left: int
        right: int
        top: int
        bottom: int

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            timestamp=self.timestamp,
            front=self.front,
            rear=self.rear,
            left=self.left,
            right=self.right,
            top=self.top,
            bottom=self.bottom,
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            timestamp=data['timestamp'],
            front=data['front'],
            rear=data['rear'],
            left=data['left'],
            right=data['right'],
            top=data['top'],
            bottom=data['bottom'],
        )

    @classmethod
    def from_dict(cls, data: HasRadarInfoTD) -> Self:
        return cls(
            timestamp=data['radar_info_timestamp'],
            front=data['front_radar_info'],
            rear=data['rear_radar_info'],
            left=data['left_radar_info'],
            right=data['right_radar_info'],
            top=data['top_radar_info'],
            bottom=data['bottom_radar_info'],
        )


class Warnings(NamedTuple):
    """Warnings generated by the drone's systems."""
    drone: str
    drone_ext: str
    gimbal: str
    vision: str
    vision_ext: str
    error_code: int

    class SerializeTD(TypedDict):
        """:meta private:"""
        drone: str
        drone_ext: str
        gimbal: str
        vision: str
        vision_ext: str
        error_code: int

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            drone=self.drone,
            drone_ext=self.drone_ext,
            gimbal=self.gimbal,
            vision=self.vision,
            vision_ext=self.vision_ext,
            error_code=self.error_code,
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            drone=data['drone'],
            drone_ext=data['drone_ext'],
            gimbal=data['gimbal'],
            vision=data['vision'],
            vision_ext=data['vision_ext'],
            error_code=data['error_code'],
        )

    @classmethod
    def from_dict(cls, data: HasDroneWarningTD) -> Self:
        return cls(
            drone=data['drone_warning'],
            drone_ext=data['drone_ext_warning'],
            gimbal=data['gimbal_warning'],
            vision=data['vision_warning'],
            vision_ext=data['vision_ext_warning'],
            error_code=data['vision_error_code'],
        )


class GoHomeInfo(NamedTuple):
    """Information about the drone's 'go home' status."""
    location: LatLon
    """Home location"""
    distance: float
    """Distance to home in meters"""
    current_journey: float
    """Current journey distance in meters"""
    time_left: float
    """Time left to reach home in seconds"""
    back_time: float
    """Estimated time to reach home in seconds"""
    satellite_count: int
    """Number of satellites connected"""
    max_flight_altitude: float
    """Maximum flight altitude in meters"""
    go_home_altitude: float
    """Go home altitude in meters"""
    low_battery_warning_threshold: float
    """Low battery warning threshold"""
    serious_battery_warning_threshold: float
    """Serious battery warning threshold"""

    @classmethod
    def from_dict(cls, data: HasGoHomeInfoTD) -> Self:
        return cls(
            location=LatLon(data['home_latitude'], data['home_longitude']),
            distance=data['distance_from_home'],
            current_journey=data['current_journey'],
            time_left=data['time_left'],
            back_time=data['back_time'],
            satellite_count=data['satellite_count'],
            max_flight_altitude=data['max_flight_altitude'],
            go_home_altitude=data['go_home_altitude'],
            low_battery_warning_threshold=data['low_battery_warning_threshold'],
            serious_battery_warning_threshold=data['serious_battery_warning_threshold'],
        )


class RCInfo(NamedTuple):
    """Information about the remote controller (RC) status."""
    mode: int
    """Current mode of the RC."""
    offline_duration: float
    """"""
    button_state: int
    """Button state"""
    signal_strength: int
    """Signal strength (rSSI)"""

    class SerializeTD(TypedDict):
        """:meta private:"""
        mode: int
        offline_duration: float
        button_state: int
        signal_strength: int

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            mode=self.mode,
            offline_duration=self.offline_duration,
            button_state=self.button_state,
            signal_strength=self.signal_strength,
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            mode=data['mode'],
            offline_duration=data['offline_duration'],
            button_state=data['button_state'],
            signal_strength=data.get('signal_strength'),
        )

    @classmethod
    def from_dict(cls, data: HasRCFullInfoTD) -> Self:
        return cls(
            mode=data['rc_mode_state'],
            offline_duration=data['offline_duration'],
            button_state=data['rc_button_state'],
            signal_strength=data['rcRSSI'],
        )


@dataclass
class RecordBase[T: RecordTypeName](ABC):
    """Base class for all parsed records"""
    RECORD_TYPE: ClassVar

    @classmethod
    def get_record_type(cls) -> T:
        return cls.RECORD_TYPE

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> Self:
        raise NotImplementedError()



@dataclass
class ParsedHead(RecordBase[Literal['head']]):
    """Header information for a flight log"""
    aircraft_sn: str
    """Aircraft serial number"""
    battery_sn: str
    """Battery serial number"""
    location_name: str
    """Location name"""
    drone_type: int
    """Drone type"""
    distance: float
    """Distance traveled in meters"""
    max_altitude: float
    """Maximum altitude in meters"""
    video_time: int
    flight_at: datetime.datetime
    """Flight start time (timezone-naive)"""
    flight_duration: float
    """Flight duration in seconds"""
    time_zone: int
    """Time zone offset in seconds from UTC"""
    start_location: LatLon
    """Starting location"""
    image_count: int
    """Number of images captured"""
    video_count: int
    """Number of videos captured"""
    firmware_size: int
    """Size of the :attr:`firmware_info` string in bytes"""
    firmware_info: str
    """Firmware version information"""

    RECORD_TYPE: ClassVar[Literal[ 'head' ]] = 'head'

    @classmethod
    def from_dict(cls, data: ParsedHeadTD) -> Self:
        return cls(
            aircraft_sn=data['aircraft_sn'],
            battery_sn=data['battery_sn'],
            location_name=data['location_name'],
            drone_type=data['drone_type'],
            distance=data['distance'],
            max_altitude=data['max_altitude'],
            video_time=data['video_time'],
            flight_at=datetime.datetime.fromtimestamp(data['flight_at'] / 1000),
            flight_duration=data['flight_time'],
            time_zone=data['time_zone'] // 1000,
            start_location=LatLon(data['start_latitude'], data['start_longitude']),
            image_count=data['image_count'],
            video_count=data['video_count'],
            firmware_size=data['firmware_size'],
            firmware_info=data['firmware_info'],
        )


@dataclass
class ParsedMedia[T: Literal['video', 'image'], D: ParseMediaTD](RecordBase[T]):
    """Base class for media records (video or image)"""
    filename: str
    """Media file name"""
    timestamp: datetime.datetime
    """Timestamp of the media (timezone-naive)"""
    location: LatLon
    """Location where the media was captured"""

    # RECORD_TYPE: ClassVar[T]

    @classmethod
    def from_parsed_dicts(cls, data: Iterable[D]) -> dict[datetime.datetime, Self]:
        result = {}
        for d in data:
            record = cls.from_dict(d)
            result[record.timestamp] = record
        return result

    @classmethod
    @abstractmethod
    def from_dict(cls, data: D) -> Self:
        raise NotImplementedError()


@dataclass
class ParsedVideo(ParsedMedia[Literal['video'], ParsedVideoTD]):
    """Parsed video media record"""
    duration: float
    """Duration of the video in seconds"""

    RECORD_TYPE: ClassVar[Literal['video']] = 'video'

    @classmethod
    def from_dict(cls, data: ParsedVideoTD) -> Self:
        return cls(
            filename=data['media_filename'],
            timestamp=datetime.datetime.fromtimestamp(data['media_timestamp'] / 1000),
            location=LatLon(data['latitude'], data['longitude']),
            duration=data['duration'],
        )


@dataclass
class ParsedImage(ParsedMedia[Literal['image'], ParsedImageTD]):
    """Parsed image media record"""
    RECORD_TYPE: ClassVar[Literal['image']] = 'image'

    @classmethod
    def from_dict(cls, data: ParsedImageTD) -> Self:
        return cls(
            filename=data['media_filename'],
            timestamp=datetime.datetime.fromtimestamp(data['media_timestamp'] / 1000),
            location=LatLon(data['latitude'], data['longitude']),
        )


@dataclass
class FlightRecordBase[T: RecordTypeName, D: ParseFlightRecordTD](RecordBase[T]):
    """Base class for flight records"""
    timestamp: float
    """Seconds since flight start"""

    @classmethod
    def from_parsed_dicts(cls, data: Iterable[D]) -> dict[datetime.datetime, Self]:
        result = {}
        for d in data:
            record = cls.from_dict(d)
            result[record.timestamp] = record
        return result

    @classmethod
    @abstractmethod
    def from_dict(cls, data: D) -> Self:
        raise NotImplementedError()



@dataclass
class ParsedInBase[
    T: Literal['in_base', 'in_full'], D: (ParsedInBaseTD | ParsedInFullTD)
](FlightRecordBase[T, D]):
    """Base class for `in_base` and `in_full` flight records"""
    drone_speed: Speed
    """Drone speed in m/s"""
    gimbal_orientation: Orientation[Literal['degrees']]
    """Gimbal orientation (pitch, roll, yaw)"""
    drone_orientation: Orientation[Literal['degrees']]
    """Drone orientation (pitch, roll, yaw)"""
    flight_control: FlightControl
    """Flight control information"""
    radar_info: RadarInfo
    """Radar information"""
    drone_altitude: float
    """Drone altitude in meters"""
    phone_heading: float
    """Phone heading (units unclear)"""
    param_1: int
    param_2: int

    RECORD_TYPE: ClassVar[Literal['in_base']] = 'in_base'

    @classmethod
    def from_dict(cls, data: ParsedInBaseTD) -> Self:
        return cls(
            timestamp=data['current_time'] / 1000,
            drone_altitude=data['drone_altitude'],
            drone_speed=Speed(data['x_speed'], data['y_speed'], data['z_speed']),
            gimbal_orientation=Orientation(
                pitch=data['gimbal_pitch'], roll=data['gimbal_roll'], yaw=data['gimbal_yaw'],
                unit='degrees',
            ),
            drone_orientation=Orientation(
                pitch=data['drone_pitch'], roll=data['drone_roll'], yaw=data['drone_yaw'],
                unit='radians',
            ).to_degrees(),
            flight_control=FlightControl.from_dict(data),
            radar_info=RadarInfo.from_dict(data),
            phone_heading=data['phone_heading'],
            param_1=data['param_1'],
            param_2=data['param_2'],
        )


@dataclass
class ParsedInFull(ParsedInBase[Literal['in_full'], ParsedInFullTD]):
    """Parsed `in_full` flight record with extended information"""
    battery_info: BatteryInfo
    """Battery information"""
    warnings: Warnings
    """Warnings"""
    rc_info: RCInfo
    """RC information"""
    flight_mode: int
    """Flight mode"""
    camera_mode: int
    """Camera mode"""
    m_mode: int
    """M mode"""
    time_left: float
    """Time left"""
    max_flight_altitude: float
    """Max flight altitude"""
    go_home_altitude: float
    """Go home altitude"""
    beginner_mode_enable: int
    """Beginner mode enable"""
    low_battery_warning_threshold: float
    """Low battery warning threshold"""
    serious_battery_warning_threshold: float
    """Serious battery warning threshold"""
    max_flight_radius: float
    """Max flight radius"""
    max_flight_horizontal_speed: float
    """Max flight horizontal speed"""
    obstacle_avoidance_enable: int | None
    """Obstacle avoidance enable"""
    radar_enable: int | None
    """Radar enable"""
    max_error: int
    """Max error"""

    param_3: int
    param_4: int
    param_5: int

    RECORD_TYPE: ClassVar[Literal['in_full']] = 'in_full'

    @classmethod
    def from_dict(cls, data: ParsedInFullTD) -> Self:
        in_base = ParsedInBase.from_dict(data)
        return cls(
            **dataclasses.asdict(in_base),
            battery_info=BatteryInfo.from_dict(data),
            warnings=Warnings.from_dict(data),
            flight_mode=data['flight_mode'],
            camera_mode=data['camera_mode'],
            rc_info=RCInfo.from_dict(data),
            m_mode=data['m_mode'],
            time_left=data['time_left'],
            max_flight_altitude=data['max_flight_altitude'],
            go_home_altitude=data['go_home_altitude'],
            beginner_mode_enable=data['beginner_mode_enable'],
            low_battery_warning_threshold=data['low_battery_warning_threshold'],
            serious_battery_warning_threshold=data['serious_battery_warning_threshold'],
            max_flight_radius=data['max_flight_radius'],
            max_flight_horizontal_speed=data['max_flight_horizontal_speed'],
            obstacle_avoidance_enable=data.get('obstacle_avoidance_enable'),
            radar_enable=data.get('radar_enable'),
            max_error=data['max_error'],
            param_3=data['param_3'],
            param_4=data['param_4'],
            param_5=data['param_5'],
        )


@dataclass
class ParsedOutBase[
    T: Literal['out_base', 'out_full'], D: (ParsedOutBaseTD | ParsedOutFullTD)
](FlightRecordBase[T, D]):
    """Base class for `out_base` and `out_full` flight records"""
    drone_location: LatLonAlt
    """The drone location (latitude, longitude, altitude)

    .. note::

        Altitude is AGL (Above Ground Level), or relative to the takeoff point.
    """
    drone_speed: Speed
    """Drone speed in m/s"""
    gimbal_orientation: Orientation[Literal['degrees']]
    """Gimbal orientation (pitch, roll, yaw)"""
    drone_orientation: Orientation[Literal['degrees']]
    """Drone orientation (pitch, roll, yaw)"""
    flight_control: FlightControl
    """Flight control information"""
    radar_info: RadarInfo
    """Radar information"""

    param_1: int
    param_2: int

    RECORD_TYPE: ClassVar[Literal['out_base']] = 'out_base'

    @property
    def drone_altitude(self) -> float:
        return self.drone_location.altitude

    @classmethod
    def from_dict(cls, data: ParsedOutBaseTD) -> Self:
        return cls(
            timestamp=data['current_time'] / 1000,
            drone_location=LatLonAlt(
                data['drone_latitude'],
                data['drone_longitude'],
                data['drone_altitude'],
            ),
            drone_speed=Speed(data['x_speed'], data['y_speed'], data['z_speed']),
            gimbal_orientation=Orientation(
                pitch=data['gimbal_pitch'], roll=data['gimbal_roll'], yaw=data['gimbal_yaw'],
                unit='degrees',
            ),
            drone_orientation=Orientation(
                pitch=data['drone_pitch'], roll=data['drone_roll'], yaw=data['drone_yaw'],
                unit='radians',
            ).to_degrees(),
            flight_control=FlightControl.from_dict(data),
            radar_info=RadarInfo.from_dict(data),
            param_1=data['param_1'],
            param_2=data['param_2'],
        )


@dataclass
class ParsedOutFull(ParsedOutBase[Literal['out_full'], ParsedOutFullTD]):
    """Parsed `out_full` flight record with extended information"""
    warnings: Warnings
    """Warnings"""
    go_home_info: GoHomeInfo
    """Go home information"""
    battery_info: BatteryInfo
    """Battery information"""
    rc_info: RCInfo
    """Remote control information"""

    phone_heading: float
    """Phone heading (units unclear)"""
    flight_mode: int
    """Flight mode"""
    camera_mode: int
    """Camera mode"""
    gps_signal_level: int
    """GPS signal level"""
    beginner_mode: bool
    """Beginner mode"""
    m_mode: int
    """M mode"""
    max_flight_radius: float
    """Max flight radius"""
    max_flight_horizontal_speed: float
    """Max flight horizontal speed"""
    obstacle_avoidance_enable: int|None
    """Obstacle avoidance enable"""
    radar_enable: int|None
    """Radar enable"""
    max_error: int
    """Max error"""

    param_3: int
    param_4: int
    param_5: int

    RECORD_TYPE: ClassVar[Literal['out_full']] = 'out_full'

    @property
    def home_location(self) -> LatLon:
        """The home location (latitude, longitude)"""
        return self.go_home_info.location

    @classmethod
    def from_dict(cls, data: ParsedOutFullTD) -> Self:
        out_base = ParsedOutBase.from_dict(data)
        return cls(
            **dataclasses.asdict(out_base),
            warnings=Warnings.from_dict(data),
            go_home_info=GoHomeInfo.from_dict(data),
            battery_info=BatteryInfo.from_dict(data),
            phone_heading=data['phone_heading'],
            flight_mode=data['flight_mode'],
            camera_mode=data['camera_mode'],
            gps_signal_level=data['gps_signal_level'],
            beginner_mode=data['beginner_mode_enable'] == 1,
            rc_info=RCInfo.from_dict(data),
            m_mode=data['m_mode'],
            max_flight_radius=data['max_flight_radius'],
            max_flight_horizontal_speed=data['max_flight_horizontal_speed'],
            obstacle_avoidance_enable=data.get('obstacle_avoidance_enable'),
            radar_enable=data.get('radar_enable'),
            max_error=data['max_error'],
            param_3=data['param_3'],
            param_4=data['param_4'],
            param_5=data['param_5'],
        )


class ParsedRecords(TypedDict):
    """All parsed records from a flight log, using their timestamp as the key"""
    in_base: dict[datetime.datetime, ParsedInBase]
    """Parsed `in_base` flight records"""
    in_full: dict[datetime.datetime, ParsedInFull]
    """Parsed `in_full` flight records"""
    out_base: dict[datetime.datetime, ParsedOutBase]
    """Parsed `out_base` flight records"""
    out_full: dict[datetime.datetime, ParsedOutFull]
    """Parsed `out_full` flight records"""
    image: dict[datetime.datetime, ParsedImage]
    """Parsed `image` flight records"""
    video: dict[datetime.datetime, ParsedVideo]
    """Parsed `video` flight records"""


type ParsedRecordType = ParsedInBase | ParsedInFull | ParsedOutBase | ParsedOutFull | ParsedImage | ParsedVideo
"""Union of all possible parsed record types"""


class ModelResult(NamedTuple):
    """The result of parsing a flight log, including all records and metadata"""
    filename: str
    """Name of the log file"""
    header: ParsedHead
    """Parsed header information"""
    records: ParsedRecords
    """All parsed records, organized by type and timestamp"""

    def iter_records_by_type[T: (RecordBase)](self, *record_types: type[T]) -> Iterator[T]:
        """Iterate over all records of the specified types, sorted by timestamp"""
        type_map = {
            cls.get_record_type(): cls
            for cls in record_types
        }
        all_keys: list[tuple[datetime.datetime, RecordTypeName]] = []
        for key in type_map.keys():
            all_keys.extend((dt, key) for dt in self.records[key].keys())

        for key in sorted(all_keys):
            dt, record_type = key
            assert record_type != 'head'
            o = self.records[record_type][dt]
            assert isinstance(o, record_types)
            yield o


    @classmethod
    def from_parse_result(cls, parse_result: ParseResult) -> Self:
        """Create an instance from a :class:`~.record_parser.ParseResult`"""
        records: ParsedRecords = {
            'in_base': ParsedInBase.from_parsed_dicts(parse_result.records['in_base']),
            'in_full': ParsedInFull.from_parsed_dicts(parse_result.records['in_full']),
            'out_base': ParsedOutBase.from_parsed_dicts(parse_result.records['out_base']),
            'out_full': ParsedOutFull.from_parsed_dicts(parse_result.records['out_full']),
            'image': ParsedImage.from_parsed_dicts(parse_result.records['image']),
            'video': ParsedVideo.from_parsed_dicts(parse_result.records['video']),
        }
        return cls(
            filename=parse_result.filename,
            header=ParsedHead.from_dict(parse_result.header),
            records=records,
        )

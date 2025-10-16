from __future__ import annotations
import json
from typing import TypedDict, NamedTuple, Literal, Sequence, Self
from pathlib import Path
import datetime
from dataclasses import dataclass
from fractions import Fraction

from loguru import logger

from ..spatial import LatLon, LatLonAlt, GeoBox, PositionMeters, Vector3D, Speed, Orientation
from ..parser.model import (
    ModelResult, ParsedOutFull, ParsedInFull, ParsedVideo, ParsedImage, FlightControl,
    RadarInfo, Warnings, RCInfo, BatteryInfo,
)
from ..config import Config
from .media import VideoCacheData



class Flight(NamedTuple):
    """A single flight log with associated metadata and records"""
    filename: str
    """The log filename"""
    aircraft_serial_number: str
    """The aircraft serial number"""
    battery_serial_number: str
    """The battery serial number"""
    drone_type: int
    """The drone type"""
    timezone_offset: int
    """The timezone offset in seconds from UTC"""
    start_time: datetime.datetime
    """The start time of the flight"""
    duration: datetime.timedelta
    """The duration of the flight"""
    distance: float
    """The total distance flown in meters"""
    max_altitude: float
    """The maximum altitude reached in meters"""
    battery_summary: BatterySummary
    """A summary of the battery usage during the flight"""
    # max_speed: float  # in m/s
    # max_flight_radius: float  # in meters
    start_location: LatLon
    """The starting location of the flight"""
    bounding_box: GeoBox
    """The bounding box of the flight path"""
    track_items: list[TrackItem]
    """The detailed track items recorded during the flight"""
    video_items: list[VideoItem]
    """The video items associated with the flight"""
    image_items: list[ImageItem]
    """The image items associated with the flight"""

    class SerializeTD(TypedDict):
        """:meta private:"""
        filename: str
        aircraft_serial_number: str
        battery_serial_number: str
        drone_type: int
        timezone_offset: int
        start_time: str
        duration: float
        distance: float
        max_altitude: float
        battery_summary: BatterySummary.SerializeTD
        start_location: LatLon.SerializeTD
        bounding_box: GeoBox.SerializeTD
        osm_url: str
        track_items: list[TrackItem.SerializeTD]
        video_items: list[VideoItem.SerializeTD]
        image_items: list[ImageItem.SerializeTD]

    @property
    def osm_url(self) -> str:
        return self.bounding_box.osm_url

    @classmethod
    def from_model(cls, model: ModelResult) -> Self:
        """Create a Flight instance from a parsed :class:`~.parser.model.ModelResult`"""
        track_items: list[TrackItem] = []
        for i, parsed in enumerate(model.iter_records_by_type(ParsedOutFull, ParsedInFull)):
            track_item = TrackItem.from_parsed(i, model.header.flight_at, parsed)
            track_items.append(track_item)
        # for i, parsed in enumerate(model.iter_sorted_records('out_full')):
        #     track_item = TrackItem.from_parsed(i, model.header.flight_at, parsed)
        #     track_items.append(track_item)
        video_items = [
            VideoItem.from_parsed(model.header.flight_at, parsed)
            for parsed in model.iter_records_by_type(ParsedVideo)
        ]
        image_items = [
            ImageItem.from_parsed(model.header.flight_at, parsed)
            for parsed in model.iter_records_by_type(ParsedImage)
        ]
        bbox = GeoBox.from_points(
            [item.location for item in track_items if item.location is not None]
        )
        return cls(
            filename=model.filename,
            aircraft_serial_number=model.header.aircraft_sn,
            battery_serial_number=model.header.battery_sn,
            drone_type=model.header.drone_type,
            timezone_offset=model.header.time_zone,
            start_time=model.header.flight_at,
            duration=datetime.timedelta(seconds=model.header.flight_duration),
            distance=model.header.distance,
            max_altitude=model.header.max_altitude,
            # max_speed=model.out_full.max_speed,
            # max_flight_radius=model.out_full.max_flight_radius,
            battery_summary=BatterySummary.from_records(model.header.battery_sn, track_items),
            start_location=model.header.start_location,
            bounding_box=bbox,
            track_items=track_items,
            video_items=video_items,
            image_items=image_items,
        )

    def serialize(self) -> SerializeTD:
        return {
            'filename': self.filename,
            'aircraft_serial_number': self.aircraft_serial_number,
            'battery_serial_number': self.battery_serial_number,
            'drone_type': self.drone_type,
            'timezone_offset': self.timezone_offset,
            'start_time': self.start_time.isoformat(),
            'duration': self.duration.total_seconds(),
            'distance': self.distance,
            'max_altitude': self.max_altitude,
            'battery_summary': self.battery_summary.serialize(),
            'start_location': self.start_location.serialize(),
            'bounding_box': self.bounding_box.serialize(),
            'osm_url': self.osm_url,
            'track_items': [item.serialize() for item in self.track_items],
            'video_items': [item.serialize() for item in self.video_items],
            'image_items': [item.serialize() for item in self.image_items],
        }

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            filename=data['filename'],
            aircraft_serial_number=data['aircraft_serial_number'],
            battery_serial_number=data['battery_serial_number'],
            drone_type=data['drone_type'],
            timezone_offset=data['timezone_offset'],
            start_time=datetime.datetime.fromisoformat(data['start_time']),
            duration=datetime.timedelta(seconds=data['duration']),
            distance=data['distance'],
            max_altitude=data['max_altitude'],
            battery_summary=BatterySummary.deserialize(data['battery_summary']),
            start_location=LatLon.deserialize(data['start_location']),
            bounding_box=GeoBox.deserialize(data['bounding_box']),
            track_items=[
                TrackItem.deserialize(item) for item in data['track_items']
            ],
            video_items=[
                VideoItem.deserialize(item) for item in data['video_items']
            ],
            image_items=[
                ImageItem.deserialize(item) for item in data['image_items']
            ],
        )

    def save(self, path: Path|str) -> None:
        """Save the flight data to a JSON file at the given path"""
        path = Path(path)
        path.write_text(json.dumps(self.serialize(), indent=2))
    # def save(self, config: Config) -> None:
    #     data_dir = config.data_dir
    #     if data_dir is None:
    #         raise ValueError('Config data_dir is not set')
    #     out_file = data_dir / f'{self.filename}.json'
    #     out_file.write_text(json.dumps(self.serialize(), indent=2))

    @classmethod
    def load(cls, path: Path|str) -> Self:
        """Load flight data from a JSON file at the given path"""
        path = Path(path)
        data = json.loads(path.read_text())
        return cls.deserialize(data)

    @classmethod
    def get_data_filename(cls, log_filename: str, config: Config) -> Path:
        data_dir = config.raw_log_dir
        if data_dir is None:
            raise ValueError('Config.raw_log_dir is not set')
        base_name = Path(log_filename).stem
        return data_dir / f'{base_name}.json'

    def search_videos(self, config: Config) -> bool:
        """Search for video files associated with this flight"""
        cache_data = VideoCacheData.load_from_cache(config)
        changed = False
        for item in self.video_items:
            logger.debug(f"Searching for video files for item {item.filename}...")
            if item.local_filename is not None:
                continue
            results = cache_data.search_from_flight_item(item, config)
            if not results:
                continue
            best = results[0]
            if best.confidence < 0.5:
                continue
            if best.item.filename == item.local_filename:
                continue
            logger.info(f"Matched video file {item.filename} to {best.item.filename} with confidence {best.confidence:.2f}")
            item.local_filename = best.item.filename
            item.fps = best.item.fps
            item.duration = best.item.duration
            changed = True
        return changed


type SummaryValueT = int|float|list[int]|list[float]

class SummaryItem[T: SummaryValueT](NamedTuple):
    """A summary item with a value, index, and time offset
    """
    value: T
    """The item value"""
    index: int
    """The item index"""
    time_offset: float
    """The item time offset in seconds since start of flight"""

    class SerializeTD[ST: SummaryValueT](TypedDict):
        """:meta private:"""
        value: ST
        index: int
        time_offset: float

    def serialize(self) -> SerializeTD[T]:
        return {
            'value': self.value,
            'index': self.index,
            'time_offset': self.time_offset,
        }

    @classmethod
    def deserialize(cls, data: SerializeTD[T]) -> Self:
        return cls(
            value=data['value'],
            index=data['index'],
            time_offset=data['time_offset'],
        )


class BatterySummary(NamedTuple):
    serial_number: str
    """The battery's :attr:`serial_number <.parser.model.ParsedHead.battery_sn>`"""
    capacity: float
    """The :attr:`full charge volume <.parser.model.BatteryInfo.full_charge_volume>` in mAh"""
    max_voltage: SummaryItem[float]
    """The maximum :attr:`voltage <.parser.model.BatteryInfo.current_voltage>` in VDC"""
    min_voltage: SummaryItem[float]
    """The minimum :attr:`voltage <.parser.model.BatteryInfo.current_voltage>` in VDC"""
    max_current: SummaryItem[float]
    """The maximum :attr:`current output <.parser.model.BatteryInfo.current_current>` in Amps"""
    max_power: SummaryItem[float]
    """The maximum :attr:`power output <.parser.model.BatteryInfo.current_electricity>` in Watts"""
    max_temperature: SummaryItem[float]
    """The maximum :attr:`~.parser.model.BatteryInfo.temperature` in Celsius"""
    min_temperature: SummaryItem[float]
    """The minimum :attr:`~.parser.model.BatteryInfo.temperature` in Celsius"""
    max_remaining: SummaryItem[float]
    """The maximum :attr:`remaining power <.parser.model.BatteryInfo.remain_power_percent>` in percent"""
    min_remaining: SummaryItem[float]
    """The minimum :attr:`remaining power <.parser.model.BatteryInfo.remain_power_percent>` in percent"""

    class SerializeTD(TypedDict):
        """:meta private:"""
        serial_number: str
        capacity: float
        max_voltage: SummaryItem.SerializeTD[float]
        min_voltage: SummaryItem.SerializeTD[float]
        max_current: SummaryItem.SerializeTD[float]
        max_power: SummaryItem.SerializeTD[float]
        max_temperature: SummaryItem.SerializeTD[float]
        min_temperature: SummaryItem.SerializeTD[float]
        max_remaining: SummaryItem.SerializeTD[float]
        min_remaining: SummaryItem.SerializeTD[float]

    def serialize(self) -> SerializeTD:
        return {
            'serial_number': self.serial_number,
            'capacity': self.capacity,
            'max_voltage': self.max_voltage.serialize(),
            'min_voltage': self.min_voltage.serialize(),
            'max_current': self.max_current.serialize(),
            'max_power': self.max_power.serialize(),
            'max_temperature': self.max_temperature.serialize(),
            'min_temperature': self.min_temperature.serialize(),
            'max_remaining': self.max_remaining.serialize(),
            'min_remaining': self.min_remaining.serialize(),
        }

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            serial_number=data['serial_number'],
            capacity=data['capacity'],
            max_voltage=SummaryItem.deserialize(data['max_voltage']),
            min_voltage=SummaryItem.deserialize(data['min_voltage']),
            max_current=SummaryItem.deserialize(data['max_current']),
            max_power=SummaryItem.deserialize(data['max_power']),
            max_temperature=SummaryItem.deserialize(data['max_temperature']),
            min_temperature=SummaryItem.deserialize(data['min_temperature']),
            max_remaining=SummaryItem.deserialize(data['max_remaining']),
            min_remaining=SummaryItem.deserialize(data['min_remaining']),
        )

    @classmethod
    def from_records(cls, serial_number: str, records: Sequence[TrackItem]) -> Self:
        if not len(records):
            raise ValueError("No records provided")
        voltages = [
            (rec.battery.current_voltage, rec.index, rec.time_offset)
            for rec in records
        ]
        currents = [
            (rec.battery.current_current, rec.index, rec.time_offset)
            for rec in records
        ]
        temperatures = [
            (rec.battery.temperature, rec.index, rec.time_offset)
            for rec in records
        ]
        remainings = [
            (rec.battery.remain_power_percent, rec.index, rec.time_offset)
            for rec in records
        ]
        powers = [
            (rec.battery.current_electricity, rec.index, rec.time_offset)
            for rec in records
        ]
        capacity = records[0].battery.full_charge_volume
        assert all(capacity == rec.battery.full_charge_volume for rec in records), "Battery capacity changed during flight"
        return cls(
            serial_number=serial_number,
            capacity=capacity,
            max_voltage=SummaryItem(*max(voltages)),
            min_voltage=SummaryItem(*min(voltages)),
            max_current=SummaryItem(*max(currents)),
            max_power=SummaryItem(*max(powers)),
            max_temperature=SummaryItem(*max(temperatures)),
            min_temperature=SummaryItem(*min(temperatures)),
            max_remaining=SummaryItem(*max(remainings)),
            min_remaining=SummaryItem(*min(remainings)),
        )


class TrackItem(NamedTuple):
    """A single track item recorded during a flight"""
    index: int
    """The item index"""
    time: datetime.datetime
    """The item datetime"""
    time_offset: float
    """The item time offset in seconds since the flight's :attr:`~Flight.start_time`"""
    location: LatLon|None
    """The drone's location at this time, or None if not available"""
    altitude: float
    """The drone's altitude in meters"""
    drone_orientation: Orientation[Literal['degrees']]
    """The drone's orientation (pitch, roll, yaw) in degrees"""
    gimbal_orientation: Orientation[Literal['degrees']]
    """The gimbal's orientation (pitch, roll, yaw) in degrees"""
    speed: Speed
    """The drone's speed in m/s"""
    relative_location: PositionMeters|None
    """The drone's location relative to the flight :attr:`~Flight.start_location`
    in meters, or None if :attr:`location` is not available
    """
    distance: float|None
    """The distance from the :attr:`~Flight.start_location` in meters,
    or None if :attr:`location` is not available
    """
    phone_heading: float
    """The phone's heading (units are unknown)"""
    max_error: int
    """The maximum error (value format is unknown)"""
    gps_signal_level: int|None
    """The GPS signal level (possibly 0-5), or None if not available"""
    flight_controls: FlightControl
    """The flight control inputs at this time"""
    battery: BatteryInfo
    """The battery information at this time"""
    radar: RadarInfo
    """The radar information at this time"""
    rc_info: RCInfo
    """The RC information at this time"""
    warnings: Warnings
    """The warnings active at this time"""

    class SerializeTD(TypedDict):
        """:meta private:"""
        index: int
        time: str
        time_offset: float
        location: LatLon.SerializeTD|None
        altitude: float
        drone_orientation: Orientation.SerializeTD
        gimbal_orientation: Orientation.SerializeTD
        speed: Speed.SerializeTD
        relative_location: PositionMeters.SerializeTD|None
        distance: float|None
        phone_heading: float
        max_error: int
        gps_signal_level: int|None
        flight_controls: FlightControl.SerializeTD
        battery: BatteryInfo.SerializeTD
        radar: RadarInfo.SerializeTD
        rc_info: RCInfo.SerializeTD
        warnings: Warnings.SerializeTD

    @classmethod
    def from_parsed(
        cls,
        index: int,
        start_time: datetime.datetime,
        parsed: ParsedOutFull|ParsedInFull
    ) -> Self:
        """Create an instance from a parsed record"""
        if isinstance(parsed, ParsedOutFull):
            home_location = LatLonAlt(
                parsed.home_location.latitude,
                parsed.home_location.longitude,
                0,
            )
            relative_location = parsed.drone_location.to_position_meters(home_location)
            distance = parsed.go_home_info.distance
            location = LatLon(
                parsed.drone_location.latitude,
                parsed.drone_location.longitude,
            )
            gps_signal_level = parsed.gps_signal_level
        else:
            relative_location = None
            distance = None
            location = None
            gps_signal_level = None
        altitude = parsed.drone_altitude
        return cls(
            index=index,
            time=start_time + datetime.timedelta(seconds=parsed.timestamp),
            time_offset=parsed.timestamp,
            location=location,
            altitude=altitude,
            drone_orientation=parsed.drone_orientation,
            gimbal_orientation=parsed.gimbal_orientation,
            speed=parsed.drone_speed,
            relative_location=relative_location,
            distance=distance,
            phone_heading=parsed.phone_heading,
            max_error=parsed.max_error,
            gps_signal_level=gps_signal_level,
            flight_controls=parsed.flight_control.with_offset(),
            battery=parsed.battery_info,
            radar=parsed.radar_info,
            rc_info=parsed.rc_info,
            warnings=parsed.warnings,
        )

    def serialize(self) -> SerializeTD:
        return {
            'index': self.index,
            'time': self.time.isoformat(),
            'time_offset': self.time_offset,
            'location': None if self.location is None else self.location.serialize(),
            'altitude': self.altitude,
            'drone_orientation': self.drone_orientation.serialize(),
            'gimbal_orientation': self.gimbal_orientation.serialize(),
            'speed': self.speed.serialize(),
            'relative_location': None if self.relative_location is None else self.relative_location.serialize(),
            'distance': self.distance,
            'phone_heading': self.phone_heading,
            'max_error': self.max_error,
            'gps_signal_level': self.gps_signal_level,
            'flight_controls': self.flight_controls.serialize(),
            'battery': self.battery.serialize(),
            'radar': self.radar.serialize(),
            'rc_info': self.rc_info.serialize(),
            'warnings': self.warnings.serialize(),
        }

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            index=data['index'],
            time=datetime.datetime.fromisoformat(data['time']),
            time_offset=data['time_offset'],
            location=None if data['location'] is None else LatLon.deserialize(data['location']),
            altitude=data['altitude'],
            drone_orientation=Orientation.deserialize(data['drone_orientation'], 'degrees'),
            gimbal_orientation=Orientation.deserialize(data['gimbal_orientation'], 'degrees'),
            speed=Speed.deserialize(data['speed']),
            relative_location=None if data['relative_location'] is None else PositionMeters.deserialize(data['relative_location']),
            distance=data['distance'],
            phone_heading=data['phone_heading'],
            max_error=data['max_error'],
            gps_signal_level=data['gps_signal_level'],
            flight_controls=FlightControl.deserialize(data['flight_controls']),
            battery=BatteryInfo.deserialize(data['battery']),
            radar=RadarInfo.deserialize(data['radar']),
            rc_info=RCInfo.deserialize(data['rc_info']),
            warnings=Warnings.deserialize(data['warnings']),
        )

@dataclass
class VideoItem:
    """Represents a video item in the flight data."""
    filename: str
    """The video filename. This does not match the files stored on the SD card."""
    local_filename: Path|None
    """The local path to the video file, if found."""
    start_time: datetime.datetime
    """The start time of the video."""
    start_time_offset: float
    """The start time offset in seconds since the flight's :attr:`~Flight.start_time`"""
    location: LatLon
    """The location when recording started"""
    duration: datetime.timedelta
    """The duration of the video"""
    fps: Fraction|None
    """The frame rate of the video, if known"""

    class SerializeTD(TypedDict):
        """:meta private:"""
        filename: str
        local_filename: str|None
        start_time: str
        start_time_offset: float
        location: LatLon.SerializeTD
        duration: float
        fps: str|None


    @property
    def end_time(self) -> datetime.datetime:
        """The end time of the video."""
        return self.start_time + self.duration

    @property
    def end_time_offset(self) -> float:
        """The end time offset in seconds since the flight's :attr:`~Flight.start_time`"""
        return self.start_time_offset + self.duration.total_seconds()

    @property
    def fps_float(self) -> float|None:
        """The frame rate as a float, or None if not known"""
        if self.fps is None:
            return None
        return float(self.fps)

    @property
    def fps_str(self) -> str|None:
        """The frame rate as a string, or None if not known"""
        if self.fps is None:
            return None
        return f"{self.fps.numerator}/{self.fps.denominator}"

    @classmethod
    def from_parsed(
        cls, flight_start_time: datetime.datetime, parsed: ParsedVideo
    ) -> Self:
        """Create an instance from a parsed record"""
        start_time_offset = parsed.timestamp - flight_start_time
        return cls(
            filename=parsed.filename,
            local_filename=None,
            start_time=parsed.timestamp,
            start_time_offset=start_time_offset.total_seconds(),
            location=parsed.location,
            duration=datetime.timedelta(seconds=parsed.duration),
            fps=None,
        )

    def serialize(self) -> SerializeTD:
        return {
            'filename': self.filename,
            'local_filename': None if self.local_filename is None else str(self.local_filename),
            'start_time': self.start_time.isoformat(),
            'start_time_offset': self.start_time_offset,
            'location': self.location.serialize(),
            'duration': self.duration.total_seconds(),
            'fps': self.fps_str,
        }

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            filename=data['filename'],
            local_filename=None if data['local_filename'] is None else Path(data['local_filename']),
            start_time=datetime.datetime.fromisoformat(data['start_time']),
            start_time_offset=data['start_time_offset'],
            location=LatLon.deserialize(data['location']),
            duration=datetime.timedelta(seconds=data['duration']),
            fps=None if data['fps'] is None else Fraction(data['fps']),
        )


class ImageItem(NamedTuple):
    """Represents an image item in the flight data."""
    filename: str
    """The image filename."""
    time: datetime.datetime
    """The time when the image was taken."""
    time_offset: float
    """The time offset in seconds since the flight's :attr:`~Flight.start_time`"""
    location: LatLon
    """The location when the image was taken."""

    class SerializeTD(TypedDict):
        """:meta private:"""
        filename: str
        time: str
        time_offset: float
        location: LatLon.SerializeTD

    @classmethod
    def from_parsed(
        cls, flight_start_time: datetime.datetime, parsed: ParsedImage
    ) -> Self:
        time_offset = (parsed.timestamp - flight_start_time).total_seconds()
        return cls(
            filename=parsed.filename,
            time=parsed.timestamp,
            time_offset=time_offset,
            location=parsed.location,
        )

    def serialize(self) -> SerializeTD:
        return {
            'filename': self.filename,
            'time': self.time.isoformat(),
            'time_offset': self.time_offset,
            'location': self.location.serialize(),
        }

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            filename=data['filename'],
            time=datetime.datetime.fromisoformat(data['time']),
            time_offset=data['time_offset'],
            location=LatLon.deserialize(data['location']),
        )

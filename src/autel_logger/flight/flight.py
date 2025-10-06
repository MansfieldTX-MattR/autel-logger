from __future__ import annotations
import json
from typing import TypedDict, NamedTuple, Literal, Self
from pathlib import Path
import datetime
from dataclasses import dataclass
from fractions import Fraction

from loguru import logger

from ..spatial import LatLon, LatLonAlt, GeoBox, PositionMeters, Vector3D, Speed, Orientation
from ..parser.model import (
    ModelResult, ParsedOutFull, ParsedInFull, ParsedVideo, ParsedImage, FlightControl,
    RadarInfo, RCInfo, BatteryInfo,
)
from ..config import Config
from .media import VideoCacheData

# class Battery(TypedDict):
#     serial_number: str
#     design_volume: float
#     full_charge_volume: float
#     cycle_count: int
#     cell_count: int


class Flight(NamedTuple):
    filename: str
    aircraft_serial_number: str
    battery_serial_number: str
    drone_type: int
    start_time: datetime.datetime
    duration: datetime.timedelta
    distance: float  # in meters
    max_altitude: float  # in meters
    # max_speed: float  # in m/s
    # max_flight_radius: float  # in meters
    start_location: LatLon
    bounding_box: GeoBox
    track_items: list[TrackItem]
    video_items: list[VideoItem]
    image_items: list[ImageItem]

    class SerializeTD(TypedDict):
        filename: str
        aircraft_serial_number: str
        battery_serial_number: str
        drone_type: int
        start_time: str
        duration: float
        distance: float
        max_altitude: float
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
            start_time=model.header.flight_at,
            duration=datetime.timedelta(seconds=model.header.flight_duration),
            distance=model.header.distance,
            max_altitude=model.header.max_altitude,
            # max_speed=model.out_full.max_speed,
            # max_flight_radius=model.out_full.max_flight_radius,
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
            'start_time': self.start_time.isoformat(),
            'duration': self.duration.total_seconds(),
            'distance': self.distance,
            'max_altitude': self.max_altitude,
            'start_location': {
                'latitude': self.start_location.latitude,
                'longitude': self.start_location.longitude,
            },
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
            start_time=datetime.datetime.fromisoformat(data['start_time']),
            duration=datetime.timedelta(seconds=data['duration']),
            distance=data['distance'],
            max_altitude=data['max_altitude'],
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
            changed = True
        return changed


class TrackItem(NamedTuple):
    index: int
    time: datetime.datetime
    time_offset: float  # seconds since start of flight
    location: LatLon|None
    altitude: float
    drone_orientation: Orientation[Literal['degrees']]
    gimbal_orientation: Orientation[Literal['degrees']]
    speed: Speed
    relative_location: PositionMeters|None  # in meters from start location
    distance: float|None  # in meters from start location
    flight_controls: FlightControl
    battery: BatteryInfo
    radar: RadarInfo
    rc_info: RCInfo

    class SerializeTD(TypedDict):
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
        flight_controls: FlightControl.SerializeTD
        battery: BatteryInfo.SerializeTD
        radar: RadarInfo.SerializeTD
        rc_info: RCInfo.SerializeTD

    @classmethod
    def from_parsed(
        cls,
        index: int,
        start_time: datetime.datetime,
        parsed: ParsedOutFull|ParsedInFull
    ) -> Self:
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
        else:
            relative_location = None
            distance = None
            location = None
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
            flight_controls=parsed.flight_control.with_offset(),
            battery=parsed.battery_info,
            radar=parsed.radar_info,
            rc_info=parsed.rc_info,
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
            'flight_controls': self.flight_controls.serialize(),
            'battery': self.battery.serialize(),
            'radar': self.radar.serialize(),
            'rc_info': self.rc_info.serialize(),
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
            flight_controls=FlightControl.deserialize(data['flight_controls']),
            battery=BatteryInfo.deserialize(data['battery']),
            radar=RadarInfo.deserialize(data['radar']),
            rc_info=RCInfo.deserialize(data['rc_info']),
        )

@dataclass
class VideoItem:
    filename: str
    local_filename: Path|None
    start_time: datetime.datetime
    start_time_offset: float  # seconds since start of flight
    location: LatLon
    duration: datetime.timedelta
    fps: Fraction|None

    class SerializeTD(TypedDict):
        filename: str
        local_filename: str|None
        start_time: str
        start_time_offset: float
        location: LatLon.SerializeTD
        duration: float
        fps: str|None


    @property
    def end_time(self) -> datetime.datetime:
        return self.start_time + self.duration

    @property
    def end_time_offset(self) -> float:
        return self.start_time_offset + self.duration.total_seconds()

    @property
    def fps_float(self) -> float|None:
        if self.fps is None:
            return None
        return float(self.fps)

    @property
    def fps_str(self) -> str|None:
        if self.fps is None:
            return None
        return f"{self.fps.numerator}/{self.fps.denominator}"

    @classmethod
    def from_parsed(
        cls, flight_start_time: datetime.datetime, parsed: ParsedVideo
    ) -> Self:
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
    filename: str
    time: datetime.datetime
    time_offset: float  # seconds since start of flight
    location: LatLon

    class SerializeTD(TypedDict):
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

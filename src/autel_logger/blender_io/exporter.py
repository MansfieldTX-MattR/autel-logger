from __future__ import annotations
from typing import Literal
from pathlib import Path
import json

from .types import *
from ..spatial import Orientation
from ..flight.flight import Flight, TrackItem



def build_flight_path_data(flight: Flight) -> BlFlightPathData:
    # vertices = [
    #     (item.relative_location.x, item.relative_location.y, item.relative_location.z)
    #     for item in flight.track_items
    # ]
    vertices = []
    vertex_times = []
    for item in flight.track_items:
        xy = item.relative_location
        z = item.altitude
        if xy is None:
            continue
        vertices.append((xy.x, xy.y, z))
        vertex_times.append(item.time_offset)
    return BlFlightPathData(
        name='Flight Path',
        type='CURVE',
        vertices=vertices,
        vertex_times=vertex_times,
    )


def build_track_items_data(flight: Flight) -> list[BlTrackItemData]:
    items = []
    prev_drone_rot: Orientation[Literal['radians']] | None = None
    prev_gimbal_rot: Orientation[Literal['radians']] | None = None
    orientation_offset = Orientation(0, 0, 180, 'degrees').to_radians()
    for item in flight.track_items:
        drone_rot = item.drone_orientation.to_radians()
        gimbal_rot = item.gimbal_orientation.to_radians()

        # Adjust drone rotation to match Blender's coordinate system
        drone_rot = drone_rot.inverted(pitch=True, roll=False, yaw=True).normalize()
        drone_rot = drone_rot + orientation_offset

        # Adjust gimbal rotation to match Blender's coordinate system
        gimbal_rot = gimbal_rot.inverted(pitch=True, roll=False, yaw=True).normalize()
        gimbal_rot = gimbal_rot + orientation_offset

        gimbal_relative_rot = gimbal_rot - drone_rot
        gimbal_relative_rot = gimbal_relative_rot.normalize()
        # gimbal_rot = gimbal_relative_rot


        if prev_drone_rot is not None:
            drone_rot = drone_rot.wrap_yaw(prev_drone_rot)
        prev_drone_rot = drone_rot

        if prev_gimbal_rot is not None:
            gimbal_rot = gimbal_rot.wrap_yaw(prev_gimbal_rot)
        prev_gimbal_rot = gimbal_rot

        # drone_rot, gimbal_rot = drone_rot.to_degrees(), gimbal_rot.to_degrees()
        loc = item.location
        rel_loc = item.relative_location
        items.append(BlTrackItemData(
            index=item.index,
            time=item.time_offset,
            location=None if loc is None else loc.serialize(),
            altitude=item.altitude,
            drone_orientation=(drone_rot.pitch, drone_rot.roll, drone_rot.yaw),
            gimbal_orientation=(gimbal_rot.pitch, gimbal_rot.roll, gimbal_rot.yaw),
            gimbal_orientation_relative=(gimbal_relative_rot.pitch, gimbal_relative_rot.roll, gimbal_relative_rot.yaw),
            speed=(item.speed.x, item.speed.y, item.speed.z),
            relative_location=None if rel_loc is None else (rel_loc.x, rel_loc.y),
            relative_height=item.altitude,
            distance=item.distance,
            flight_controls=BlFlightControlsData(
                left_stick=BlFlightStickData(
                    x=item.flight_controls.left_stick.horizontal,
                    y=item.flight_controls.left_stick.vertical,
                ),
                right_stick=BlFlightStickData(
                    x=item.flight_controls.right_stick.horizontal,
                    y=item.flight_controls.right_stick.vertical,
                ),
                is_calibrated=item.flight_controls_calibrated,
            )
        ))
    return items


def build_media_items_data(flight: Flight) -> tuple[list[BlVideoItemData], list[BlImageItemData]]:
    video_items = []
    for item in flight.video_items:
        fps = None
        if item.fps is not None:
            fps = float(item.fps)
        video_items.append(BlVideoItemData(
            filename=str(item.local_filename if item.local_filename is not None else item.filename),
            start_time=item.start_time_offset,
            end_time=item.end_time_offset,
            duration=item.duration.total_seconds(),
            location=item.location.serialize(),
            frame_rate=fps,
            exists_locally=item.local_filename is not None and item.local_filename.exists(),
        ))
    image_items = []
    for item in flight.image_items:
        image_items.append(BlImageItemData(
            filename=item.filename,
            time=item.time_offset,
            location=item.location.serialize(),
        ))
    return video_items, image_items


def build_export_data(flight: Flight) -> BlExportData:
    video_items, image_items = build_media_items_data(flight)
    camera_info: BlCameraInfoData|None = None
    if flight.camera_info is not None:
        camera_info = BlCameraInfoData(
            focal_length=flight.camera_info.focal_length,
            sensor_width=flight.camera_info.sensor_width,
            sensor_height=flight.camera_info.sensor_height,
        )
    return BlExportData(
        filename=flight.filename,
        distance=flight.distance,
        max_altitude=flight.max_altitude,
        start_location=flight.start_location.serialize(),
        flight_path=build_flight_path_data(flight),
        track_items=build_track_items_data(flight),
        video_items=video_items,
        image_items=image_items,
        start_timestamp=flight.start_time.timestamp(),
        start_time=flight.start_time.isoformat(),
        duration=flight.duration.total_seconds(),
        camera_info=camera_info,
    )


def export_flight_to_json(flight: Flight, filename: Path, indent: int = 2) -> None:
    data = build_export_data(flight)
    filename.write_text(json.dumps(data, indent=indent))


def bl_data_matches(data1: BlExportData, data2: BlExportData) -> bool:
    js1 = json.dumps(data1, indent=2, sort_keys=True)
    js2 = json.dumps(data2, indent=2, sort_keys=True)
    return js1 == js2

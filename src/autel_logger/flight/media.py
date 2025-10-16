from __future__ import annotations
from typing import TypedDict, NamedTuple, Literal, Iterator, Self, TYPE_CHECKING
from pathlib import Path
from fractions import Fraction
import json
import datetime
from dataclasses import dataclass, field
import shlex
import subprocess
import mimetypes
import fnmatch
import tempfile

from loguru import logger

from ..spatial import LatLon, LatLonAlt, Orientation
from ..config import MediaSearchPath, Config
from ..parser.model import (
    ParsedVideo, ParsedImage,
)
if TYPE_CHECKING:
    from .flight import VideoItem, ImageItem


class MediaParseError(ValueError):
    pass

@logger.catch(reraise=True)
def get_video_duration_and_fps(path: Path) -> tuple[datetime.timedelta|None, Fraction|None]:
    """Get video duration and frame rate using ffprobe"""
    # try:
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=duration,r_frame_rate',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    output = result.stdout.strip().splitlines()
    if len(output) < 2:
        raise MediaParseError(f"ffprobe output has insufficient lines: {output}")
        return None, None
    duration_str = output[1].strip()
    fps_str = output[0].strip()
    try:
        duration = datetime.timedelta(seconds=float(duration_str))
    except ValueError:
        raise
        duration = None
    try:
        num, denom = map(int, fps_str.split('/'))
        fps = Fraction(num, denom)
    except (ValueError, ZeroDivisionError):
        raise
        fps = None
    return duration, fps
    # except (subprocess.CalledProcessError, ValueError) as e:
    #     logger.exception(e)
    #     # return None, None
    #     raise


class CameraSettings(NamedTuple):
    """Represents the camera settings for a video frame."""
    iso: int
    """The ISO setting of the camera."""
    shutter: int  # in 1/x seconds
    """The shutter speed of the camera in 1/x seconds."""
    ev: float
    """The exposure value (EV) of the camera."""
    f_num: float
    """The f-number (aperture) of the camera."""

    class SerializeTD(TypedDict):
        """:meta private:"""
        iso: int
        shutter: int
        ev: float
        f_num: float

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            iso=data['iso'],
            shutter=data['shutter'],
            ev=data['ev'],
            f_num=data['f_num'],
        )

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            iso=self.iso,
            shutter=self.shutter,
            ev=self.ev,
            f_num=self.f_num,
        )

class SubtitleEntry(NamedTuple):
    """Represents a single subtitle entry from a video's subtitle stream.

    This includes timestamp, GPS coordinates, camera settings, and orientations
    taken each second during video recording.
    """
    index: int
    """The index of the subtitle entry."""
    start_pts: float
    """The start time of the subtitle entry in seconds."""
    end_pts: float
    """The end time of the subtitle entry in seconds."""
    datetime: datetime.datetime
    """The datetime when the subtitle entry was recorded."""
    home_coords: LatLon
    """The home coordinates (latitude and longitude) of the drone."""
    gps_coords: LatLonAlt
    """The current location of the drone (latitude, longitude, altitude).

    .. note::

        Altitude is in MSL (mean sea level), not AGL (above ground level) and
        stored as meters.
    """
    camera_settings: CameraSettings
    """The camera settings at the time of the subtitle entry."""
    f_pry: Orientation[Literal['degrees']]
    """The drone's orientation (pitch, roll, yaw) in degrees."""
    g_pry: Orientation[Literal['degrees']]
    """The gimbal's orientation (pitch, roll, yaw) in degrees."""

    class SerializeTD(TypedDict):
        """:meta private:"""
        index: int
        start_pts: float
        end_pts: float
        datetime: str
        home_coords: LatLon.SerializeTD
        gps_coords: LatLonAlt.SerializeTD
        camera_settings: CameraSettings.SerializeTD
        f_pry: Orientation.SerializeTD[Literal['degrees']]
        g_pry: Orientation.SerializeTD[Literal['degrees']]

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            index=self.index,
            start_pts=self.start_pts,
            end_pts=self.end_pts,
            datetime=self.datetime.isoformat(),
            home_coords=self.home_coords.serialize(),
            gps_coords=self.gps_coords.serialize(),
            camera_settings=self.camera_settings.serialize(),
            f_pry=self.f_pry.serialize(),
            g_pry=self.g_pry.serialize(),
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            index=data['index'],
            start_pts=data['start_pts'],
            end_pts=data['end_pts'],
            datetime=datetime.datetime.fromisoformat(data['datetime']),
            home_coords=LatLon.deserialize(data['home_coords']),
            gps_coords=LatLonAlt.deserialize(data['gps_coords']),
            camera_settings=CameraSettings.deserialize(data['camera_settings']),
            f_pry=Orientation.deserialize(data['f_pry'], 'degrees'),
            g_pry=Orientation.deserialize(data['g_pry'], 'degrees'),
        )

    @staticmethod
    def _parse_srt_timestamp(timestamp: str) -> float:
        """Convert SRT timestamp (e.g., "00:00:01,000") to seconds."""
        time_parts = timestamp.replace(',', '.').split(':')
        if len(time_parts) != 3:
            raise MediaParseError(f"Invalid SRT timestamp format: {timestamp}")
        hours, minutes = map(int, time_parts[:2])
        seconds = float(time_parts[2])
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds

    @staticmethod
    def _parse_latlon(coord_str: str) -> LatLon:
        """Parse a coordinate string like "W: 97.109543, N: 32.593742"."""
        parts = coord_str.split(',')
        if len(parts) != 2:
            raise MediaParseError(f"Invalid coordinate format: {coord_str}")
        lon_part = parts[0].strip()
        lat_part = parts[1].strip()
        lon_dir, lon_value = lon_part.split(':')
        lat_dir, lat_value = lat_part.split(':')
        lon = float(lon_value.strip())
        lat = float(lat_value.strip())
        if lon_dir.strip() == 'W':
            lon = -lon
        if lat_dir.strip() == 'S':
            lat = -lat
        return LatLon(latitude=lat, longitude=lon)

    @staticmethod
    def _parse_home_line(line: str) -> tuple[LatLon, datetime.datetime]:
        """Parse HOME line like "HOME(W: 97.109879, N: 32.593616) 2025-08-27 13:21:35"."""
        if not line.startswith('HOME('):
            raise MediaParseError(f"Invalid HOME line: {line}")
        coord_part, datetime_part = line[5:].rsplit(') ', 1)
        coords = SubtitleEntry._parse_latlon(coord_part)
        dt = datetime.datetime.fromisoformat(datetime_part.strip())
        return coords, dt

    @staticmethod
    def _parse_gps_line(line: str) -> LatLonAlt:
        """Parse GPS line like "GPS(W: 97.109543, N: 32.593742, 174.21m)"."""
        if not line.startswith('GPS(') or not line.endswith(')'):
            raise MediaParseError(f"Invalid GPS line: {line}")
        content = line[4:-1]
        parts = content.split(',')
        if len(parts) != 3:
            raise MediaParseError(f"Invalid GPS format: {line}")
        lon_part = parts[0].strip()
        lat_part = parts[1].strip()
        alt_part = parts[2].strip()
        lon = float(lon_part.split(':')[1].strip())
        lat = float(lat_part.split(':')[1].strip())
        alt_str = alt_part#.split(':')[1].strip()
        if alt_str.endswith('m'):
            alt_str = alt_str[:-1]
        altitude = float(alt_str)
        if lon_part.startswith('W'):
            lon = -lon
        if lat_part.startswith('S'):
            lat = -lat
        return LatLonAlt(latitude=lat, longitude=lon, altitude=altitude)

    @staticmethod
    def _parse_camera_settings(line: str) -> CameraSettings:
        """Parse camera settings line like "ISO:100 SHUTTER:400 EV:0.0 F-NUM:2.8"."""
        parts = line.split()
        if len(parts) != 4:
            raise MediaParseError(f"Invalid camera settings format: {line}")
        iso = int(parts[0].split(':')[1])
        shutter = int(parts[1].split(':')[1])
        ev = float(parts[2].split(':')[1])
        f_num = float(parts[3].split(':')[1])
        return CameraSettings(iso=iso, shutter=shutter, ev=ev, f_num=f_num)

    @staticmethod
    def _parse_orientation(line: str, prefix: str) -> Orientation[Literal['degrees']]:
        """Parse orientation line like "F.PRY (0.6°, 1.2°, -31.2°)"."""
        if prefix not in line:
            raise MediaParseError(f"Invalid orientation line: {line}")
        start = line.index(prefix) + len(prefix)
        coord_str = line[start:].strip().lstrip('(').rstrip(')')
        parts = coord_str.split(',')
        if len(parts) != 3:
            raise MediaParseError(f"Invalid orientation format: {line}")
        pitch = float(parts[0].strip().rstrip('°'))
        roll = float(parts[1].strip().rstrip('°'))
        yaw = float(parts[2].strip().rstrip('°'))
        return Orientation(pitch=pitch, roll=roll, yaw=yaw, unit='degrees')

    @classmethod
    def from_srt_lines(cls, lines: list[str]) -> Self:
        if len(lines) < 4:
            raise MediaParseError("Not enough lines for subtitle entry")
        index = int(lines[0].strip())
        time_parts = lines[1].strip().split(' --> ')
        start_str, end_str = time_parts
        start_pts = cls._parse_srt_timestamp(start_str)
        end_pts = cls._parse_srt_timestamp(end_str)
        # datetime_str = lines[2].strip().split(' ', 1)[1]
        # datetime_obj = datetime.datetime.fromisoformat(datetime_str)
        home_line = lines[2].strip()
        gps_line = lines[3].strip()
        home_coords, datetime_obj = cls._parse_home_line(home_line)
        gps_coords = cls._parse_gps_line(gps_line)
        camera_settings = cls._parse_camera_settings(lines[4].strip())
        f_pry_part = lines[5].strip().split(', G.PRY')[0]
        g_pry_part = lines[5].strip().split(', G.PRY')[1]
        g_pry_part = f'G.PRY{g_pry_part}'
        f_pry = cls._parse_orientation(f_pry_part, 'F.PRY')
        g_pry = cls._parse_orientation(g_pry_part, 'G.PRY')
        # f_pry = cls._parse_orientation(lines[5].strip(), 'F.PRY')
        # g_pry = cls._parse_orientation(lines[5].strip(), 'G.PRY')
        return cls(
            index=index,
            start_pts=start_pts,
            end_pts=end_pts,
            datetime=datetime_obj,
            home_coords=home_coords,
            gps_coords=gps_coords,
            camera_settings=camera_settings,
            f_pry=f_pry,
            g_pry=g_pry,
        )


# ffmpeg -i MAX_0009.MOV -map 0:s:0 -vn -an  MAX_0008.srt
@logger.catch(reraise=True)
def get_video_subtitles(path: Path) -> list[SubtitleEntry]:
    """Get a list of :class:`SubtitleEntry` from the video's subtitle stream.

    Subtitle stream includes entries formatted like:

    .. code-block:: text

        1
        00:00:00,000 --> 00:00:01,000
        HOME(W: 97.109879, N: 32.593616) 2025-08-27 13:21:35
        GPS(W: 97.109543, N: 32.593742, 174.21m)
        ISO:100 SHUTTER:400 EV:0.0 F-NUM:2.8
        F.PRY (0.6°, 1.2°, -31.2°), G.PRY (-40.3°, 0.0°, -31.2°)

        2
        00:00:01,000 --> 00:00:02,000
        HOME(W: 97.109879, N: 32.593616) 2025-08-27 13:21:36
        GPS(W: 97.109543, N: 32.593742, 174.23m)
        ISO:100 SHUTTER:400 EV:0.0 F-NUM:2.8
        F.PRY (1.2°, 0.3°, -31.1°), G.PRY (-40.3°, 0.0°, -31.2°)

        3
        ...

    """

    def split_entries(lines: list[str]) -> Iterator[list[str]]:
        current_entry = []
        for line in lines:
            if line.strip() == '' and current_entry:
                yield current_entry
                current_entry = []
            else:
                current_entry.append(line)
        if current_entry:
            yield current_entry

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir).resolve()
        tmp_path = tmpdir / 'subtitles.srt'
        # try:
        subprocess.run(
            ['ffmpeg', '-i', str(path), '-map', '0:s:0', '-vn', '-an', str(tmp_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        if not tmp_path.exists():
            return []
        content = tmp_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.splitlines()
        entries = []
        for entry_lines in split_entries(lines):
            try:
                entry = SubtitleEntry.from_srt_lines(entry_lines)
                entries.append(entry)
            except MediaParseError as e:
                raise
                logger.exception(e)
                continue
        return entries
        # except subprocess.CalledProcessError as e:
        #     logger.exception(e)
        #     return []


@dataclass
class VideoFileInfo:
    """Metadata and subtitle information for a video file."""
    filename: Path
    """Local path to the video file."""
    duration: datetime.timedelta
    """The actual duration of the video.

    This may differ from the duration recorded in the flight log.
    """
    fps: Fraction
    """The frame rate of the video as a fraction (e.g., 30/1)."""
    subtitle_entries: list[SubtitleEntry]
    """List of subtitle entries extracted from the video's subtitle stream."""

    class SerializeTD(TypedDict):
        """:meta private:"""
        filename: str
        duration: float  # in seconds
        fps: str  # as a string fraction, e.g. "30/1"
        subtitle_entries: list[SubtitleEntry.SerializeTD]

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            filename=str(self.filename),
            duration=self.duration.total_seconds(),
            fps=f"{self.fps.numerator}/{self.fps.denominator}",
            subtitle_entries=[entry.serialize() for entry in self.subtitle_entries],
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        num, denom = map(int, data['fps'].split('/'))
        fps = Fraction(num, denom)
        return cls(
            filename=Path(data['filename']),
            duration=datetime.timedelta(seconds=data['duration']),
            fps=fps,
            subtitle_entries=[SubtitleEntry.deserialize(entry) for entry in data['subtitle_entries']],
        )

    @classmethod
    def from_file(cls, path: Path) -> Self:
        """Create an instance by analyzing the given video file."""
        duration, fps = get_video_duration_and_fps(path)
        if duration is None or fps is None:
            raise ValueError(f"Could not get duration or fps for video file: {path}")
        subtitle_entries = get_video_subtitles(path)
        return cls(
            filename=path,
            duration=duration,
            fps=fps,
            subtitle_entries=subtitle_entries,
        )

    @property
    def fps_float(self) -> float:
        """:attr:`fps` as a float."""
        return float(self.fps)

    @property
    def fps_str(self) -> str:
        """:attr:`fps` as a string fraction, e.g. "30/1"."""
        return f"{self.fps.numerator}/{self.fps.denominator}"

    @property
    def start_time(self) -> datetime.datetime|None:
        """The start time of the video based on the first subtitle entry, or None if no subtitles."""
        if not self.subtitle_entries:
            return None
        return self.subtitle_entries[0].datetime


class SearchResult[T](NamedTuple):
    """Represents a search result for a media file."""
    item: T
    """The :class:`VideoFileInfo` or :class:`ImageFileInfo` item found."""
    search_path: MediaSearchPath
    """The :class:`~.config.MediaSearchPath` where the item was found."""
    confidence: float
    """The confidence score of the search result."""


@dataclass
class VideoCacheData:
    """Cache of video file metadata to speed up searches."""
    video_files: list[VideoFileInfo] = field(default_factory=list)
    """List of cached video files."""
    files_by_path: dict[Path, VideoFileInfo] = field(init=False)
    """Mapping of file paths to :class:`VideoFileInfo` for quick lookup."""

    def __post_init__(self) -> None:
        self.files_by_path = {vf.filename: vf for vf in self.video_files}

    class SerializeTD(TypedDict):
        """:meta private:"""
        video_files: list[VideoFileInfo.SerializeTD]

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            video_files=[video_file.serialize() for video_file in self.video_files],
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            video_files=[VideoFileInfo.deserialize(entry) for entry in data['video_files']],
        )

    @classmethod
    def load_from_cache(cls, config: Config) -> Self:
        """Load cache data from the configured cache directory."""
        cache_path = config.cache_dir / 'video_cache.json'
        if not cache_path.exists():
            return cls()
        content = cache_path.read_text(encoding='utf-8')
        data = json.loads(content)
        return cls.deserialize(data)

    def save_to_cache(self, config: Config) -> None:
        """Save cache data to the configured cache directory."""
        cache_path = config.cache_dir / 'video_cache.json'
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.serialize()
        cache_path.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def add_file(self, path: Path) -> VideoFileInfo:
        """Add a video file to the cache by analyzing it."""
        video_info = VideoFileInfo.from_file(path)
        self.video_files.append(video_info)
        self.files_by_path[path] = video_info
        return video_info

    def _iter_video_files(self, config: Config) -> Iterator[tuple[MediaSearchPath[Literal['video']], Path]]:
        seen = set()
        def _search(search_path: MediaSearchPath) -> Iterator[Path]:
            for item in search_path.path.iterdir():
                if item.is_dir():
                    if search_path.recursive:
                        yield from _search(MediaSearchPath(
                            path=item,
                            recursive=True,
                            glob_pattern=search_path.glob_pattern,
                            type=search_path.type,
                        ))
                    continue

                if item in seen:
                    continue
                mime_type, _ = mimetypes.guess_type(item)
                if mime_type is None or not mime_type.startswith('video'):
                    continue
                if search_path.glob_pattern is not None:
                    if not fnmatch.fnmatch(item.name, search_path.glob_pattern):
                        continue
                seen.add(item)
                yield item

        for search_path in config.video_search_paths:
            # logger.debug(f"Searching for video files in {search_path.path}...")
            assert search_path.path.is_absolute()
            for p in _search(search_path):
                yield search_path, p

    def search_from_flight_item(
        self,
        item: VideoItem,
        config: Config,
        ignore_cache: bool = False,
    ) -> list[SearchResult[VideoFileInfo]]:
        """Search for video files matching the given :class:`~.flight.VideoItem`."""
        return self.search(
            start_time=item.start_time,
            duration=item.duration,
            config=config,
            ignore_cache=ignore_cache,
        )

    def search(
        self,
        start_time: datetime.datetime,
        duration: datetime.timedelta,
        config: Config,
        ignore_cache: bool = False,
    ) -> list[SearchResult[VideoFileInfo]]:
        """Search for video files matching the given start time and duration.

        If an item is not found in the cache, it will be analyzed and added.
        """
        results = []
        start_time_max_delta = datetime.timedelta(seconds=5)
        for search_path, path in self._iter_video_files(config):
            # path_mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime)
            # path_mdelta = abs(path_mtime - start_time)
            # if path_mdelta > start_time_max_delta:
            #     logger.debug(f"Skipping {path} due to mtime delta {path_mdelta}")
            #     continue
            cached = None
            if not ignore_cache:
                cached = self.files_by_path.get(path)
            if cached is None:
                # logger.debug(f"Parsing video file {path}...")
                cached = self.add_file(path)
                # try:
                #     logger.debug(f"Parsing video file {path}...")
                #     cached = self.add_file(path)
                # except (ValueError, MediaParseError) as e:
                #     # logger.warning(f"Skipping file {path}: {e}")
                #     logger.exception(e)
                #     raise
                #     continue
                self.save_to_cache(config)
            if abs(cached.duration - duration) > datetime.timedelta(seconds=5):
                # logger.debug(f"Skipping {path} due to duration mismatch (file: {cached.duration}, expected: {duration})")
                continue
            vid_start = cached.start_time
            if vid_start is None:
                # logger.debug(f"Skipping {path} due to missing start time")
                continue
            confidence = 1.0 - (abs((vid_start - start_time).total_seconds()) / start_time_max_delta.total_seconds())
            # confidence = 1.0 - (path_mdelta.total_seconds() / start_time_max_delta.total_seconds())
            # logger.debug(f"Video file {path} has confidence {confidence}")
            results.append(SearchResult(
                item=cached,
                search_path=search_path,
                confidence=confidence,
            ))
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

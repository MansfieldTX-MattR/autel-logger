from __future__ import annotations
from typing import TypedDict, NamedTuple, Literal, ClassVar, Self
from pathlib import Path
import json
import datetime
from dataclasses import dataclass, field
import importlib.metadata

from platformdirs import PlatformDirs

from .parser.types import MediaRecordTypeName


assert __package__ is not None
_meta = importlib.metadata.metadata(__package__)
APP_NAME = _meta['Name']
APP_VERSION = _meta['Version']


DIRS = PlatformDirs(APP_NAME, appauthor=False)
CONFIG_PATH = Path(DIRS.user_config_dir) / 'config.json'
CACHE_DIR = Path(DIRS.user_cache_dir)
DATA_DIR = Path(DIRS.user_data_dir)


class MediaSearchPath[T: MediaRecordTypeName](NamedTuple):
    path: Path
    type: T
    glob_pattern: str|None = None
    recursive: bool = False

    class SerializeTD(TypedDict):
        """:meta private:"""
        path: str
        type: T
        glob_pattern: str|None
        recursive: bool

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            path=Path(data['path']),
            type=data['type'],
            glob_pattern=data.get('glob_pattern'),
            recursive=data.get('recursive', False),
        )

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            path=str(self.path),
            type=self.type,
            glob_pattern=self.glob_pattern,
            recursive=self.recursive
        )


@dataclass
class Config:
    raw_log_dir: Path|None = None
    data_dir: Path = DATA_DIR
    cache_dir: Path = CACHE_DIR
    blender_export_dir: Path|None = None
    video_search_paths: list[MediaSearchPath[Literal['video']]] = field(
        default_factory=list
    )
    image_search_paths: list[MediaSearchPath[Literal['image']]] = field(
        default_factory=list
    )

    DEFAULT_FILENAME: ClassVar[Path] = CONFIG_PATH

    class SerializeTD(TypedDict):
        """:meta private:"""
        raw_log_dir: str|None
        data_dir: str
        cache_dir: str
        blender_export_dir: str|None
        video_search_paths: list[MediaSearchPath[Literal['video']].SerializeTD]
        image_search_paths: list[MediaSearchPath[Literal['image']].SerializeTD]


    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            raw_log_dir=None if data['raw_log_dir'] is None else Path(data['raw_log_dir']),
            data_dir=Path(data['data_dir']),
            cache_dir=Path(data['cache_dir']),
            blender_export_dir=None if data['blender_export_dir'] is None else Path(data['blender_export_dir']),
            video_search_paths=[
                MediaSearchPath.deserialize(item)
                for item in data.get('video_search_paths', [])
            ],
            image_search_paths=[
                MediaSearchPath.deserialize(item)
                for item in data.get('image_search_paths', [])
            ],
        )

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            raw_log_dir=None if self.raw_log_dir is None else str(self.raw_log_dir),
            data_dir=str(self.data_dir),
            cache_dir=str(self.cache_dir),
            blender_export_dir=None if self.blender_export_dir is None else str(self.blender_export_dir),
            video_search_paths=[
                item.serialize() for item in self.video_search_paths
            ],
            image_search_paths=[
                item.serialize() for item in self.image_search_paths
            ],
        )

    @classmethod
    def load(cls, path: Path|str = DEFAULT_FILENAME) -> Self:
        path = Path(path)
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls.deserialize(data)

    def save(self, filename: Path|str = DEFAULT_FILENAME) -> None:
        filename = Path(filename)
        if not filename.parent.exists():
            filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_text(json.dumps(self.serialize(), indent=4))

    def _get_media_search_paths[T: MediaRecordTypeName](self, media_type: T) -> list[MediaSearchPath[T]]:
        if media_type == 'video':
            return self.video_search_paths # type: ignore[return-value]
        elif media_type == 'image':
            return self.image_search_paths # type: ignore[return-value]
        else:
            raise ValueError(f'Invalid media type: {media_type}')

    def add_media_search_path[T: MediaRecordTypeName](
        self,
        media_type: T,
        path: Path|str,
        glob_pattern: str|None = None,
        recursive: bool = False
    ) -> MediaSearchPath[T]:
        path = Path(path).expanduser().resolve()
        if not path.is_dir():
            raise ValueError(f'Path {path} is not a directory')
        sp = MediaSearchPath(
            path=path,
            type=media_type,
            glob_pattern=glob_pattern,
            recursive=recursive,
        )
        paths = self._get_media_search_paths(media_type)
        if sp in paths:
            raise ValueError(f'Path {path} is already in the config')
        paths.append(sp)
        self.save()
        return sp

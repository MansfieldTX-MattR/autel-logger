from __future__ import annotations
from typing import NamedTuple, TypedDict, Literal, Self, overload, cast

import struct
from pathlib import Path

from .types import (
    RecordTypeName, RecordKeyMap, RECORD_SIZES, RECORD_FORMATS, AllLogKey,
    ParsedInFullTD, ParsedInBaseTD, ParsedOutFullTD, ParsedOutBaseTD,
    ParsedHeadTD, ParsedVideoTD, ParsedImageTD, RECORD_TYPE_MAP,
    ParseRecordTD, ParsedRecordsTD,
)


type DataView = memoryview[bytes]
IS_LE = True


class ParseResult(NamedTuple):
    filename: str
    header: ParsedHeadTD
    records: ParsedRecordsTD
    record_tracks: dict[RecordTypeName, RecordTrack]
    total_records: int

    class SerializeTD(TypedDict):
        filename: str
        header: ParsedHeadTD
        records: ParsedRecordsTD
        record_tracks: dict[RecordTypeName, RecordTrack.SerializeTD]
        total_records: int

    def serialize(self) -> SerializeTD:
        return {
            'filename': self.filename,
            'header': self.header,
            'records': self.records,
            'record_tracks': {k: v.serialize() for k, v in self.record_tracks.items()},
            'total_records': self.total_records,
        }

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            filename=data['filename'],
            header=data['header'],
            records=data['records'],
            record_tracks={
                k: RecordTrack.deserialize(v) for k, v in data['record_tracks'].items()
            },
            total_records=data['total_records'],
        )


def read_uint8(data: DataView, offset: int) -> int:
    return struct.unpack_from("<B" if IS_LE else ">B", data, offset)[0]

def read_uint16(data: DataView, offset: int) -> int:
    return struct.unpack_from("<H" if IS_LE else ">H", data, offset)[0]

def read_uint32(data: DataView, offset: int) -> int:
    return struct.unpack_from("<I" if IS_LE else ">I", data, offset)[0]

def read_uint64(data: DataView, offset: int) -> int:
    return struct.unpack_from("<Q" if IS_LE else ">Q", data, offset)[0]

def read_float32(data: DataView, offset: int) -> float:
    return struct.unpack_from("<f" if IS_LE else ">f", data, offset)[0]

def read_float64(data: DataView, offset: int) -> float:
    return struct.unpack_from("<d" if IS_LE else ">d", data, offset)[0]

def read_string(data: DataView, offset: int, length: int) -> str:
    b = struct.unpack_from(f'<{length}s' if IS_LE else f'>{length}s', data, offset)[0]
    return b.split(b'\x00', 1)[0].decode('utf-8')




class RecordTrack[T: RecordTypeName]:
    class SerializeTD(TypedDict):
        name: T
        count: int
        size: int
        offsets: list[int]

    def __init__(self, name: T, size: int, offsets: list[int]|None = None) -> None:
        self.__name = name
        self.__size = size
        self.__offsets: list[int] = offsets if offsets is not None else []

    @property
    def name(self) -> T:
        return self.__name

    @property
    def size(self) -> int:
        return self.__size

    @property
    def offsets(self) -> list[int]:
        return self.__offsets

    @property
    def count(self) -> int:
        return len(self.__offsets)

    def append(self, offset: int) -> None:
        self.__offsets.append(offset)

    def serialize(self) -> SerializeTD:
        return {
            'name': self.name,
            'count': self.count,
            'size': self.size,
            'offsets': self.offsets,
        }

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(data['name'], data['size'], data['offsets'])

    def __len__(self) -> int:
        return len(self.__offsets)

    def __iter__(self):
        yield from self.__offsets

    def __repr__(self) -> str:
        return f"RecordTrack(name='{self.name}', count={self.count}, size={self.size})"


class UnknownRecordTypeError(Exception):
    def __init__(self, type_id: int, offset: int, context: bytes) -> None:
        self.type_id = type_id
        self.offset = offset
        self.context = context
        super().__init__()#f"Unknown record type ID: {type_id} at offset {offset}, context: {context}")


    def __str__(self) -> str:
        def bytes_to_hex(b: bytes) -> str:
            return ' '.join(f'{x:02X}' for x in b)
        debug_start_bytes = self.context[:10]
        debug_end_bytes = self.context[-10:]
        debug_start_hex = bytes_to_hex(debug_start_bytes)
        debug_end_hex = bytes_to_hex(debug_end_bytes)
        return f"type ID: {self.type_id} at offset {self.offset}, context: ... {debug_start_hex} | {debug_end_hex} ..."


def get_record_type_from_offset(data: DataView, offset: int) -> RecordTypeName:
    type_id = read_uint8(data, offset)
    if type_id not in RECORD_TYPE_MAP:
        raise UnknownRecordTypeError(type_id, offset, data[offset-10:offset+10])
    return RECORD_TYPE_MAP[type_id]

def get_total_record_size(record_type: RecordTypeName) -> int:
    keys = RecordKeyMap[record_type].value
    total_size = 0
    for key in keys:
        size = RECORD_SIZES[key]
        if size == 0:
            raise ValueError(f"Unsupported key '{key}' for {record_type} with size 0")
        total_size += size
    return total_size

# def get_all_record_sizes() -> dict[RecordTypeName, int]:
#     sizes: dict[RecordTypeName, int] = {}
#     for record_type in RECORD_TYPE_MAP.values():
#         sizes[record_type] = get_total_record_size(record_type)
#     return sizes


def get_record_tracks(in_data: DataView) -> dict[RecordTypeName, RecordTrack]:
    offset = 14
    head_info, head_offset = parse_record(in_data, 'head', offset)
    offset = head_offset

    record_tracks: dict[RecordTypeName, RecordTrack] = {
        key: RecordTrack(key, get_total_record_size(key))
        for key in RECORD_TYPE_MAP.values()
    }
    record_tracks['head'].append(14)
    # last_record_type = 'head'
    while offset < len(in_data):
        # print(f'Offset: {offset}, Last record type: {last_record_type}')
        try:
            record_type = get_record_type_from_offset(in_data, offset)
        except UnknownRecordTypeError as e:
            raise e
            # msg = f'{e} (last record type: {last_record_type}, last offset: {offset})'
            # raise Exception(msg) from e
        record_track = record_tracks[record_type]
        record_track.append(offset)
        offset += record_track.size + 1
        # last_record_type = record_type
    return record_tracks


def parse_log_data(in_data: bytes|DataView, filename: str) -> ParseResult:
    if not isinstance(in_data, memoryview):
        data: memoryview[bytes] = memoryview(in_data)
    else:
        data = in_data
    magic = read_string(data, 0, 8)
    version = read_uint32(data, 8)
    if magic != 'AUTEL_FR':
        raise ValueError(f"Invalid magic: {magic}")
    if version != 3:
        raise ValueError(f"Unsupported version: {version}")
    record_tracks = get_record_tracks(data)
    # print(f'Record tracks: {record_tracks}')
    header_offset = record_tracks['head'].offsets[0]
    header, _ = parse_record(data, 'head', header_offset)
    records: ParsedRecordsTD = {
        'head': cast(ParsedHeadTD, header),
        'in_full': [],
        'in_base': [],
        'out_full': [],
        'out_base': [],
        'video': [],
        'image': [],
    }
    total_records = 0
    for record_type, track in record_tracks.items():
        if record_type == 'head':
            continue
        for offset in track.offsets:
            record, _ = parse_record(data, record_type, offset + 1)
            records[record_type].append(record)  # type: ignore
            total_records += 1
    return ParseResult(
        filename=filename,
        header=cast(ParsedHeadTD, header),
        records=records,
        record_tracks=record_tracks,
        total_records=total_records,
    )



def parse_log_file(file_path: Path|str):# -> ParseResult:
    path = Path(file_path)
    with path.open('rb') as f:
        data = f.read()
    return parse_log_data(data, filename=path.name)
    # return get_record_tracks(memoryview(data))


@overload
def parse_record(data: DataView, record_type: Literal['head'], offset: int) -> tuple[ParsedHeadTD, int]: ...
@overload
def parse_record(data: DataView, record_type: Literal['in_full'], offset: int) -> tuple[ParsedInFullTD, int]: ...
@overload
def parse_record(data: DataView, record_type: Literal['in_base'], offset: int) -> tuple[ParsedInBaseTD, int]: ...
@overload
def parse_record(data: DataView, record_type: Literal['out_full'], offset: int) -> tuple[ParsedOutFullTD, int]: ...
@overload
def parse_record(data: DataView, record_type: Literal['out_base'], offset: int) -> tuple[ParsedOutBaseTD, int]: ...
@overload
def parse_record(data: DataView, record_type: Literal['video'], offset: int) -> tuple[ParsedVideoTD, int]: ...
@overload
def parse_record(data: DataView, record_type: Literal['image'], offset: int) -> tuple[ParsedImageTD, int]: ...
def parse_record(data: DataView, record_type: RecordTypeName, offset: int) -> tuple[ParseRecordTD, int]:
    keys = RecordKeyMap[record_type].value
    # offset = record_info.offset
    # total_size = 0
    result = {}
    for key in keys:
        if key == 'firmware_info':
            assert record_type == 'head'
            size = result['firmware_size']
            assert size > 1, f"Invalid firmware size: {size}"
            value = read_string(data, offset, size)
            result[key] = value
            offset += size
            continue
            # fw_size = result['firmware_size']
            # fw_info = read_string(data, offset, fw_size)
            # result[key] = fw_info
            # offset += fw_size
            # continue
        else:
            value, size, new_offset = parse_record_item(data, offset, record_type, key)

            if record_type in ('in_base', 'in_full', 'out_base', 'out_full'):
                cur_time = result.get('current_time')
                if key == 'current_time' and cur_time is not None and isinstance(value, (int, float)) and cur_time != value:
                    if cur_time > value:
                        result['current_time'] = value

                    # if value < cur_time:
                    #     raise ValueError(f"Non-monotonic current_time: {value} < {cur_time} at offset {offset} for {record_type}")
                    offset = new_offset
                    continue


        result[key] = value
        offset = new_offset
        # total_size += size
    return cast(ParseRecordTD, result), offset



def parse_record_item(data: DataView, offset: int, record_type: RecordTypeName, key: AllLogKey):
    size = RECORD_SIZES[key]
    fmt = RECORD_FORMATS.get(key)
    if size == 0:
        raise ValueError(f"Unsupported key '{key}' for {record_type} with size 0")
    if size == 1:
        value = read_uint8(data, offset)
    elif size == 2:
        value = read_uint16(data, offset)
    elif size == 4:
        if fmt is None:
            value = read_float32(data, offset)
        elif fmt == 'h':
            # convert to hex string
            value = hex(read_uint32(data, offset))
        elif fmt == 'i':
            value = read_uint32(data, offset)
        else:
            value = read_uint32(data, offset)
    elif size == 8:
        if fmt is None or fmt == 'i':
            value = read_uint64(data, offset)
        else:
            value = read_float64(data, offset)
    else:
        if fmt is None:
            value = read_string(data, offset, size)
        else:
            assert fmt == '[f'
            count = size // 4
            value = [read_float32(data, offset + i * 4) for i in range(count)]
    return value, size, offset + size

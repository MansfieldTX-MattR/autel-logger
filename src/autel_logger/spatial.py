from __future__ import annotations
import math
from typing import NamedTuple, TypedDict, Literal, Sequence, Self
from urllib.parse import quote_plus
from urllib.request import urlopen, Request


from pathlib import Path

# from geopy.point import Point
# from geopy.location import Location
# from geopy import distance as geopy_distance
# from geopy.units import arcminutes, arcseconds, degrees, radians, meters

type AngleUnit = Literal['degrees', 'radians']
type Latitude = float
type Longitude = float



class PositionMeters(NamedTuple):
    x: float
    y: float
    z: float

    class SerializeTD(TypedDict):
        """:meta private:"""
        x: float
        y: float
        z: float

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(x=self.x, y=self.y, z=self.z)

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(x=data['x'], y=data['y'], z=data['z'])




class LatLon(NamedTuple):
    latitude: Latitude
    longitude: Longitude

    class SerializeTD(TypedDict):
        """:meta private:"""
        latitude: float
        longitude: float

    def distance_to(self, other: LatLon) -> float:
        """Calculate the distance in meters to another LatLon point."""
        # Using Haversine formula
        R = 6371000  # Radius of the Earth in meters
        lat1_rad = math.radians(self.latitude)
        lat2_rad = math.radians(other.latitude)
        delta_lat = math.radians(other.latitude - self.latitude)
        delta_lon = math.radians(other.longitude - self.longitude)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    # def bearing_to(self, other: LatLon) -> float:
    #     """Calculate the bearing in degrees to another LatLon point."""
    #     lat1 = math.radians(self.latitude)
    #     lat2 = math.radians(other.latitude)
    #     diff_long = math.radians(other.longitude - self.longitude)

    #     x = math.sin(diff_long) * math.cos(lat2)
    #     y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diff_long))

    #     initial_bearing = math.atan2(x, y)

    #     # Convert from radians to degrees and normalize to 0-360
    #     initial_bearing = math.degrees(initial_bearing)
    #     compass_bearing = (initial_bearing + 360) % 360

    #     return compass_bearing

    # def to_point(self) -> Point:
    #     return Point(self.latitude, self.longitude)

    def distance_to_2d(self, other: LatLon) -> PositionMeters:
        """
        Haversine formula to calculate the great-circle distance between two points
        on the Earth's surface given their latitude and longitude.
        This gives the shortest distance over the earth's surface.
        However, it does not give x and y components directly.
        To get x and y components, we can calculate the bearing and then
        decompose the distance into x and y using trigonometry.
        """
        R = 6371000  # Radius of the Earth in meters
        phi_1 = math.radians(self.latitude)
        phi_2 = math.radians(other.latitude)
        delta_phi = math.radians(other.latitude - self.latitude)
        delta_lambda = math.radians(other.longitude - self.longitude)
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi_1) * math.cos(phi_2) *
             math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c  # in meters
        if distance == 0:
            return PositionMeters(0.0, 0.0, 0.0)
        # Calculate bearing
        y = math.sin(delta_lambda) * math.cos(phi_2)
        x = (math.cos(phi_1) * math.sin(phi_2) -
             math.sin(phi_1) * math.cos(phi_2) * math.cos(delta_lambda))
        bearing = math.atan2(y, x)
        # Decompose distance into x and y components
        x_comp = distance * math.cos(bearing)
        y_comp = distance * math.sin(bearing)
        result = PositionMeters(y_comp, x_comp, 0.0)
        if self.latitude > other.latitude:
            assert result.y < 0, f"{self.latitude} > {other.latitude} but {result.y} >= 0"
        else:
            assert result.y >= 0, f"{self.latitude} <= {other.latitude} but {result.y} < 0"
        if self.longitude > other.longitude:
            assert result.x < 0, f"{self.longitude} > {other.longitude} but {result.x} >= 0"
        else:
            assert result.x >= 0, f"{self.longitude} <= {other.longitude} but {result.x} < 0"
        return result


    def to_position_meters(self, reference: LatLon) -> PositionMeters:
        return self.distance_to_2d(reference)
        # # distance = self.distance_to(reference)
        # # bearing = math.radians(reference.bearing_to(self))
        # lat_distance = self.distance_to(LatLon(self.latitude, reference.longitude))
        # lon_distance = self.distance_to(LatLon(reference.latitude, self.longitude))
        # if self.latitude < reference.latitude:
        #     lat_distance = -lat_distance
        # if self.longitude < reference.longitude:
        #     lon_distance = -lon_distance
        # return PositionMeters(lon_distance, lat_distance, 0.0)

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            latitude=self.latitude,
            longitude=self.longitude,
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            latitude=data['latitude'],
            longitude=data['longitude'],
        )


class GeoBox(NamedTuple):
    southwest: LatLon
    northeast: LatLon

    class SerializeTD(TypedDict):
        """:meta private:"""
        southwest: LatLon.SerializeTD
        northeast: LatLon.SerializeTD

    @classmethod
    def from_points(cls, points: Sequence[LatLon|LatLonAlt]) -> Self:
        points = list(points)
        min_lat = min(p.latitude for p in points)
        max_lat = max(p.latitude for p in points)
        min_lon = min(p.longitude for p in points)
        max_lon = max(p.longitude for p in points)
        r =  cls(
            southwest=LatLon(min_lat, min_lon),
            northeast=LatLon(max_lat, max_lon),
        )
        for p in points:
            assert p in r, f"Point {p} not in GeoBox {r}"
        return r

    @property
    def north(self) -> Latitude:
        return self.northeast.latitude

    @property
    def south(self) -> Latitude:
        return self.southwest.latitude

    @property
    def east(self) -> Longitude:
        return self.northeast.longitude

    @property
    def west(self) -> Longitude:
        return self.southwest.longitude

    @property
    def northwest(self) -> LatLon:
        return LatLon(self.north, self.west)

    @property
    def southeast(self) -> LatLon:
        return LatLon(self.south, self.east)

    @property
    def center(self) -> LatLon:
        return LatLon(
            (self.southwest.latitude + self.northeast.latitude) / 2,
            (self.southwest.longitude + self.northeast.longitude) / 2,
        )

    @property
    def osm_url(self) -> str:
        return f"https://www.openstreetmap.org/?mlat={self.center.latitude}&mlon={self.center.longitude}#map=12/{self.center.latitude}/{self.center.longitude}"

    def get_overpass_request_payload(
        self,
        output_format: str = 'xml',
        timeout: int = 25,
        output_content: str = 'geom',
    ) -> str:
        body = '\n'.join([
            f'[out:{output_format}][timeout:{timeout}];',
            # f'[bbox:{self.south},{self.west},{self.north},{self.east}];',
            f'(',
            f' node({self.south},{self.west},{self.north},{self.east});',
            f' <;',
            f');',
            f'out {output_content};',
        ])
        return f"data={quote_plus(body)}"

    def get_overpass_data(
        self,
        api_endpoint: str = 'https://overpass-api.de/api/interpreter',
        output_format: str = 'xml',
        timeout: int = 25,
        output_content: str = 'geom',
    ) -> bytes:
        request = Request(
            api_endpoint,
            data=self.get_overpass_request_payload(
                output_format=output_format,
                timeout=timeout,
                output_content=output_content
            ).encode('utf-8'),
            method='POST'
        )
        with urlopen(request) as response:
            if response.status != 200:
                raise RuntimeError(f"Overpass API request failed with status {response.status}")
            return response.read()

    def save_overpass_data(
        self,
        path: Path|str,
        api_endpoint: str = 'https://overpass-api.de/api/interpreter',
        output_format: str = 'xml',
        timeout: int = 25,
        output_content: str = 'geom',
    ) -> None:
        data = self.get_overpass_data(
            api_endpoint=api_endpoint,
            output_format=output_format,
            timeout=timeout,
            output_content=output_content
        )
        with open(path, 'wb') as f:
            f.write(data)

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            southwest=self.southwest.serialize(),
            northeast=self.northeast.serialize(),
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            southwest=LatLon.deserialize(data['southwest']),
            northeast=LatLon.deserialize(data['northeast']),
        )

    def __contains__(self, item: LatLon|LatLonAlt) -> bool:
        if self.southwest.latitude > item.latitude:
            return False
        if self.northeast.latitude < item.latitude:
            return False
        if self.southwest.longitude > item.longitude:
            return False
        if self.northeast.longitude < item.longitude:
            return False
        return True



class LatLonAlt(NamedTuple):
    latitude: Latitude
    longitude: Longitude
    altitude: float

    class SerializeTD(TypedDict):
        """:meta private:"""
        latitude: float
        longitude: float
        altitude: float

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(
            latitude=self.latitude,
            longitude=self.longitude,
            altitude=self.altitude,
        )

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(
            latitude=data['latitude'],
            longitude=data['longitude'],
            altitude=data['altitude'],
        )

    def distance_to(self, other: LatLon|LatLonAlt) -> float:
        """Calculate the 3D distance in meters to another LatLonAlt point."""
        horizontal_distance = LatLon(self.latitude, self.longitude).distance_to(
            LatLon(other.latitude, other.longitude)
        )
        if isinstance(other, LatLon):
            return horizontal_distance
        vertical_distance = self.altitude - other.altitude
        return math.sqrt(horizontal_distance**2 + vertical_distance**2)

    def to_position_meters(self, reference: LatLon|LatLonAlt) -> PositionMeters:
        horizontal = LatLon(self.latitude, self.longitude).to_position_meters(
            LatLon(reference.latitude, reference.longitude)
        )
        if isinstance(reference, LatLon):
            return PositionMeters(horizontal.x, horizontal.y, 0.0)
        vertical = self.altitude - reference.altitude
        return PositionMeters(horizontal.x, horizontal.y, vertical)


class Vector3D(NamedTuple):
    x: float
    y: float
    z: float

    class SerializeTD(TypedDict):
        """:meta private:"""
        x: float
        y: float
        z: float

    def serialize(self) -> SerializeTD:
        return self.SerializeTD(x=self.x, y=self.y, z=self.z)

    @classmethod
    def deserialize(cls, data: SerializeTD) -> Self:
        return cls(x=data['x'], y=data['y'], z=data['z'])


class Speed(Vector3D):
    pass


class Orientation[T: AngleUnit](NamedTuple):
    pitch: float
    roll: float
    yaw: float
    unit: T

    class SerializeTD[_T: AngleUnit](TypedDict):
        """:meta private:"""
        pitch: float
        roll: float
        yaw: float
        unit: _T

    def serialize(self) -> SerializeTD[T]:
        return self.SerializeTD(
            pitch=self.pitch,
            roll=self.roll,
            yaw=self.yaw,
            unit=self.unit,
        )

    @classmethod
    def deserialize[_T: AngleUnit](cls, data: SerializeTD, unit: _T) -> Orientation[_T]:
        r = cls(
            pitch=data['pitch'],
            roll=data['roll'],
            yaw=data['yaw'],
            unit=data['unit'],
        )
        return r.to_unit(unit)

    def to_unit[Ot: AngleUnit](self, target_unit: Ot) -> Orientation[Ot]:
        if self.unit == target_unit:
            return Orientation(self.pitch, self.roll, self.yaw, target_unit)
        if target_unit == 'degrees':
            return Orientation(
                math.degrees(self.pitch),
                math.degrees(self.roll),
                math.degrees(self.yaw),
                target_unit,
            )
        else:  # target_unit == 'radians'
            return Orientation(
                math.radians(self.pitch),
                math.radians(self.roll),
                math.radians(self.yaw),
                target_unit,
            )

    def to_degrees(self) -> Orientation[Literal['degrees']]:
        return self.to_unit('degrees')

    def to_radians(self) -> Orientation[Literal['radians']]:
        return self.to_unit('radians')

    def normalize(self) -> Self:
        """Normalize pitch, roll, and yaw to be within -180 to 180 degrees or -π to π radians."""
        normalized = self.normalize_yaw()
        if self.unit == 'degrees':
            pitch = ((normalized.pitch + 180) % 360) - 180
            roll = ((normalized.roll + 180) % 360) - 180
            return self.__class__(pitch, roll, normalized.yaw, self.unit)
        else:  # self.unit == 'radians'
            pitch = ((normalized.pitch + math.pi) % (2 * math.pi)) - math.pi
            roll = ((normalized.roll + math.pi) % (2 * math.pi)) - math.pi
            return self.__class__(pitch, roll, normalized.yaw, self.unit)

    def normalize_yaw(self) -> Orientation[T]:
        """Normalize yaw to be within -180 to 180 degrees or -π to π radians."""
        if self.unit == 'degrees':
            yaw = ((self.yaw + 180) % 360) - 180
            return Orientation(self.pitch, self.roll, yaw, self.unit)
        else:  # self.unit == 'radians'
            yaw = ((self.yaw + math.pi) % (2 * math.pi)) - math.pi
            return Orientation(self.pitch, self.roll, yaw, self.unit)

    def wrap_yaw(self, previous: Orientation[T]) -> Orientation[T]:
        """Wrap yaw to be continuous with previous yaw value."""
        if self.unit != previous.unit:
            previous = previous.to_unit(self.unit)
        delta_yaw = self.yaw - previous.yaw
        if self.unit == 'degrees':
            delta_yaw = math.radians(delta_yaw)
        if delta_yaw > math.pi:
            yaw_radians = self.yaw - 2 * math.pi
        elif delta_yaw < -math.pi:
            yaw_radians = self.yaw + 2 * math.pi
        else:
            yaw_radians = self.yaw
        if self.unit == 'degrees':
            yaw = math.degrees(yaw_radians)
        else:
            yaw = yaw_radians
        return Orientation(self.pitch, self.roll, yaw, self.unit)

    def inverted(self, pitch: bool, roll: bool, yaw: bool) -> Orientation[T]:
        return Orientation(
            -self.pitch if pitch else self.pitch,
            -self.roll if roll else self.roll,
            -self.yaw if yaw else self.yaw,
            self.unit,
        )

    def __add__(self, other: Orientation[T]) -> Orientation[T]:
        if other.unit != self.unit:
            other = other.to_unit(self.unit)
        return Orientation(
            self.pitch + other.pitch,
            self.roll + other.roll,
            self.yaw + other.yaw,
            self.unit,
        )

    def __sub__(self, other: Orientation[T]) -> Orientation[T]:
        if other.unit != self.unit:
            other = other.to_unit(self.unit)
        return Orientation(
            self.pitch - other.pitch,
            self.roll - other.roll,
            self.yaw - other.yaw,
            self.unit,
        )

    def __neg__(self) -> Orientation[T]:
        return Orientation(-self.pitch, -self.roll, -self.yaw, self.unit)

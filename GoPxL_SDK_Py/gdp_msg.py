"""GDP message types - mirrors GoPxLSdk GoGdpMsg classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import MessageType
from .kserializer import KSerializerReader, image_row_size, pixel_bytes

_COMMON_ATTRS = (
    "data_source_id_",
    "stamp_source_id_",
    "space_type",
    "arrayed_count",
    "arrayed_index",
    "data_set_id_",
    "is_last_msg_",
    "gdp_id",
)


@dataclass(slots=True)
class GoGdpMsg:
    msg_type: MessageType
    data_source_id_: str = ""
    stamp_source_id_: str = ""
    space_type: int = 0
    arrayed_count: int = 0
    arrayed_index: int = 0
    data_set_id_: int = 0
    is_last_msg_: bool = False
    gdp_id: int = 0
    raw: bytes = field(default_factory=bytes, repr=False)

    def type(self) -> MessageType:
        return self.msg_type

    def data_source_id(self) -> str:
        return self.data_source_id_

    def stamp_source_id(self) -> str:
        return self.stamp_source_id_

    def data_set_id(self) -> int:
        return self.data_set_id_

    def is_last_msg(self) -> bool:
        return self.is_last_msg_

    @staticmethod
    def parse_common(reader: KSerializerReader, msg_type: MessageType) -> GoGdpMsg:
        msg = GoGdpMsg(msg_type=msg_type)
        section = reader.section_u32()
        msg.space_type = section.read_u8()
        if section.read_u8() > 0:
            _skip_transform(section)
        if section.read_u8() > 0:
            _skip_bbox(section)
        msg.arrayed_count = section.read_u32()
        msg.arrayed_index = section.read_u32()
        ds_len = section.read_u16()
        msg.data_source_id_ = section.read_text(ds_len)
        st_len = section.read_u16()
        msg.stamp_source_id_ = section.read_text(st_len)
        msg.data_set_id_ = section.read_u64()
        msg.is_last_msg_ = section.read_u8() > 0
        msg.gdp_id = section.read_u16()
        return msg


def _apply_common(msg: GoGdpMsg, common: GoGdpMsg) -> None:
    for attr in _COMMON_ATTRS:
        setattr(msg, attr, getattr(common, attr))


@dataclass(slots=True)
class GoGdpProfileUniform(GoGdpMsg):
    width_: int = 0
    intensity_width_: int = 0
    resolution_x: float = 0.0
    resolution_z: float = 0.0
    offset_x: float = 0.0
    offset_z: float = 0.0
    exposure: float = 0.0
    ranges_: list[int] = field(default_factory=list)
    intensities_: bytes = b""

    def width(self) -> int:
        return self.width_

    def ranges(self) -> list[int]:
        return self.ranges_

    def intensities(self) -> bytes:
        return self.intensities_


@dataclass(slots=True)
class GoGdpProfilePointCloud(GoGdpMsg):
    width_: int = 0
    resolution_x: float = 0.0
    resolution_z: float = 0.0
    offset_x: float = 0.0
    offset_z: float = 0.0
    exposure: float = 0.0
    points_: list[tuple[int, int]] = field(default_factory=list)

    def width(self) -> int:
        return self.width_

    def points(self) -> list[tuple[int, int]]:
        return self.points_


@dataclass(slots=True)
class GoGdpSurfaceUniform(GoGdpMsg):
    length_: int = 0
    width_: int = 0
    intensity_length_: int = 0
    intensity_width_: int = 0
    resolution: tuple[float, float, float] = (0.0, 0.0, 0.0)
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    surface_id: int = 0
    exposure: float = 0.0
    intensity_pixel_format: int = 0
    ranges_: list[int] = field(default_factory=list)
    intensities_: bytes = b""

    def length(self) -> int:
        return self.length_

    def width(self) -> int:
        return self.width_

    def ranges(self) -> list[int]:
        return self.ranges_

    def intensities(self) -> bytes:
        return self.intensities_


@dataclass(slots=True)
class GoGdpSurfacePointCloud(GoGdpMsg):
    length_: int = 0
    width_: int = 0
    intensity_length_: int = 0
    intensity_width_: int = 0
    resolution: tuple[float, float, float] = (0.0, 0.0, 0.0)
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    surface_id: int = 0
    exposure: float = 0.0
    is_adjacent: bool = False
    intensity_pixel_format: int = 0
    ranges_: list[tuple[int, int, int]] = field(default_factory=list)
    intensities_: bytes = b""

    def length(self) -> int:
        return self.length_

    def width(self) -> int:
        return self.width_

    def ranges(self) -> list[tuple[int, int, int]]:
        return self.ranges_

    def intensities(self) -> bytes:
        return self.intensities_


@dataclass(slots=True)
class GoGdpImage(GoGdpMsg):
    height_: int = 0
    width_: int = 0
    pixel_size: int = 0
    color_filter: int = 0
    pixel_format: int = 0
    exposure: float = 0.0
    resolution: tuple[float, float, float] = (0.0, 0.0, 0.0)
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    pixels_: bytes = b""

    def height(self) -> int:
        return self.height_

    def width(self) -> int:
        return self.width_

    def pixels(self) -> bytes:
        return self.pixels_


@dataclass(slots=True)
class GdpSpot:
    slice: int = 0
    centre: int = 0


@dataclass(slots=True)
class GoGdpSpots(GoGdpMsg):
    point_count: int = 0
    exposure: float = 0.0
    column_based: bool = False
    slice_scale: float = 0.0
    slice_offset: float = 0.0
    center_scale: float = 0.0
    center_offset: float = 0.0
    max_slice_count: int = 0
    spot_center_min: int = 0
    spot_center_max: int = 0
    spots_: list[GdpSpot] = field(default_factory=list)

    def spots(self) -> list[GdpSpot]:
        return self.spots_


@dataclass(slots=True)
class MeshChannel:
    id: int = 0
    type: int = 0
    state: int = 0
    flag: int = 0
    allocated_count: int = 0
    used_count: int = 0
    data: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class GoGdpMesh(GoGdpMsg):
    has_data: bool = False
    system_channel_count: int = 0
    max_user_channel_count: int = 0
    user_channel_count: int = 0
    channel_count: int = 0
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    range: tuple[float, float, float] = (0.0, 0.0, 0.0)
    channels_: list[MeshChannel] = field(default_factory=list)

    def channels(self) -> list[MeshChannel]:
        return self.channels_


@dataclass(slots=True)
class GoGdpStamp(GoGdpMsg):
    frame_index: int = 0
    timestamp: int = 0
    encoder: int = 0
    encoder_at_z: int = 0
    status: int = 0
    system_time_seconds: int = 0
    system_time_nanoseconds: int = 0


@dataclass(slots=True)
class GoGdpMeasurement(GoGdpMsg):
    value: float = 0.0
    decision: int = 0
    label_position: tuple[float, float, float] | None = None


@dataclass(slots=True)
class GoGdpString(GoGdpMsg):
    text: str = ""
    decision: int = 0
    label_position: tuple[float, float, float] | None = None


@dataclass(slots=True)
class GoPointSet:
    size: float = 0.0
    color: int = 0
    shape: int = 0
    points: list[tuple[float, float, float]] = field(default_factory=list)


@dataclass(slots=True)
class GoLineSet:
    width: float = 0.0
    color: int = 0
    has_start_point_arrow: bool = False
    has_end_point_arrow: bool = False
    points: list[tuple[float, float, float]] = field(default_factory=list)


@dataclass(slots=True)
class GoPlane:
    distance: float = 0.0
    normal: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(slots=True)
class GoRay:
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: tuple[float, float, float] = (0.0, 0.0, 0.0)
    width: float = 0.0
    color: int = 0


@dataclass(slots=True)
class GoLabel:
    text: str = ""
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(slots=True)
class GoPosition:
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    type: int = 0


@dataclass(slots=True)
class GoGraphics:
    point_sets: list[GoPointSet] = field(default_factory=list)
    line_sets: list[GoLineSet] = field(default_factory=list)
    regions: list[dict[str, Any]] = field(default_factory=list)
    planes: list[GoPlane] = field(default_factory=list)
    rays: list[GoRay] = field(default_factory=list)
    labels: list[GoLabel] = field(default_factory=list)
    positions: list[GoPosition] = field(default_factory=list)


@dataclass(slots=True)
class GoGdpRendering(GoGdpMsg):
    graphics_: GoGraphics = field(default_factory=GoGraphics)

    def graphics(self) -> GoGraphics:
        return self.graphics_


@dataclass(slots=True)
class GoGdpFeaturePoint(GoGdpMsg):
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(slots=True)
class GoGdpFeatureLine(GoGdpMsg):
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(slots=True)
class GoGdpFeaturePlane(GoGdpMsg):
    normal: tuple[float, float, float] = (0.0, 0.0, 0.0)
    distance_to_origin: float = 0.0


@dataclass(slots=True)
class GoGdpFeatureCircle(GoGdpMsg):
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 0.0


_MESH_ID_VERTEX = 1
_MESH_ID_FACET = 2
_MESH_ID_VERTEX_TEXTURE = 3
_MESH_ID_FACET_NORMAL = 4
_MESH_ID_VERTEX_NORMAL = 5
_MESH_ID_VERTEX_CURVATURE = 6

_REGION_PROFILE_2D = 1
_REGION_SURFACE_2D = 2
_REGION_3D = 3


def parse_gdp_message(msg_type: int, packet: bytes) -> GoGdpMsg:
    body = packet[6:]
    reader = KSerializerReader(body)
    mtype = MessageType(msg_type)
    common = GoGdpMsg.parse_common(reader, mtype)

    if mtype == MessageType.UNIFORM_PROFILE:
        msg = GoGdpProfileUniform(msg_type=mtype)
        _apply_common(msg, common)
        section = reader.section_u16()
        msg.width_ = section.read_u32()
        msg.intensity_width_ = section.read_u32()
        msg.resolution_x = section.read_f64()
        msg.resolution_z = section.read_f64()
        msg.offset_x = section.read_f64()
        msg.offset_z = section.read_f64()
        msg.exposure = section.read_f32()
        msg.ranges_ = section.read_i16_array(msg.width_)
        if msg.intensity_width_ > 0:
            msg.intensities_ = section.read_u8_array(msg.intensity_width_)
        msg.raw = packet
        return msg

    if mtype == MessageType.PROFILE_POINT_CLOUD:
        msg = GoGdpProfilePointCloud(msg_type=mtype)
        _apply_common(msg, common)
        section = reader.section_u16()
        msg.width_ = section.read_u32()
        msg.resolution_x = section.read_f64()
        msg.resolution_z = section.read_f64()
        msg.offset_x = section.read_f64()
        msg.offset_z = section.read_f64()
        msg.exposure = section.read_f32()
        raw = section.read_i16_array(msg.width_ * 2)
        msg.points_ = [(raw[i], raw[i + 1]) for i in range(0, len(raw), 2)]
        msg.raw = packet
        return msg

    if mtype == MessageType.UNIFORM_SURFACE:
        msg = GoGdpSurfaceUniform(msg_type=mtype)
        _apply_common(msg, common)
        section = reader.section_u16()
        _read_surface_base(section, msg)
        msg.intensity_pixel_format = _read_intensity_pixel_format(section, msg.intensity_length_, msg.intensity_width_)
        msg.ranges_ = section.read_i16_array(msg.length_ * msg.width_)
        if msg.intensity_length_ > 0 and msg.intensity_width_ > 0:
            row = msg.intensity_width_ * pixel_bytes(msg.intensity_pixel_format)
            msg.intensities_ = section.read_u8_array(msg.intensity_length_ * row)
        msg.raw = packet
        return msg

    if mtype == MessageType.SURFACE_POINT_CLOUD:
        msg = GoGdpSurfacePointCloud(msg_type=mtype)
        _apply_common(msg, common)
        section = reader.section_u16()
        _read_surface_base(section, msg)
        msg.is_adjacent = section.read_u8() > 0
        msg.intensity_pixel_format = _read_intensity_pixel_format(section, msg.intensity_length_, msg.intensity_width_)
        raw = section.read_i16_array(msg.length_ * msg.width_ * 3)
        msg.ranges_ = [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw), 3)]
        if msg.intensity_length_ > 0 and msg.intensity_width_ > 0:
            row = msg.intensity_width_ * pixel_bytes(msg.intensity_pixel_format)
            msg.intensities_ = section.read_u8_array(msg.intensity_length_ * row)
        msg.raw = packet
        return msg

    if mtype == MessageType.IMAGE:
        msg = GoGdpImage(msg_type=mtype)
        _apply_common(msg, common)
        section = reader.section_u16()
        msg.height_ = section.read_u32()
        msg.width_ = section.read_u32()
        msg.pixel_size = section.read_u32()
        msg.color_filter = section.read_u32()
        msg.pixel_format = section.read_i32()
        msg.exposure = section.read_f32()
        msg.resolution = (section.read_f64(), section.read_f64(), section.read_f64())
        msg.offset = (section.read_f64(), section.read_f64(), section.read_f64())
        row = image_row_size(msg.width_, msg.pixel_size, msg.color_filter, msg.pixel_format)
        msg.pixels_ = section.read_u8_array(msg.height_ * row)
        msg.raw = packet
        return msg

    if mtype == MessageType.SPOTS:
        msg = GoGdpSpots(msg_type=mtype)
        _apply_common(msg, common)
        section = reader.section_u16()
        msg.point_count = section.read_u32()
        msg.exposure = section.read_f32()
        msg.column_based = section.read_u8() > 0
        msg.slice_scale = section.read_f32()
        msg.slice_offset = section.read_f32()
        msg.center_scale = section.read_f32()
        msg.center_offset = section.read_f32()
        msg.max_slice_count = section.read_u32()
        msg.spot_center_min = section.read_u32()
        msg.spot_center_max = section.read_u32()
        for _ in range(msg.point_count):
            msg.spots_.append(GdpSpot(slice=reader.read_u16(), centre=reader.read_u32()))
        msg.raw = packet
        return msg

    if mtype == MessageType.MESH:
        msg = GoGdpMesh(msg_type=mtype)
        _apply_common(msg, common)
        section = reader.section_u16()
        msg.has_data = section.read_u8() > 0
        msg.system_channel_count = section.read_u32()
        msg.max_user_channel_count = section.read_u32()
        msg.user_channel_count = section.read_u32()
        msg.channel_count = section.read_u32()
        msg.offset = (section.read_f64(), section.read_f64(), section.read_f64())
        msg.range = (section.read_f64(), section.read_f64(), section.read_f64())
        for _ in range(msg.channel_count):
            ch_section = reader.section_u16()
            channel = MeshChannel(
                id=ch_section.read_u32(),
                type=ch_section.read_u32(),
                state=ch_section.read_i32(),
                flag=ch_section.read_u32(),
                allocated_count=ch_section.read_u32(),
                used_count=ch_section.read_u32(),
            )
            channel.data = _read_mesh_channel(reader, channel.id, channel.allocated_count)
            msg.channels_.append(channel)
        msg.raw = packet
        return msg

    if mtype == MessageType.STAMP:
        msg = GoGdpStamp(msg_type=mtype)
        _apply_common(msg, common)
        section = reader.section_u16()
        msg.frame_index = section.read_u64()
        msg.timestamp = section.read_u64()
        msg.encoder = int(section.read_u64())
        msg.encoder_at_z = int(section.read_u64())
        msg.status = section.read_u64()
        msg.system_time_seconds = section.read_u64()
        msg.system_time_nanoseconds = section.read_u64()
        msg.raw = packet
        return msg

    if mtype == MessageType.MEASUREMENT:
        msg = GoGdpMeasurement(msg_type=mtype)
        _apply_common(msg, common)
        msg.value = reader.read_f64()
        msg.decision = reader.read_u8()
        if reader.remaining() >= 24:
            msg.label_position = (reader.read_f64(), reader.read_f64(), reader.read_f64())
        msg.raw = packet
        return msg

    if mtype == MessageType.STRING:
        msg = GoGdpString(msg_type=mtype)
        _apply_common(msg, common)
        strlen = reader.read_u32()
        msg.text = reader.read_text(strlen)
        msg.decision = reader.read_u8()
        if reader.remaining() >= 24:
            msg.label_position = (reader.read_f64(), reader.read_f64(), reader.read_f64())
        msg.raw = packet
        return msg

    if mtype == MessageType.RENDERING:
        msg = GoGdpRendering(msg_type=mtype)
        _apply_common(msg, common)
        msg.graphics_ = _parse_graphics(reader)
        msg.raw = packet
        return msg

    if mtype == MessageType.POINT_FEATURE:
        msg = GoGdpFeaturePoint(msg_type=mtype)
        _apply_common(msg, common)
        msg.position = (reader.read_f64(), reader.read_f64(), reader.read_f64())
        msg.raw = packet
        return msg

    if mtype == MessageType.LINE_FEATURE:
        msg = GoGdpFeatureLine(msg_type=mtype)
        _apply_common(msg, common)
        msg.position = (reader.read_f64(), reader.read_f64(), reader.read_f64())
        msg.direction = (reader.read_f64(), reader.read_f64(), reader.read_f64())
        msg.raw = packet
        return msg

    if mtype == MessageType.PLANE_FEATURE:
        msg = GoGdpFeaturePlane(msg_type=mtype)
        _apply_common(msg, common)
        msg.normal = (reader.read_f64(), reader.read_f64(), reader.read_f64())
        msg.distance_to_origin = reader.read_f64()
        msg.raw = packet
        return msg

    if mtype == MessageType.CIRCLE_FEATURE:
        msg = GoGdpFeatureCircle(msg_type=mtype)
        _apply_common(msg, common)
        msg.center = (reader.read_f64(), reader.read_f64(), reader.read_f64())
        msg.normal = (reader.read_f64(), reader.read_f64(), reader.read_f64())
        msg.radius = reader.read_f64()
        msg.raw = packet
        return msg

    common.raw = packet
    return common


def _read_surface_base(section: KSerializerReader, msg: GoGdpSurfaceUniform | GoGdpSurfacePointCloud) -> None:
    msg.length_ = section.read_u32()
    msg.width_ = section.read_u32()
    msg.intensity_length_ = section.read_u32()
    msg.intensity_width_ = section.read_u32()
    msg.resolution = (section.read_f64(), section.read_f64(), section.read_f64())
    msg.offset = (section.read_f64(), section.read_f64(), section.read_f64())
    msg.surface_id = section.read_u32()
    msg.exposure = section.read_f32()


def _read_intensity_pixel_format(section: KSerializerReader, intensity_length: int, intensity_width: int) -> int:
    if intensity_length <= 0 or intensity_width <= 0:
        return 0
    if section.remaining() >= 4:
        return section.read_i32()
    return 1


def _read_mesh_channel(reader: KSerializerReader, channel_id: int, count: int) -> list[Any]:
    if count <= 0:
        return []
    if channel_id in (_MESH_ID_VERTEX, _MESH_ID_FACET_NORMAL, _MESH_ID_VERTEX_NORMAL):
        return [(reader.read_f32(), reader.read_f32(), reader.read_f32()) for _ in range(count)]
    if channel_id == _MESH_ID_FACET:
        return [(reader.read_u32(), reader.read_u32(), reader.read_u32()) for _ in range(count)]
    if channel_id == _MESH_ID_VERTEX_CURVATURE:
        return [reader.read_f32() for _ in range(count)]
    if channel_id == _MESH_ID_VERTEX_TEXTURE:
        return [reader.read_u8() for _ in range(count)]
    return [reader.read_u8() for _ in range(count)]


def _parse_graphics(reader: KSerializerReader) -> GoGraphics:
    graphics = GoGraphics()
    section = reader.section_u16()
    point_count = section.read_u16()
    line_count = section.read_u16()
    region_count = section.read_u16()
    plane_count = section.read_u16()
    ray_count = section.read_u16()
    label_count = section.read_u16()
    position_count = section.read_u16()

    for _ in range(point_count):
        ps = GoPointSet()
        ps_section = reader.section_u16()
        ps.size = ps_section.read_f32()
        ps.color = ps_section.read_u32()
        ps.shape = ps_section.read_i32()
        n = ps_section.read_u16()
        for _ in range(n):
            ps.points.append((reader.read_f32(), reader.read_f32(), reader.read_f32()))
        graphics.point_sets.append(ps)

    for _ in range(line_count):
        ls = GoLineSet()
        ls_section = reader.section_u16()
        ls.width = ls_section.read_f32()
        ls.color = ls_section.read_u32()
        ls.has_start_point_arrow = ls_section.read_u8() > 0
        ls.has_end_point_arrow = ls_section.read_u8() > 0
        n = ls_section.read_u16()
        for _ in range(n):
            ls.points.append((reader.read_f32(), reader.read_f32(), reader.read_f32()))
        graphics.line_sets.append(ls)

    for _ in range(region_count):
        region_type = reader.read_u8()
        if region_type == _REGION_PROFILE_2D:
            sec = reader.section_u16()
            graphics.regions.append(
                {
                    "type": region_type,
                    "x": sec.read_f64(),
                    "z": sec.read_f64(),
                    "width": sec.read_f64(),
                    "height": sec.read_f64(),
                    "angleY": sec.read_f64(),
                }
            )
        elif region_type == _REGION_SURFACE_2D:
            sec = reader.section_u16()
            graphics.regions.append(
                {
                    "type": region_type,
                    "x": sec.read_f64(),
                    "y": sec.read_f64(),
                    "width": sec.read_f64(),
                    "length": sec.read_f64(),
                    "angleZ": sec.read_f64(),
                }
            )
        elif region_type == _REGION_3D:
            sec = reader.section_u16()
            graphics.regions.append(
                {
                    "type": region_type,
                    "x": sec.read_f64(),
                    "y": sec.read_f64(),
                    "z": sec.read_f64(),
                    "width": sec.read_f64(),
                    "length": sec.read_f64(),
                    "height": sec.read_f64(),
                    "angleZ": sec.read_f64(),
                }
            )

    for _ in range(plane_count):
        sec = reader.section_u16()
        graphics.planes.append(
            GoPlane(
                distance=sec.read_f32(),
                normal=(sec.read_f32(), sec.read_f32(), sec.read_f32()),
            )
        )

    for _ in range(ray_count):
        sec = reader.section_u16()
        graphics.rays.append(
            GoRay(
                position=(sec.read_f32(), sec.read_f32(), sec.read_f32()),
                direction=(sec.read_f32(), sec.read_f32(), sec.read_f32()),
                width=sec.read_f32(),
                color=sec.read_u32(),
            )
        )

    for _ in range(label_count):
        sec = reader.section_u16()
        length = sec.read_u16()
        text = sec.read_text(length) if length else ""
        graphics.labels.append(
            GoLabel(
                text=text,
                position=(sec.read_f64(), sec.read_f64(), sec.read_f64()),
            )
        )

    for _ in range(position_count):
        sec = reader.section_u16()
        graphics.positions.append(
            GoPosition(
                position=(sec.read_f64(), sec.read_f64(), sec.read_f64()),
                type=sec.read_u8(),
            )
        )

    return graphics


def _skip_transform(section: KSerializerReader) -> None:
    for _ in range(16):
        section.read_f32()


def _skip_bbox(section: KSerializerReader) -> None:
    for _ in range(6):
        section.read_f64()

from __future__ import annotations

import json
from dataclasses import dataclass
from math import atan2, cos, degrees, pi, sin
from pathlib import Path

from rebar_schedule.domain.models import RebarScheduleRow


@dataclass(frozen=True, slots=True)
class LinePrimitive:
    x1: float
    y1: float
    x2: float
    y2: float
    layer: str


@dataclass(frozen=True, slots=True)
class ArcPrimitive:
    cx: float
    cy: float
    radius: float
    start_angle: float
    end_angle: float
    layer: str


@dataclass(frozen=True, slots=True)
class TextPrimitive:
    x: float
    y: float
    value: str
    height: float
    layer: str


@dataclass(frozen=True, slots=True)
class CirclePrimitive:
    cx: float
    cy: float
    radius: float
    layer: str


@dataclass(frozen=True, slots=True)
class WorkshopDrawing:
    lines: tuple[LinePrimitive, ...]
    arcs: tuple[ArcPrimitive, ...]
    texts: tuple[TextPrimitive, ...]
    circles: tuple[CirclePrimitive, ...] = ()


_DEFAULT_PATTERN_PATH = Path(__file__).resolve().parents[3] / "build" / "member-58.patterns.json"
_PATTERN_CACHE: dict[str, object] | None = None


def build_shape_geometry(
    row: RebarScheduleRow,
    *,
    x: float,
    row_top: float,
    width: float,
    height: float,
    shape_layer: str,
    text_layer: str,
) -> WorkshopDrawing | None:
    if row.workshop_shape_code == "ACI-10":
        return _build_aci10_geometry(
            row,
            x=x,
            row_top=row_top,
            width=width,
            height=height,
            shape_layer=shape_layer,
            text_layer=text_layer,
        )
    return None


def _build_aci10_geometry(
    row: RebarScheduleRow,
    *,
    x: float,
    row_top: float,
    width: float,
    height: float,
    shape_layer: str,
    text_layer: str,
) -> WorkshopDrawing:
    section_w = row.section_width_mm or 250.0
    section_h = row.section_height_mm or section_w
    cover = row.concrete_cover_mm or 30.0
    outer_w_mm = max(section_w - 2.0 * cover - row.diameter_mm, 80.0)
    outer_h_mm = max(section_h - 2.0 * cover - row.diameter_mm, 80.0)
    hook_len_mm = _resolve_aci_hook_length_mm(row)

    max_draw_w = 3.0
    max_draw_h = 1.95
    scale = min(max_draw_w / outer_w_mm, max_draw_h / outer_h_mm)
    draw_w = outer_w_mm * scale
    draw_h = outer_h_mm * scale
    draw_hook = max(min(draw_w, draw_h) * 0.22, hook_len_mm * scale * 0.65)
    radius = min(draw_w, draw_h) * 0.12

    left = x + (width - draw_w) / 2.0
    top = row_top - 0.92
    right = left + draw_w
    bottom = top - draw_h

    lines: list[LinePrimitive] = []
    arcs: list[ArcPrimitive] = []
    texts: list[TextPrimitive] = []
    circles: list[CirclePrimitive] = []

    if row.section_shape_code == "circular":
        return _build_circular_stirrup_geometry(
            row,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            shape_layer=shape_layer,
            text_layer=text_layer,
            x=x,
            row_top=row_top,
            height=height,
        )

    native_pattern = _load_native_aci10_pattern()
    outer, _used_native_outer = _outer_stirrup_from_pattern(
        native_pattern,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        fallback_radius=radius,
        fallback_hook_len=draw_hook,
        layer=shape_layer,
    )
    lines.extend(outer.lines)
    arcs.extend(outer.arcs)
    circles.extend(
        _longitudinal_bar_circles(
            row,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            layer=text_layer,
        )
    )

    if row.crossties_active:
        horizontal, vertical = _symbolic_crossties(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            layer=shape_layer,
        )
        lines.extend(horizontal.lines)
        lines.extend(vertical.lines)

    hook_label = _stirrup_hook_label(row.stirrup_type)

    texts.extend(
        [
            TextPrimitive(
                x=(left + right) / 2.0 - 0.45,
                y=bottom - 0.60,
                value=f"{outer_w_mm / 10.0:.0f}",
                height=0.20,
                layer=text_layer,
            ),
            TextPrimitive(
                x=left - 0.60,
                y=(top + bottom) / 2.0,
                value=f"{outer_h_mm / 10.0:.0f}",
                height=0.20,
                layer=text_layer,
            ),
            TextPrimitive(
                x=left - 0.20,
                y=bottom - 0.22,
                value=hook_label,
                height=0.16,
                layer=text_layer,
            ),
        ]
    )
    if row.spacing_mm:
        texts.append(
            TextPrimitive(
                x=x + 0.25,
                y=row_top - height + 0.55,
                value=f"c/{row.spacing_mm / 10.0:.0f}",
                height=0.16,
                layer=text_layer,
            )
        )

    return WorkshopDrawing(lines=tuple(lines), arcs=tuple(arcs), texts=tuple(texts), circles=tuple(circles))


def _build_circular_stirrup_geometry(
    row: RebarScheduleRow,
    *,
    left: float,
    top: float,
    right: float,
    bottom: float,
    shape_layer: str,
    text_layer: str,
    x: float,
    row_top: float,
    height: float,
) -> WorkshopDrawing:
    cx = (left + right) / 2.0
    cy = (top + bottom) / 2.0
    radius = min(right - left, top - bottom) * 0.5
    bar_radius = radius * 0.09
    stirrup_radius = radius - bar_radius * 1.8
    circles = [
        CirclePrimitive(
            cx=cx + stirrup_radius * cos(2.0 * pi * index / max(row.count, 1)),
            cy=cy + stirrup_radius * sin(2.0 * pi * index / max(row.count, 1)),
            radius=bar_radius,
            layer=text_layer,
        )
        for index in range(max(row.count, 1))
    ]
    texts = [
        TextPrimitive(
            x=cx - 0.45,
            y=bottom - 0.60,
            value=f"{((row.section_width_mm or row.section_height_mm or 0.0) - 2.0 * (row.concrete_cover_mm or 30.0)) / 10.0:.0f}",
            height=0.20,
            layer=text_layer,
        )
    ]
    if row.spacing_mm:
        texts.append(
            TextPrimitive(
                x=x + 0.25,
                y=row_top - height + 0.55,
                value=f"c/{row.spacing_mm / 10.0:.0f}",
                height=0.16,
                layer=text_layer,
            )
        )
    return WorkshopDrawing(
        lines=(),
        arcs=(),
        texts=tuple(texts),
        circles=(CirclePrimitive(cx=cx, cy=cy, radius=radius - bar_radius, layer=shape_layer), *circles),
    )


def _load_native_aci10_pattern() -> dict[str, object] | None:
    global _PATTERN_CACHE
    if _PATTERN_CACHE is not None:
        return _PATTERN_CACHE
    if not _DEFAULT_PATTERN_PATH.exists():
        _PATTERN_CACHE = {}
        return _PATTERN_CACHE
    try:
        _PATTERN_CACHE = json.loads(_DEFAULT_PATTERN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _PATTERN_CACHE = {}
    return _PATTERN_CACHE


def _resolve_aci_hook_length_mm(row: RebarScheduleRow) -> float:
    if row.bending_diameter_mm and row.bending_diameter_mm > 0:
        return max(row.bending_diameter_mm * 6.0, 75.0)
    return max(row.diameter_mm * 10.0, 75.0)


def _outer_stirrup_aci10(
    *,
    left: float,
    top: float,
    right: float,
    bottom: float,
    radius: float,
    hook_len: float,
    layer: str,
) -> WorkshopDrawing:
    lines: list[LinePrimitive] = []
    arcs: list[ArcPrimitive] = []

    hook_root_x = right - radius * 0.95
    hook_root_y = top - radius * 0.95
    hook_end_x = hook_root_x - hook_len * 0.72
    hook_end_y = hook_root_y - hook_len * 0.72

    lines.extend(
        [
            LinePrimitive(left + radius, top, right - radius, top, layer),
            LinePrimitive(left, top - radius, left, bottom + radius, layer),
            LinePrimitive(left + radius, bottom, right - radius, bottom, layer),
            LinePrimitive(right, bottom + radius, right, hook_root_y, layer),
            LinePrimitive(hook_root_x, hook_root_y, hook_end_x, hook_end_y, layer),
        ]
    )
    arcs.extend(
        [
            ArcPrimitive(left + radius, top - radius, radius, 90.0, 180.0, layer),
            ArcPrimitive(left + radius, bottom + radius, radius, 180.0, 270.0, layer),
            ArcPrimitive(right - radius, bottom + radius, radius, 270.0, 360.0, layer),
            ArcPrimitive(right - radius, top - radius, radius, 0.0, 45.0, layer),
        ]
    )
    return WorkshopDrawing(lines=tuple(lines), arcs=tuple(arcs), texts=())


def _rounded_rect_primitives(
    *,
    left: float,
    top: float,
    right: float,
    bottom: float,
    radius: float,
    layer: str,
) -> tuple[list[LinePrimitive], list[ArcPrimitive]]:
    lines = [
        LinePrimitive(left + radius, top, right - radius, top, layer),
        LinePrimitive(left, top - radius, left, bottom + radius, layer),
        LinePrimitive(left + radius, bottom, right - radius, bottom, layer),
        LinePrimitive(right, top - radius, right, bottom + radius, layer),
    ]
    arcs = [
        ArcPrimitive(left + radius, top - radius, radius, 90.0, 180.0, layer),
        ArcPrimitive(left + radius, bottom + radius, radius, 180.0, 270.0, layer),
        ArcPrimitive(right - radius, bottom + radius, radius, 270.0, 360.0, layer),
        ArcPrimitive(right - radius, top - radius, radius, 0.0, 90.0, layer),
    ]
    return lines, arcs


def _outer_stirrup_from_pattern(
    pattern_payload: dict[str, object] | None,
    *,
    left: float,
    top: float,
    right: float,
    bottom: float,
    fallback_radius: float,
    fallback_hook_len: float,
    layer: str,
) -> tuple[WorkshopDrawing, bool]:
    piece = _pattern_piece(pattern_payload, "cerco_principal")
    if not piece:
        return (
            _outer_stirrup_aci10(
                left=left,
                top=top,
                right=right,
                bottom=bottom,
                radius=fallback_radius,
                hook_len=fallback_hook_len,
                layer=layer,
            ),
            False,
        )
    drawing = _scale_pattern_piece_to_box(piece, left=left, top=top, right=right, bottom=bottom, layer=layer)
    return drawing, True


def _symbolic_crossties(
    *,
    left: float,
    top: float,
    right: float,
    bottom: float,
    layer: str,
) -> tuple[WorkshopDrawing, WorkshopDrawing]:
    width = right - left
    height = top - bottom
    cx = (left + right) / 2.0
    cy = (top + bottom) / 2.0
    margin_x = width * 0.16
    margin_y = height * 0.16

    horizontal = WorkshopDrawing(
        lines=(LinePrimitive(left + margin_x, cy, right - margin_x, cy, layer),),
        arcs=(),
        texts=(),
        circles=(),
    )
    vertical = WorkshopDrawing(
        lines=(LinePrimitive(cx, bottom + margin_y, cx, top - margin_y, layer),),
        arcs=(),
        texts=(),
        circles=(),
    )
    return horizontal, vertical


def _pattern_piece(pattern_payload: dict[str, object] | None, key: str) -> dict[str, object] | None:
    if not pattern_payload:
        return None
    patterns = pattern_payload.get("patrones")
    if not isinstance(patterns, dict):
        return None
    piece = patterns.get(key)
    if not isinstance(piece, dict):
        return None
    return piece


def _scale_pattern_piece_to_box(
    piece: dict[str, object],
    *,
    left: float,
    top: float,
    right: float,
    bottom: float,
    layer: str,
) -> WorkshopDrawing:
    primitives = piece.get("primitivas_locales", [])
    bounds = _piece_local_bounds(primitives)
    return _scale_pattern_primitives(primitives, bounds, left, top, right, bottom, layer)


def _scale_pattern_primitives(
    primitives: list[dict[str, object]],
    bounds: dict[str, float],
    left: float,
    top: float,
    right: float,
    bottom: float,
    layer: str,
) -> WorkshopDrawing:
    width = max(bounds["max_x"] - bounds["min_x"], 1e-6)
    height = max(bounds["max_y"] - bounds["min_y"], 1e-6)
    sx = (right - left) / width
    sy = (top - bottom) / height
    x_mid_src = (bounds["min_x"] + bounds["max_x"]) / 2.0
    y_mid_src = (bounds["min_y"] + bounds["max_y"]) / 2.0
    x_mid_dst = (left + right) / 2.0
    y_mid_dst = (top + bottom) / 2.0

    lines: list[LinePrimitive] = []
    arcs: list[ArcPrimitive] = []
    for primitive in primitives:
        primitive_type = primitive["tipo"]
        geometry = primitive["geometria_local"]
        if primitive_type == "POLYLINE":
            vertices = geometry["vertices"]
            for index in range(len(vertices) - 1):
                x1 = x_mid_dst + (float(vertices[index]["x"]) - x_mid_src) * sx
                y1 = y_mid_dst + (float(vertices[index]["y"]) - y_mid_src) * sy
                x2 = x_mid_dst + (float(vertices[index + 1]["x"]) - x_mid_src) * sx
                y2 = y_mid_dst + (float(vertices[index + 1]["y"]) - y_mid_src) * sy
                lines.append(LinePrimitive(x1, y1, x2, y2, layer))
        elif primitive_type == "LINE":
            x1 = x_mid_dst + (float(geometry["x1"]) - x_mid_src) * sx
            y1 = y_mid_dst + (float(geometry["y1"]) - y_mid_src) * sy
            x2 = x_mid_dst + (float(geometry["x2"]) - x_mid_src) * sx
            y2 = y_mid_dst + (float(geometry["y2"]) - y_mid_src) * sy
            lines.append(LinePrimitive(x1, y1, x2, y2, layer))
        elif primitive_type == "ARC":
            cx = x_mid_dst + (float(geometry["cx"]) - x_mid_src) * sx
            cy = y_mid_dst + (float(geometry["cy"]) - y_mid_src) * sy
            radius = float(geometry["radio"]) * min(sx, sy)
            arcs.append(
                ArcPrimitive(
                    cx=cx,
                    cy=cy,
                    radius=radius,
                    start_angle=float(geometry["angulo_inicio"]),
                    end_angle=float(geometry["angulo_fin"]),
                    layer=layer,
                )
            )
    return WorkshopDrawing(lines=tuple(lines), arcs=tuple(arcs), texts=())


def _piece_local_bounds(primitives: list[dict[str, object]]) -> dict[str, float]:
    xs: list[float] = []
    ys: list[float] = []
    for primitive in primitives:
        geometry = primitive["geometria_local"]
        primitive_type = primitive["tipo"]
        if primitive_type == "ARC":
            cx = float(geometry["cx"])
            cy = float(geometry["cy"])
            radius = float(geometry["radio"])
            xs.extend([cx - radius, cx + radius])
            ys.extend([cy - radius, cy + radius])
        elif primitive_type == "LINE":
            xs.extend([float(geometry["x1"]), float(geometry["x2"])])
            ys.extend([float(geometry["y1"]), float(geometry["y2"])])
        else:
            for vertex in geometry["vertices"]:
                xs.append(float(vertex["x"]))
                ys.append(float(vertex["y"]))
    if not xs or not ys:
        return {"min_x": -0.5, "max_x": 0.5, "min_y": -0.5, "max_y": 0.5}
    return {"min_x": min(xs), "max_x": max(xs), "min_y": min(ys), "max_y": max(ys)}


def _filter_horizontal_pattern(piece: dict[str, object]) -> list[dict[str, object]]:
    primitives = piece.get("primitivas_locales", [])
    filtered: list[dict[str, object]] = []
    for primitive in primitives:
        if primitive["tipo"] != "POLYLINE":
            continue
        vertices = primitive["geometria_local"]["vertices"]
        dx = abs(float(vertices[-1]["x"]) - float(vertices[0]["x"]))
        dy = abs(float(vertices[-1]["y"]) - float(vertices[0]["y"]))
        if dx >= dy:
            filtered.append(primitive)
    if filtered:
        return filtered[:1]
    return []


def _filter_vertical_pattern(piece: dict[str, object]) -> list[dict[str, object]]:
    primitives = piece.get("primitivas_locales", [])
    lines: list[dict[str, object]] = []
    arcs: list[dict[str, object]] = []
    for primitive in primitives:
        if primitive["tipo"] == "ARC":
            arcs.append(primitive)
            continue
        vertices = primitive["geometria_local"]["vertices"]
        dx = abs(float(vertices[-1]["x"]) - float(vertices[0]["x"]))
        dy = abs(float(vertices[-1]["y"]) - float(vertices[0]["y"]))
        if dy >= dx:
            lines.append(primitive)
    filtered = lines[:1] + arcs[:2]
    return filtered


def _resolve_pattern_span(piece: dict[str, object] | None, *, default_span: float, axis: str) -> float:
    if not piece:
        return default_span
    bounds = piece.get("bounds_originales")
    if not isinstance(bounds, dict):
        return default_span
    key = "ancho" if axis == "x" else "alto"
    try:
        value = float(bounds.get(key, 0.0))
    except (TypeError, ValueError):
        return default_span
    if value <= 0:
        return default_span
    return default_span


def _stirrup_hook_label(stirrup_type: str | None) -> str:
    if not stirrup_type:
        return ""
    if "HOOK_135" in stirrup_type:
        return "135%%d"
    if "HOOK_90" in stirrup_type:
        return "90%%d"
    if "HOOK_180" in stirrup_type:
        return "180%%d"
    return ""


def _longitudinal_bar_circles(
    row: RebarScheduleRow,
    *,
    left: float,
    top: float,
    right: float,
    bottom: float,
    layer: str,
) -> list[CirclePrimitive]:
    width = right - left
    height = top - bottom
    radius = min(width, height) * 0.055
    x_left = left + width * 0.12
    x_mid = (left + right) / 2.0
    x_right = right - width * 0.12
    y_top = top - height * 0.12
    y_mid = (top + bottom) / 2.0
    y_bottom = bottom + height * 0.12

    if row.crossties_active:
        positions = [
            (x_left, y_top),
            (x_mid, y_top),
            (x_right, y_top),
            (x_left, y_mid),
            (x_right, y_mid),
            (x_left, y_bottom),
            (x_mid, y_bottom),
            (x_right, y_bottom),
        ]
    else:
        positions = [
            (x_left, y_top),
            (x_right, y_top),
            (x_left, y_bottom),
            (x_right, y_bottom),
        ]
    return [CirclePrimitive(cx=x_pos, cy=y_pos, radius=radius, layer=layer) for x_pos, y_pos in positions]


def _uniform_layout_bar_circles(
    row: RebarScheduleRow,
    *,
    left: float,
    top: float,
    right: float,
    bottom: float,
    layer: str,
) -> list[CirclePrimitive]:
    width = right - left
    height = top - bottom
    radius = min(width, height) * 0.045
    x_left = left + width * 0.10
    x_mid = (left + right) / 2.0
    x_right = right - width * 0.10
    y_top = top - height * 0.10
    y_mid = (top + bottom) / 2.0
    y_bottom = bottom + height * 0.10

    is_tall = (row.section_height_mm or 0.0) >= (row.section_width_mm or 0.0) * 1.2
    count = max(row.count, 4)
    if count <= 4:
        positions = [
            (x_left, y_top),
            (x_right, y_top),
            (x_left, y_bottom),
            (x_right, y_bottom),
        ]
    elif count == 6:
        positions = (
            [
                (x_left, y_top),
                (x_right, y_top),
                (x_left, y_mid),
                (x_right, y_mid),
                (x_left, y_bottom),
                (x_right, y_bottom),
            ]
            if is_tall
            else [
                (x_left, y_top),
                (x_mid, y_top),
                (x_right, y_top),
                (x_left, y_bottom),
                (x_mid, y_bottom),
                (x_right, y_bottom),
            ]
        )
    else:
        positions = [
            (x_left, y_top),
            (x_mid, y_top),
            (x_right, y_top),
            (x_left, y_mid),
            (x_right, y_mid),
            (x_left, y_bottom),
            (x_mid, y_bottom),
            (x_right, y_bottom),
        ]
    return [CirclePrimitive(cx=x_pos, cy=y_pos, radius=radius, layer=layer) for x_pos, y_pos in positions]


def line_angle_degrees(line: LinePrimitive) -> float:
    return degrees(atan2(line.y2 - line.y1, line.x2 - line.x1))

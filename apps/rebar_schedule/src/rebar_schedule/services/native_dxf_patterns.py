from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rebar_schedule.services.native_dxf_analysis import DxfBounds, analyze_native_rfem_dxf


@dataclass(frozen=True, slots=True)
class RawPrimitive:
    primitive_type: str
    layer: str
    geometry: dict[str, object]


def extract_native_section_patterns(dxf_path: str, analysis_path: str | None = None) -> dict[str, object]:
    source_path = Path(dxf_path)
    analysis = (
        json.loads(Path(analysis_path).read_text(encoding="utf-8"))
        if analysis_path
        else analyze_native_rfem_dxf(str(source_path))
    )
    primitives = _parse_raw_primitives(source_path)
    subforms = analysis["subformas_seccion"]

    return {
        "archivo_dxf": str(source_path),
        "origen_analisis": analysis_path or "in_memory",
        "patrones": {
            "cerco_principal": _extract_pattern_piece(
                primitives,
                target_layer=subforms["cerco_principal"]["layer"],
                target_bounds=_bounds_from_dict(subforms["cerco_principal"]["bounds"]),
                grow=0.01,
                code="ACI-10-CERCO",
            ),
            "cruceta_horizontal": _extract_pattern_piece(
                primitives,
                target_layer=subforms["cruceta_horizontal"]["layer"],
                target_bounds=_bounds_from_dict(subforms["cruceta_horizontal"]["bounds"]),
                grow=0.012,
                code="ACI-10-CRUCETA-H",
            ),
            "cruceta_vertical": _extract_pattern_piece(
                primitives,
                target_layer=subforms["cruceta_vertical"]["layer"],
                target_bounds=_bounds_from_dict(subforms["cruceta_vertical"]["bounds"]),
                grow=0.012,
                code="ACI-10-CRUCETA-V",
            ),
        },
    }


def _parse_raw_primitives(path: Path) -> list[RawPrimitive]:
    raw = path.read_text(encoding="cp1252", errors="ignore").splitlines()
    pairs = [(raw[index].strip(), raw[index + 1].rstrip("\n")) for index in range(0, len(raw) - 1, 2)]

    primitives: list[RawPrimitive] = []
    index = 0
    while index < len(pairs):
        code, value = pairs[index]
        if code != "0":
            index += 1
            continue

        entity_type = value.strip()
        if entity_type in {"LINE", "ARC"}:
            data: dict[str, str] = {"type": entity_type}
            index += 1
            while index < len(pairs) and pairs[index][0] != "0":
                inner_code, inner_value = pairs[index]
                data[inner_code] = inner_value.strip()
                index += 1
            primitive = _build_simple_primitive(data)
            if primitive is not None:
                primitives.append(primitive)
            continue

        if entity_type == "POLYLINE":
            data = {"type": entity_type, "vertices": []}
            index += 1
            while index < len(pairs):
                inner_code, inner_value = pairs[index]
                if inner_code == "0" and inner_value.strip() == "VERTEX":
                    vertex: dict[str, str] = {}
                    index += 1
                    while index < len(pairs) and pairs[index][0] != "0":
                        vertex_code, vertex_value = pairs[index]
                        vertex[vertex_code] = vertex_value.strip()
                        index += 1
                    data["vertices"].append(vertex)
                    continue
                if inner_code == "0" and inner_value.strip() == "SEQEND":
                    index += 1
                    break
                if inner_code == "0":
                    break
                data[inner_code] = inner_value.strip()
                index += 1
            primitive = _build_polyline_primitive(data)
            if primitive is not None:
                primitives.append(primitive)
            continue

        index += 1

    return primitives


def _build_simple_primitive(data: dict[str, str]) -> RawPrimitive | None:
    layer = _normalize_layer_name(data.get("8", "").strip())
    if data["type"] == "LINE":
        return RawPrimitive(
            primitive_type="LINE",
            layer=layer,
            geometry={
                "x1": float(data["10"]),
                "y1": float(data["20"]),
                "x2": float(data["11"]),
                "y2": float(data["21"]),
            },
        )
    if data["type"] == "ARC":
        return RawPrimitive(
            primitive_type="ARC",
            layer=layer,
            geometry={
                "cx": float(data["10"]),
                "cy": float(data["20"]),
                "radio": float(data["40"]),
                "angulo_inicio": float(data["50"]),
                "angulo_fin": float(data["51"]),
            },
        )
    return None


def _build_polyline_primitive(data: dict[str, object]) -> RawPrimitive | None:
    layer = _normalize_layer_name(str(data.get("8", "")).strip())
    vertices = [
        {"x": float(vertex["10"]), "y": float(vertex["20"])}
        for vertex in data.get("vertices", [])
        if "10" in vertex and "20" in vertex
    ]
    if not vertices:
        return None
    return RawPrimitive(
        primitive_type="POLYLINE",
        layer=layer,
        geometry={"vertices": vertices},
    )


def _extract_pattern_piece(
    primitives: list[RawPrimitive],
    *,
    target_layer: str,
    target_bounds: DxfBounds,
    grow: float,
    code: str,
) -> dict[str, object]:
    expanded = DxfBounds(
        target_bounds.xmin - grow,
        target_bounds.ymin - grow,
        target_bounds.xmax + grow,
        target_bounds.ymax + grow,
    )
    selected = [
        primitive
        for primitive in primitives
        if primitive.layer == target_layer and _primitive_intersects_window(primitive, expanded)
    ]
    local_primitives = [
        _to_local_primitive_dict(primitive, origin_x=target_bounds.center_x, origin_y=target_bounds.center_y)
        for primitive in selected
    ]
    unique_primitives = _deduplicate_local_primitives(local_primitives)

    return {
        "codigo": code,
        "layer": target_layer,
        "bounds_originales": target_bounds.to_dict(),
        "bounds_extraccion": expanded.to_dict(),
        "cantidad_primitivas_brutas": len(local_primitives),
        "cantidad_primitivas_unicas": len(unique_primitives),
        "primitivas_locales": unique_primitives,
    }


def _primitive_intersects_window(primitive: RawPrimitive, window: DxfBounds) -> bool:
    bounds = _primitive_bounds(primitive)
    return not (
        bounds.xmax < window.xmin
        or bounds.xmin > window.xmax
        or bounds.ymax < window.ymin
        or bounds.ymin > window.ymax
    )


def _primitive_bounds(primitive: RawPrimitive) -> DxfBounds:
    geometry = primitive.geometry
    if primitive.primitive_type == "LINE":
        xs = [float(geometry["x1"]), float(geometry["x2"])]
        ys = [float(geometry["y1"]), float(geometry["y2"])]
        return DxfBounds(min(xs), min(ys), max(xs), max(ys))
    if primitive.primitive_type == "ARC":
        cx = float(geometry["cx"])
        cy = float(geometry["cy"])
        radius = float(geometry["radio"])
        return DxfBounds(cx - radius, cy - radius, cx + radius, cy + radius)
    vertices = geometry["vertices"]
    xs = [float(vertex["x"]) for vertex in vertices]
    ys = [float(vertex["y"]) for vertex in vertices]
    return DxfBounds(min(xs), min(ys), max(xs), max(ys))


def _to_local_primitive_dict(primitive: RawPrimitive, *, origin_x: float, origin_y: float) -> dict[str, object]:
    geometry = primitive.geometry
    if primitive.primitive_type == "LINE":
        local_geometry = {
            "x1": round(float(geometry["x1"]) - origin_x, 6),
            "y1": round(float(geometry["y1"]) - origin_y, 6),
            "x2": round(float(geometry["x2"]) - origin_x, 6),
            "y2": round(float(geometry["y2"]) - origin_y, 6),
        }
    elif primitive.primitive_type == "ARC":
        local_geometry = {
            "cx": round(float(geometry["cx"]) - origin_x, 6),
            "cy": round(float(geometry["cy"]) - origin_y, 6),
            "radio": round(float(geometry["radio"]), 6),
            "angulo_inicio": round(float(geometry["angulo_inicio"]), 6),
            "angulo_fin": round(float(geometry["angulo_fin"]), 6),
        }
    else:
        local_geometry = {
            "vertices": [
                {
                    "x": round(float(vertex["x"]) - origin_x, 6),
                    "y": round(float(vertex["y"]) - origin_y, 6),
                }
                for vertex in geometry["vertices"]
            ]
        }
    return {
        "tipo": primitive.primitive_type,
        "layer": primitive.layer,
        "geometria_local": local_geometry,
    }


def _bounds_from_dict(payload: dict[str, object]) -> DxfBounds:
    return DxfBounds(
        xmin=float(payload["xmin"]),
        ymin=float(payload["ymin"]),
        xmax=float(payload["xmax"]),
        ymax=float(payload["ymax"]),
    )


def _deduplicate_local_primitives(primitives: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    unique: list[dict[str, object]] = []
    for primitive in primitives:
        signature = _primitive_signature(primitive)
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(primitive)
    return unique


def _primitive_signature(primitive: dict[str, object]) -> str:
    primitive_type = str(primitive["tipo"])
    geometry = primitive["geometria_local"]
    if primitive_type == "LINE":
        points = sorted(
            [
                (round(float(geometry["x1"]), 5), round(float(geometry["y1"]), 5)),
                (round(float(geometry["x2"]), 5), round(float(geometry["y2"]), 5)),
            ]
        )
        return f"LINE:{points[0][0]}:{points[0][1]}:{points[1][0]}:{points[1][1]}"

    if primitive_type == "ARC":
        start_angle, end_angle = _normalize_arc_angles(
            float(geometry["angulo_inicio"]),
            float(geometry["angulo_fin"]),
        )
        return (
            "ARC:"
            f"{round(float(geometry['cx']), 5)}:{round(float(geometry['cy']), 5)}:"
            f"{round(float(geometry['radio']), 5)}:{start_angle}:{end_angle}"
        )

    vertices = geometry["vertices"]
    forward = tuple((round(float(vertex["x"]), 5), round(float(vertex["y"]), 5)) for vertex in vertices)
    backward = tuple(reversed(forward))
    canonical = min(forward, backward)
    return f"POLYLINE:{canonical}"


def _normalize_arc_angles(start_angle: float, end_angle: float) -> tuple[float, float]:
    start = round(start_angle % 360.0, 5)
    end = round(end_angle % 360.0, 5)
    if abs(start - 360.0) < 1e-5:
        start = 0.0
    if abs(end - 360.0) < 1e-5:
        end = 0.0
    return (start, end)


def _normalize_layer_name(value: str) -> str:
    replacements = {
        "Ã˜": "Ø",
        "ÃƒËœ": "Ø",
        "Lï¿ƒï¾\xadneas": "Líneas",
        "LÃƒÂ­neas": "Líneas",
    }
    normalized = value
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized

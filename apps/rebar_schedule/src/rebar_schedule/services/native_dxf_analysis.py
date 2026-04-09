from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median


@dataclass(frozen=True, slots=True)
class DxfBounds:
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def width(self) -> float:
        return self.xmax - self.xmin

    @property
    def height(self) -> float:
        return self.ymax - self.ymin

    @property
    def center_x(self) -> float:
        return (self.xmin + self.xmax) / 2.0

    @property
    def center_y(self) -> float:
        return (self.ymin + self.ymax) / 2.0

    def to_dict(self) -> dict[str, float]:
        return {
            "xmin": round(self.xmin, 6),
            "ymin": round(self.ymin, 6),
            "xmax": round(self.xmax, 6),
            "ymax": round(self.ymax, 6),
            "ancho": round(self.width, 6),
            "alto": round(self.height, 6),
            "centro_x": round(self.center_x, 6),
            "centro_y": round(self.center_y, 6),
        }


@dataclass(frozen=True, slots=True)
class DxfEntity:
    entity_type: str
    layer: str
    bounds: DxfBounds
    vertex_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "tipo": self.entity_type,
            "layer": self.layer,
            "vertices": self.vertex_count,
            "bounds": self.bounds.to_dict(),
        }


def analyze_native_rfem_dxf(path: str) -> dict[str, object]:
    entities = _parse_entities(Path(path))
    layers = sorted({entity.layer for entity in entities})
    section_window = _infer_section_window(entities)
    section_entities = [
        entity
        for entity in entities
        if _is_inside_window(entity.bounds, section_window)
    ]

    return {
        "archivo": str(Path(path)),
        "layers": layers,
        "total_entidades": len(entities),
        "conteo_por_layer": _count_by_layer(entities),
        "conteo_por_tipo_y_layer": _count_by_type_and_layer(entities),
        "ventana_seccion": section_window.to_dict(),
        "entidades_seccion": [entity.to_dict() for entity in section_entities],
        "conteo_seccion_por_tipo_y_layer": _count_by_type_and_layer(section_entities),
        "subformas_seccion": _infer_section_subforms(section_entities),
    }


def _parse_entities(path: Path) -> list[DxfEntity]:
    raw = path.read_text(encoding="cp1252", errors="ignore").splitlines()
    pairs = [(raw[index].strip(), raw[index + 1].rstrip("\n")) for index in range(0, len(raw) - 1, 2)]

    entities: list[DxfEntity] = []
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
            entity = _build_simple_entity(data)
            if entity is not None:
                entities.append(entity)
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
            entity = _build_polyline_entity(data)
            if entity is not None:
                entities.append(entity)
            continue

        index += 1

    return entities


def _build_simple_entity(data: dict[str, str]) -> DxfEntity | None:
    layer = _normalize_layer_name(data.get("8", "").strip())
    if data["type"] == "LINE":
        xs = [float(data["10"]), float(data["11"])]
        ys = [float(data["20"]), float(data["21"])]
    elif data["type"] == "ARC":
        cx = float(data["10"])
        cy = float(data["20"])
        radius = float(data["40"])
        xs = [cx - radius, cx + radius]
        ys = [cy - radius, cy + radius]
    else:
        return None
    return DxfEntity(
        entity_type=data["type"],
        layer=layer,
        bounds=DxfBounds(min(xs), min(ys), max(xs), max(ys)),
        vertex_count=0,
    )


def _build_polyline_entity(data: dict[str, object]) -> DxfEntity | None:
    layer = _normalize_layer_name(str(data.get("8", "")).strip())
    vertices = data.get("vertices", [])
    points = [
        (float(vertex.get("10", 0.0)), float(vertex.get("20", 0.0)))
        for vertex in vertices
        if "10" in vertex and "20" in vertex
    ]
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return DxfEntity(
        entity_type="POLYLINE",
        layer=layer,
        bounds=DxfBounds(min(xs), min(ys), max(xs), max(ys)),
        vertex_count=len(points),
    )


def _infer_section_window(entities: list[DxfEntity]) -> DxfBounds:
    section_candidates = [
        entity
        for entity in entities
        if entity.layer.startswith("Stirrup") or entity.layer.startswith("Rebar")
    ]
    if not section_candidates:
        return DxfBounds(0.0, 0.0, 0.0, 0.0)

    center_x = median(entity.bounds.center_x for entity in section_candidates)
    center_y = median(entity.bounds.center_y for entity in section_candidates)
    near_center = [
        entity
        for entity in section_candidates
        if abs(entity.bounds.center_x - center_x) <= 0.4 and abs(entity.bounds.center_y - center_y) <= 0.4
    ]
    if not near_center:
        near_center = section_candidates

    xmin = min(entity.bounds.xmin for entity in near_center)
    ymin = min(entity.bounds.ymin for entity in near_center)
    xmax = max(entity.bounds.xmax for entity in near_center)
    ymax = max(entity.bounds.ymax for entity in near_center)
    return DxfBounds(xmin, ymin, xmax, ymax)


def _is_inside_window(bounds: DxfBounds, window: DxfBounds) -> bool:
    return (
        bounds.center_x >= window.xmin
        and bounds.center_x <= window.xmax
        and bounds.center_y >= window.ymin
        and bounds.center_y <= window.ymax
    )


def _count_by_layer(entities: list[DxfEntity]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entity in entities:
        counts[entity.layer] = counts.get(entity.layer, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _count_by_type_and_layer(entities: list[DxfEntity]) -> list[dict[str, object]]:
    counts: dict[tuple[str, str], int] = {}
    for entity in entities:
        key = (entity.entity_type, entity.layer)
        counts[key] = counts.get(key, 0) + 1
    return [
        {"tipo": entity_type, "layer": layer, "cantidad": count}
        for (entity_type, layer), count in sorted(counts.items(), key=lambda item: (item[0][1], item[0][0]))
    ]


def _infer_section_subforms(entities: list[DxfEntity]) -> dict[str, object]:
    stirrup_layers = sorted({entity.layer for entity in entities if entity.layer.startswith("Stirrup")})
    rebar_layers = sorted({entity.layer for entity in entities if entity.layer.startswith("Rebar")})
    center_x = median(entity.bounds.center_x for entity in entities) if entities else 0.0
    center_y = median(entity.bounds.center_y for entity in entities) if entities else 0.0

    return {
        "cerco_principal": _infer_outer_stirrup(entities, stirrup_layers),
        "cruceta_horizontal": _infer_horizontal_crosstie(entities, stirrup_layers, center_y),
        "cruceta_vertical": _infer_vertical_crosstie(entities, stirrup_layers, center_x),
        "barras_longitudinales": _infer_longitudinal_bars(entities, rebar_layers),
    }


def _infer_outer_stirrup(entities: list[DxfEntity], stirrup_layers: list[str]) -> dict[str, object] | None:
    if not stirrup_layers:
        return None
    target_layer = stirrup_layers[0]
    candidates = [entity for entity in entities if entity.layer == target_layer]
    if not candidates:
        return None
    xs = [entity.bounds.xmin for entity in candidates] + [entity.bounds.xmax for entity in candidates]
    ys = [entity.bounds.ymin for entity in candidates] + [entity.bounds.ymax for entity in candidates]
    return {
        "layer": target_layer,
        "tipo_referencia": "cerco_principal",
        "bounds": DxfBounds(min(xs), min(ys), max(xs), max(ys)).to_dict(),
        "entidades": len(candidates),
    }


def _infer_horizontal_crosstie(
    entities: list[DxfEntity],
    stirrup_layers: list[str],
    center_y: float,
) -> dict[str, object] | None:
    if len(stirrup_layers) < 2:
        return None
    target_layer = stirrup_layers[-1]
    candidates = [
        entity
        for entity in entities
        if entity.layer == target_layer
        and entity.bounds.width > entity.bounds.height
        and abs(entity.bounds.center_y - center_y) < 0.03
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda entity: entity.bounds.width)
    return {
        "layer": target_layer,
        "tipo_referencia": "cruceta_horizontal",
        "bounds": best.bounds.to_dict(),
        "entidades_parecidas": len(candidates),
    }


def _infer_vertical_crosstie(
    entities: list[DxfEntity],
    stirrup_layers: list[str],
    center_x: float,
) -> dict[str, object] | None:
    if len(stirrup_layers) < 2:
        return None
    target_layer = stirrup_layers[-1]
    candidates = [
        entity
        for entity in entities
        if entity.layer == target_layer
        and entity.bounds.height > entity.bounds.width
        and abs(entity.bounds.center_x - center_x) < 0.03
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda entity: entity.bounds.height)
    return {
        "layer": target_layer,
        "tipo_referencia": "cruceta_vertical",
        "bounds": best.bounds.to_dict(),
        "entidades_parecidas": len(candidates),
    }


def _infer_longitudinal_bars(entities: list[DxfEntity], rebar_layers: list[str]) -> dict[str, object] | None:
    if not rebar_layers:
        return None
    target_layer = rebar_layers[0]
    candidates = [
        entity
        for entity in entities
        if entity.layer == target_layer and entity.bounds.width > 0.15 and entity.bounds.height < 0.02
    ]
    if not candidates:
        return None
    ys = sorted({round(entity.bounds.center_y, 6) for entity in candidates})
    return {
        "layer": target_layer,
        "tipo_referencia": "barras_longitudinales",
        "cantidad_trazos_horizontales": len(candidates),
        "niveles_y": ys,
    }


def _normalize_layer_name(value: str) -> str:
    replacements = {
        "Ã˜": "Ø",
        "Lï¿ƒï¾\xadneas": "Líneas",
    }
    normalized = value
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Aci10Calibration:
    outer_width: float
    outer_height: float
    horizontal_span_ratio: float
    horizontal_offset_y_ratio: float
    vertical_span_ratio: float
    vertical_offset_x_ratio: float
    horizontal_stub_ratio: float
    vertical_stub_ratio: float
    crosstie_arc_radius_ratio: float
    outer_hook_ratio: float


DEFAULT_ACI10_CALIBRATION = Aci10Calibration(
    outer_width=1.0,
    outer_height=1.0,
    horizontal_span_ratio=0.89,
    horizontal_offset_y_ratio=-0.044,
    vertical_span_ratio=0.89,
    vertical_offset_x_ratio=-0.044,
    horizontal_stub_ratio=0.13,
    vertical_stub_ratio=0.13,
    crosstie_arc_radius_ratio=0.091,
    outer_hook_ratio=0.153,
)


@lru_cache(maxsize=1)
def load_aci10_calibration() -> Aci10Calibration:
    analysis_path = _default_analysis_path()
    if not analysis_path.exists():
        return DEFAULT_ACI10_CALIBRATION

    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    subforms = payload.get("subformas_seccion") or {}
    outer = ((subforms.get("cerco_principal") or {}).get("bounds")) or {}
    horizontal = ((subforms.get("cruceta_horizontal") or {}).get("bounds")) or {}
    vertical = ((subforms.get("cruceta_vertical") or {}).get("bounds")) or {}
    entities = payload.get("entidades_seccion") or []

    outer_width = float(outer.get("ancho", 1.0) or 1.0)
    outer_height = float(outer.get("alto", 1.0) or 1.0)
    outer_center_x = float(outer.get("centro_x", 0.0) or 0.0)
    outer_center_y = float(outer.get("centro_y", 0.0) or 0.0)

    horizontal_span_ratio = _safe_ratio(float(horizontal.get("ancho", outer_width) or outer_width), outer_width, 0.89)
    horizontal_offset_y_ratio = _safe_ratio(
        float(horizontal.get("centro_y", outer_center_y) or outer_center_y) - outer_center_y,
        outer_height,
        -0.044,
    )
    vertical_span_ratio = _safe_ratio(float(vertical.get("alto", outer_height) or outer_height), outer_height, 0.89)
    vertical_offset_x_ratio = _safe_ratio(
        float(vertical.get("centro_x", outer_center_x) or outer_center_x) - outer_center_x,
        outer_width,
        -0.044,
    )

    stirrup_6_entities = [entity for entity in entities if entity.get("layer") == "Stirrup Ø6"]
    horizontal_stub_ratio = _derive_stub_ratio(
        stirrup_6_entities,
        outer_width,
        prefer="horizontal",
        fallback=0.13,
    )
    vertical_stub_ratio = _derive_stub_ratio(
        stirrup_6_entities,
        outer_height,
        prefer="vertical",
        fallback=0.13,
    )
    crosstie_arc_radius_ratio = _derive_arc_ratio(stirrup_6_entities, outer_width, fallback=0.091)

    stirrup_10_entities = [entity for entity in entities if entity.get("layer") == "Stirrup Ø10"]
    outer_hook_ratio = _derive_diagonal_ratio(stirrup_10_entities, outer_width, fallback=0.153)

    return Aci10Calibration(
        outer_width=outer_width,
        outer_height=outer_height,
        horizontal_span_ratio=horizontal_span_ratio,
        horizontal_offset_y_ratio=horizontal_offset_y_ratio,
        vertical_span_ratio=vertical_span_ratio,
        vertical_offset_x_ratio=vertical_offset_x_ratio,
        horizontal_stub_ratio=horizontal_stub_ratio,
        vertical_stub_ratio=vertical_stub_ratio,
        crosstie_arc_radius_ratio=crosstie_arc_radius_ratio,
        outer_hook_ratio=outer_hook_ratio,
    )


def _default_analysis_path() -> Path:
    return Path(__file__).resolve().parents[3] / "build" / "member-58.analysis.json"


def _safe_ratio(value: float, base: float, fallback: float) -> float:
    if abs(base) < 1e-9:
        return fallback
    return value / base


def _derive_stub_ratio(
    entities: list[dict[str, object]],
    outer_size: float,
    *,
    prefer: str,
    fallback: float,
) -> float:
    candidates: list[float] = []
    for entity in entities:
        bounds = entity.get("bounds") or {}
        width = float(bounds.get("ancho", 0.0) or 0.0)
        height = float(bounds.get("alto", 0.0) or 0.0)
        if prefer == "horizontal" and 0.02 <= width <= 0.05 and height <= 0.01:
            candidates.append(width)
        if prefer == "vertical" and 0.02 <= height <= 0.05 and width <= 0.01:
            candidates.append(height)
    if not candidates or abs(outer_size) < 1e-9:
        return fallback
    return max(candidates) / outer_size


def _derive_arc_ratio(entities: list[dict[str, object]], outer_size: float, *, fallback: float) -> float:
    candidates: list[float] = []
    for entity in entities:
        if entity.get("tipo") != "ARC":
            continue
        bounds = entity.get("bounds") or {}
        width = float(bounds.get("ancho", 0.0) or 0.0)
        height = float(bounds.get("alto", 0.0) or 0.0)
        if 0.015 <= width <= 0.03 and abs(width - height) < 0.005:
            candidates.append(width / 2.0)
    if not candidates or abs(outer_size) < 1e-9:
        return fallback
    return max(candidates) / outer_size


def _derive_diagonal_ratio(entities: list[dict[str, object]], outer_size: float, *, fallback: float) -> float:
    candidates: list[float] = []
    for entity in entities:
        if entity.get("tipo") != "POLYLINE":
            continue
        bounds = entity.get("bounds") or {}
        width = float(bounds.get("ancho", 0.0) or 0.0)
        height = float(bounds.get("alto", 0.0) or 0.0)
        if 0.02 <= width <= 0.06 and abs(width - height) < 0.01:
            candidates.append(max(width, height))
    if not candidates or abs(outer_size) < 1e-9:
        return fallback
    return max(candidates) / outer_size

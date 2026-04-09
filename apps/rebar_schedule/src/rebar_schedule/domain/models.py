from __future__ import annotations

from dataclasses import asdict, dataclass, field


def _tipo_fuente_es(value: str) -> str:
    return {
        "member": "Barra",
        "surface": "Superficie",
    }.get(value, value)


def _forma_es(value: str) -> str:
    return {
        "STRAIGHT": "Barra recta",
        "LONGITUDINAL": "Armadura longitudinal",
        "STIRRUP_CLOSED": "Cerco cerrado",
        "ACI-01": "Barra recta",
        "ACI-02": "Barra con una patilla a 90 grados",
        "ACI-03": "Barra con una patilla a 135 grados",
        "ACI-04": "Barra con dos patillas a 90 grados",
        "ACI-05": "Barra con dos patillas a 135 grados",
        "ACI-10": "Estribo cerrado de 2 ramas con gancho de 135 grados",
        "ACI-11": "Estribo cerrado de 2 ramas con gancho de 90 grados",
        "ACI-12": "Estribo abierto de 2 ramas",
        "ACI-20": "Cruceta interior con gancho de 135 grados",
    }.get(value, value)


def _disposicion_longitudinal_es(value: str | None) -> str | None:
    if value is None:
        return None
    return {
        "uniformemente_alrededor": "Conjunto uniforme alrededor",
        "linea": "Conjunto en linea",
        "esquina": "Barras de esquina",
        "simetrica": "Conjunto simetrico",
        "superior_inferior": "Conjunto superior e inferior",
        "lateral": "Conjunto lateral",
        "individual": "Barra individual",
    }.get(value, value)


@dataclass(slots=True)
class ReinforcementItem:
    source_type: str
    source_id: int | str
    host_label: str
    bar_mark: str
    diameter_mm: float
    steel_grade: str
    shape_code: str
    count: int
    cut_length_mm: float
    segments_mm: list[float] = field(default_factory=list)
    unit_weight_override_kg_m: float | None = None
    total_weight_override_kg: float | None = None
    material_no: int | None = None
    longitudinal_layout_code: str | None = None
    longitudinal_layout_label: str | None = None
    bending_diameter_mm: float | None = None
    hook_detail: str | None = None
    stirrup_type: str | None = None
    direction: str | None = None
    spacing_mm: float | None = None
    section_width_mm: float | None = None
    section_height_mm: float | None = None
    section_shape_code: str | None = None
    concrete_cover_mm: float | None = None
    crossties_active: bool | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ReinforcementItem":
        segments_raw = payload.get("segments_mm") or []
        return cls(
            source_type=str(payload.get("source_type", "")).strip(),
            source_id=payload.get("source_id", ""),
            host_label=str(payload.get("host_label", "")).strip(),
            bar_mark=str(payload.get("bar_mark", "")).strip(),
            diameter_mm=float(payload.get("diameter_mm", 0.0)),
            steel_grade=str(payload.get("steel_grade", "")).strip() or "UNSPECIFIED",
            material_no=int(payload["material_no"]) if payload.get("material_no") is not None else None,
            longitudinal_layout_code=(
                str(payload["longitudinal_layout_code"]).strip() if payload.get("longitudinal_layout_code") else None
            ),
            longitudinal_layout_label=(
                str(payload["longitudinal_layout_label"]).strip() if payload.get("longitudinal_layout_label") else None
            ),
            shape_code=str(payload.get("shape_code", "")).strip() or "STRAIGHT",
            count=int(payload.get("count", 0)),
            cut_length_mm=float(payload.get("cut_length_mm", 0.0)),
            segments_mm=[float(value) for value in segments_raw],
            unit_weight_override_kg_m=(
                float(payload["unit_weight_override_kg_m"])
                if payload.get("unit_weight_override_kg_m") is not None
                else None
            ),
            total_weight_override_kg=(
                float(payload["total_weight_override_kg"])
                if payload.get("total_weight_override_kg") is not None
                else None
            ),
            bending_diameter_mm=(
                float(payload["bending_diameter_mm"])
                if payload.get("bending_diameter_mm") is not None
                else None
            ),
            hook_detail=str(payload["hook_detail"]).strip() if payload.get("hook_detail") else None,
            stirrup_type=str(payload["stirrup_type"]).strip() if payload.get("stirrup_type") else None,
            direction=str(payload["direction"]).strip() if payload.get("direction") else None,
            spacing_mm=float(payload["spacing_mm"]) if payload.get("spacing_mm") is not None else None,
            section_width_mm=float(payload["section_width_mm"]) if payload.get("section_width_mm") is not None else None,
            section_height_mm=float(payload["section_height_mm"]) if payload.get("section_height_mm") is not None else None,
            section_shape_code=str(payload["section_shape_code"]).strip() if payload.get("section_shape_code") else None,
            concrete_cover_mm=float(payload["concrete_cover_mm"]) if payload.get("concrete_cover_mm") is not None else None,
            crossties_active=bool(payload["crossties_active"]) if payload.get("crossties_active") is not None else None,
            notes=str(payload["notes"]).strip() if payload.get("notes") else None,
        )

    def validate(self) -> None:
        if self.source_type not in {"member", "surface"}:
            raise ValueError(f"source_type invalido para {self.bar_mark or 'item'}: {self.source_type}")
        if not self.bar_mark:
            raise ValueError("Cada item debe tener bar_mark.")
        if self.count <= 0:
            raise ValueError(f"count debe ser mayor que cero en {self.bar_mark}.")
        if self.diameter_mm <= 0:
            raise ValueError(f"diameter_mm debe ser mayor que cero en {self.bar_mark}.")
        if self.cut_length_mm <= 0:
            raise ValueError(f"cut_length_mm debe ser mayor que cero en {self.bar_mark}.")

    def unit_weight_kg_per_m(self) -> float:
        if self.unit_weight_override_kg_m is not None and self.unit_weight_override_kg_m > 0:
            return self.unit_weight_override_kg_m
        return (self.diameter_mm ** 2) / 162.0

    def total_length_m(self) -> float:
        return self.count * self.cut_length_mm / 1000.0

    def total_weight_kg(self) -> float:
        if self.total_weight_override_kg is not None and self.total_weight_override_kg > 0:
            return self.total_weight_override_kg
        return self.total_length_m() * self.unit_weight_kg_per_m()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class RebarScheduleRow:
    source_type: str
    source_id: int | str
    host_label: str
    bar_mark: str
    shape_code: str
    diameter_mm: float
    steel_grade: str
    material_no: int | None
    workshop_shape_code: str | None
    workshop_shape_name: str | None
    workshop_shape_family: str | None
    count: int
    cut_length_mm: float
    total_length_m: float
    unit_weight_kg_m: float
    total_weight_kg: float
    segments_mm: list[float]
    bending_diameter_mm: float | None = None
    hook_detail: str | None = None
    stirrup_type: str | None = None
    direction: str | None = None
    spacing_mm: float | None = None
    section_width_mm: float | None = None
    section_height_mm: float | None = None
    section_shape_code: str | None = None
    concrete_cover_mm: float | None = None
    crossties_active: bool | None = None
    longitudinal_layout_code: str | None = None
    longitudinal_layout_label: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_spanish_dict(self) -> dict[str, object]:
        return {
            "tipo_fuente": _tipo_fuente_es(self.source_type),
            "id_fuente": self.source_id,
            "elemento": self.host_label,
            "marca": self.bar_mark,
            "forma": _forma_es(self.shape_code),
            "diametro_mm": round(self.diameter_mm, 3),
            "acero": self.steel_grade,
            "material_no": self.material_no,
            "disposicion_longitudinal_codigo": self.longitudinal_layout_code,
            "disposicion_longitudinal": _disposicion_longitudinal_es(self.longitudinal_layout_code)
            or self.longitudinal_layout_label,
            "forma_taller_codigo": self.workshop_shape_code,
            "forma_taller": self.workshop_shape_name,
            "familia_forma_taller": self.workshop_shape_family,
            "cantidad": self.count,
            "longitud_corte_mm": round(self.cut_length_mm, 3),
            "longitud_total_m": round(self.total_length_m, 3),
            "peso_unitario_kg_m": round(self.unit_weight_kg_m, 3),
            "peso_total_kg": round(self.total_weight_kg, 3),
            "segmentos_mm": [round(value, 3) for value in self.segments_mm],
            "diametro_doblado_mm": round(self.bending_diameter_mm, 3) if self.bending_diameter_mm is not None else None,
            "detalle_gancho": self.hook_detail,
            "tipo_estribo": self.stirrup_type,
            "direccion": self.direction,
            "separacion_mm": round(self.spacing_mm, 3) if self.spacing_mm is not None else None,
            "ancho_seccion_mm": round(self.section_width_mm, 3) if self.section_width_mm is not None else None,
            "alto_seccion_mm": round(self.section_height_mm, 3) if self.section_height_mm is not None else None,
            "forma_seccion": self.section_shape_code,
            "recubrimiento_mm": round(self.concrete_cover_mm, 3) if self.concrete_cover_mm is not None else None,
            "con_crucetas": self.crossties_active,
            "observaciones": self.notes,
        }


@dataclass(slots=True)
class RebarSchedule:
    project_name: str
    rows: list[RebarScheduleRow]

    @property
    def total_weight_kg(self) -> float:
        return sum(row.total_weight_kg for row in self.rows)

    @property
    def total_bars(self) -> int:
        return sum(row.count for row in self.rows)

    def to_dict(self) -> dict[str, object]:
        return {
            "proyecto": self.project_name,
            "resumen": {
                "total_filas": len(self.rows),
                "total_barras": self.total_bars,
                "peso_total_kg": round(self.total_weight_kg, 3),
            },
            "filas": [row.to_spanish_dict() for row in self.rows],
        }

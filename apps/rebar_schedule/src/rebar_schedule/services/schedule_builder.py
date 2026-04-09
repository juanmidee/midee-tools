from __future__ import annotations

from rebar_schedule.domain.models import RebarSchedule, RebarScheduleRow, ReinforcementItem
from rebar_schedule.domain.shape_catalog import map_rfem_to_workshop_shape


def build_schedule(project_name: str, items: list[ReinforcementItem]) -> RebarSchedule:
    validated_items: list[ReinforcementItem] = []
    for item in items:
        item.validate()
        validated_items.append(item)

    rows: list[RebarScheduleRow] = []
    for item in sorted(
        validated_items,
        key=lambda current: (
            current.source_type,
            str(current.host_label),
            current.bar_mark,
        ),
    ):
        workshop_shape = map_rfem_to_workshop_shape(
            shape_code=item.shape_code,
            stirrup_type=item.stirrup_type,
            hook_detail=item.hook_detail,
            crossties_active=item.crossties_active,
        )
        rows.append(
            RebarScheduleRow(
                source_type=item.source_type,
                source_id=item.source_id,
                host_label=item.host_label,
                bar_mark=item.bar_mark,
                shape_code=item.shape_code,
                diameter_mm=item.diameter_mm,
                steel_grade=item.steel_grade,
                material_no=item.material_no,
                longitudinal_layout_code=item.longitudinal_layout_code,
                longitudinal_layout_label=item.longitudinal_layout_label,
                workshop_shape_code=workshop_shape.code,
                workshop_shape_name=workshop_shape.name_es,
                workshop_shape_family=workshop_shape.family,
                count=item.count,
                cut_length_mm=item.cut_length_mm,
                total_length_m=round(item.total_length_m(), 3),
                unit_weight_kg_m=round(item.unit_weight_kg_per_m(), 3),
                total_weight_kg=round(item.total_weight_kg(), 3),
                segments_mm=item.segments_mm,
                bending_diameter_mm=item.bending_diameter_mm,
                hook_detail=item.hook_detail,
                stirrup_type=item.stirrup_type,
                direction=item.direction,
                spacing_mm=item.spacing_mm,
                section_width_mm=item.section_width_mm,
                section_height_mm=item.section_height_mm,
                section_shape_code=item.section_shape_code,
                concrete_cover_mm=item.concrete_cover_mm,
                crossties_active=item.crossties_active,
                notes=item.notes,
            )
        )
    return RebarSchedule(project_name=project_name, rows=rows)

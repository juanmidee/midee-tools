from __future__ import annotations

from collections import defaultdict

from rebar_schedule.domain.models import ReinforcementItem


def build_quantity_audit(project_name: str, items: list[ReinforcementItem]) -> dict[str, object]:
    valid_items: list[ReinforcementItem] = []
    for item in items:
        item.validate()
        valid_items.append(item)

    rows: list[dict[str, object]] = []
    totals_by_material: dict[str, dict[str, float]] = defaultdict(lambda: {"longitud_m": 0.0, "peso_kg": 0.0})
    totals_by_diameter: dict[float, dict[str, float]] = defaultdict(lambda: {"longitud_m": 0.0, "peso_kg": 0.0})

    for item in sorted(valid_items, key=lambda current: (str(current.host_label), current.bar_mark)):
        total_length_m = round(item.total_length_m(), 3)
        unit_weight = round(item.unit_weight_kg_per_m(), 3)
        total_weight_kg = round(item.total_weight_kg(), 3)
        row = {
            "elemento": item.host_label,
            "marca": item.bar_mark,
            "tipo": "cortante" if item.shape_code == "STIRRUP_CLOSED" else "longitudinal",
            "disposicion_longitudinal": item.longitudinal_layout_label,
            "diametro_mm": round(item.diameter_mm, 3),
            "material": item.steel_grade,
            "material_no": item.material_no,
            "cantidad": item.count,
            "longitud_unidad_m": round(item.cut_length_mm / 1000.0, 3),
            "longitud_total_m": total_length_m,
            "peso_unitario_kg_m": unit_weight,
            "peso_total_kg": total_weight_kg,
            "separacion_mm": round(item.spacing_mm, 3) if item.spacing_mm is not None else None,
            "ancho_seccion_mm": round(item.section_width_mm, 3) if item.section_width_mm is not None else None,
            "alto_seccion_mm": round(item.section_height_mm, 3) if item.section_height_mm is not None else None,
            "con_crucetas": item.crossties_active,
            "tipo_estribo": item.stirrup_type,
            "detalle_gancho": item.hook_detail,
            "observaciones": item.notes,
        }
        rows.append(row)
        totals_by_material[item.steel_grade]["longitud_m"] += total_length_m
        totals_by_material[item.steel_grade]["peso_kg"] += total_weight_kg
        totals_by_diameter[item.diameter_mm]["longitud_m"] += total_length_m
        totals_by_diameter[item.diameter_mm]["peso_kg"] += total_weight_kg

    return {
        "proyecto": project_name,
        "criterio_diametros": {
            "longitudinal": [
                "bar_diameter_uniformly_surrounding",
                "bar_size_designation_uniformly_surrounding",
                "bar_diameter_corner",
            ],
            "cortante": ["stirrup_diameter", "stirrup_bar_size"],
            "unidad_original_rfem": "m",
            "unidad_exportada": "mm",
        },
        "criterio_longitudes": {
            "longitudinal": ["one_rebar_length"],
            "cortante": ["one_stirrup_length"],
            "unidad_original_rfem": "m",
            "unidad_exportada": "m",
        },
        "criterio_cantidades": {
            "longitudinal": [
                "bar_count_uniformly_surrounding",
                "bar_count_corner",
                "bar_count_line",
                "bar_count_symmetrical",
                "bar_count_unsymmetrical_top_side",
                "bar_count_unsymmetrical_bottom_side",
                "bar_count_unsymmetrical_at_side",
            ],
            "cortante": ["stirrup_count"],
        },
        "criterio_pesos": {
            "metodo": "teorico_por_diametro",
            "formula": "kg/m = d_mm^2 / 162",
            "origen": "calculo interno de la app, no densidad leida desde RFEM",
        },
        "resumen": {
            "total_items": len(rows),
            "longitud_total_m": round(sum(row["longitud_total_m"] for row in rows), 3),
            "peso_total_kg": round(sum(row["peso_total_kg"] for row in rows), 3),
        },
        "totales_por_material": [
            {
                "material": material,
                "longitud_total_m": round(values["longitud_m"], 3),
                "peso_total_kg": round(values["peso_kg"], 3),
            }
            for material, values in sorted(totals_by_material.items(), key=lambda item: item[0])
        ],
        "totales_por_diametro": [
            {
                "diametro_mm": round(diameter, 3),
                "longitud_total_m": round(values["longitud_m"], 3),
                "peso_total_kg": round(values["peso_kg"], 3),
            }
            for diameter, values in sorted(totals_by_diameter.items(), key=lambda item: item[0])
        ],
        "items": rows,
    }

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from rebar_schedule.domain.models import ReinforcementItem

try:
    from dlubal.api import rfem
except ModuleNotFoundError:
    rfem = None


@dataclass(slots=True)
class RfemRebarAdapter:
    api_key_name: str = "default"
    api_key_value: str | None = None
    port: int = 9000

    def available(self) -> bool:
        return rfem is not None

    def probe_active_model(self, model_path: str | None = None) -> dict[str, Any]:
        if rfem is None:
            raise RuntimeError(
                "La libreria 'dlubal.api' no esta instalada. Instalala con: pip install -e .[rfem]"
            )

        with rfem.Application(**self._application_kwargs()) as app:
            resolved_model = self._resolve_model_context(app, model_path)
            result = {
                "estado": "rfem_probe_ok",
                "modelo": resolved_model,
                "aplicacion": self._to_jsonable(self._safe_get_application_info(app)),
                "conteos_objetos": self._collect_basic_object_counts(app),
                "conteos_armado": self._collect_reinforcement_object_counts(app),
                "escaneo_tablas_armado": self._scan_reinforcement_result_tables(app),
                "simbolos_api_candidatos": self._collect_api_candidates(),
            }
        return result

    def load_snapshot_file(self, snapshot_path: str) -> dict[str, Any]:
        payload = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("El snapshot RFEM debe ser un objeto JSON.")
        return payload

    def build_items_from_snapshot(self, payload: dict[str, Any]) -> tuple[str, list[ReinforcementItem]]:
        project_name = str(payload.get("project_name", "RFEM 6 Reinforcement")).strip()
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise ValueError("El snapshot debe incluir una lista 'items'.")

        items = [ReinforcementItem.from_dict(item) for item in raw_items if isinstance(item, dict)]
        if not items:
            raise ValueError("El snapshot no contiene items de armadura.")
        return project_name, items

    def read_reinforcement_from_rfem(
        self,
        model_path: str | None = None,
    ) -> tuple[str, list[ReinforcementItem]]:
        if rfem is None:
            raise RuntimeError(
                "La libreria 'dlubal.api' no esta instalada. Instalala con: pip install -e .[rfem]"
            )

        with rfem.Application(**self._application_kwargs()) as app:
            resolved_model = self._resolve_model_context(app, model_path)
            project_name = resolved_model["name"]
            items = self._extract_member_reinforcement_items(app)
            items.extend(self._extract_member_set_reinforcement_items(app))

        if not items:
            raise RuntimeError(
                "No se encontraron armaduras embebidas en los members del modelo activo de RFEM. "
                "Verifica que el dimensionamiento de hormigon este corrido y que la armadura de barra este disponible."
            )

        return project_name, items

    def _application_kwargs(self) -> dict[str, object]:
        if self.api_key_value:
            return {"api_key_value": self.api_key_value, "port": self.port}
        return {"api_key_name": self.api_key_name, "port": self.port}

    def _resolve_model_context(self, app: Any, model_path: str | None) -> dict[str, str]:
        active_model = self._read_active_model_context(app)
        if active_model is not None:
            return active_model

        normalized_path = (model_path or "").strip()
        if not normalized_path:
            raise RuntimeError(
                "RFEM no tiene un modelo activo. Deja un modelo abierto o indica --modelo-rfem."
            )

        app.open_model(path=normalized_path)
        opened_model = self._read_active_model_context(app)
        if opened_model is not None:
            return opened_model

        return {
            "path": normalized_path,
            "name": re.split(r"[\\/]", normalized_path)[-1],
            "source": "abierto_desde_archivo",
        }

    def _read_active_model_context(self, app: Any) -> dict[str, str] | None:
        try:
            active_model = app.get_active_model()
        except Exception:
            active_model = None

        active_model_data = self._to_jsonable(active_model)
        if not self._has_active_model_id(active_model_data):
            return None

        try:
            parameters = app.get_model_main_parameters()
        except Exception:
            return {"path": "", "name": "Modelo activo de RFEM", "source": "modelo_activo"}

        parameters_data = self._to_jsonable(parameters)
        file_path = (
            parameters_data.get("file_path")
            or parameters_data.get("file_name")
            or parameters_data.get("filepath")
            or ""
        )
        name = (
            parameters_data.get("name")
            or parameters_data.get("model_name")
            or (re.split(r"[\\/]", file_path)[-1] if file_path else "Modelo activo de RFEM")
        )
        return {"path": file_path, "name": name, "source": "modelo_activo"}

    @staticmethod
    def _has_active_model_id(model_data: Any) -> bool:
        if model_data is None:
            return False
        if isinstance(model_data, dict):
            for key in ("guid", "id", "name", "file_path", "file_name", "no"):
                value = model_data.get(key)
                if isinstance(value, str) and value.strip():
                    return True
                if isinstance(value, (int, float)) and value != 0:
                    return True
            return False
        if isinstance(model_data, str):
            return bool(model_data.strip())
        return True

    def _collect_basic_object_counts(self, app: Any) -> dict[str, object]:
        candidates = [
            ("members", "OBJECT_TYPE_MEMBER"),
            ("surfaces", "OBJECT_TYPE_SURFACE"),
            ("materials", "OBJECT_TYPE_MATERIAL"),
            ("lines", "OBJECT_TYPE_LINE"),
            ("nodes", "OBJECT_TYPE_NODE"),
            ("cross_sections", "OBJECT_TYPE_CROSS_SECTION"),
            ("thicknesses", "OBJECT_TYPE_THICKNESS"),
            ("load_cases", "OBJECT_TYPE_LOAD_CASE"),
        ]
        counts: dict[str, object] = {}
        for label, object_type_name in candidates:
            object_type = getattr(rfem, object_type_name, None)
            if object_type is None:
                counts[label] = {"available": False}
                continue
            try:
                object_ids = app.get_object_id_list(object_type=object_type)
                raw_items = list(getattr(object_ids, "object_id", [])) or list(getattr(object_ids, "rows", []))
                sample_numbers = [
                    getattr(item, "no", None)
                    for item in raw_items[:10]
                    if isinstance(getattr(item, "no", None), int)
                ]
                counts[label] = {
                    "available": True,
                    "count": len(raw_items),
                    "sample_numbers": sample_numbers,
                }
            except Exception as error:
                counts[label] = {"available": True, "error": str(error)}
        return counts

    def _extract_member_reinforcement_items(self, app: Any) -> list[ReinforcementItem]:
        member_numbers = self._object_numbers(app, getattr(rfem, "OBJECT_TYPE_MEMBER", None))
        if not member_numbers:
            return []

        items: list[ReinforcementItem] = []
        material_cache: dict[int, str] = {}
        for member_no in member_numbers:
            member = app.get_object(rfem.structure_core.Member(no=member_no))
            member_name = self._element_label(member, fallback=f"Member {member_no}")
            section_width_mm, section_height_mm, section_shape_code = self._member_section_dimensions_mm(app, member)
            concrete_cover_mm = self._first_numeric_attr(
                member,
                ["concrete_cover", "concrete_cover_top", "concrete_cover_bottom"],
                default=0.0,
            )
            concrete_cover_mm = concrete_cover_mm * 1000.0 if concrete_cover_mm > 0 else None

            longitudinal_table = getattr(member, "concrete_longitudinal_reinforcement_items", None)
            if longitudinal_table is not None:
                for row_index, row in enumerate(getattr(longitudinal_table, "rows", []), start=1):
                    item = self._build_longitudinal_item(
                        app=app,
                        member_no=member_no,
                        member_name=member_name,
                        row=row,
                        row_index=row_index,
                        material_cache=material_cache,
                        section_width_mm=section_width_mm,
                        section_height_mm=section_height_mm,
                        section_shape_code=section_shape_code,
                        concrete_cover_mm=concrete_cover_mm,
                    )
                    if item is not None:
                        items.append(item)

            shear_table = getattr(member, "concrete_shear_reinforcement_spans", None)
            if shear_table is not None:
                for row_index, row in enumerate(getattr(shear_table, "rows", []), start=1):
                    item = self._build_shear_item(
                        app=app,
                        member_no=member_no,
                        member_name=member_name,
                        row=row,
                        row_index=row_index,
                        material_cache=material_cache,
                        section_width_mm=section_width_mm,
                        section_height_mm=section_height_mm,
                        section_shape_code=section_shape_code,
                        concrete_cover_mm=concrete_cover_mm,
                    )
                    if item is not None:
                        items.append(item)
        return items

    def _extract_member_set_reinforcement_items(self, app: Any) -> list[ReinforcementItem]:
        member_set_numbers = self._object_numbers(app, getattr(rfem, "OBJECT_TYPE_MEMBER_SET", None))
        if not member_set_numbers:
            return []

        items: list[ReinforcementItem] = []
        material_cache: dict[int, str] = {}
        for member_set_no in member_set_numbers:
            member_set = app.get_object(rfem.structure_core.MemberSet(no=member_set_no))
            member_set_name = self._element_label(member_set, fallback=f"MemberSet {member_set_no}")
            representative_member = self._member_set_representative_member_no(member_set)
            section_width_mm, section_height_mm, section_shape_code = self._member_set_section_dimensions_mm(app, member_set)
            concrete_cover_mm = self._first_numeric_attr(
                member_set,
                ["concrete_cover", "concrete_cover_top", "concrete_cover_bottom"],
                default=0.0,
            )
            concrete_cover_mm = concrete_cover_mm * 1000.0 if concrete_cover_mm > 0 else None

            longitudinal_table = getattr(member_set, "concrete_longitudinal_reinforcement_items", None)
            if longitudinal_table is not None:
                for row_index, row in enumerate(getattr(longitudinal_table, "rows", []), start=1):
                    item = self._build_longitudinal_item(
                        app=app,
                        member_no=member_set_no,
                        member_name=member_set_name,
                        row=row,
                        row_index=row_index,
                        material_cache=material_cache,
                        section_width_mm=section_width_mm,
                        section_height_mm=section_height_mm,
                        section_shape_code=section_shape_code,
                        concrete_cover_mm=concrete_cover_mm,
                    )
                    if item is not None:
                        item.bar_mark = f"MS{member_set_no}-L{row_index}"
                        item.notes = (
                            f"{item.notes} | RFEM member set | members={','.join(str(no) for no in getattr(member_set, 'members', []))}"
                        )
                        if representative_member is not None:
                            item.notes = f"{item.notes} | representative_member={representative_member}"
                        items.append(item)

            raw_shear_items: list[ReinforcementItem] = []
            shear_table = getattr(member_set, "concrete_shear_reinforcement_spans", None)
            if shear_table is not None:
                for row_index, row in enumerate(getattr(shear_table, "rows", []), start=1):
                    item = self._build_shear_item(
                        app=app,
                        member_no=member_set_no,
                        member_name=member_set_name,
                        row=row,
                        row_index=row_index,
                        material_cache=material_cache,
                        section_width_mm=section_width_mm,
                        section_height_mm=section_height_mm,
                        section_shape_code=section_shape_code,
                        concrete_cover_mm=concrete_cover_mm,
                    )
                    if item is not None:
                        item.bar_mark = f"MS{member_set_no}-S{row_index}"
                        item.notes = (
                            f"{item.notes} | RFEM member set | members={','.join(str(no) for no in getattr(member_set, 'members', []))}"
                        )
                        if representative_member is not None:
                            item.notes = f"{item.notes} | representative_member={representative_member}"
                        raw_shear_items.append(item)
            items.extend(self._merge_member_set_shear_items(raw_shear_items, member_set_no))
        return items

    def _build_longitudinal_item(
        self,
        app: Any,
        member_no: int,
        member_name: str,
        row: Any,
        row_index: int,
        material_cache: dict[int, str],
        section_width_mm: float | None,
        section_height_mm: float | None,
        section_shape_code: str | None,
        concrete_cover_mm: float | None,
    ) -> ReinforcementItem | None:
        count, diameter_m, layout_code, layout_label = self._resolve_longitudinal_quantity_and_diameter(row)
        one_rebar_length_m = self._first_numeric_attr(row, ["one_rebar_length"], default=0.0)
        total_length_m = self._first_numeric_attr(row, ["length"], default=0.0)
        if count <= 0 or diameter_m <= 0 or one_rebar_length_m <= 0:
            return None

        anchorage_start = self._enum_label(getattr(row, "anchorage_start_anchor_type", None))
        anchorage_end = self._enum_label(getattr(row, "anchorage_end_anchor_type", None))
        material_no = int(getattr(row, "material", 0) or 0) or None
        span_start = self._first_numeric_attr(row, ["span_start_absolute"], default=0.0)
        span_end = self._first_numeric_attr(row, ["span_end_absolute"], default=0.0)
        row_name = str(getattr(row, "name", "") or f"L{row_index}")
        notes = (
            f"RFEM longitudinal | disposicion {layout_label} | span {span_start:.3f}-{span_end:.3f} m | "
            f"anchor {anchorage_start} / {anchorage_end}"
        )
        one_rebar_weight_kg = self._first_numeric_attr(row, ["one_rebar_weight"], default=0.0)
        total_weight_kg = self._first_numeric_attr(row, ["weight"], default=0.0)
        unit_weight_override = (
            one_rebar_weight_kg / one_rebar_length_m if one_rebar_weight_kg > 0 and one_rebar_length_m > 0 else None
        )

        return ReinforcementItem(
            source_type="member",
            source_id=member_no,
            host_label=member_name,
            bar_mark=f"M{member_no}-L{row_index}",
            diameter_mm=diameter_m * 1000.0,
            steel_grade=self._material_name(app, material_no, material_cache),
            material_no=material_no,
            longitudinal_layout_code=layout_code,
            longitudinal_layout_label=layout_label,
            shape_code="LONGITUDINAL",
            count=count,
            cut_length_mm=one_rebar_length_m * 1000.0,
            segments_mm=[one_rebar_length_m * 1000.0],
            unit_weight_override_kg_m=unit_weight_override,
            total_weight_override_kg=total_weight_kg or None,
            bending_diameter_mm=self._first_numeric_attr(row, ["anchorage_start_bending_diameter"], default=0.0) * 1000.0 or None,
            hook_detail=f"{anchorage_start} -> {anchorage_end}",
            section_width_mm=section_width_mm,
            section_height_mm=section_height_mm,
            section_shape_code=section_shape_code,
            concrete_cover_mm=concrete_cover_mm,
            notes=f"{row_name} | {notes} | total_length={total_length_m:.3f} m",
        )

    def _resolve_longitudinal_layout(self, row: Any) -> tuple[str, str]:
        candidates = [
            ("uniformemente_alrededor", "Conjunto uniforme alrededor", ["bar_count_uniformly_surrounding"]),
            ("linea", "Conjunto en linea", ["bar_count_line"]),
            ("esquina", "Barras de esquina", ["bar_count_corner"]),
            ("simetrica", "Conjunto simetrico", ["bar_count_symmetrical"]),
            (
                "superior_inferior",
                "Conjunto superior e inferior",
                ["bar_count_unsymmetrical_top_side", "bar_count_unsymmetrical_bottom_side"],
            ),
            ("lateral", "Conjunto lateral", ["bar_count_unsymmetrical_at_side"]),
            ("individual", "Barra individual", ["bar_diameter_single"]),
        ]
        for code, label, field_names in candidates:
            values = [self._first_numeric_attr(row, [field_name], default=0.0) for field_name in field_names]
            if any(value > 0 for value in values):
                return code, label
        return "individual", "Barra individual"

    def _resolve_longitudinal_quantity_and_diameter(self, row: Any) -> tuple[int, float, str, str]:
        candidates = [
            (
                "uniformemente_alrededor",
                "Conjunto uniforme alrededor",
                ["bar_count_uniformly_surrounding"],
                ["bar_diameter_uniformly_surrounding", "bar_size_designation_uniformly_surrounding"],
            ),
            (
                "linea",
                "Conjunto en linea",
                ["bar_count_line"],
                ["bar_diameter_line", "bar_size_designation_line"],
            ),
            (
                "esquina",
                "Barras de esquina",
                ["bar_count_corner"],
                ["bar_diameter_corner", "bar_size_designation_corner"],
            ),
            (
                "simetrica",
                "Conjunto simetrico",
                ["bar_count_symmetrical"],
                ["bar_diameter_symmetrical", "bar_size_designation_symmetrical"],
            ),
            (
                "superior_inferior",
                "Conjunto superior e inferior",
                ["bar_count_unsymmetrical_top_side", "bar_count_unsymmetrical_bottom_side"],
                ["bar_diameter_unsymmetrical_top_side", "bar_diameter_unsymmetrical_bottom_side"],
            ),
            (
                "lateral",
                "Conjunto lateral",
                ["bar_count_unsymmetrical_at_side"],
                ["bar_diameter_unsymmetrical_at_side"],
            ),
        ]
        for code, label, count_fields, diameter_fields in candidates:
            count = int(sum(self._first_numeric_attr(row, [field_name], default=0.0) for field_name in count_fields))
            if code == "simetrica" and count > 0:
                count *= 2
            diameter = self._first_numeric_attr(row, diameter_fields, default=0.0)
            if count > 0 and diameter > 0:
                return count, diameter, code, label

        diameter = self._first_numeric_attr(row, ["bar_diameter_single", "bar_size_designation_single"], default=0.0)
        if diameter > 0:
            return 1, diameter, "individual", "Barra individual"
        return 0, 0.0, "individual", "Barra individual"

    def _build_shear_item(
        self,
        app: Any,
        member_no: int,
        member_name: str,
        row: Any,
        row_index: int,
        material_cache: dict[int, str],
        section_width_mm: float | None,
        section_height_mm: float | None,
        section_shape_code: str | None,
        concrete_cover_mm: float | None,
    ) -> ReinforcementItem | None:
        count = int(self._first_numeric_attr(row, ["stirrup_count"], default=0))
        diameter_m = self._first_numeric_attr(row, ["stirrup_diameter", "stirrup_bar_size"], default=0.0)
        one_stirrup_length_m = self._first_numeric_attr(row, ["one_stirrup_length"], default=0.0)
        spacing_m = self._first_numeric_attr(row, ["stirrup_distances"], default=0.0)
        if count <= 0 or diameter_m <= 0 or one_stirrup_length_m <= 0:
            return None

        stirrup_type = self._enum_name(row, "stirrup_type")
        material_no = int(getattr(row, "material", 0) or 0) or None
        span_start = self._first_numeric_attr(row, ["span_start_absolute"], default=0.0)
        span_end = self._first_numeric_attr(row, ["span_end_absolute"], default=0.0)
        row_name = str(getattr(row, "name", "") or f"S{row_index}")
        crossties = bool(getattr(row, "crossties_active", False))
        notes = (
            f"RFEM shear | span {span_start:.3f}-{span_end:.3f} m | "
            f"crossties={'yes' if crossties else 'no'}"
        )
        one_stirrup_weight_kg = self._first_numeric_attr(row, ["one_stirrup_weight"], default=0.0)
        total_weight_kg = self._first_numeric_attr(row, ["all_stirrups_weight", "weight"], default=0.0)
        unit_weight_override = (
            one_stirrup_weight_kg / one_stirrup_length_m if one_stirrup_weight_kg > 0 and one_stirrup_length_m > 0 else None
        )

        return ReinforcementItem(
            source_type="member",
            source_id=member_no,
            host_label=member_name,
            bar_mark=f"M{member_no}-S{row_index}",
            diameter_mm=diameter_m * 1000.0,
            steel_grade=self._material_name(app, material_no, material_cache),
            material_no=material_no,
            shape_code="STIRRUP_CLOSED",
            count=count,
            cut_length_mm=one_stirrup_length_m * 1000.0,
            segments_mm=[one_stirrup_length_m * 1000.0],
            unit_weight_override_kg_m=unit_weight_override,
            total_weight_override_kg=total_weight_kg or None,
            bending_diameter_mm=None,
            hook_detail=stirrup_type,
            stirrup_type=stirrup_type,
            spacing_mm=spacing_m * 1000.0 if spacing_m > 0 else None,
            section_width_mm=section_width_mm,
            section_height_mm=section_height_mm,
            section_shape_code=section_shape_code,
            concrete_cover_mm=concrete_cover_mm,
            crossties_active=crossties,
            notes=f"{row_name} | {notes}",
        )

    @staticmethod
    def _member_set_representative_member_no(member_set: Any) -> int | None:
        members = list(getattr(member_set, "members", []) or [])
        for member_no in members:
            if isinstance(member_no, int) and member_no > 0:
                return member_no
        return None

    def _member_set_section_dimensions_mm(self, app: Any, member_set: Any) -> tuple[float | None, float | None, str | None]:
        representative_member_no = self._member_set_representative_member_no(member_set)
        if representative_member_no is None:
            return None, None, None
        try:
            member = app.get_object(rfem.structure_core.Member(no=representative_member_no))
        except Exception:
            return None, None, None
        return self._member_section_dimensions_mm(app, member)

    @staticmethod
    def _merge_member_set_shear_items(items: list[ReinforcementItem], member_set_no: int) -> list[ReinforcementItem]:
        merged: dict[tuple[object, ...], ReinforcementItem] = {}
        for item in items:
            key = (
                round(item.diameter_mm, 3),
                round(item.cut_length_mm, 3),
                item.stirrup_type or "",
                round(item.spacing_mm or 0.0, 3),
                bool(item.crossties_active),
                round(item.section_width_mm or 0.0, 3),
                round(item.section_height_mm or 0.0, 3),
            )
            existing = merged.get(key)
            if existing is None:
                merged[key] = item
                continue
            existing.count += item.count
            existing.cut_length_mm = item.cut_length_mm
            existing.segments_mm = item.segments_mm
            existing.notes = f"{existing.notes} + {item.bar_mark}"
            existing.bar_mark = existing.bar_mark.replace(f"MS{member_set_no}-S", f"MS{member_set_no}-SG")
        return list(merged.values())

    def _collect_api_candidates(self) -> dict[str, list[str]]:
        keywords = ("rein", "concrete", "surface", "member", "design", "result", "slab", "beam")
        result: dict[str, list[str]] = {}
        for module_name in dir(rfem):
            if module_name.startswith("_"):
                continue
            module = getattr(rfem, module_name, None)
            names = []
            for candidate in dir(module):
                if candidate.startswith("_"):
                    continue
                normalized = candidate.lower()
                if any(keyword in normalized for keyword in keywords):
                    names.append(candidate)
            if names:
                result[module_name] = sorted(names)[:80]
        return result

    @staticmethod
    def _object_numbers(app: Any, object_type: int | None) -> list[int]:
        if object_type is None:
            return []
        object_ids = app.get_object_id_list(object_type=object_type)
        raw_items = list(getattr(object_ids, "object_id", [])) or list(getattr(object_ids, "rows", []))
        return [getattr(item, "no", None) for item in raw_items if isinstance(getattr(item, "no", None), int)]

    @staticmethod
    def _first_numeric_attr(row: Any, names: list[str], default: float = 0.0) -> float:
        for name in names:
            value = getattr(row, name, None)
            if isinstance(value, (int, float)):
                return float(value)
        return default

    @staticmethod
    def _enum_label(value: Any) -> str:
        if value is None:
            return ""
        text = str(value)
        if "." in text:
            text = text.split(".")[-1]
        return text

    @staticmethod
    def _enum_name(row: Any, field_name: str) -> str:
        try:
            descriptor = row.DESCRIPTOR.fields_by_name[field_name]
            enum_type = descriptor.enum_type
            value = getattr(row, field_name, None)
            if enum_type is not None and isinstance(value, int):
                enum_value = enum_type.values_by_number.get(value)
                if enum_value is not None:
                    return enum_value.name
        except Exception:
            pass
        return RfemRebarAdapter._enum_label(getattr(row, field_name, None))

    def _material_name(self, app: Any, material_no: int | None, cache: dict[int, str]) -> str:
        if material_no is None:
            return "Material no definido"
        if material_no in cache:
            return cache[material_no]

        material_class = getattr(rfem.structure_core, "Material", None)
        if material_class is None:
            cache[material_no] = f"Material {material_no}"
            return cache[material_no]

        try:
            material = app.get_object(material_class(no=material_no))
            name = str(getattr(material, "name", "") or f"Material {material_no}").strip()
        except Exception:
            name = f"Material {material_no}"
        cache[material_no] = name
        return name

    @staticmethod
    def _element_label(obj: Any, fallback: str) -> str:
        for field_name in ("comment", "name", "description"):
            value = getattr(obj, field_name, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return fallback

    @staticmethod
    def _member_section_dimensions_mm(app: Any, member: Any) -> tuple[float | None, float | None, str | None]:
        cross_section_no = (
            getattr(member, "cross_section_start", None)
            or getattr(member, "cross_section_internal", None)
            or getattr(member, "cross_section_end", None)
        )
        if not isinstance(cross_section_no, int) or cross_section_no <= 0:
            return None, None, None

        try:
            cross_section = app.get_object(rfem.structure_core.CrossSection(no=cross_section_no))
        except Exception:
            return None, None, None

        b = getattr(cross_section, "b", None)
        h = getattr(cross_section, "h", None)
        d = getattr(cross_section, "d", None)
        width_mm = float(b) * 1000.0 if isinstance(b, (int, float)) and b > 0 else None
        height_mm = float(h) * 1000.0 if isinstance(h, (int, float)) and h > 0 else None
        section_name = str(getattr(cross_section, "name", "") or "").upper()
        is_circular = "CIRCLE" in section_name
        if not is_circular and isinstance(d, (int, float)) and d > 0 and width_mm and height_mm:
            diameter_mm = float(d) * 1000.0
            is_circular = abs(width_mm - diameter_mm) < 1e-6 and abs(height_mm - diameter_mm) < 1e-6
        return width_mm, height_mm, ("circular" if is_circular else "rectangular")

    def _collect_reinforcement_object_counts(self, app: Any) -> dict[str, object]:
        candidates = [
            ("surface_reinforcement", "OBJECT_TYPE_SURFACE_REINFORCEMENT"),
            ("reinforcement_direction", "OBJECT_TYPE_REINFORCEMENT_DIRECTION"),
            ("punching_reinforcement", "OBJECT_TYPE_PUNCHING_REINFORCEMENT"),
            ("design_strip", "OBJECT_TYPE_DESIGN_STRIP"),
            ("concrete_design_configuration", "OBJECT_TYPE_CONCRETE_DESIGN_CONFIGURATION"),
            ("concrete_design_uls_configuration", "OBJECT_TYPE_CONCRETE_DESIGN_ULS_CONFIGURATION"),
            ("concrete_design_sls_configuration", "OBJECT_TYPE_CONCRETE_DESIGN_SLS_CONFIGURATION"),
            ("design_situation", "OBJECT_TYPE_DESIGN_SITUATION"),
            ("result_combination", "OBJECT_TYPE_RESULT_COMBINATION"),
        ]
        counts: dict[str, object] = {}
        for label, object_type_name in candidates:
            object_type = getattr(rfem, object_type_name, None)
            if object_type is None:
                counts[label] = {"available": False}
                continue
            try:
                object_ids = app.get_object_id_list(object_type=object_type)
                raw_items = list(getattr(object_ids, "object_id", [])) or list(getattr(object_ids, "rows", []))
                counts[label] = {
                    "available": True,
                    "count": len(raw_items),
                    "sample_numbers": [
                        getattr(item, "no", None)
                        for item in raw_items[:10]
                        if isinstance(getattr(item, "no", None), int)
                    ],
                }
            except Exception as error:
                counts[label] = {"available": True, "error": str(error)}
        return counts

    def _scan_reinforcement_result_tables(self, app: Any) -> dict[str, object]:
        tables = {
            "surface_reinforcement_table": getattr(rfem.results, "CONCRETE_DESIGN_SURFACE_REINFORCEMENT_TABLE", None),
            "surface_required_by_surface": getattr(
                rfem.results, "CONCRETE_DESIGN_REQUIRED_REINFORCEMENT_AREA_ON_SURFACES_BY_SURFACE_TABLE", None
            ),
            "surface_provided_by_surface": getattr(
                rfem.results, "CONCRETE_DESIGN_PROVIDED_REINFORCEMENT_AREA_ON_SURFACES_BY_SURFACE_TABLE", None
            ),
            "member_reinforcement_table": getattr(rfem.results, "CONCRETE_DESIGN_MEMBER_REINFORCEMENT_TABLE", None),
            "member_required_by_member": getattr(
                rfem.results, "CONCRETE_DESIGN_REQUIRED_REINFORCEMENT_AREA_ON_MEMBERS_BY_MEMBER_TABLE", None
            ),
            "member_provided_by_member": getattr(
                rfem.results, "CONCRETE_DESIGN_PROVIDED_REINFORCEMENT_AREA_ON_MEMBERS_BY_MEMBER_TABLE", None
            ),
        }
        loading_sources = [
            ("load_case", "OBJECT_TYPE_LOAD_CASE"),
            ("design_situation", "OBJECT_TYPE_DESIGN_SITUATION"),
            ("result_combination", "OBJECT_TYPE_RESULT_COMBINATION"),
        ]
        scan: dict[str, object] = {}
        for loading_label, object_type_name in loading_sources:
            object_type = getattr(rfem, object_type_name, None)
            if object_type is None:
                scan[loading_label] = {"available": False}
                continue
            try:
                object_ids = app.get_object_id_list(object_type=object_type)
                raw_items = list(getattr(object_ids, "object_id", [])) or list(getattr(object_ids, "rows", []))
            except Exception as error:
                scan[loading_label] = {"available": True, "error": str(error)}
                continue

            entries: dict[str, object] = {}
            for item in raw_items[:10]:
                no = getattr(item, "no", None)
                if not isinstance(no, int):
                    continue
                object_id = rfem.ObjectId(no=no, object_type=object_type)
                loading_key = f"{loading_label}_{no}"
                entries[loading_key] = {}
                for table_label, table_id in tables.items():
                    if table_id is None:
                        entries[loading_key][table_label] = {"available": False}
                        continue
                    try:
                        table = app.get_result_table(table_id, object_id)
                        data = self._to_jsonable(table)
                        payload = data.get("data", {}) if isinstance(data, dict) else {}
                        rows = payload.get("rows", []) if isinstance(payload, dict) else []
                        entries[loading_key][table_label] = {
                            "rows": len(rows),
                            "keys": sorted(list(payload.keys()))[:20] if isinstance(payload, dict) else [],
                            "warning": data.get("warning", "") if isinstance(data, dict) else "",
                        }
                    except Exception as error:
                        entries[loading_key][table_label] = {"error": str(error)}
            scan[loading_label] = entries
        return scan

    @staticmethod
    def _safe_get_application_info(app: Any) -> Any:
        getter = getattr(app, "get_application_info", None)
        if getter is None:
            return {"detalle": "La API conecto, pero no expone get_application_info en esta version."}
        return getter()

    @classmethod
    def _to_jsonable(cls, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, dict):
            return {str(key): cls._to_jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls._to_jsonable(item) for item in value]
        if hasattr(value, "ListFields"):
            return {
                field.name: cls._to_jsonable(field_value)
                for field, field_value in value.ListFields()
            }
        if hasattr(value, "__dict__"):
            return {
                key: cls._to_jsonable(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        return str(value)

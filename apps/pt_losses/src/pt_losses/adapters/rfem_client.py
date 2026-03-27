from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any

try:
    from google.protobuf.json_format import MessageToDict
except ModuleNotFoundError:
    MessageToDict = None

from pt_losses.services.rfem_conversion import RfemLoadCasePayload

try:
    from dlubal.api import rfem
except ModuleNotFoundError:
    rfem = None


@dataclass(slots=True)
class Rfem6ApiAdapter:
    api_key_name: str = "default"
    api_key_value: str | None = None
    port: int = 9000

    def disponible(self) -> bool:
        return rfem is not None

    def probar_conexion(self) -> dict[str, object]:
        if rfem is None:
            raise RuntimeError(
                "La libreria 'dlubal.api' no esta instalada. Instalala con: pip install dlubal.api"
            )

        with rfem.Application(**self._application_kwargs()) as app:
            info = self._safe_get_application_info(app)

        return {
            "estado": "conexion_ok",
            "api_key_name": self.api_key_name,
            "puerto": self.port,
            "informacion_aplicacion": info,
        }

    def leer_modelo_postensado(
        self,
        model_path: str | None = None,
        max_member_scan: int = 5000,
        stop_after_missing: int = 250,
    ) -> dict[str, object]:
        if rfem is None:
            raise RuntimeError(
                "La libreria 'dlubal.api' no esta instalada. Instalala con: pip install dlubal.api"
            )

        with rfem.Application(**self._application_kwargs()) as app:
            resolved_model = self._resolve_model_context(app, model_path)
            all_members = self._get_all_members(app)
            tendon_members = self._filter_tendon_members(all_members)
            if not tendon_members:
                raise RuntimeError("No se encontraron miembros tipo tendon en el modelo RFEM abierto.")

            tendon_member_data = [self._to_jsonable(member) for member in tendon_members]
            member_numbers = sorted(
                int(data["no"])
                for data in tendon_member_data
                if isinstance(data.get("no"), (int, float))
            )
            section_numbers = [
                int(number)
                for number in (
                    data.get("cross_section_start") or data.get("cross_section_internal")
                    for data in tendon_member_data
                )
                if isinstance(number, (int, float))
            ]
            material_numbers = [
                int(number)
                for number in (data.get("cross_section_material") for data in tendon_member_data)
                if isinstance(number, (int, float))
            ]

            primary_cross_section_no = self._most_common_number(section_numbers)
            primary_material_no = self._most_common_number(material_numbers)
            if primary_cross_section_no is None or primary_material_no is None:
                raise RuntimeError(
                    "No fue posible identificar la seccion o el material principal de los tendones."
                )

            cross_section = app.get_object(rfem.structure_core.CrossSection(no=primary_cross_section_no))
            material = app.get_object(rfem.structure_core.Material(no=primary_material_no))
            cross_section_data = self._to_jsonable(cross_section)
            material_data = self._to_jsonable(material)
            concrete_material_no, concrete_material_obj, concrete_material_data = self._find_primary_concrete_material(
                all_members=all_members,
                app=app,
            )
            tendon_group_ids = self._collect_tendon_group_ids(tendon_member_data)
            candidate_surface_numbers = self._find_candidate_tendon_surface_numbers(app)

            average_length = sum(
                float(data.get("length", 0.0))
                for data in tendon_member_data
                if isinstance(data.get("length"), (int, float))
            ) / len(tendon_member_data)

            area_m2 = self._pick_numeric(cross_section_data, ["area_axial", "A"])
            area_mm2 = self._square_m_to_square_mm(area_m2)
            strand_count = self._pick_numeric(
                cross_section_data,
                ["nw", "number_of_wires", "number_of_strands", "n_wires", "n_strands"],
                default=None,
            ) or self._pick_numeric(
                material_data,
                ["nw", "number_of_wires", "number_of_strands", "n_wires", "n_strands"],
                default=None,
            )
            ep_mpa = self._extract_temperature_property_mpa(
                material,
                ["elasticity_modulus_global", "elasticity_modulus_x"],
            ) or self._extract_material_property_mpa(
                material,
                material_data,
                ["e_p", "elasticity_modulus_global", "elasticity_modulus_x", "elasticity_modulus_global_x", "E", "e"],
            )
            fpk_mpa = self._force_over_area_to_mpa(
                self._pick_numeric(cross_section_data, ["F_m"]),
                area_m2,
            ) or self._extract_material_property_mpa(
                material,
                material_data,
                ["r_m", "Rm", "fpk", "characteristic_strength"],
            )
            fp01k_mpa = self._force_over_area_to_mpa(
                self._pick_numeric(cross_section_data, ["F_p01", "F_p0_1"]),
                area_m2,
            ) or self._extract_material_property_mpa(
                material,
                material_data,
                ["f_p0_1k", "fp01k", "proof_strength"],
            )
            mu_fric = self._pick_numeric(cross_section_data, ["curvature_friction_factor", "mu"], default=None)
            k_wobble = self._pick_numeric(cross_section_data, ["wobble_friction_factor", "k_wf"], default=None)
            relaxation = self._pick_numeric(
                material_data,
                ["prestressing_steel_relaxation_loss_1000_en1992", "relaxation_loss_ratio"],
                default=None,
            )
            concrete_ec_mpa = self._extract_temperature_property_mpa(
                concrete_material_obj,
                ["elasticity_modulus_global", "elasticity_modulus_x"],
            ) or self._extract_material_property_mpa(
                concrete_material_obj,
                concrete_material_data,
                ["e_cm", "e", "elasticity_modulus_global", "elasticity_modulus_x", "E"],
            )
            concrete_fc_mpa = self._extract_material_property_mpa(
                concrete_material_obj,
                concrete_material_data,
                ["f_c", "f_ck", "fc", "compressive_strength"],
            )

        return {
            "estado": "modelo_leido",
            "modelo": resolved_model["path"],
            "modelo_nombre": resolved_model["name"],
            "origen_modelo": resolved_model["source"],
            "api_key_name": self.api_key_name,
            "puerto": self.port,
            "miembros_tendon": member_numbers,
            "cantidad_miembros_tendon": len(member_numbers),
            "cantidad_cordones": len(tendon_group_ids) if tendon_group_ids else len(member_numbers),
            "grupos_tendon": tendon_group_ids,
            "longitud_promedio_m": average_length,
            "tipo_modelado_tendon": "members",
            "superficies_tendon_candidatas": candidate_surface_numbers,
            "superficies_tendon_soportadas": False,
            "material_tendon": {
                "no": primary_material_no,
                "nombre": material_data.get("name"),
                "Ep_MPa": ep_mpa,
                "fpk_MPa": fpk_mpa,
                "fp01k_MPa": fp01k_mpa,
                "relajacion": relaxation,
            },
            "seccion_tendon": {
                "no": primary_cross_section_no,
                "nombre": cross_section_data.get("name"),
                "Ap_mm2": area_mm2,
                "cordones_por_seccion": int(strand_count) if isinstance(strand_count, (int, float)) else None,
                "mu_fric": mu_fric,
                "k_wobble": k_wobble,
            },
            "material_hormigon": {
                "no": concrete_material_no,
                "nombre": concrete_material_data.get("name") if isinstance(concrete_material_data, dict) else None,
                "Ec_MPa": concrete_ec_mpa,
                "fc_MPa": concrete_fc_mpa,
            },
            "resumen_lectura": {
                "Ep": ep_mpa,
                "Ec": concrete_ec_mpa,
                "fpk": fpk_mpa,
                "fp01k": fp01k_mpa,
                "fc": concrete_fc_mpa,
                "Ap": area_mm2,
                "n_tendons": len(tendon_group_ids) if tendon_group_ids else len(member_numbers),
                "tendon_length": average_length,
                "mu_fric": mu_fric,
                "k_wobble": k_wobble,
                "relaxation_loss_ratio": relaxation,
            },
            "observaciones": [
                "La aplicacion automatica actual solo trabaja sobre members/barra.",
                "Si el postensado esta modelado como superficie, debe revisarse o ampliarse el adaptador antes de aplicar cargas.",
            ],
        }

    def aplicar_deformaciones_axiales(
        self,
        model_path: str | None,
        tendon_member_nos: list[int],
        payloads: list[RfemLoadCasePayload],
        strain_unit: str = "percent",
        strain_scale: float = 1.0,
        action_start_no: int = 1,
        load_case_start_no: int = 1,
        member_load_start_no: int = 1,
        calculate: bool = True,
        save: bool = True,
    ) -> dict[str, object]:
        if rfem is None:
            raise RuntimeError(
                "La libreria 'dlubal.api' no esta instalada. Instalala con: pip install dlubal.api"
            )
        if not tendon_member_nos:
            raise ValueError("Debes indicar al menos un miembro de tendon para aplicar las cargas.")

        created_cases: list[dict[str, object]] = []

        with rfem.Application(**self._application_kwargs()) as app:
            resolved_model = self._resolve_model_context(app, model_path)

            load_case_class = getattr(rfem.loading, "LoadCase", None)
            member_load_class = getattr(rfem.loads, "MemberLoad", None)
            if load_case_class is None or member_load_class is None:
                raise RuntimeError("La API instalada no expone LoadCase o MemberLoad.")

            used_member_load_nos = self._used_object_numbers(app, rfem.OBJECT_TYPE_MEMBER_LOAD)
            next_load_case_candidate = load_case_start_no

            for index, payload in enumerate(payloads):
                load_case_no = self._next_free_load_case_no(app, next_load_case_candidate)
                next_load_case_candidate = load_case_no + 1
                member_load_no = self._next_free_number(used_member_load_nos, member_load_start_no + index)
                used_member_load_nos.add(member_load_no)
                deformacion = payload.deformacion_axial(strain_unit) * strain_scale

                load_case_object = self._build_load_case(load_case_no, payload.state_name)
                app.create_object(load_case_object)
                app.get_object(load_case_class(no=load_case_no))

                member_load_object = self._build_member_load(
                    no=member_load_no,
                    load_case_no=load_case_no,
                    members=tendon_member_nos,
                    magnitude=deformacion,
                )
                app.create_object(member_load_object)

                created_cases.append(
                    {
                        "caso_carga_no": load_case_no,
                        "carga_miembro_no": member_load_no,
                        "estado_temporal": payload.state_name,
                        "deformacion_axial": deformacion,
                        "unidad": strain_unit,
                        "factor_escala": strain_scale,
                        "miembros": tendon_member_nos,
                        "categoria_objetivo": "Tp",
                    }
                )

            if calculate:
                app.calculate_all(skip_warnings=True)
            if save:
                app.save_model()

            lectura_rfem = self._leer_objetos_creados(
                app,
                [item["caso_carga_no"] for item in created_cases],
                [item["carga_miembro_no"] for item in created_cases],
            )

        return {
            "estado": "aplicado",
            "modelo": resolved_model["path"],
            "modelo_nombre": resolved_model["name"],
            "origen_modelo": resolved_model["source"],
            "api_key_name": self.api_key_name,
            "puerto": self.port,
            "modo_creacion": "casos_tp_independientes",
            "casos": created_cases,
            "lectura_rfem": lectura_rfem,
        }

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
                "RFEM no tiene un modelo activo. Selecciona un archivo .rf6 y la aplicaci?n lo abrir? en RFEM autom?ticamente."
            )

        app.open_model(path=normalized_path)
        opened_model = self._read_active_model_context(app)
        if opened_model is not None:
            return opened_model

        return {
            "path": normalized_path,
            "name": re.split(r"[\/]", normalized_path)[-1],
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
            or (re.split(r"[\/]", file_path)[-1] if file_path else "Modelo activo de RFEM")
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

    def _build_load_case(self, no: int, state_name: str) -> Any:
        load_case_class = getattr(rfem.loading, "LoadCase", None)
        if load_case_class is None:
            raise RuntimeError("No se encontro rfem.loading.LoadCase en la API instalada.")
        return load_case_class(
            no=no,
            name=f"Postensado {state_name}",
            analysis_type=load_case_class.ANALYSIS_TYPE_STATIC_ANALYSIS,
            action_category=load_case_class.ACTION_CATEGORY_SELF_STRAINING_FORCE_PERMANENT_TP,
            self_weight_active=False,
        )

    def _used_object_numbers(self, app: Any, object_type: int) -> set[int]:
        object_ids = app.get_object_id_list(object_type=object_type)
        raw_items = list(getattr(object_ids, "object_id", [])) or list(getattr(object_ids, "rows", []))
        used_numbers: set[int] = set()
        for item in raw_items:
            no = self._extract_object_number(item)
            if no is not None:
                used_numbers.add(no)
        if not used_numbers and object_type == getattr(rfem, "OBJECT_TYPE_LOAD_CASE", None):
            used_numbers = self._probe_existing_load_case_numbers(app)
        return used_numbers

    @staticmethod
    def _next_free_number(used_numbers: set[int], requested_no: int) -> int:
        candidate = requested_no
        while candidate in used_numbers:
            candidate += 1
        return candidate

    def _next_free_load_case_no(self, app: Any, requested_no: int) -> int:
        load_case_class = getattr(getattr(rfem, "loading", None), "LoadCase", None)
        if load_case_class is None:
            raise RuntimeError("No se encontro rfem.loading.LoadCase en la API instalada.")

        candidate = max(1, int(requested_no))
        while True:
            try:
                obj = app.get_object(load_case_class(no=candidate))
            except Exception:
                return candidate
            if obj is None:
                return candidate
            candidate += 1

    def _next_free_object_no(self, app: Any, object_type: int, requested_no: int) -> int:
        return self._next_free_number(self._used_object_numbers(app, object_type), requested_no)

    def _probe_existing_load_case_numbers(self, app: Any) -> set[int]:
        load_case_class = getattr(getattr(rfem, "loading", None), "LoadCase", None)
        if load_case_class is None:
            return set()

        used_numbers: set[int] = set()
        consecutive_misses = 0
        candidate = 1
        max_candidate = 5000
        max_consecutive_misses = 250

        while candidate <= max_candidate and consecutive_misses < max_consecutive_misses:
            try:
                obj = app.get_object(load_case_class(no=candidate))
            except Exception:
                consecutive_misses += 1
            else:
                if obj is not None:
                    used_numbers.add(candidate)
                    consecutive_misses = 0
                else:
                    consecutive_misses += 1
            candidate += 1

        return used_numbers

    @classmethod
    def _extract_object_number(cls, item: Any) -> int | None:
        if isinstance(item, bool):
            return None
        if isinstance(item, int):
            return item
        if isinstance(item, float) and item.is_integer():
            return int(item)
        if isinstance(item, dict):
            for key in ("no", "object_no", "id", "object_id"):
                value = item.get(key)
                if isinstance(value, int):
                    return value
                if isinstance(value, float) and value.is_integer():
                    return int(value)
        no = getattr(item, "no", None)
        if isinstance(no, int):
            return no
        if isinstance(no, float) and no.is_integer():
            return int(no)
        item_id = getattr(item, "id", None)
        if isinstance(item_id, int):
            return item_id
        if isinstance(item_id, float) and item_id.is_integer():
            return int(item_id)
        payload = cls._to_jsonable(item)
        if isinstance(payload, dict):
            for key in ("no", "object_no", "id", "object_id"):
                value = payload.get(key)
                if isinstance(value, int):
                    return value
                if isinstance(value, float) and value.is_integer():
                    return int(value)
        return None

    def _build_member_load(
        self,
        no: int,
        load_case_no: int,
        members: list[int],
        magnitude: float,
    ) -> Any:
        member_load_class = getattr(rfem.loads, "MemberLoad", None)
        if member_load_class is None:
            raise RuntimeError("No se encontro rfem.loads.MemberLoad en la API instalada.")

        kwargs_common = {
            "no": no,
            "load_case": load_case_no,
            "members": members,
            "load_type": self._enum_value(member_load_class, ["LOAD_TYPE_AXIAL_STRAIN"]),
            "load_distribution": self._enum_value(member_load_class, ["LOAD_DISTRIBUTION_UNIFORM"]),
            "load_direction": self._enum_value(
                member_load_class,
                ["LOAD_DIRECTION_LOCAL_X", "LOAD_DIRECTION_X_LOCAL", "LOAD_DIRECTION_LOCAL_X_OR_U"],
            ),
        }

        attempts = [
            {**kwargs_common, "magnitude": magnitude},
            {**kwargs_common, "magnitude_1": magnitude},
            {**kwargs_common, "axial_strain": magnitude},
            {**kwargs_common, "strain": magnitude},
        ]

        last_error: Exception | None = None
        for attempt in attempts:
            try:
                return member_load_class(**attempt)
            except TypeError as error:
                last_error = error

        raise RuntimeError(
            "No fue posible construir la carga de deformacion axial con la firma disponible en dlubal.api. "
            f"Ultimo error: {last_error}"
        )

    def _leer_objetos_creados(
        self,
        app: Any,
        load_case_nos: list[int],
        member_load_nos: list[int],
    ) -> dict[str, object]:
        load_case_class = getattr(rfem.loading, "LoadCase", None)
        member_load_class = getattr(rfem.loads, "MemberLoad", None)
        if load_case_class is None or member_load_class is None:
            return {"detalle": "No fue posible leer los objetos creados desde la API instalada."}

        casos = []
        for no in load_case_nos:
            try:
                obj = app.get_object(load_case_class(no=no))
            except Exception as error:
                casos.append({"no": no, "error": str(error)})
                continue
            casos.append(self._extraer_campos_relevantes_load_case(obj))

        cargas = []
        for no, lc_no in zip(member_load_nos, load_case_nos):
            try:
                obj = app.get_object(member_load_class(no=no, load_case=lc_no))
            except Exception as error:
                cargas.append({"no": no, "load_case": lc_no, "error": str(error)})
                continue
            cargas.append(self._extraer_campos_relevantes_member_load(obj))

        return {
            "casos_carga": casos,
            "cargas_miembro": cargas,
        }

    def _find_primary_concrete_material(
        self,
        all_members: list[Any],
        app: Any,
    ) -> tuple[int | None, Any, dict[str, object]]:
        material_class = getattr(rfem.structure_core, "Material", None)
        if material_class is None:
            return None, None, {}

        material_counts: dict[int, int] = {}
        for member in all_members:
            payload = self._to_jsonable(member)
            if self._is_tendon_member_payload(payload):
                continue
            material_no = payload.get("cross_section_material")
            if isinstance(material_no, (int, float)):
                material_counts[int(material_no)] = material_counts.get(int(material_no), 0) + 1

        ordered_materials = [material_no for material_no, _count in sorted(material_counts.items(), key=lambda item: item[1], reverse=True)]

        if not ordered_materials:
            object_ids = app.get_object_id_list(object_type=rfem.OBJECT_TYPE_MATERIAL)
            raw_items = list(getattr(object_ids, "object_id", []))
            if not raw_items and hasattr(object_ids, "rows"):
                raw_items = list(getattr(object_ids, "rows", []))
            for item in raw_items:
                no = getattr(item, "no", None)
                if isinstance(no, int):
                    ordered_materials.append(no)

        for material_no in ordered_materials:
            try:
                material = app.get_object(material_class(no=material_no))
            except Exception:
                continue
            material_data = self._to_jsonable(material)
            concrete_strength = self._pick_numeric(
                material_data,
                ["f_c", "f_ck", "fc", "compressive_strength"],
                default=None,
            )
            if concrete_strength is not None:
                return material_no, material, material_data

        return None, None, {}

    def _get_all_members(self, app: Any) -> list[Any]:
        member_class = getattr(rfem.structure_core, "Member", None)
        if member_class is None:
            raise RuntimeError("No se encontro rfem.structure_core.Member en la API instalada.")

        object_ids = app.get_object_id_list(object_type=rfem.OBJECT_TYPE_MEMBER)
        member_numbers: list[int] = []
        raw_items = list(getattr(object_ids, "object_id", []))
        if not raw_items and hasattr(object_ids, "rows"):
            raw_items = list(getattr(object_ids, "rows", []))

        for item in raw_items:
            no = getattr(item, "no", None)
            if isinstance(no, int):
                member_numbers.append(no)

        if not member_numbers:
            return []

        members = app.get_object_list([member_class(no=no) for no in member_numbers])
        return list(members)

    def _filter_tendon_members(self, members: list[Any]) -> list[Any]:
        return [member for member in members if self._is_tendon_member_payload(self._to_jsonable(member))]

    @staticmethod
    def _normalize_text(value: object) -> str:
        text = str(value or "")
        normalized = unicodedata.normalize("NFKD", text)
        return "".join(char for char in normalized if not unicodedata.combining(char)).lower()

    @classmethod
    def _is_tendon_member_payload(cls, payload: dict[str, object]) -> bool:
        member_class = getattr(rfem.structure_core, "Member", None)
        tendon_constant = getattr(member_class, "TYPE_TENDON", None) if member_class is not None else None
        member_type = payload.get("type")
        if tendon_constant is not None and member_type == tendon_constant:
            return True

        normalized_type = cls._normalize_text(member_type)
        if any(token in normalized_type for token in ("tendon", "type_tendon", "member_type_tendon")):
            return True

        if payload.get("tendon_type") is not None:
            return True

        for key in ("name", "type_name", "type_description", "member_type", "member_type_name", "description"):
            normalized_value = cls._normalize_text(payload.get(key))
            if any(token in normalized_value for token in ("tendon", "postens", "cable", "cordon")):
                return True
        return False

    @classmethod
    def _extract_tendon_group_id(cls, payload: dict[str, object]) -> str | None:
        for key in ("tendon_no", "tendon", "tendon_id", "tendon_member_no"):
            value = payload.get(key)
            if isinstance(value, (int, float)):
                return str(int(value))
            if isinstance(value, str) and value.strip():
                return value.strip()

        name = str(payload.get("name") or "")
        normalized_name = cls._normalize_text(name)
        match = re.search(r"tendon\s*\|\s*(\d+)", normalized_name, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    @classmethod
    def _collect_tendon_group_ids(cls, payloads: list[dict[str, object]]) -> list[str]:
        group_ids: list[str] = []
        for payload in payloads:
            group_id = cls._extract_tendon_group_id(payload)
            if group_id and group_id not in group_ids:
                group_ids.append(group_id)
        return group_ids

    def _find_candidate_tendon_surface_numbers(self, app: Any) -> list[int]:
        object_types = getattr(rfem, "ObjectType", None)
        surface_class = getattr(rfem.structure_core, "Surface", None)
        if surface_class is None:
            return []

        surface_type = getattr(object_types, "OBJECT_TYPE_SURFACE", None) if object_types is not None else None
        if surface_type is None:
            surface_type = getattr(rfem, "OBJECT_TYPE_SURFACE", None)
        if surface_type is None:
            return []

        try:
            object_ids = app.get_object_id_list(object_type=surface_type)
        except Exception:
            return []

        raw_items = list(getattr(object_ids, "object_id", [])) or list(getattr(object_ids, "rows", []))
        surface_numbers: list[int] = []
        for item in raw_items:
            no = getattr(item, "no", None)
            if isinstance(no, int):
                surface_numbers.append(no)

        if not surface_numbers:
            return []

        try:
            surfaces = app.get_object_list([surface_class(no=no) for no in surface_numbers])
        except Exception:
            return []

        candidates: list[int] = []
        for surface in surfaces:
            payload = self._to_jsonable(surface)
            name = self._normalize_text(payload.get("name"))
            if any(token in name for token in ("tendon", "postens", "cable", "cordon")):
                no = payload.get("no")
                if isinstance(no, int):
                    candidates.append(no)
        return candidates

    @classmethod
    def _extraer_campos_relevantes_load_case(cls, obj: Any) -> dict[str, object]:
        data = cls._to_jsonable(obj)
        if isinstance(data, dict):
            return {
                "no": data.get("no"),
                "name": data.get("name"),
                "analysis_type": data.get("analysis_type"),
                "action_category": data.get("action_category"),
                "self_weight_active": data.get("self_weight_active"),
            }
        return {"detalle": data}

    @classmethod
    def _extraer_campos_relevantes_member_load(cls, obj: Any) -> dict[str, object]:
        data = cls._to_jsonable(obj)
        if isinstance(data, dict):
            return {
                "no": data.get("no"),
                "load_case": data.get("load_case"),
                "load_type": data.get("load_type"),
                "load_distribution": data.get("load_distribution"),
                "load_direction": data.get("load_direction"),
                "magnitude": data.get("magnitude"),
                "magnitude_1": data.get("magnitude_1"),
                "magnitude_2": data.get("magnitude_2"),
                "members": data.get("members"),
            }
        return {"detalle": data}

    @classmethod
    def _extract_temperature_property_mpa(cls, material_obj: Any, attrs: list[str]) -> float | None:
        temperature = getattr(material_obj, "temperature", None) if material_obj is not None else None
        if temperature is None:
            return None

        for attr in attrs:
            value = getattr(temperature, attr, None)
            if isinstance(value, (int, float)) and value != 0:
                return value / 1_000_000.0 if abs(value) > 1_000_000 else float(value)

        temperature_data = cls._to_jsonable(temperature)
        raw_value = cls._pick_numeric(temperature_data, attrs, default=None)
        return cls._normalize_mpa(raw_value)

    @staticmethod
    def _force_over_area_to_mpa(force_value: float | None, area_m2: float | None) -> float | None:
        if force_value is None or area_m2 in (None, 0):
            return None
        return float(force_value) / float(area_m2) / 1_000_000.0

    @classmethod
    def _extract_material_property_mpa(
        cls,
        material_obj: Any,
        material_data: dict[str, object],
        candidate_keys: list[str],
    ) -> float | None:
        raw_value = None
        temperature = getattr(material_obj, "temperature", None) if material_obj is not None else None
        if temperature is not None:
            for attr in candidate_keys:
                normalized_attr = attr.replace("E", "e") if attr == "E" else attr
                if hasattr(temperature, normalized_attr):
                    candidate = getattr(temperature, normalized_attr)
                    if isinstance(candidate, (int, float)) and candidate != 0:
                        raw_value = float(candidate)
                        break

        if raw_value is None and material_obj is not None:
            raw_value = cls._extract_from_material_values_tree(material_obj, candidate_keys)

        if raw_value is None:
            raw_value = cls._pick_numeric(material_data, candidate_keys, default=None)

        return cls._normalize_mpa(raw_value)

    @classmethod
    def _extract_from_material_values_tree(cls, material_obj: Any, candidate_keys: list[str]) -> float | None:
        material_values = getattr(material_obj, "material_values", None)
        if material_values is None:
            return None
        return cls._search_material_rows(getattr(material_values, "rows", None), candidate_keys)

    @classmethod
    def _search_material_rows(cls, node: Any, candidate_keys: list[str]) -> float | None:
        if node is None:
            return None
        rows = []
        if hasattr(node, "material_values_tree"):
            rows = list(getattr(getattr(node, "material_values_tree"), "rows", []))
        elif hasattr(node, "rows"):
            rows = list(getattr(node, "rows", []))
        elif isinstance(node, list):
            rows = list(node)

        for row in rows:
            key = getattr(row, "key", None)
            if isinstance(key, str) and key in candidate_keys:
                value = cls._extract_numeric_leaf(cls._to_jsonable(getattr(row, "value", None)))
                if value is not None:
                    return value
            nested = cls._search_material_rows(row, candidate_keys)
            if nested is not None:
                return nested
        return None

    @staticmethod
    def _most_common_number(values: list[int]) -> int | None:
        if not values:
            return None
        counts: dict[int, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return max(counts, key=lambda item: (counts[item], -item))

    @classmethod
    def _pick_numeric(
        cls,
        data: Any,
        candidate_keys: list[str],
        default: float | None = None,
    ) -> float | None:
        if isinstance(data, dict):
            keyed_name = data.get("key")
            if isinstance(keyed_name, str) and keyed_name in candidate_keys:
                keyed_value = cls._extract_numeric_leaf(data.get("value"))
                if keyed_value is not None:
                    return keyed_value

            for key, value in data.items():
                if key in candidate_keys and isinstance(value, (int, float)):
                    return float(value)
                nested = cls._pick_numeric(value, candidate_keys, default=None)
                if nested is not None:
                    return nested
        elif isinstance(data, list):
            for item in data:
                nested = cls._pick_numeric(item, candidate_keys, default=None)
                if nested is not None:
                    return nested
        return default

    @classmethod
    def _extract_numeric_leaf(cls, data: Any) -> float | None:
        if isinstance(data, (int, float)):
            return float(data)
        if isinstance(data, dict):
            for key in ["double_value", "float_value", "int_value", "uint_value", "number_value"]:
                value = data.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
            for value in data.values():
                nested = cls._extract_numeric_leaf(value)
                if nested is not None:
                    return nested
        elif isinstance(data, list):
            for item in data:
                nested = cls._extract_numeric_leaf(item)
                if nested is not None:
                    return nested
        return None

    @staticmethod
    def _normalize_mpa(value: float | None) -> float | None:
        if value is None:
            return None
        return value / 1_000_000.0 if abs(value) > 1_000_000 else value

    @staticmethod
    def _square_m_to_square_mm(value: float | None) -> float | None:
        if value is None:
            return None
        return value * 1_000_000.0 if abs(value) < 1 else value

    @staticmethod
    def _enum_value(owner: Any, names: list[str]) -> Any:
        for name in names:
            if hasattr(owner, name):
                return getattr(owner, name)
        raise RuntimeError(f"No se encontro ninguna constante esperada en la API: {', '.join(names)}")

    @classmethod
    def _safe_get_application_info(cls, app: Any) -> dict[str, object]:
        getter = getattr(app, "get_application_info", None)
        if getter is None:
            return {"detalle": "La API conecto, pero no expone get_application_info en esta version."}

        info = getter()
        return cls._to_jsonable(info)

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
        if hasattr(value, "DESCRIPTOR"):
            if MessageToDict is not None:
                return cls._to_jsonable(MessageToDict(value, preserving_proto_field_name=True))
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


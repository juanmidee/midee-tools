from __future__ import annotations

import json
from pathlib import Path

from dlubal.api import rfem

MODEL_PATH = r"D:\01 Juan Bejar\xx Proyectos RFEM\Ejemplos\Postensado\260312-postensado-conectividad-py.rf6"
API_KEY_NAME = "mi_api"
PORT = 9000
LOAD_CASE_NO = 901
MEMBER_LOAD_NO = 9001
MEMBERS = [4, 5, 6, 7, 8, 9, 10, 11]
MAGNITUDE = -0.5723076923


def to_jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "ListFields"):
        return {field.name: to_jsonable(field_value) for field, field_value in value.ListFields()}
    if hasattr(value, "__dict__"):
        return {k: to_jsonable(v) for k, v in vars(value).items() if not k.startswith("_")}
    return str(value)


def build_load_case() -> object:
    cls = rfem.loading.LoadCase
    return cls(
        no=LOAD_CASE_NO,
        name="Diagnostico Tp",
        analysis_type=cls.ANALYSIS_TYPE_STATIC_ANALYSIS,
        action_category=cls.ACTION_CATEGORY_SELF_STRAINING_FORCE_PERMANENT_TP,
        self_weight_active=False,
    )


def build_member_load() -> object:
    cls = rfem.loads.MemberLoad
    return cls(
        no=MEMBER_LOAD_NO,
        load_case=LOAD_CASE_NO,
        members=MEMBERS,
        load_type=cls.LOAD_TYPE_AXIAL_STRAIN,
        load_distribution=cls.LOAD_DISTRIBUTION_UNIFORM,
        load_direction=cls.LOAD_DIRECTION_LOCAL_X,
        magnitude=MAGNITUDE,
    )


def main() -> None:
    result = {
        "modelo": MODEL_PATH,
        "load_case_no": LOAD_CASE_NO,
        "member_load_no": MEMBER_LOAD_NO,
        "members": MEMBERS,
        "magnitude": MAGNITUDE,
    }

    with rfem.Application(api_key_name=API_KEY_NAME, port=PORT) as app:
        app.open_model(path=MODEL_PATH)
        result["aplicacion"] = to_jsonable(app.get_application_info())

        load_case = build_load_case()
        app.create_object(load_case)
        result["load_case_creado"] = True

        read_lc = app.get_object(rfem.loading.LoadCase(no=LOAD_CASE_NO))
        result["load_case_leido"] = to_jsonable(read_lc)

        app.save_model()
        app.open_model(path=MODEL_PATH)
        read_lc_reopen = app.get_object(rfem.loading.LoadCase(no=LOAD_CASE_NO))
        result["load_case_reabierto"] = to_jsonable(read_lc_reopen)

        member_load = build_member_load()
        app.create_object(member_load)
        result["member_load_creado"] = True

        read_ml = app.get_object(rfem.loads.MemberLoad(no=MEMBER_LOAD_NO))
        result["member_load_leido"] = to_jsonable(read_ml)

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

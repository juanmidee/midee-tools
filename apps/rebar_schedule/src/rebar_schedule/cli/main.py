from __future__ import annotations

import argparse
import json
from pathlib import Path

from rebar_schedule.adapters.rfem_client import RfemRebarAdapter
from rebar_schedule.exporters.autocad import export_schedule_to_dxf
from rebar_schedule.exporters.excel import export_schedule_to_excel
from rebar_schedule.services.quantity_audit import build_quantity_audit
from rebar_schedule.services.schedule_builder import build_schedule


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera planillas de corte y doblado a partir de RFEM 6."
    )
    parser.add_argument(
        "--snapshot",
        help="Ruta a un snapshot JSON normalizado con el armado proveniente de RFEM.",
    )
    parser.add_argument(
        "--modelo-rfem",
        help="Ruta opcional al modelo RFEM cuando se use lectura directa por API.",
    )
    parser.add_argument(
        "--leer-rfem-directo",
        action="store_true",
        help="Intenta leer el armado calculado directamente desde RFEM 6 por API.",
    )
    parser.add_argument(
        "--probe-rfem",
        action="store_true",
        help="Ejecuta una lectura de diagnostico no destructiva sobre el modelo activo de RFEM.",
    )
    parser.add_argument(
        "--json-output",
        help="Ruta para guardar la planilla en JSON.",
    )
    parser.add_argument(
        "--auditoria-output",
        help="Ruta para guardar un reporte JSON de computo simple desde RFEM.",
    )
    parser.add_argument(
        "--excel-output",
        help="Ruta para guardar la planilla en .xml o .xlsx.",
    )
    parser.add_argument(
        "--dxf-output",
        help="Ruta para guardar la planilla en DXF.",
    )
    parser.add_argument(
        "--api-key-name",
        default="default",
        help="Nombre de la API key de Dlubal.",
    )
    parser.add_argument(
        "--puerto-rfem",
        type=int,
        default=9000,
        help="Puerto del servicio gRPC de RFEM.",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.snapshot and not args.leer_rfem_directo and not args.probe_rfem:
        parser.error("Debes indicar --snapshot, usar --leer-rfem-directo o usar --probe-rfem.")

    adapter = RfemRebarAdapter(api_key_name=args.api_key_name, port=args.puerto_rfem)
    if args.probe_rfem:
        payload = adapter.probe_active_model(model_path=args.modelo_rfem)
        if args.json_output:
            output_path = Path(args.json_output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    if args.leer_rfem_directo:
        project_name, items = adapter.read_reinforcement_from_rfem(model_path=args.modelo_rfem)
    else:
        snapshot = adapter.load_snapshot_file(args.snapshot)
        project_name, items = adapter.build_items_from_snapshot(snapshot)

    schedule = build_schedule(project_name=project_name, items=items)
    payload = schedule.to_dict()
    audit_payload = build_quantity_audit(project_name=project_name, items=items)

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.auditoria_output:
        output_path = Path(args.auditoria_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(audit_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.excel_output:
        export_schedule_to_excel(schedule, args.excel_output)

    if args.dxf_output:
        export_schedule_to_dxf(schedule, args.dxf_output)

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

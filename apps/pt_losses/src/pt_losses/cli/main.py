from __future__ import annotations

import argparse
import json
from pathlib import Path

from pt_losses.adapters.rfem_client import Rfem6ApiAdapter
from pt_losses.adapters.rfem_stub import Rfem6AdapterStub
from pt_losses.services.calculator import calculate_losses
from pt_losses.services.io import load_input_file, write_result_file
from pt_losses.services.rfem_conversion import build_rfem_load_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calcula perdidas de postensado y deformaciones equivalentes para RFEM 6."
    )
    parser.add_argument(
        "--input",
        "--entrada",
        dest="input",
        required=True,
        help="Ruta del archivo de entrada en formato JSON o YAML.",
    )
    parser.add_argument(
        "--output",
        "--salida",
        dest="output",
        help="Ruta opcional para guardar el resultado en formato JSON.",
    )
    parser.add_argument(
        "--export-rfem-stub",
        "--exportar-rfem-stub",
        action="store_true",
        help="Incluye en la salida JSON la carga simulada para la futura integracion con RFEM 6.",
    )
    parser.add_argument(
        "--probar-conexion-rfem",
        action="store_true",
        help="Prueba la conexion con RFEM sin modificar el modelo.",
    )
    parser.add_argument(
        "--aplicar-en-rfem",
        action="store_true",
        help="Abre RFEM y aplica los estados T0 y Tinf sobre los miembros de tendon indicados.",
    )
    parser.add_argument(
        "--modelo-rfem",
        help="Ruta del modelo RFEM (.rf6) sobre el cual se aplicaran las cargas.",
    )
    parser.add_argument(
        "--miembros-tendon",
        nargs="+",
        type=int,
        help="Lista de numeros de miembro que representan los tendones en RFEM.",
    )
    parser.add_argument(
        "--api-key-name",
        default="default",
        help="Nombre de la API key configurada para la API de Dlubal.",
    )
    parser.add_argument(
        "--puerto-rfem",
        type=int,
        default=9000,
        help="Puerto del servicio gRPC de RFEM.",
    )
    parser.add_argument(
        "--unidad-deformacion-rfem",
        choices=["percent", "adimensional"],
        default="adimensional",
        help="Unidad enviada a RFEM para la deformacion axial equivalente.",
    )
    parser.add_argument(
        "--factor-escala-rfem",
        type=float,
        default=1.0,
        help="Factor multiplicador adicional aplicado a la deformacion enviada a RFEM.",
    )
    parser.add_argument(
        "--inicio-acciones-rfem",
        type=int,
        default=1,
        help="Numero inicial para la accion padre creada en RFEM.",
    )
    parser.add_argument(
        "--inicio-casos-carga-rfem",
        type=int,
        default=1,
        help="Numero inicial para los casos de carga creados en RFEM.",
    )
    parser.add_argument(
        "--inicio-cargas-miembro-rfem",
        type=int,
        default=1,
        help="Numero inicial para las cargas de miembro creadas en RFEM.",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    losses_input = load_input_file(args.input)
    result = calculate_losses(losses_input)
    payloads = build_rfem_load_payload(result)

    payload: dict[str, object] = result.to_nested_dict()
    if args.export_rfem_stub:
        payload["rfem_stub"] = Rfem6AdapterStub().export_axial_strain_states(
            tendon_id=Path(args.input).stem,
            payloads=payloads,
        )

    if args.probar_conexion_rfem:
        adapter = Rfem6ApiAdapter(api_key_name=args.api_key_name, port=args.puerto_rfem)
        payload["rfem_conexion"] = adapter.probar_conexion()

    if args.aplicar_en_rfem:
        if not args.modelo_rfem:
            parser.error("Debes indicar --modelo-rfem para aplicar las cargas en RFEM.")
        if not args.miembros_tendon:
            parser.error("Debes indicar --miembros-tendon para aplicar las cargas en RFEM.")

        adapter = Rfem6ApiAdapter(api_key_name=args.api_key_name, port=args.puerto_rfem)
        payload["rfem_real"] = adapter.aplicar_deformaciones_axiales(
            model_path=args.modelo_rfem,
            tendon_member_nos=args.miembros_tendon,
            payloads=payloads,
            strain_unit=args.unidad_deformacion_rfem,
            strain_scale=args.factor_escala_rfem,
            action_start_no=args.inicio_acciones_rfem,
            load_case_start_no=args.inicio_casos_carga_rfem,
            member_load_start_no=args.inicio_cargas_miembro_rfem,
        )

    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)

    if args.output:
        write_result_file(args.output, payload)

    return 0


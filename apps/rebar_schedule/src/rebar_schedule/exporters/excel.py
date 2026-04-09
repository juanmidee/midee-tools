from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from rebar_schedule.domain.models import RebarSchedule

try:
    from openpyxl import Workbook
except ModuleNotFoundError:
    Workbook = None


HEADERS = [
    "Tipo de fuente",
    "ID fuente",
    "Elemento",
    "Marca",
    "Forma",
    "Disposicion longitudinal",
    "Diametro [mm]",
    "Acero",
    "Cantidad",
    "Longitud de corte [mm]",
    "Segmentos [mm]",
    "Direccion",
    "Separacion [mm]",
    "Gancho / anclaje",
    "Diametro de doblado [mm]",
    "Peso unitario [kg/m]",
    "Longitud total [m]",
    "Peso total [kg]",
    "Observaciones",
]


def export_schedule_to_excel(schedule: RebarSchedule, target_path: str) -> str:
    path = Path(target_path)
    if path.suffix.lower() == ".xlsx":
        return _export_xlsx(schedule, path)
    return _export_spreadsheet_xml(schedule, path)


def _schedule_rows(schedule: RebarSchedule) -> list[list[object]]:
    rows: list[list[object]] = []
    for row in schedule.rows:
        rows.append(
            [
                row.source_type,
                row.source_id,
                row.host_label,
                row.bar_mark,
                _forma_es(row.shape_code),
                row.longitudinal_layout_label or row.longitudinal_layout_code or "",
                row.diameter_mm,
                row.steel_grade,
                row.count,
                row.cut_length_mm,
                ", ".join(str(int(value)) if float(value).is_integer() else f"{value:.1f}" for value in row.segments_mm),
                row.direction or "",
                row.spacing_mm or "",
                row.hook_detail or "",
                row.bending_diameter_mm or "",
                row.unit_weight_kg_m,
                row.total_length_m,
                row.total_weight_kg,
                row.notes or "",
            ]
        )
    return rows


def _export_xlsx(schedule: RebarSchedule, path: Path) -> str:
    if Workbook is None:
        raise RuntimeError(
            "Para exportar a .xlsx debes instalar openpyxl. Usa: pip install -e .[excel]"
        )

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Planilla"
    worksheet.append(["Proyecto", schedule.project_name])
    worksheet.append(["Total de filas", len(schedule.rows)])
    worksheet.append(["Total de barras", schedule.total_bars])
    worksheet.append(["Peso total [kg]", schedule.total_weight_kg])
    worksheet.append([])
    worksheet.append(HEADERS)

    for row in _schedule_rows(schedule):
        worksheet.append(row)

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    return str(path)


def _export_spreadsheet_xml(schedule: RebarSchedule, path: Path) -> str:
    rows_xml: list[str] = []
    rows_xml.append(_xml_row(["Proyecto", schedule.project_name]))
    rows_xml.append(_xml_row(["Total de filas", len(schedule.rows)]))
    rows_xml.append(_xml_row(["Total de barras", schedule.total_bars]))
    rows_xml.append(_xml_row(["Peso total [kg]", round(schedule.total_weight_kg, 3)]))
    rows_xml.append(_xml_row([""]))
    rows_xml.append(_xml_row(HEADERS))

    for row in _schedule_rows(schedule):
        rows_xml.append(_xml_row(row))

    workbook_xml = f"""<?xml version="1.0"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="Planilla">
  <Table>
   {''.join(rows_xml)}
  </Table>
 </Worksheet>
</Workbook>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(workbook_xml, encoding="utf-8")
    return str(path)


def _xml_row(values: list[object]) -> str:
    cells = "".join(_xml_cell(value) for value in values)
    return f"<Row>{cells}</Row>"


def _xml_cell(value: object) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<Cell><Data ss:Type="Number">{value}</Data></Cell>'
    return f'<Cell><Data ss:Type="String">{escape(str(value))}</Data></Cell>'


def _forma_es(value: str) -> str:
    return {
        "STRAIGHT": "Barra recta",
        "LONGITUDINAL": "Armadura longitudinal",
        "STIRRUP_CLOSED": "Cerco cerrado",
    }.get(value, value)

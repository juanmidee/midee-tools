from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from rebar_schedule.domain.models import RebarSchedule, RebarScheduleRow
from rebar_schedule.services.workshop_geometry import ArcPrimitive, CirclePrimitive, LinePrimitive, TextPrimitive, build_shape_geometry

PAGE_WIDTH = 21.0
PAGE_HEIGHT = 29.7
MARGIN_LEFT = 1.75
MARGIN_RIGHT = 0.5
MARGIN_TOP = 1.05
MARGIN_BOTTOM = 0.5
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
ROWS_PER_PAGE = 6
PAGE_GAP = 2.0

COL_POS = 1.2
COL_DIA = 1.0
COL_CU = 1.2
COL_TOTAL = 1.2
COL_FORMA = 9.4
COL_LARGO_CU = 1.4
COL_LARGO_TOTAL = 1.7

LAYER_FRAME = "ARM_BARRAS_PowerIng"
LAYER_TEXT = "ARM_TEXTOS_PowerIng"
LAYER_GRID = "ARM_DISTRIB_PowerIng"
LAYER_SHAPE = "BBARRAS"
LAYER_DIM = "BTEXTO"
LAYER_ROTULO = "Resumen_PI"
LAYER_SUMMARY = "RESUMEN"

LAYERS = [
    ("0", 3),
    (LAYER_FRAME, 4),
    (LAYER_TEXT, 3),
    (LAYER_GRID, 1),
    (LAYER_SHAPE, 5),
    (LAYER_DIM, 3),
    (LAYER_ROTULO, 3),
    (LAYER_SUMMARY, 3),
]

TEXT_STYLE = "ROMANS"


def export_schedule_to_dxf(schedule: RebarSchedule, target_path: str) -> str:
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_build_dxf(schedule), encoding="cp1252", errors="replace")
    return str(path)


def _build_dxf(schedule: RebarSchedule) -> str:
    lines: list[str] = []
    lines.extend(_header_section())
    lines.extend(_tables_section())
    lines.extend(["0", "SECTION", "2", "ENTITIES"])

    page_index = 0
    lines.extend(_draw_summary_page(schedule, x0=page_index * (PAGE_WIDTH + PAGE_GAP), y0=0.0))
    page_index += 1

    grouped: dict[str, list[RebarScheduleRow]] = defaultdict(list)
    for row in schedule.rows:
        grouped[row.host_label].append(row)

    for host_label, rows in grouped.items():
        chunks = [rows[index : index + ROWS_PER_PAGE] for index in range(0, len(rows), ROWS_PER_PAGE)]
        for chunk in chunks:
            x0 = page_index * (PAGE_WIDTH + PAGE_GAP)
            lines.extend(_draw_detail_page(schedule, host_label, chunk, page_index + 1, x0=x0, y0=0.0))
            page_index += 1

    lines.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(lines) + "\n"


def _header_section() -> list[str]:
    return [
        "0",
        "SECTION",
        "2",
        "HEADER",
        "9",
        "$ACADVER",
        "1",
        "AC1009",
        "9",
        "$DWGCODEPAGE",
        "3",
        "ANSI_1252",
        "9",
        "$TEXTSTYLE",
        "7",
        TEXT_STYLE,
        "9",
        "$TEXTSIZE",
        "40",
        "0.20",
        "0",
        "ENDSEC",
    ]


def _tables_section() -> list[str]:
    lines = [
        "0",
        "SECTION",
        "2",
        "TABLES",
        "0",
        "TABLE",
        "2",
        "LTYPE",
        "70",
        "1",
        "0",
        "LTYPE",
        "2",
        "CONTINUOUS",
        "70",
        "0",
        "3",
        "Solid line",
        "72",
        "65",
        "73",
        "0",
        "40",
        "0.0",
        "0",
        "ENDTAB",
        "0",
        "TABLE",
        "2",
        "LAYER",
        "70",
        str(len(LAYERS)),
    ]
    for name, color in LAYERS:
        lines.extend(
            [
                "0",
                "LAYER",
                "2",
                name,
                "70",
                "0",
                "62",
                str(color),
                "6",
                "CONTINUOUS",
            ]
        )

    lines.extend(
        [
            "0",
            "ENDTAB",
            "0",
            "TABLE",
            "2",
            "STYLE",
            "70",
            "1",
            "0",
            "STYLE",
            "2",
            TEXT_STYLE,
            "70",
            "0",
            "40",
            "0.0",
            "41",
            "0.8",
            "50",
            "0.0",
            "71",
            "0",
            "42",
            "0.2",
            "3",
            "romans.shx",
            "4",
            "",
            "0",
            "ENDTAB",
            "0",
            "ENDSEC",
        ]
    )
    return lines


def _draw_summary_page(schedule: RebarSchedule, x0: float, y0: float) -> list[str]:
    entities: list[str] = []
    inner_left, inner_right, inner_top, inner_bottom = _sheet_bounds(x0, y0)

    entities.extend(_draw_sheet_frame(x0, y0))
    entities.extend(_add_text(inner_left + 6.2, inner_top - 1.2, "RESUMEN DE ARMADURA", 0.36, LAYER_FRAME))

    rows = _summary_rows(schedule)
    x = inner_left
    table_top = inner_top - 3.0
    widths = [1.8, 4.3, 2.0, 4.1]
    row_h = 1.25
    total_w = sum(widths)
    total_h = row_h * (len(rows) + 2)
    bottom = table_top - total_h
    x1 = x + widths[0]
    x2 = x1 + widths[1]
    x3 = x2 + widths[2]
    x4 = x3 + widths[3]

    entities.extend(_add_rect(x, table_top, total_w, total_h, LAYER_SUMMARY))
    for x_line in [x1, x2, x3]:
        entities.extend(_add_line(x_line, table_top, x_line, bottom, LAYER_SUMMARY))
    for i in range(1, len(rows) + 2):
        y_line = table_top - row_h * i
        entities.extend(_add_line(x, y_line, x4, y_line, LAYER_SUMMARY))

    entities.extend(_add_text(x + 0.75, table_top - 0.82, "%%c", 0.25, LAYER_TEXT))
    entities.extend(_add_text(x1 + 0.35, table_top - 0.82, "LONGITUD(m)", 0.25, LAYER_TEXT))
    entities.extend(_add_text(x2 + 0.45, table_top - 0.82, "kg/ml", 0.25, LAYER_TEXT))
    entities.extend(_add_text(x3 + 0.75, table_top - 0.82, "PESO(Kg)", 0.25, LAYER_TEXT))

    for index, row in enumerate(rows, start=1):
        y_text = table_top - row_h * index - 0.82
        entities.extend(_add_text(x + 0.82, y_text, row["diametro"], 0.27, LAYER_TEXT))
        entities.extend(_add_text(x1 + 1.45, y_text, row["longitud"], 0.27, LAYER_TEXT))
        entities.extend(_add_text(x2 + 0.55, y_text, row["kg_ml"], 0.27, LAYER_TEXT))
        entities.extend(_add_text(x3 + 1.45, y_text, row["peso"], 0.27, LAYER_TEXT))

    total_y = table_top - row_h * (len(rows) + 1) - 0.82
    entities.extend(_add_text(x2 + 0.72, total_y, "TOTAL", 0.27, LAYER_TEXT))
    entities.extend(_add_text(x3 + 1.45, total_y, f"{schedule.total_weight_kg:.0f}", 0.27, LAYER_TEXT))
    entities.extend(_add_text(x + 0.25, bottom - 0.9, _steel_label(schedule), 0.25, LAYER_TEXT))
    entities.extend(_draw_rotulo(inner_left, inner_right, inner_bottom, "1"))
    return entities


def _draw_detail_page(schedule: RebarSchedule, host_label: str, rows: list[RebarScheduleRow], sheet_no: int, x0: float, y0: float) -> list[str]:
    entities: list[str] = []
    inner_left, inner_right, inner_top, inner_bottom = _sheet_bounds(x0, y0)

    entities.extend(_draw_sheet_frame(x0, y0))
    entities.extend(_add_text(inner_left + 5.9, inner_top - 0.95, "PLANILLA DE ARMADURA", 0.36, LAYER_FRAME))
    entities.extend(_add_text(inner_left + 0.45, inner_top - 2.05, host_label, 0.24, LAYER_TEXT))
    entities.extend(_add_text(inner_left + 10.2, inner_top - 2.05, f"Proyecto: {schedule.project_name}", 0.18, LAYER_TEXT))

    table_top = inner_top - 3.15
    entities.extend(_draw_main_table(inner_left, table_top, rows))
    entities.extend(_draw_rotulo(inner_left, inner_right, inner_bottom, str(sheet_no)))
    return entities


def _draw_main_table(x: float, y_top: float, rows: list[RebarScheduleRow]) -> list[str]:
    entities: list[str] = []
    header_h1 = 0.95
    header_h2 = 0.72
    row_h = 3.55
    total_w = CONTENT_WIDTH
    total_h = header_h1 + header_h2 + row_h * ROWS_PER_PAGE
    bottom = y_top - total_h

    x_pos = x
    x_dia = x_pos + COL_POS
    x_cu = x_dia + COL_DIA
    x_total = x_cu + COL_CU
    x_forma = x_total + COL_TOTAL
    x_largo_cu = x_forma + COL_FORMA
    x_largo_total = x_largo_cu + COL_LARGO_CU
    x_end = x + total_w

    entities.extend(_add_rect(x, y_top, total_w, total_h, LAYER_GRID))
    for x_line in [x_dia, x_cu, x_total, x_forma, x_largo_cu, x_largo_total]:
        entities.extend(_add_line(x_line, y_top, x_line, bottom, LAYER_GRID))

    header_split_y = y_top - header_h1
    second_header_y = y_top - header_h1 - header_h2
    entities.extend(_add_line(x_cu, header_split_y, x_total, header_split_y, LAYER_GRID))
    entities.extend(_add_line(x_largo_cu, header_split_y, x_end, header_split_y, LAYER_GRID))
    entities.extend(_add_line(x, second_header_y, x_end, second_header_y, LAYER_GRID))

    for index in range(1, ROWS_PER_PAGE + 1):
        y_line = second_header_y - row_h * index
        entities.extend(_add_line(x, y_line, x_end, y_line, LAYER_GRID))

    entities.extend(_add_text(x_pos + 0.32, y_top - 0.95, "POS.", 0.20, LAYER_TEXT))
    entities.extend(_add_text(x_dia + 0.35, y_top - 0.95, "%%c", 0.22, LAYER_TEXT))
    entities.extend(_add_text(x_cu + 0.15, y_top - 0.48, "CANTIDAD", 0.18, LAYER_TEXT))
    entities.extend(_add_text(x_cu + 0.22, y_top - 1.38, "C/U", 0.17, LAYER_TEXT))
    entities.extend(_add_text(x_total + 0.16, y_top - 1.38, "TOTAL", 0.17, LAYER_TEXT))
    entities.extend(_add_text(x_forma + 1.75, y_top - 0.48, "FORMA DE LA BARRA", 0.22, LAYER_TEXT))
    entities.extend(_add_text(x_forma + 1.58, y_top - 1.20, "Dimensiones exteriores (cm)", 0.16, LAYER_TEXT))
    entities.extend(_add_text(x_largo_cu + 0.10, y_top - 0.48, "LARGO en mts.", 0.18, LAYER_TEXT))
    entities.extend(_add_text(x_largo_cu + 0.15, y_top - 1.38, "C/U", 0.17, LAYER_TEXT))
    entities.extend(_add_text(x_largo_total + 0.12, y_top - 1.38, "TOTAL", 0.17, LAYER_TEXT))

    base_y = second_header_y
    for index, row in enumerate(rows, start=1):
        row_top = base_y - row_h * (index - 1)
        row_bottom = row_top - row_h
        row_center = (row_top + row_bottom) / 2.0

        entities.extend(_add_text(x_pos + 0.42, row_center, str(index), 0.23, LAYER_TEXT))
        entities.extend(_add_text(x_dia + 0.22, row_center, _format_number(row.diameter_mm), 0.23, LAYER_TEXT))
        entities.extend(_add_text(x_cu + 0.42, row_center, "--", 0.23, LAYER_TEXT))
        entities.extend(_add_text(x_total + 0.32, row_center, str(row.count), 0.23, LAYER_TEXT))
        entities.extend(_add_text(x_largo_cu + 0.10, row_center, f"{row.cut_length_mm / 1000.0:.2f}", 0.23, LAYER_TEXT))
        entities.extend(_add_text(x_largo_total + 0.12, row_center, f"{row.total_length_m:.2f}", 0.23, LAYER_TEXT))
        entities.extend(_draw_shape_cell(x_forma, row_top, COL_FORMA, row_h, row))

    return entities


def _draw_shape_cell(x: float, row_top: float, width: float, height: float, row: RebarScheduleRow) -> list[str]:
    workshop = build_shape_geometry(
        row,
        x=x,
        row_top=row_top,
        width=width,
        height=height,
        shape_layer=LAYER_SHAPE,
        text_layer=LAYER_DIM,
    )
    if workshop is not None:
        return _render_workshop_geometry(workshop)
    if row.shape_code == "STIRRUP_CLOSED":
        return _draw_stirrup_shape(x, row_top, width, height, row)
    return _draw_longitudinal_shape(x, row_top, width, height, row)


def _render_workshop_geometry(drawing: object) -> list[str]:
    entities: list[str] = []
    if not hasattr(drawing, "lines"):
        return entities
    for line in drawing.lines:
        entities.extend(_primitive_line(line))
    for arc in drawing.arcs:
        entities.extend(_primitive_arc(arc))
    for circle in getattr(drawing, "circles", ()):
        entities.extend(_primitive_circle(circle))
    for text in drawing.texts:
        entities.extend(_primitive_text(text))
    return entities


def _draw_longitudinal_shape(x: float, row_top: float, width: float, height: float, row: RebarScheduleRow) -> list[str]:
    entities: list[str] = []
    left_hook, right_hook = _segments_for_longitudinal(row)
    y = row_top - height * 0.58
    x1 = x + 1.5
    x2 = x + width - 1.5
    hook_h = 0.95

    entities.extend(_add_line(x1, y, x2, y, LAYER_SHAPE))
    if left_hook > 0:
        entities.extend(_add_line(x1, y, x1, y + hook_h, LAYER_SHAPE))
    if right_hook > 0:
        entities.extend(_add_line(x2, y, x2, y + hook_h, LAYER_SHAPE))

    entities.extend(_add_text((x1 + x2) / 2.0 - 0.55, y - 0.68, _format_cm(row.cut_length_mm), 0.22, LAYER_DIM))
    if row.bending_diameter_mm:
        entities.extend(_add_text(x + 0.28, row_top - height + 0.55, f"dobl. {_format_cm(row.bending_diameter_mm)}", 0.15, LAYER_DIM))
    return entities


def _draw_stirrup_shape(x: float, row_top: float, width: float, height: float, row: RebarScheduleRow) -> list[str]:
    entities: list[str] = []
    shape = _stirrup_geometry(row)
    left = x + (width - shape["draw_w"]) / 2.0
    top = row_top - 0.95
    right = left + shape["draw_w"]
    bottom = top - shape["draw_h"]
    radius = shape["radius"]
    hook = shape["hook"]

    entities.extend(_draw_rounded_rect(left, top, right, bottom, radius, LAYER_SHAPE))
    entities.extend(_draw_outer_hooks(left, top, right, bottom, radius, hook, row.stirrup_type))

    if row.crossties_active:
        entities.extend(_draw_crossties(left, top, right, bottom, radius, hook, row.stirrup_type))

    entities.extend(_add_text((left + right) / 2.0 - 0.45, bottom - 0.60, _format_cm(shape["width_mm"]), 0.20, LAYER_DIM))
    entities.extend(_add_text(left - 0.60, (top + bottom) / 2.0, _format_cm(shape["height_mm"]), 0.20, LAYER_DIM))
    if row.spacing_mm:
        entities.extend(_add_text(x + 0.25, row_top - height + 0.55, f"c/{row.spacing_mm / 10.0:.0f}", 0.16, LAYER_DIM))
    return entities


def _stirrup_geometry(row: RebarScheduleRow) -> dict[str, float]:
    section_w = row.section_width_mm or 250.0
    section_h = row.section_height_mm or section_w
    cover = row.concrete_cover_mm or 30.0
    outer_w_mm = max(section_w - 2.0 * cover - row.diameter_mm, 80.0)
    outer_h_mm = max(section_h - 2.0 * cover - row.diameter_mm, 80.0)
    max_draw_w = 3.1
    max_draw_h = 1.8
    scale = min(max_draw_w / outer_w_mm, max_draw_h / outer_h_mm)
    draw_w = outer_w_mm * scale
    draw_h = outer_h_mm * scale
    hook = min(draw_w, draw_h) * 0.22
    radius = min(draw_w, draw_h) * 0.10
    return {
        "width_mm": outer_w_mm,
        "height_mm": outer_h_mm,
        "draw_w": draw_w,
        "draw_h": draw_h,
        "hook": hook,
        "radius": radius,
    }


def _hook_label(stirrup_type: str | None) -> str:
    if not stirrup_type:
        return ""
    if "HOOK_135" in stirrup_type:
        return "135%%d"
    if "HOOK_90" in stirrup_type:
        return "90%%d"
    if "HOOK_180" in stirrup_type:
        return "180%%d"
    return stirrup_type.replace("STIRRUP_TYPE_", "")


def _segments_for_longitudinal(row: RebarScheduleRow) -> tuple[float, float]:
    hooks = (row.hook_detail or "").split("->")
    left_code = hooks[0].strip() if len(hooks) == 2 else ""
    right_code = hooks[1].strip() if len(hooks) == 2 else ""
    hook_len = max(row.diameter_mm * 9.5, 120.0)
    left = hook_len if left_code in {"1", "2"} else 0.0
    right = hook_len if right_code in {"1", "2"} else 0.0
    return left, right


def _summary_rows(schedule: RebarSchedule) -> list[dict[str, str]]:
    diameters = [6, 8, 10, 12, 16, 20, 25, 32, 40]
    grouped: dict[int, dict[str, float]] = {diam: {"longitud": 0.0, "kg_ml": (diam**2) / 162.0, "peso": 0.0} for diam in diameters}
    for row in schedule.rows:
        diam = int(round(row.diameter_mm))
        grouped.setdefault(diam, {"longitud": 0.0, "kg_ml": row.unit_weight_kg_m, "peso": 0.0})
        grouped[diam]["longitud"] += row.total_length_m
        grouped[diam]["peso"] += row.total_weight_kg
        grouped[diam]["kg_ml"] = row.unit_weight_kg_m
    return [
        {
            "diametro": str(diam),
            "longitud": "" if data["longitud"] == 0 else f"{data['longitud']:.0f}",
            "kg_ml": f"{data['kg_ml']:.2f}",
            "peso": "" if data["peso"] == 0 else f"{data['peso']:.0f}",
        }
        for diam, data in sorted(grouped.items(), key=lambda item: item[0])
    ]


def _steel_label(schedule: RebarSchedule) -> str:
    values = [row.steel_grade.strip() for row in schedule.rows if row.steel_grade and row.steel_grade.strip()]
    if not values:
        return "ACERO"
    return Counter(values).most_common(1)[0][0]


def _sheet_bounds(x0: float, y0: float) -> tuple[float, float, float, float]:
    return (
        x0 + MARGIN_LEFT,
        x0 + PAGE_WIDTH - MARGIN_RIGHT,
        y0 - MARGIN_TOP,
        y0 - PAGE_HEIGHT + MARGIN_BOTTOM,
    )


def _draw_sheet_frame(x0: float, y0: float) -> list[str]:
    inner_left, _, inner_top, _ = _sheet_bounds(x0, y0)
    return [
        *_add_rect(x0, y0, PAGE_WIDTH, PAGE_HEIGHT, LAYER_FRAME),
        *_add_rect(inner_left, inner_top, CONTENT_WIDTH, PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM, LAYER_FRAME),
    ]


def _draw_rotulo(inner_left: float, inner_right: float, inner_bottom: float, sheet_label: str) -> list[str]:
    entities: list[str] = []
    footer_top = inner_bottom + 1.00
    footer_mid = inner_bottom + 0.45
    splits = [inner_left + 1.0, inner_left + 2.6, inner_left + 10.8, inner_left + 13.2, inner_left + 15.3]
    entities.extend(_add_line(inner_left, footer_top, inner_right, footer_top, LAYER_ROTULO))
    entities.extend(_add_line(inner_left, footer_mid, inner_right, footer_mid, LAYER_ROTULO))
    for x in splits:
        entities.extend(_add_line(x, footer_top, x, inner_bottom, LAYER_ROTULO))
    entities.extend(_add_text(inner_left + 0.18, inner_bottom + 0.60, "Rev.", 0.13, LAYER_ROTULO))
    entities.extend(_add_text(splits[0] + 0.18, inner_bottom + 0.60, "Fecha", 0.13, LAYER_ROTULO))
    entities.extend(_add_text(splits[1] + 0.45, inner_bottom + 0.60, "Descripcion", 0.13, LAYER_ROTULO))
    entities.extend(_add_text(splits[2] + 0.12, inner_bottom + 0.60, "Corresponde a plano", 0.13, LAYER_ROTULO))
    entities.extend(_add_text(splits[3] + 0.15, inner_bottom + 0.60, "Lista Nro.", 0.13, LAYER_ROTULO))
    entities.extend(_add_text(splits[4] + 0.15, inner_bottom + 0.60, "Hoja", 0.13, LAYER_ROTULO))
    entities.extend(_add_text(splits[2] + 0.20, inner_bottom + 0.18, "N", 0.15, LAYER_ROTULO))
    entities.extend(_add_text(splits[3] + 0.35, inner_bottom + 0.18, "N", 0.15, LAYER_ROTULO))
    entities.extend(_add_text(splits[4] + 0.28, inner_bottom + 0.18, sheet_label, 0.15, LAYER_ROTULO))
    return entities


def _format_number(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.1f}"


def _format_cm(value_mm: float) -> str:
    return f"{value_mm / 10.0:.0f}"


def _add_text(x: float, y: float, value: str, height: float, layer: str) -> list[str]:
    return [
        "0",
        "TEXT",
        "8",
        layer,
        "7",
        TEXT_STYLE,
        "10",
        f"{x:.3f}",
        "20",
        f"{y:.3f}",
        "30",
        "0.0",
        "40",
        f"{height:.3f}",
        "1",
        value.replace("\n", " ").replace("\r", " "),
    ]


def _primitive_text(text: TextPrimitive) -> list[str]:
    return _add_text(text.x, text.y, text.value, text.height, text.layer)


def _add_line(x1: float, y1: float, x2: float, y2: float, layer: str) -> list[str]:
    return [
        "0",
        "LINE",
        "8",
        layer,
        "10",
        f"{x1:.3f}",
        "20",
        f"{y1:.3f}",
        "30",
        "0.0",
        "11",
        f"{x2:.3f}",
        "21",
        f"{y2:.3f}",
        "31",
        "0.0",
    ]


def _primitive_line(line: LinePrimitive) -> list[str]:
    return _add_line(line.x1, line.y1, line.x2, line.y2, line.layer)


def _add_rect(x: float, y: float, width: float, height: float, layer: str) -> list[str]:
    return [
        *_add_line(x, y, x + width, y, layer),
        *_add_line(x + width, y, x + width, y - height, layer),
        *_add_line(x + width, y - height, x, y - height, layer),
        *_add_line(x, y - height, x, y, layer),
    ]


def _draw_rounded_rect(left: float, top: float, right: float, bottom: float, radius: float, layer: str) -> list[str]:
    return [
        *_add_line(left + radius, top, right - radius, top, layer),
        *_add_line(right, top - radius, right, bottom + radius, layer),
        *_add_line(right - radius, bottom, left + radius, bottom, layer),
        *_add_line(left, bottom + radius, left, top - radius, layer),
        *_add_arc(left + radius, top - radius, radius, 90, 180, layer),
        *_add_arc(right - radius, top - radius, radius, 0, 90, layer),
        *_add_arc(right - radius, bottom + radius, radius, 270, 360, layer),
        *_add_arc(left + radius, bottom + radius, radius, 180, 270, layer),
    ]


def _draw_outer_hooks(
    left: float,
    top: float,
    right: float,
    bottom: float,
    radius: float,
    hook: float,
    stirrup_type: str | None,
) -> list[str]:
    hook_type = stirrup_type or ""
    if "HOOK_135" in hook_type:
        start_x = right - radius * 0.95
        start_y = top - radius * 0.95
        elbow_x = start_x - hook * 0.78
        elbow_y = start_y - hook * 0.78
        end_x = elbow_x - hook * 0.22
        end_y = elbow_y - hook * 0.22
        return [
            *_add_line(start_x, start_y, elbow_x, elbow_y, LAYER_SHAPE),
            *_add_line(elbow_x, elbow_y, end_x, end_y, LAYER_SHAPE),
        ]
    if "HOOK_90" in hook_type:
        start_x = right - radius * 0.55
        start_y = top - radius * 0.55
        return [
            *_add_line(start_x, start_y, start_x, start_y - hook, LAYER_SHAPE),
            *_add_line(start_x, start_y - hook, start_x - hook * 0.7, start_y - hook, LAYER_SHAPE),
        ]
    if "HOOK_180" in hook_type:
        cx = right - radius * 0.9 - hook * 0.35
        cy = top - radius * 0.9 - hook * 0.35
        return [
            *_add_line(right - radius * 0.9, top - radius * 0.9, cx + hook * 0.35, cy, LAYER_SHAPE),
            *_add_arc(cx, cy, hook * 0.35, 0, 180, LAYER_SHAPE),
        ]
    return []


def _draw_crossties(
    left: float,
    top: float,
    right: float,
    bottom: float,
    radius: float,
    hook: float,
    stirrup_type: str | None,
) -> list[str]:
    entities: list[str] = []
    cx = (left + right) / 2.0
    cy = (top + bottom) / 2.0
    inner_left = left + radius * 1.3
    inner_right = right - radius * 1.3
    inner_top = top - radius * 1.3
    inner_bottom = bottom + radius * 1.3

    hook_type = stirrup_type or ""

    # Horizontal crosstie with connected hooks at both ends.
    horizontal_start_x = inner_left + hook * 0.72
    horizontal_end_x = inner_right - hook * 0.72
    entities.extend(_add_line(horizontal_start_x, cy, horizontal_end_x, cy, LAYER_SHAPE))

    # Vertical crosstie with connected hooks at top and bottom.
    vertical_top_y = inner_top - hook * 0.72
    vertical_bottom_y = inner_bottom + hook * 0.72
    entities.extend(_add_line(cx, vertical_top_y, cx, vertical_bottom_y, LAYER_SHAPE))

    if "HOOK_135" in hook_type:
        entities.extend(_add_line(horizontal_start_x, cy, inner_left, cy - hook * 0.32, LAYER_SHAPE))
        entities.extend(_add_line(horizontal_end_x, cy, inner_right, cy - hook * 0.32, LAYER_SHAPE))
        entities.extend(_add_line(cx, vertical_top_y, cx + hook * 0.68, inner_top, LAYER_SHAPE))
        entities.extend(_add_line(cx, vertical_bottom_y, cx - hook * 0.68, inner_bottom, LAYER_SHAPE))
    elif "HOOK_90" in hook_type:
        entities.extend(_add_line(horizontal_start_x, cy, inner_left, cy, LAYER_SHAPE))
        entities.extend(_add_line(horizontal_end_x, cy, inner_right, cy, LAYER_SHAPE))
        entities.extend(_add_line(cx, vertical_top_y, cx + hook * 0.68, vertical_top_y, LAYER_SHAPE))
        entities.extend(_add_line(cx, vertical_bottom_y, cx - hook * 0.68, vertical_bottom_y, LAYER_SHAPE))
    return entities


def _add_arc(cx: float, cy: float, radius: float, start_angle: float, end_angle: float, layer: str) -> list[str]:
    return [
        "0",
        "ARC",
        "8",
        layer,
        "10",
        f"{cx:.3f}",
        "20",
        f"{cy:.3f}",
        "30",
        "0.0",
        "40",
        f"{radius:.3f}",
        "50",
        f"{start_angle:.3f}",
        "51",
        f"{end_angle:.3f}",
    ]


def _primitive_arc(arc: ArcPrimitive) -> list[str]:
    return _add_arc(arc.cx, arc.cy, arc.radius, arc.start_angle, arc.end_angle, arc.layer)


def _add_circle(cx: float, cy: float, radius: float, layer: str) -> list[str]:
    return [
        "0",
        "CIRCLE",
        "8",
        layer,
        "10",
        f"{cx:.3f}",
        "20",
        f"{cy:.3f}",
        "30",
        "0.0",
        "40",
        f"{radius:.3f}",
    ]


def _primitive_circle(circle: CirclePrimitive) -> list[str]:
    return _add_circle(circle.cx, circle.cy, circle.radius, circle.layer)

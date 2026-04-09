from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ShapeParameter:
    key: str
    label: str
    unit: str
    required: bool
    description: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WorkshopShape:
    code: str
    family: str
    name_es: str
    aci_scope: str
    description: str
    geometry_notes: tuple[str, ...]
    rfem_stirrup_types: tuple[str, ...] = ()
    rfem_shape_codes: tuple[str, ...] = ()
    parameters: tuple[ShapeParameter, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["parameters"] = [parameter.to_dict() for parameter in self.parameters]
        return payload


def _param(key: str, label: str, unit: str, required: bool, description: str) -> ShapeParameter:
    return ShapeParameter(
        key=key,
        label=label,
        unit=unit,
        required=required,
        description=description,
    )


CATALOGO_FORMAS: dict[str, WorkshopShape] = {
    "ACI-01": WorkshopShape(
        code="ACI-01",
        family="barra",
        name_es="Barra recta",
        aci_scope="Barras longitudinales o de reparto sin patillas",
        description="Barra recta de taller definida por un unico largo de corte.",
        geometry_notes=(
            "La geometria de fabricacion es una sola linea recta.",
            "No incorpora ganchos ni dobleces terminales.",
        ),
        rfem_shape_codes=("STRAIGHT", "LONGITUDINAL"),
        parameters=(
            _param("L", "Largo total", "mm", True, "Longitud total de corte de la barra."),
        ),
    ),
    "ACI-02": WorkshopShape(
        code="ACI-02",
        family="barra",
        name_es="Barra con una patilla a 90 grados",
        aci_scope="Anclajes simples y barras terminales con un solo gancho",
        description="Barra con un tramo principal y una patilla terminal a 90 grados.",
        geometry_notes=(
            "La patilla debe dibujarse como parte de la trayectoria continua de la barra.",
            "La cota de la patilla se controla separada del tramo principal.",
        ),
        parameters=(
            _param("A", "Tramo principal", "mm", True, "Longitud entre doblez y extremo recto."),
            _param("B", "Patilla", "mm", True, "Longitud recta del gancho a 90 grados."),
        ),
    ),
    "ACI-03": WorkshopShape(
        code="ACI-03",
        family="barra",
        name_es="Barra con una patilla a 135 grados",
        aci_scope="Anclajes especiales o barras con gancho terminal a 135 grados",
        description="Barra con un tramo principal y una unica patilla terminal a 135 grados.",
        geometry_notes=(
            "El gancho debe quedar conectado geometricamente al vertice de doblado.",
            "La representacion requiere angulo real de 135 grados y patilla visible.",
        ),
        parameters=(
            _param("A", "Tramo principal", "mm", True, "Longitud entre doblez y extremo recto."),
            _param("B", "Patilla 135", "mm", True, "Longitud recta de la patilla a 135 grados."),
        ),
    ),
    "ACI-04": WorkshopShape(
        code="ACI-04",
        family="barra",
        name_es="Barra con dos patillas a 90 grados",
        aci_scope="Barras en U o barras con anclaje en ambos extremos",
        description="Barra con tramo principal central y dos patillas terminales a 90 grados.",
        geometry_notes=(
            "Las patillas forman parte de una unica trayectoria continua.",
            "Las dos patas pueden ser simetricas o de distinta longitud.",
        ),
        parameters=(
            _param("A", "Tramo principal", "mm", True, "Longitud entre dobleces."),
            _param("B1", "Patilla 1", "mm", True, "Longitud recta del primer extremo."),
            _param("B2", "Patilla 2", "mm", True, "Longitud recta del segundo extremo."),
        ),
    ),
    "ACI-05": WorkshopShape(
        code="ACI-05",
        family="barra",
        name_es="Barra con dos patillas a 135 grados",
        aci_scope="Barras cerradas o de confinamiento con ambos extremos enganchados",
        description="Barra con dobleces de 135 grados en ambos extremos.",
        geometry_notes=(
            "Los dos ganchos deben representarse en continuidad con la barra.",
            "No aplica a estribos cerrados con perimetro completo.",
        ),
        parameters=(
            _param("A", "Tramo principal", "mm", True, "Longitud entre dobleces."),
            _param("B1", "Patilla 135 izquierda", "mm", True, "Longitud del primer gancho."),
            _param("B2", "Patilla 135 derecha", "mm", True, "Longitud del segundo gancho."),
        ),
    ),
    "ACI-10": WorkshopShape(
        code="ACI-10",
        family="estribo",
        name_es="Estribo cerrado de 2 ramas con gancho de 135 grados",
        aci_scope="Cercos de vigas y columnas bajo criterio ACI con gancho sismico",
        description="Estribo perimetral cerrado de dos ramas con un gancho terminal a 135 grados.",
        geometry_notes=(
            "El gancho exterior debe quedar en un solo vertice de cierre.",
            "El recorrido se interpreta como una unica barra cerrada con remate a 135 grados.",
            "Las dimensiones A y B son exteriores de taller.",
        ),
        rfem_stirrup_types=("STIRRUP_TYPE_TWO_LEGGED_CLOSED_HOOK_135",),
        rfem_shape_codes=("STIRRUP_CLOSED",),
        parameters=(
            _param("A", "Ancho exterior", "mm", True, "Dimension exterior horizontal del estribo."),
            _param("B", "Alto exterior", "mm", True, "Dimension exterior vertical del estribo."),
            _param("P", "Patilla 135", "mm", True, "Longitud recta del gancho terminal."),
        ),
    ),
    "ACI-11": WorkshopShape(
        code="ACI-11",
        family="estribo",
        name_es="Estribo cerrado de 2 ramas con gancho de 90 grados",
        aci_scope="Cercos no sismicos o configuraciones de taller con gancho a 90 grados",
        description="Estribo perimetral cerrado de dos ramas con un gancho terminal a 90 grados.",
        geometry_notes=(
            "El cierre se realiza en un solo vertice con patilla a 90 grados.",
            "La barra debe leerse como una pieza unica de fabricacion.",
        ),
        rfem_stirrup_types=("STIRRUP_TYPE_TWO_LEGGED_CLOSED_HOOK_90",),
        rfem_shape_codes=("STIRRUP_CLOSED",),
        parameters=(
            _param("A", "Ancho exterior", "mm", True, "Dimension exterior horizontal del estribo."),
            _param("B", "Alto exterior", "mm", True, "Dimension exterior vertical del estribo."),
            _param("P", "Patilla 90", "mm", True, "Longitud recta del gancho terminal."),
        ),
    ),
    "ACI-12": WorkshopShape(
        code="ACI-12",
        family="estribo",
        name_es="Estribo abierto de 2 ramas",
        aci_scope="Estribos abiertos o marcos sin cierre completo",
        description="Estribo tipo U o abierto, con ramas principales y dobleces terminales.",
        geometry_notes=(
            "No debe representarse como contorno cerrado.",
            "Los extremos terminales dependen del tipo de patilla configurado.",
        ),
        rfem_stirrup_types=("STIRRUP_TYPE_TWO_LEGGED_OPEN",),
        parameters=(
            _param("A", "Ancho exterior", "mm", True, "Dimension exterior horizontal."),
            _param("B", "Alto exterior", "mm", True, "Dimension vertical de ramas."),
            _param("P1", "Patilla izquierda", "mm", False, "Patilla de un extremo."),
            _param("P2", "Patilla derecha", "mm", False, "Patilla del otro extremo."),
        ),
    ),
    "ACI-20": WorkshopShape(
        code="ACI-20",
        family="cruceta",
        name_es="Cruceta interior con gancho de 135 grados",
        aci_scope="Crucetas o crossties interiores de confinamiento",
        description="Barra interior de confinamiento con un tramo recto y ganchos terminales a 135 grados.",
        geometry_notes=(
            "Las patillas deben quedar claramente conectadas a la barra interior.",
            "Se usa en combinacion con estribos cerrados cuando RFEM informa crossties activos.",
        ),
        parameters=(
            _param("A", "Longitud util", "mm", True, "Tramo recto entre dobleces."),
            _param("P1", "Gancho 1", "mm", True, "Patilla del extremo inicial."),
            _param("P2", "Gancho 2", "mm", True, "Patilla del extremo final."),
        ),
    ),
}


def get_workshop_shape(code: str) -> WorkshopShape:
    if code not in CATALOGO_FORMAS:
        raise KeyError(f"Forma de taller no definida: {code}")
    return CATALOGO_FORMAS[code]


def list_workshop_shapes() -> list[WorkshopShape]:
    return [CATALOGO_FORMAS[key] for key in sorted(CATALOGO_FORMAS)]


def map_rfem_to_workshop_shape(
    *,
    shape_code: str | None,
    stirrup_type: str | None,
    hook_detail: str | None = None,
    crossties_active: bool | None = None,
) -> WorkshopShape:
    stirrup_type_clean = (stirrup_type or "").strip().upper()
    shape_code_clean = (shape_code or "").strip().upper()
    hook_detail_clean = (hook_detail or "").strip().upper()

    if stirrup_type_clean == "STIRRUP_TYPE_TWO_LEGGED_CLOSED_HOOK_135":
        return get_workshop_shape("ACI-10")
    if stirrup_type_clean == "STIRRUP_TYPE_TWO_LEGGED_CLOSED_HOOK_90":
        return get_workshop_shape("ACI-11")
    if stirrup_type_clean == "STIRRUP_TYPE_TWO_LEGGED_OPEN":
        return get_workshop_shape("ACI-12")
    if "135" in hook_detail_clean and crossties_active:
        return get_workshop_shape("ACI-20")
    if "135" in hook_detail_clean:
        return get_workshop_shape("ACI-03")
    if "90" in hook_detail_clean:
        return get_workshop_shape("ACI-02")
    if shape_code_clean == "STIRRUP_CLOSED":
        return get_workshop_shape("ACI-10")
    if shape_code_clean in {"STRAIGHT", "LONGITUDINAL"}:
        return get_workshop_shape("ACI-01")
    return get_workshop_shape("ACI-01")

# Rebar Schedule

Aplicacion Python para transformar resultados de dimensionamiento de armaduras provenientes de RFEM 6 en:

- planillas de corte y doblado
- archivos compatibles con Excel
- archivos DXF simples para AutoCAD

## Estado actual

Esta primera base deja preparado el flujo de trabajo y el modelo de datos. Hoy soporta:

- lectura de un snapshot JSON normalizado
- consolidacion de barras y superficies en una planilla unica
- exportacion a JSON
- exportacion a SpreadsheetML 2003 (`.xml`) compatible con Excel sin dependencias extra
- exportacion a `.xlsx` si `openpyxl` esta instalado
- exportacion a DXF ASCII simple para abrir en AutoCAD
- catalogo base de formas de taller ACI en espanol para clasificar la armadura leida desde RFEM

La lectura directa del armado calculado desde RFEM 6 via `dlubal.api` queda iniciada en el adaptador, pero depende de confirmar los objetos y tablas exactas expuestas por la API para resultados de hormigon armado.

## Estructura

```text
apps/rebar_schedule/
|-- examples/
|   `-- sample_rfem_snapshot.json
|-- src/
|   `-- rebar_schedule/
|       |-- adapters/
|       |-- cli/
|       |-- domain/
|       |-- exporters/
|       `-- services/
|-- tests/
|-- pyproject.toml
`-- README.md
```

## Instalacion

Desde `D:\EDIFICIOS\midee-tools\apps\rebar_schedule`:

```bash
python -m pip install -e .[dev]
```

Para exportar a `.xlsx`:

```bash
python -m pip install -e .[excel]
```

Para trabajar con RFEM 6:

```bash
python -m pip install -e .[rfem]
```

## Uso

```bash
python -m rebar_schedule --snapshot examples/sample_rfem_snapshot.json --json-output output/schedule.json --excel-output output/schedule.xml --dxf-output output/schedule.dxf
```

## Formato esperado del snapshot

```json
{
  "project_name": "Losa PB",
  "items": [
    {
      "source_type": "member",
      "source_id": 101,
      "host_label": "Viga V1",
      "bar_mark": "V1-01",
      "diameter_mm": 16,
      "steel_grade": "ADN 420",
      "shape_code": "STRAIGHT",
      "count": 4,
      "cut_length_mm": 5820,
      "segments_mm": [5820],
      "notes": "Inferior continuo"
    }
  ]
}
```

## Siguientes pasos recomendados

1. Completar el mapeo entre configuraciones RFEM y el catalogo de formas de taller ACI.
2. Incorporar cotas parametricas reales por forma (A, B, P, radios y diametros de doblado).
3. Generar bloques CAD a partir del catalogo, no desde dibujos aproximados.
4. Extender la lectura a armaduras de superficies y mallados.

## Catalogo de formas de taller ACI

La aplicacion ya incluye un catalogo base en:

`src/rebar_schedule/domain/shape_catalog.py`

Objetivo del catalogo:

- separar la geometria de taller de los datos crudos de RFEM
- tener codigos de forma estables para DXF, Excel y validaciones
- mapear tipos de estribo y ganchos de RFEM hacia formas entendibles para taller

Formas iniciales incluidas:

- `ACI-01`: barra recta
- `ACI-02`: barra con una patilla a 90 grados
- `ACI-03`: barra con una patilla a 135 grados
- `ACI-04`: barra con dos patillas a 90 grados
- `ACI-05`: barra con dos patillas a 135 grados
- `ACI-10`: estribo cerrado de 2 ramas con gancho de 135 grados
- `ACI-11`: estribo cerrado de 2 ramas con gancho de 90 grados
- `ACI-12`: estribo abierto de 2 ramas
- `ACI-20`: cruceta interior con gancho de 135 grados

La planilla construida ahora guarda, por cada fila, la clasificacion de taller:

- `forma_taller_codigo`
- `forma_taller`
- `familia_forma_taller`

Ese sera el punto de apoyo para la siguiente etapa: generar formas CAD geometricamente correctas a partir de un codigo de taller definido y no desde heuristicas visuales.

## Analisis de DXF nativo de RFEM

Para estudiar la geometria real que exporta RFEM, se agrego un analizador local de DXF nativo:

`src/rebar_schedule/services/native_dxf_analysis.py`

Tambien hay un runner simple:

```bash
python tools/analyze_native_rfem_dxf.py build/member-58.dxf build/member-58.analysis.json
```

Este analizador:

- lee entidades `LINE`, `ARC` y `POLYLINE`
- resume capas y tipos de entidad
- detecta una ventana candidata de seccion
- deja una base objetiva para calibrar la familia `ACI-10` con datos exportados por RFEM

## Extraccion de patrones nativos

Tambien se agrego un extractor de subgeometrias desde el DXF nativo de RFEM:

`src/rebar_schedule/services/native_dxf_patterns.py`

Runner:

```bash
python tools/extract_native_rfem_patterns.py build/member-58.dxf build/member-58.analysis.json build/member-58.patterns.json
```

Salida esperada:

- `cerco_principal`
- `cruceta_horizontal`
- `cruceta_vertical`

Cada pieza queda guardada en coordenadas locales, lista para usarse como patron reutilizable de la familia `ACI-10`.

## Arquitectura objetivo de planillas

Se agrego una hoja de ruta de diseno para ordenar la evolucion del proyecto:

`docs/arquitectura_planillas_rebar.md`

Ese documento fija:

- el modelo interno de posicion de armadura
- la separacion entre datos RFEM, catalogo ACI y geometria de taller
- el uso de RFEM nativo como patron geometrico para formas complejas
- la referencia funcional tomada de Revit como benchmark de planillas

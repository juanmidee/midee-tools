# Catalogo de Formas de Taller ACI

Este catalogo define la capa intermedia entre:

- los datos crudos que provienen de RFEM
- la geometria de taller que luego se dibujara en Excel y AutoCAD

La idea es no dibujar mas desde heuristicas visuales. Primero se clasifica cada armadura contra una forma de taller estable y luego se genera la geometria correspondiente.

## Principio de trabajo

1. RFEM informa tipo de barra, tipo de estribo, material, separacion y dimensiones generales.
2. `shape_catalog.py` traduce esa informacion a una forma de taller ACI.
3. El exportador CAD debera dibujar exclusivamente a partir del codigo de forma y sus parametros.

## Formas base

| Codigo | Familia | Nombre | Uso base |
| --- | --- | --- | --- |
| `ACI-01` | barra | Barra recta | Barras longitudinales o de reparto sin patillas |
| `ACI-02` | barra | Barra con una patilla a 90 grados | Anclajes simples con un gancho |
| `ACI-03` | barra | Barra con una patilla a 135 grados | Ganchos especiales a 135 grados |
| `ACI-04` | barra | Barra con dos patillas a 90 grados | Barras en U o ancladas en ambos extremos |
| `ACI-05` | barra | Barra con dos patillas a 135 grados | Barras con ambos extremos enganchados |
| `ACI-10` | estribo | Estribo cerrado de 2 ramas con gancho de 135 grados | Cercos sismicos o de confinamiento |
| `ACI-11` | estribo | Estribo cerrado de 2 ramas con gancho de 90 grados | Cercos no sismicos |
| `ACI-12` | estribo | Estribo abierto de 2 ramas | Estribos tipo U o marcos abiertos |
| `ACI-20` | cruceta | Cruceta interior con gancho de 135 grados | Crossties interiores |

## Mapeo inicial RFEM -> taller

| Dato RFEM | Forma de taller |
| --- | --- |
| `shape_code=STRAIGHT` | `ACI-01` |
| `shape_code=LONGITUDINAL` | `ACI-01` |
| `stirrup_type=STIRRUP_TYPE_TWO_LEGGED_CLOSED_HOOK_135` | `ACI-10` |
| `stirrup_type=STIRRUP_TYPE_TWO_LEGGED_CLOSED_HOOK_90` | `ACI-11` |
| `stirrup_type=STIRRUP_TYPE_TWO_LEGGED_OPEN` | `ACI-12` |
| `hook_detail` con `90` | `ACI-02` |
| `hook_detail` con `135` | `ACI-03` |
| `hook_detail` con `135` y `crossties_active=true` | `ACI-20` |

## Parametros geometricos esperados

Cada forma debera terminar resolviendose con parametros de taller como:

- `L`: largo total
- `A`: ancho exterior o tramo principal
- `B`: alto exterior o tramo secundario
- `P`: patilla
- `P1`, `P2`: patillas terminales
- diametro de doblado
- radio interior de doblado

## Siguiente etapa

La siguiente etapa del proyecto ya no consiste en "dibujar parecido". Consiste en:

1. definir la trayectoria geometrica exacta de cada codigo
2. parametrizar sus cotas
3. usar esa geometria en DXF y Excel
4. validar forma por forma contra RFEM y contra criterio de taller

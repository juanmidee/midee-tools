# Arquitectura Objetivo de Planillas de Armadura

## Objetivo

Definir una arquitectura clara para que `rebar_schedule` evolucione desde un exportador de datos hacia una aplicacion capaz de generar:

- planillas de armadura entendibles para taller
- computo de acero por posicion y por diametro
- croquis de doblado geometricamente correctos
- hojas DXF y Excel consistentes entre si

La referencia funcional de calidad es la experiencia de planillas de armadura de Revit, pero la fuente de datos y geometria del proyecto sigue siendo RFEM 6.

## Principios

1. RFEM es la fuente de verdad de cantidades, materiales, diametros, separaciones y configuracion de armaduras.
2. El catalogo ACI es la fuente de verdad de las familias de forma de taller.
3. El DXF nativo de RFEM se usa como referencia geometrica para calibrar o reutilizar formas complejas.
4. Excel y DXF deben salir del mismo modelo interno de posicion de armadura.
5. No se debe dibujar geometria de taller desde heuristicas visuales aisladas.

## Modelo conceptual

### 1. Posicion de armadura

Unidad minima de planilla.

Debe contener al menos:

- identificador de elemento
- numero de posicion
- diametro
- cantidad
- longitud unitaria
- longitud total
- peso unitario
- peso total
- material de armadura
- forma de taller
- parametros geometricos de la forma

### 2. Forma de taller

Representa una familia estable de doblado.

Campos base:

- `forma_taller_codigo`
- `familia_forma_taller`
- `descripcion`
- `parametros_requeridos`
- `reglas_normativas`

Ejemplos:

- `ACI-01`: barra recta
- `ACI-03`: barra con patilla a 135 grados
- `ACI-10`: estribo cerrado de dos ramas con gancho 135 grados
- `ACI-20`: cruceta interior con gancho 135 grados

### 3. Parametros geometricos

Cada forma debe resolverse mediante parametros explicitamente calculados.

Ejemplos:

- `A`, `B`, `C`
- radios de doblado
- longitud de gancho
- angulo de gancho
- recubrimiento
- ancho y alto utiles
- diametro de barra

## Pipeline objetivo

### Etapa 1. Extraccion desde RFEM

Salida:

- datos de armadura longitudinal
- datos de armadura transversal
- material real
- tipo de estribo
- separacion
- seccion
- recubrimiento

### Etapa 2. Clasificacion a catalogo ACI

Mapeo:

- RFEM `hook_detail` -> familia de barra doblada
- RFEM `stirrup_type` -> familia de estribo
- RFEM `crossties_active` -> inclusion de crucetas

Salida:

- `forma_taller_codigo`
- parametros geometricos minimos para esa forma

### Etapa 3. Resolucion geometrica

Dos modos:

- `parametrico puro`: para formas simples
- `calibrado por patron RFEM`: para formas complejas como `ACI-10`

Salida:

- primitivas geometricas limpias
- etiquetas de cota
- texto normativo minimo

### Etapa 4. Exportacion

#### Excel

Cada fila de planilla debe expresar:

- posicion
- diametro
- cantidad
- forma
- dimensiones
- largo unitario
- largo total
- peso

#### DXF

Cada hoja debe expresar:

- marco A4 vertical
- resumen de armadura en primera hoja
- hoja por elemento o grupo
- tabla de posiciones
- croquis de doblado por posicion
- layers separados para impresion

## Benchmark funcional tomado de Revit

Aspectos a imitar:

- una fila representa una posicion clara
- la celda de forma muestra un bending detail entendible
- las dimensiones salen desde parametros, no desde dibujo manual
- las planillas y el computo nacen del mismo modelo interno

Aspectos que no se deben copiar literalmente:

- formato propietario de familias de Revit
- reglas internas no documentadas de su motor grafico

## Estrategia recomendada por familias

### Formas simples

Resolver primero con geometria parametrica propia:

- `ACI-01`
- `ACI-02`
- `ACI-03`
- `ACI-04`
- `ACI-05`

### Formas complejas

Resolver con patron nativo RFEM + parametrizacion:

- `ACI-10`
- `ACI-11`
- `ACI-20`

## Hoja de ruta inmediata

1. Consumir `member-58.patterns.json` desde el generador de geometria.
2. Reemplazar el dibujo heuristico de `ACI-10` por un dibujo basado en patron nativo RFEM.
3. Separar visualmente en la celda:
   - cerco principal
   - cruceta horizontal
   - cruceta vertical
4. Unificar el mismo modelo para DXF y Excel.
5. Extender el mismo esquema a barras longitudinales con patillas.

## Criterio de aceptacion

La salida sera aceptable cuando:

- el croquis se reconozca de inmediato como forma real de taller
- las patillas y ganchos sean geometricamente coherentes
- el material salga desde RFEM
- el computo coincida con RFEM
- el DXF pueda imprimirse por layers
- Excel y DXF representen exactamente la misma posicion

# PT Losses

Herramienta Python modular para calcular perdidas de postensado y convertir los resultados a deformaciones axiales equivalentes utilizables en RFEM 6.

## Objetivo

El proyecto calcula:

- tension maxima admisible de tesado
- tension inicial `T = 0`
- tension final `T = infinito`
- perdidas inmediatas y diferidas como coeficientes adimensionales
- fuerzas por tendon y fuerzas totales
- deformaciones equivalentes para RFEM 6 en porcentaje y por mil

La herramienta funciona sin conexion a RFEM, a partir de archivos `JSON` o `YAML`, y deja preparada una capa de adaptacion para integracion futura.

## Estructura

```text
apps/pt_losses/
├── examples/
├── src/
│   └── pt_losses/
│       ├── adapters/
│       ├── cli/
│       ├── domain/
│       └── services/
├── tests/
├── pyproject.toml
└── README.md
```

## Instalacion

Desde `D:\EDIFICIOS\midee-tools\apps\pt_losses`:

```bash
python -m pip install -e .[dev]
```

## Uso

Ejecutar con el ejemplo incluido:

```bash
python -m pt_losses --input examples/sample_input.json
```

Tambien acepta YAML:

```bash
python -m pt_losses --input examples/sample_input.yaml
```

Para exportar la salida a un archivo:

```bash
python -m pt_losses --input examples/sample_input.json --output result.json
```

## Entradas esperadas

El archivo de entrada debe incluir como minimo:

- `Ep`
- `Ec`
- `fpk`
- `fp01k`
- `fc`
- `Ap`
- `n_tendons`
- `tendon_length`
- `theta_total`
- `eccentricity`
- `mu_tesado`
- `mu_fric`
- `k_wobble`
- `anchorage_slip_mm`
- `concrete_stress_at_tendon`
- `creep_coeff`
- `shrinkage_strain`
- `relaxation_loss_ratio`

## Formulas implementadas

El modelo actual implementa las siguientes expresiones:

```text
sigma_max = min(0.80 * fpk, 0.94 * fp01k)
sigma_0 = mu_tesado * sigma_max

eta_fr = 1 - exp(-(mu_fric * theta_total + k_wobble * tendon_length))

delta_sigma_anc = Ep * (anchorage_slip_mm / tendon_length_mm)
eta_anc = delta_sigma_anc / sigma_0

delta_sigma_el = Ep * (concrete_stress_at_tendon / Ec)
eta_el = delta_sigma_el / sigma_0

delta_sigma_flu = Ep * creep_coeff * (concrete_stress_at_tendon / Ec)
eta_flu = delta_sigma_flu / sigma_0

delta_sigma_ret = Ep * shrinkage_strain
eta_ret = delta_sigma_ret / sigma_0

eta_rel = relaxation_loss_ratio

eta_total = min(eta_fr + eta_anc + eta_el + eta_rel + eta_flu + eta_ret, 0.99)

sigma_inf = sigma_0 * (1 - eta_total)

T0_percent = -(sigma_0 / Ep) * 100
Tinf_percent = -(sigma_inf / Ep) * 100
```

Interpretacion de cada formula:

- `sigma_max = min(0.80 * fpk, 0.94 * fp01k)`
  Esta expresion busca definir la tension maxima utilizable de tesado del acero de postensado. Se toma el menor valor entre dos limites habituales de seguridad para evitar que el tesado supere un nivel excesivo respecto de la resistencia caracteristica del acero.

- `sigma_0 = mu_tesado * sigma_max`
  Esta formula obtiene la tension inicial realmente aplicada en el tendon en el instante del tesado. El factor `mu_tesado` permite representar que, en la practica, no siempre se tesa exactamente al maximo utilizable, sino a una fraccion de ese valor.

- `eta_fr = 1 - exp(-(mu_fric * theta_total + k_wobble * tendon_length))`
  Esta expresion representa la perdida por rozamiento a lo largo del tendon. Combina el efecto de la curvatura total del trazado y el efecto de desviaciones accidentales o wobble. El resultado `eta_fr` es adimensional y expresa que parte de la tension inicial se pierde por friccion.

- `delta_sigma_anc = Ep * (anchorage_slip_mm / tendon_length_mm)`
  Esta formula calcula la caida de tension debida al asiento o deslizamiento del anclaje. Si las cu?as se acomodan y el tendon retrocede una peque?a longitud, se genera una disminucion de deformacion y por lo tanto una disminucion de tension proporcional al modulo elastico del acero.

- `eta_anc = delta_sigma_anc / sigma_0`
  Aqui la perdida por anclaje se transforma en coeficiente adimensional. Esto permite sumar esta perdida con las demas en una misma escala relativa respecto de la tension inicial de tesado.

- `delta_sigma_el = Ep * (concrete_stress_at_tendon / Ec)`
  Esta expresion calcula la perdida por acortamiento elastico del hormigon. Cuando el hormigon se comprime, el tendon acompana esa deformacion y pierde parte de su tension. La formula vincula la deformacion del hormigon con la respuesta elastica del acero.

- `eta_el = delta_sigma_el / sigma_0`
  Esta formula convierte la perdida por acortamiento elastico en un coeficiente relativo respecto de la tension inicial del tendon, para poder integrarla con el resto de las perdidas.

- `delta_sigma_flu = Ep * creep_coeff * (concrete_stress_at_tendon / Ec)`
  Esta expresion estima la perdida por fluencia del hormigon. A largo plazo, bajo una tension sostenida, el hormigon sigue deformandose y esa deformacion adicional reduce la tension del tendon. El coeficiente de fluencia amplifica la deformacion elastica inicial para representar ese efecto diferido.

- `eta_flu = delta_sigma_flu / sigma_0`
  Igual que en los casos anteriores, la perdida por fluencia se expresa como fraccion de la tension inicial para poder sumarse de forma consistente con las otras contribuciones.

- `delta_sigma_ret = Ep * shrinkage_strain`
  Esta formula representa la perdida por retraccion del hormigon. La retraccion genera una deformacion propia del elemento de hormigon que reduce la deformacion efectiva del tendon y, en consecuencia, su tension.

- `eta_ret = delta_sigma_ret / sigma_0`
  Esta expresion pasa la perdida por retraccion a formato adimensional relativo a la tension inicial del tendon.

- `eta_rel = relaxation_loss_ratio`
  Esta formula incorpora directamente la perdida por relajacion del acero. La relajacion describe la reduccion de tension en el tendon con el tiempo aun si la deformacion se mantiene aproximadamente constante.

- `eta_total = min(eta_fr + eta_anc + eta_el + eta_rel + eta_flu + eta_ret, 0.99)`
  Esta expresion suma todas las perdidas en forma de coeficientes adimensionales para obtener una perdida total simplificada. El limite superior de `0.99` evita resultados no fisicos, por ejemplo tensiones finales negativas o practicamente nulas por una suma excesiva.

- `sigma_inf = sigma_0 * (1 - eta_total)`
  Esta formula calcula la tension remanente del tendon a tiempo infinito, es decir, despues de considerar el efecto conjunto de las perdidas inmediatas y diferidas.

- `T0_percent = -(sigma_0 / Ep) * 100`
  Esta expresion convierte la tension inicial del tendon en una deformacion axial equivalente en porcentaje. El signo negativo se adopta para representar el efecto de compresion introducido por el postensado dentro del flujo de trabajo usado en RFEM.

- `Tinf_percent = -(sigma_inf / Ep) * 100`
  Esta formula convierte la tension final a tiempo infinito en la deformacion axial equivalente que se aplicara en RFEM para el estado de largo plazo. Como `sigma_inf` ya incorpora perdidas, el valor absoluto de esta deformacion debe ser menor que el de `T0_percent`.

Notas de unidades:

- `Ep`, `Ec`, `fpk`, `fp01k`, `fc`, `sigma_*` en MPa
- `Ap` en mm2
- `tendon_length` en m
- `anchorage_slip_mm` en mm
- `theta_total` en rad
- `shrinkage_strain` como deformacion adimensional

## Salidas

La herramienta devuelve, entre otros, los siguientes campos:

- `sigma_max_MPa`
- `sigma_0_MPa`
- `sigma_inf_MPa`
- `eta_fr`
- `eta_anc`
- `eta_el`
- `eta_rel`
- `eta_flu`
- `eta_ret`
- `eta_total`
- `T0_percent`
- `Tinf_percent`
- `T0_permille`
- `Tinf_permille`
- `initial_force_per_tendon_kN`
- `initial_force_total_kN`
- `final_force_per_tendon_kN`
- `final_force_total_kN`

## Limitaciones actuales

- El modelo usa una suma directa de perdidas adimensionales.
- No contempla variacion espacial de la fuerza a lo largo del tendon.
- No incorpora etapas constructivas ni secuencias de tesado.
- No consulta todavia datos reales de RFEM 6.
- La perdida total se limita a `0.99` para evitar resultados no fisicos.

## Integracion futura con RFEM 6

La carpeta `adapters/` incluye un stub que define una interfaz de adaptacion. Los siguientes pasos recomendados para conectarlo con RFEM 6 son:

1. Leer geometria y materiales desde el modelo RFEM.
2. Mapear tendones del modelo a `LossesInput`.
3. Calcular `T0_percent` y `Tinf_percent`.
4. Crear o actualizar las cargas de deformacion axial mediante la API de RFEM 6.
5. Persistir trazabilidad de resultados y version de formulas aplicadas.

## Desarrollo

Ejecutar tests:

```bash
pytest
```

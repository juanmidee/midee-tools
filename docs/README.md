# MIDEE #3 Wind Tools

Aplicación profesional para cálculo de presión dinámica de viento.

Versión actual: 1.1

## Funcionalidades actuales

- Cálculo de presión dinámica: q = 0.5 · ρ · V²
- Conversión automática a:
  - Pa
  - N/m²
  - kN/m²
  - kg/m²
- Escala dinámica visual
- Exportación a CSV
- Exportación a PDF con encabezado institucional
- Sistema de activación mediante código generado desde plataforma MIDEE

## Activación

El código se genera en la plataforma web utilizando:

SHA256(email + ACTIVATION_SECRET)

Se utilizan los primeros 16 caracteres en mayúsculas.

La licencia se almacena en:

APPDATA/MIDEE_3/license.json

## Ejecución en desarrollo

```bash
python main.py

pyinstaller MIDEE_3_Wind_Tools.spec

# Arquitectura

## Entry Point
main.py

## UI Base
core/ui_base/base_window.py

Responsable de:
- Layout
- Sidebar
- Sistema de activación
- Módulo presión dinámica
- Exportaciones

## Branding
core/branding/theme.py

## Exportaciones
- CSV: método interno export_to_csv()
- PDF: método export_to_pdf() (ReportLab)

## Activación

1. Se verifica existencia de license.json
2. Si no existe → modal de activación
3. Código validado mediante:
   sha256(email + ACTIVATION_SECRET)
4. Se almacena licencia local en APPDATA/MIDEE_3

## Estructura final recomendada

midee-tools/
│
├── main.py
├── MIDEE_3_Wind_Tools.spec
├── README.md
├── CHANGELOG.md
├── ARCHITECTURE.md
├── SECURITY.md
│
├── apps/
├── core/
├── build/
└── dist/

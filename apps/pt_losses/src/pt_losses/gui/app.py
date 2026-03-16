from __future__ import annotations

import csv
import json
import os
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pt_losses.adapters.rfem_client import Rfem6ApiAdapter
from pt_losses.domain.models import LossesInput
from pt_losses.services.calculator import calculate_losses
from pt_losses.services.io import load_input_file, write_result_file
from pt_losses.services.rfem_conversion import build_rfem_load_payload

DEFAULT_INPUT: dict[str, float] = {
    "Ep": 195000.0,
    "Ec": 34000.0,
    "fpk": 1860.0,
    "fp01k": 1640.0,
    "fc": 45.0,
    "Ap": 150.0,
    "n_tendons": 12,
    "tendon_length": 32.5,
    "theta_total": 0.18,
    "eccentricity": 0.22,
    "mu_tesado": 0.75,
    "mu_fric": 0.19,
    "k_wobble": 0.0015,
    "anchorage_slip_mm": 6.0,
    "concrete_stress_at_tendon": 9.5,
    "creep_coeff": 1.8,
    "shrinkage_strain": 0.0002,
    "relaxation_loss_ratio": 0.025,
}

FIELD_LABELS: list[tuple[str, str]] = [
    ("Ep", "Ep [MPa]"),
    ("Ec", "Ec [MPa]"),
    ("fpk", "fpk [MPa]"),
    ("fp01k", "fp01k [MPa]"),
    ("fc", "fc [MPa]"),
    ("Ap", "Ap [mm2]"),
    ("n_tendons", "Cantidad de tendones"),
    ("tendon_length", "Longitud del tendón [m]"),
    ("theta_total", "Theta total [rad]"),
    ("eccentricity", "Excentricidad [m]"),
    ("mu_tesado", "Factor de tesado"),
    ("mu_fric", "Coeficiente de rozamiento"),
    ("k_wobble", "Coeficiente wobble"),
    ("anchorage_slip_mm", "Deslizamiento de anclaje [mm]"),
    ("concrete_stress_at_tendon", "Tensión del hormigón en tendón [MPa]"),
    ("creep_coeff", "Coeficiente de fluencia"),
    ("shrinkage_strain", "Retracción unitaria"),
    ("relaxation_loss_ratio", "Pérdida por relajación"),
]

AUTOLOAD_KEYS = [
    "Ep",
    "Ec",
    "fpk",
    "fp01k",
    "fc",
    "Ap",
    "n_tendons",
    "tendon_length",
    "mu_fric",
    "k_wobble",
    "relaxation_loss_ratio",
]

LOSS_DESCRIPTIONS = [
    ("eta_fr", "Rozamiento"),
    ("eta_anc", "Anclaje"),
    ("eta_el", "Acortamiento elástico"),
    ("eta_rel", "Relajación del acero"),
    ("eta_flu", "Fluencia del hormigón"),
    ("eta_ret", "Retracción del hormigón"),
    ("eta_total", "Pérdida total"),
]

COLORS = {
    "bg": "#e8edf3",
    "panel": "#dbe2ea",
    "card": "#f7f9fc",
    "card_alt": "#eef3f8",
    "primary": "#14273d",
    "secondary": "#4a5f77",
    "accent": "#2d4159",
}


class PtLossesApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("dlubal.com.ar | Pérdidas de postensado para RFEM 6")
        self.root.geometry("1540x930")
        self.root.minsize(1340, 840)
        self.root.configure(bg=COLORS["bg"])

        self.variables: dict[str, tk.StringVar] = {
            key: tk.StringVar(value=str(value)) for key, value in DEFAULT_INPUT.items()
        }
        self.output_path_var = tk.StringVar(value="Sin archivo cargado")
        self.result_payload: dict[str, object] | None = None
        self.current_result = None
        self.rfem_model_snapshot: dict[str, object] | None = None

        self.rfem_model_var = tk.StringVar()
        self.rfem_model_name_var = tk.StringVar(value="Ningún modelo seleccionado.")
        self.rfem_members_var = tk.StringVar(value="")
        self.rfem_member_count_var = tk.StringVar(value="-")
        self.rfem_cordones_count_var = tk.StringVar(value="-")
        self.rfem_api_key_var = tk.StringVar(value="")
        self.api_dialog: tk.Toplevel | None = None
        self.api_visibility_var = tk.BooleanVar(value=False)
        self.rfem_port_var = tk.StringVar(value="9000")
        self.rfem_unit_var = tk.StringVar(value="adimensional")
        self.rfem_scale_var = tk.StringVar(value="1.0")
        self.rfem_status_var = tk.StringVar(value="RFEM aún no conectado desde la interfaz.")
        self.logo_image: tk.PhotoImage | None = None

        self._load_settings()
        self._configure_style()
        self._build_menu()
        self._build_layout()
        self._render_welcome_state()
        self.root.bind("<F1>", self._handle_f1_help)
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Panel.TFrame", background=COLORS["bg"])
        style.configure("PanelInner.TFrame", background=COLORS["panel"])
        style.configure("Card.TFrame", background=COLORS["card"], relief="flat")
        style.configure("Headline.TLabel", background=COLORS["bg"], foreground=COLORS["primary"], font=("Segoe UI", 24, "bold"))
        style.configure("Subhead.TLabel", background=COLORS["bg"], foreground=COLORS["accent"], font=("Segoe UI", 11, "bold"))
        style.configure("PanelTitle.TLabel", background=COLORS["bg"], foreground=COLORS["primary"], font=("Segoe UI", 12, "bold"))
        style.configure("Field.TLabel", background=COLORS["card"], foreground=COLORS["primary"], font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background=COLORS["card"], foreground=COLORS["accent"], font=("Segoe UI", 10, "bold"))
        style.configure("Value.TLabel", background=COLORS["card"], foreground=COLORS["primary"], font=("Segoe UI", 15, "bold"))
        style.configure("Body.TLabel", background=COLORS["bg"], foreground=COLORS["secondary"], font=("Segoe UI", 10))
        style.configure("CardBody.TLabel", background=COLORS["card"], foreground=COLORS["secondary"], font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("PrimaryAction.TButton", font=("Segoe UI", 12, "bold"))
        style.configure("GuiNotebook.TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("GuiNotebook.TNotebook.Tab", padding=(16, 8), font=("Segoe UI", 10, "bold"))

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)
        archivo_menu = tk.Menu(menu_bar, tearoff=False)
        archivo_menu.add_command(label="Nuevo cálculo", command=self.start_new_calculation)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Salir", command=self._handle_close)
        menu_bar.add_cascade(label="Archivo", menu=archivo_menu)

        opciones_menu = tk.Menu(menu_bar, tearoff=False)
        opciones_menu.add_command(label="Configurar API RFEM...", command=self.open_api_settings_dialog)
        opciones_menu.add_separator()
        opciones_menu.add_command(label="Autocompletar RFEM", command=self.autofill_rfem_defaults)
        menu_bar.add_cascade(label="Opciones", menu=opciones_menu)

        ayuda_menu = tk.Menu(menu_bar, tearoff=False)
        ayuda_menu.add_command(label="Ayuda", command=self.open_help_dialog)
        ayuda_menu.add_command(label="Acerca de", command=self.open_about_dialog)
        menu_bar.add_cascade(label="Ayuda", menu=ayuda_menu)
        self.root.config(menu=menu_bar)

    def open_api_settings_dialog(self) -> None:
        if self.api_dialog is not None and self.api_dialog.winfo_exists():
            self.api_dialog.deiconify()
            self.api_dialog.lift()
            self.api_dialog.focus_force()
            return

        dialog_value_var = tk.StringVar(value=self.rfem_api_key_var.get())
        dialog = tk.Toplevel(self.root)
        dialog.title("Opciones | API RFEM")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.configure(bg=COLORS["bg"])
        dialog.grab_set()
        self.api_dialog = dialog

        frame = ttk.Frame(dialog, style="PanelInner.TFrame", padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Configuración de API RFEM", style="PanelTitle.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(
            frame,
            text="La API key queda guardada localmente hasta que la cambies. El campo se muestra oculto para no exponerlo en la presentación.",
            style="Body.TLabel",
            wraplength=420,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 12))

        ttk.Label(frame, text="API key o alias", style="Body.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=6)
        api_entry = ttk.Entry(frame, textvariable=dialog_value_var, width=42, show="*")
        api_entry.grid(row=2, column=1, sticky="ew", pady=6)

        def toggle_visibility() -> None:
            api_entry.configure(show="" if self.api_visibility_var.get() else "*")

        def close_dialog() -> None:
            if self.api_dialog is not None and self.api_dialog.winfo_exists():
                self.api_dialog.grab_release()
                self.api_dialog.destroy()
            self.api_dialog = None
            self.api_visibility_var.set(False)

        def save_dialog() -> None:
            self.rfem_api_key_var.set(dialog_value_var.get().strip())
            self._save_settings()
            self.rfem_status_var.set("API RFEM actualizada y guardada localmente.")
            close_dialog()

        ttk.Checkbutton(
            frame,
            text="Mostrar",
            variable=self.api_visibility_var,
            command=toggle_visibility,
        ).grid(row=2, column=2, sticky="w", padx=(10, 0), pady=6)

        ttk.Button(frame, text="Guardar", style="Accent.TButton", command=save_dialog).grid(
            row=3, column=1, sticky="e", pady=(14, 0)
        )
        ttk.Button(frame, text="Cancelar", command=close_dialog).grid(
            row=3, column=2, sticky="e", padx=(10, 0), pady=(14, 0)
        )

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)
        api_entry.focus_set()

    def open_help_dialog(self) -> None:
        self._open_manual_html()

    def open_about_dialog(self) -> None:
        about_text = "\n".join(
            [
                "Pérdidas de postensado para RFEM 6",
                "dlubal.com.ar",
                "",
                "Herramienta para calcular pérdidas de postensado y convertirlas en deformaciones axiales equivalentes para RFEM 6.",
                "",
                "Deslinde de responsabilidades:",
                "Los valores obtenidos con esta aplicación deben ser revisados, verificados y validados por un ingeniero estructural competente antes de su uso en proyecto, documentación o construcción.",
                "La herramienta no reemplaza el criterio profesional ni la verificación normativa correspondiente.",
            ]
        )
        messagebox.showinfo("Acerca de", about_text)

    def _handle_f1_help(self, _event: tk.Event | None = None) -> str:
        self._open_manual_html()
        return "break"

    def _build_layout(self) -> None:
        header = ttk.Frame(self.root, style="Panel.TFrame", padding=(24, 18))
        header.pack(fill="x")
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        title_wrap = ttk.Frame(header, style="Panel.TFrame")
        title_wrap.grid(row=0, column=0, sticky="w")

        ttk.Label(title_wrap, text="Cálculo de pérdidas de postensado", style="Headline.TLabel").pack(anchor="w")
        ttk.Label(
            title_wrap,
            text="dlubal.com.ar | Herramienta visual para T = 0, T = infinito y envío directo a RFEM 6.",
            style="Subhead.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        self.logo_header = ttk.Frame(header, style="Panel.TFrame")
        self.logo_header.grid(row=0, column=1, sticky="e")
        self._render_logo(self.logo_header, compact=True)

        body = ttk.Frame(self.root, style="Panel.TFrame", padding=(20, 0, 20, 20))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=17, minsize=760)
        body.columnconfigure(1, weight=13, minsize=560)
        body.rowconfigure(0, weight=1)

        self.left_panel = ttk.Frame(body, style="PanelInner.TFrame", padding=12)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=12)
        self.right_panel = ttk.Frame(body, style="PanelInner.TFrame", padding=16)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=12)

        self._build_input_panel()
        self._build_results_panel()

    def _build_input_panel(self) -> None:
        ttk.Label(self.left_panel, text="Panel de control", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Frame(self.left_panel, style="PanelInner.TFrame", height=6).pack(fill="x", pady=(2, 14))

        notebook = ttk.Notebook(self.left_panel, style="GuiNotebook.TNotebook")
        notebook.pack(fill="both", expand=True)

        calc_tab = ttk.Frame(notebook, style="PanelInner.TFrame", padding=12)
        rfem_tab = ttk.Frame(notebook, style="PanelInner.TFrame", padding=12)
        notebook.add(rfem_tab, text="RFEM 6")
        notebook.add(calc_tab, text="Cálculo")
        notebook.select(rfem_tab)

        self._build_calculation_tab(calc_tab)
        self._build_rfem_tab(rfem_tab)

    def _build_calculation_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Datos de entrada", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(
            parent,
            text="Edita los valores del caso, carga un archivo JSON/YAML o usa el ejemplo base.",
            style="Body.TLabel",
            wraplength=500,
        ).pack(anchor="w", pady=(2, 12))

        canvas_container = ttk.Frame(parent, style="PanelInner.TFrame")
        canvas_container.pack(fill="both", expand=True)
        canvas_container.columnconfigure(0, weight=1)
        canvas_container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(canvas_container, bg=COLORS["panel"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
        form_frame = ttk.Frame(canvas, style="PanelInner.TFrame")
        form_frame.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=form_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(10, 0))

        for row_index, (key, label) in enumerate(FIELD_LABELS):
            ttk.Label(form_frame, text=label, style="Body.TLabel").grid(
                row=row_index,
                column=0,
                sticky="w",
                padx=(0, 16),
                pady=7,
            )
            entry = ttk.Entry(form_frame, textvariable=self.variables[key], width=26)
            entry.grid(row=row_index, column=1, sticky="ew", pady=7)

        form_frame.columnconfigure(1, weight=1)

        actions = ttk.Frame(parent, style="PanelInner.TFrame")
        actions.pack(fill="x", pady=(14, 0))
        actions.columnconfigure((0, 1, 2), weight=1)

        ttk.Button(actions, text="Calcular", command=self.calculate, style="Accent.TButton").grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(actions, text="Restablecer", command=self.reset_fields).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        ttk.Button(actions, text="Cargar archivo", command=self.load_file).grid(
            row=0, column=2, sticky="ew", padx=(8, 0)
        )

        extra_actions = ttk.Frame(parent, style="PanelInner.TFrame")
        extra_actions.pack(fill="x", pady=(10, 0))
        extra_actions.columnconfigure(0, weight=1)

        ttk.Button(extra_actions, text="Cargar ejemplo", command=self.load_sample).grid(
            row=0, column=0, sticky="ew"
        )

        ttk.Label(parent, textvariable=self.output_path_var, style="Body.TLabel", wraplength=500).pack(
            anchor="w", pady=(12, 0)
        )

    def _build_rfem_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Integración con RFEM 6", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(
            parent,
            text="Carga el modelo, detecta automáticamente los tendones y completa los datos principales del acero.",
            style="Body.TLabel",
            wraplength=500,
        ).pack(anchor="w", pady=(2, 12))
        canvas_container = ttk.Frame(parent, style="PanelInner.TFrame")
        canvas_container.pack(fill="both", expand=True)
        canvas_container.columnconfigure(0, weight=1)
        canvas_container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(canvas_container, bg=COLORS["panel"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
        card = ttk.Frame(canvas, style="Card.TFrame", padding=16)
        card.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=card, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(canvas_window, width=event.width))
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(10, 0))

        card.columnconfigure(1, weight=1)
        card.columnconfigure(2, weight=0)

        ttk.Button(
            card,
            text="LEER MODELO DE RFEM 6",
            style="PrimaryAction.TButton",
            command=self.select_and_load_rfem_model,
        ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 14))

        ttk.Label(card, text="Modelo cargado", style="Field.TLabel").grid(row=1, column=0, sticky="nw", pady=7, padx=(0, 12))
        ttk.Label(
            card,
            textvariable=self.rfem_model_name_var,
            style="CardBody.TLabel",
            wraplength=560,
            justify="left",
        ).grid(row=1, column=1, columnspan=2, sticky="w", pady=7)

        self._add_rfem_row(card, 2, "IDs de members tendón", self.rfem_members_var)
        self._add_rfem_row(card, 3, "Cantidad de members", self.rfem_member_count_var)
        self._add_rfem_row(card, 4, "Cantidad de cordones", self.rfem_cordones_count_var)
        self._add_rfem_row(card, 5, "Puerto", self.rfem_port_var)
        self._add_rfem_row(card, 6, "Factor escala", self.rfem_scale_var)

        ttk.Label(card, text="Unidad RFEM", style="Field.TLabel").grid(row=7, column=0, sticky="w", pady=7, padx=(0, 12))
        unit_combo = ttk.Combobox(
            card,
            textvariable=self.rfem_unit_var,
            values=["adimensional", "percent"],
            state="readonly",
            width=20,
        )
        unit_combo.grid(row=7, column=1, sticky="ew", pady=7)

        hints = ttk.Frame(card, style="Card.TFrame")
        hints.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(10, 10))
        hints.columnconfigure(0, weight=1)
        ttk.Label(
            hints,
            text="Flujo recomendado: leer el modelo de RFEM 6, revisar o completar datos de cálculo y después aplicar en RFEM.",
            style="CardBody.TLabel",
            wraplength=560,
        ).grid(row=0, column=0, sticky="w")

        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        buttons.columnconfigure((0, 1), weight=1)
        buttons.columnconfigure((2, 3), weight=1)

        ttk.Button(buttons, text="Probar conexión", command=self.test_rfem_connection).grid(
            row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 8)
        )
        ttk.Button(buttons, text="Volver a leer modelo", command=self.load_rfem_model_data, style="Accent.TButton").grid(
            row=0, column=1, sticky="ew", padx=8, pady=(0, 8)
        )
        ttk.Button(buttons, text="Autocompletar", command=self.autofill_rfem_defaults).grid(
            row=1, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(buttons, text="Aplicar en RFEM", command=self.apply_to_rfem, style="Accent.TButton").grid(
            row=1, column=1, sticky="ew", padx=8
        )

        ttk.Label(card, textvariable=self.rfem_status_var, style="CardBody.TLabel", wraplength=500).grid(
            row=12, column=0, columnspan=3, sticky="w", pady=(14, 0)
        )

    def _add_rfem_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
    ) -> None:
        ttk.Label(parent, text=label, style="Field.TLabel").grid(row=row, column=0, sticky="w", pady=7, padx=(0, 12))
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=7)

    def _build_results_panel(self) -> None:
        top = ttk.Frame(self.right_panel, style="PanelInner.TFrame")
        top.pack(fill="x")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=0)

        intro = ttk.Frame(top, style="PanelInner.TFrame")
        intro.grid(row=0, column=0, sticky="w")
        ttk.Label(intro, text="Resultados", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(
            intro,
            text="Tensiones, fuerzas, pérdidas, deformaciones equivalentes y estado del envío a RFEM.",
            style="Body.TLabel",
            wraplength=560,
        ).pack(anchor="w", pady=(2, 16))

        ttk.Button(
            top,
            text="Exportar CSV",
            style="Accent.TButton",
            command=self.export_csv,
        ).grid(row=0, column=1, sticky="ne", padx=(16, 0), pady=(0, 8))


        ttk.Label(self.right_panel, text="Datos técnicos", style="Subhead.TLabel").pack(anchor="w", pady=(0, 10))

        self.hero_frame = ttk.Frame(self.right_panel, style="PanelInner.TFrame")
        self.hero_frame.pack(fill="x")
        self.hero_frame.columnconfigure((0, 1), weight=1)
        self.hero_frame.rowconfigure((0, 1), weight=1)

        self.cards: dict[str, ttk.Label] = {}
        for index, title in enumerate(["Tensión inicial", "Tensión final", "T0 para RFEM", "Tinf para RFEM"]):
            card = ttk.Frame(self.hero_frame, style="Card.TFrame", padding=12)
            row = index // 2
            column = index % 2
            card.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
            ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
            value_label = ttk.Label(card, text="-", style="Value.TLabel")
            value_label.pack(anchor="w", pady=(6, 0))
            self.cards[title] = value_label

        self.tables_frame = ttk.Frame(self.right_panel, style="PanelInner.TFrame")
        self.tables_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.tables_frame.columnconfigure((0, 1), weight=1)
        self.tables_frame.rowconfigure(0, weight=1)
        self.tables_frame.rowconfigure(1, weight=1)
        self.summary_text = self._create_text_card(self.tables_frame, "Resumen ejecutivo", row=0, column=0, height=5)
        self.losses_text = self._create_text_card(self.tables_frame, "Desglose de pérdidas", row=0, column=1, height=5)
        self.rfem_text = self._create_text_card(
            self.tables_frame,
            "Lectura para RFEM 6",
            row=1,
            column=0,
            columnspan=2,
            height=6,
            scrollable=True,
        )

    def _create_text_card(
        self,
        parent: ttk.Frame,
        title: str,
        row: int,
        column: int,
        columnspan: int = 1,
        height: int = 6,
        scrollable: bool = False,
    ) -> tk.Text:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=12)
        frame.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=4, pady=4)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text=title, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        text = tk.Text(
            frame,
            height=height,
            wrap="word",
            relief="flat",
            bg=COLORS["card"],
            fg=COLORS["primary"],
            font=("Consolas", 9),
            padx=4,
            pady=4,
        )
        text.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        if scrollable:
            frame.columnconfigure(1, weight=0)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
            scrollbar.grid(row=1, column=1, sticky="ns", pady=(6, 0), padx=(8, 0))
            text.configure(yscrollcommand=scrollbar.set)
        text.configure(state="disabled")
        return text

    def _render_welcome_state(self) -> None:
        self.cards["Tensión inicial"].configure(text="-")
        self.cards["Tensión final"].configure(text="-")
        self.cards["T0 para RFEM"].configure(text="-")
        self.cards["Tinf para RFEM"].configure(text="-")
        self._write_text(self.summary_text, "Carga un archivo o edita los datos y pulsa 'Calcular' para ver el resumen del caso.")
        self._write_text(
            self.losses_text,
            "Aquí aparecerá el desglose de pérdidas para presentación, con cada contribución explicada y expresada en porcentaje.",
        )
        self._write_text(self.rfem_text, "Selecciona el modelo RFEM y pulsa 'Leer modelo RFEM' para detectar automáticamente los tendones y las propiedades del acero.")
    def reset_fields(self) -> None:
        for key, value in DEFAULT_INPUT.items():
            self.variables[key].set(str(value))
        self.rfem_model_snapshot = None
        self.rfem_member_count_var.set("-")
        self.rfem_cordones_count_var.set("-")
        self.output_path_var.set("Campos restablecidos al ejemplo base.")
        self._render_welcome_state()

    def start_new_calculation(self) -> None:
        for key, value in DEFAULT_INPUT.items():
            self.variables[key].set(str(value))
        self.result_payload = None
        self.current_result = None
        self.rfem_model_snapshot = None
        self.rfem_members_var.set("")
        self.rfem_member_count_var.set("-")
        self.rfem_cordones_count_var.set("-")
        self.rfem_model_var.set("")
        self.rfem_model_name_var.set("Ningún modelo seleccionado.")
        self.rfem_unit_var.set("adimensional")
        self.rfem_scale_var.set("1.0")
        self.rfem_status_var.set("Nuevo cálculo iniciado. Selecciona un modelo o carga un archivo para continuar.")
        self.output_path_var.set("Listo para un nuevo cálculo.")
        self._render_welcome_state()

    def autofill_rfem_defaults(self) -> None:
        if not self.rfem_model_var.get().strip():
            self.rfem_model_var.set(r"D:\01 Juan Bejar\xx Proyectos RFEM\Ejemplos\Postensado\260312-postensado-conectividad-py.rf6")
        self.rfem_model_name_var.set(Path(self.rfem_model_var.get().strip()).name)
        self.rfem_unit_var.set("adimensional")
        self.rfem_scale_var.set("1.0")
        self.rfem_status_var.set("Parámetros RFEM autocompletados. Configura la API desde Opciones y luego pulsa 'Leer modelo RFEM'.")

    def browse_rfem_model(self) -> bool:
        selected_file = filedialog.askopenfilename(
            title="Seleccionar modelo RFEM",
            filetypes=[("Modelos RFEM", "*.rf6"), ("Todos los archivos", "*.*")],
        )
        if selected_file:
            self.rfem_model_var.set(selected_file)
            self.rfem_model_name_var.set(Path(selected_file).name)
            self.rfem_status_var.set("Modelo RFEM seleccionado desde la interfaz. Ahora puedes leer el modelo automáticamente.")
            return True
        return False

    def select_and_load_rfem_model(self) -> None:
        if self.browse_rfem_model():
            selected_name = self.rfem_model_name_var.get().strip() or "modelo seleccionado"
            self.rfem_model_name_var.set(f"Cargando {selected_name}...")
            self.rfem_status_var.set("Leyendo modelo RFEM 6. Espera un momento...")
            self.root.update_idletasks()
            self.load_rfem_model_data()

    def load_sample(self) -> None:
        sample_path = Path(__file__).resolve().parents[3] / "examples" / "sample_input.json"
        self._load_mapping_from_path(sample_path)

    def load_file(self) -> None:
        selected_file = filedialog.askopenfilename(
            title="Seleccionar archivo de entrada",
            filetypes=[("Archivos de entrada", "*.json *.yaml *.yml"), ("Todos los archivos", "*.*")],
        )
        if not selected_file:
            return
        self._load_mapping_from_path(Path(selected_file))

    def _load_mapping_from_path(self, path: Path) -> None:
        try:
            loss_input = load_input_file(path)
            mapping = {
                "Ep": loss_input.steel.elastic_modulus_mpa,
                "Ec": loss_input.concrete.elastic_modulus_mpa,
                "fpk": loss_input.steel.characteristic_strength_mpa,
                "fp01k": loss_input.steel.proof_strength_mpa,
                "fc": loss_input.concrete.compressive_strength_mpa,
                "Ap": loss_input.geometry.area_mm2,
                "n_tendons": loss_input.geometry.count,
                "tendon_length": loss_input.geometry.length_m,
                "theta_total": loss_input.geometry.theta_total_rad,
                "eccentricity": loss_input.geometry.eccentricity_m,
                "mu_tesado": loss_input.mu_tesado,
                "mu_fric": loss_input.mu_fric,
                "k_wobble": loss_input.k_wobble,
                "anchorage_slip_mm": loss_input.anchorage_slip_mm,
                "concrete_stress_at_tendon": loss_input.concrete_stress_at_tendon_mpa,
                "creep_coeff": loss_input.creep_coeff,
                "shrinkage_strain": loss_input.shrinkage_strain,
                "relaxation_loss_ratio": loss_input.relaxation_loss_ratio,
            }
            for key, value in mapping.items():
                self.variables[key].set(str(value))
            self.output_path_var.set(f"Archivo cargado: {path}")
            self.calculate()
        except Exception as error:
            messagebox.showerror("No se pudo cargar el archivo", str(error))

    def calculate(self) -> None:
        try:
            mapping = self._mapping_from_form()
            result = calculate_losses(LossesInput.from_mapping(mapping))
        except Exception as error:
            messagebox.showerror("Error de cálculo", str(error))
            return

        self.current_result = result
        self.result_payload = result.to_nested_dict()
        resumen = self.result_payload["resumen"]
        perdidas = self.result_payload["perdidas"]
        rfem = self.result_payload["rfem"]

        self.cards["Tensión inicial"].configure(text=f"{resumen['tension_inicial_MPa']:.2f} MPa")
        self.cards["Tensión final"].configure(text=f"{resumen['tension_final_MPa']:.2f} MPa")
        self.cards["T0 para RFEM"].configure(text=f"{rfem['T0_percent']:.4f} %")
        self.cards["Tinf para RFEM"].configure(text=f"{rfem['Tinf_percent']:.4f} %")

        self._write_text(
            self.summary_text,
            "\n".join([
                f"Tensión máxima     : {resumen['tension_maxima_MPa']:.2f} MPa",
                f"Tensión inicial    : {resumen['tension_inicial_MPa']:.2f} MPa",
                f"Tensión final      : {resumen['tension_final_MPa']:.2f} MPa",
                f"Fuerza inicial/t   : {resumen['fuerza_inicial_por_tendon_kN']:.2f} kN",
                f"Fuerza final/t     : {resumen['fuerza_final_por_tendon_kN']:.2f} kN",
                f"Fuerza inicial tot : {resumen['fuerza_inicial_total_kN']:.2f} kN",
                f"Fuerza final tot   : {resumen['fuerza_final_total_kN']:.2f} kN",
            ]),
        )
        self._write_text(
            self.losses_text,
            self._build_losses_text(perdidas),
        )
        self._write_text(self.rfem_text, self._build_rfem_text(None))
        self.output_path_var.set("Cálculo actualizado correctamente.")

    def test_rfem_connection(self) -> None:
        try:
            adapter = self._build_rfem_adapter(require_members=False)
            result = adapter.probar_conexion()
            self.rfem_status_var.set(
                f"Conexión OK con RFEM {result['informacion_aplicacion'].get('version', 'sin versión')} en puerto {result['puerto']}."
            )
            self._save_settings()
        except Exception as error:
            self.rfem_status_var.set(f"Falló la conexión con RFEM: {error}")
            messagebox.showerror("Conexión RFEM", str(error))

    def load_rfem_model_data(self) -> None:
        try:
            adapter = self._build_rfem_adapter(require_members=False)
            snapshot = adapter.leer_modelo_postensado(self.rfem_model_var.get().strip())
        except Exception as error:
            self.rfem_status_var.set(f"No se pudo leer el modelo RFEM: {error}")
            messagebox.showerror("Lectura de modelo RFEM", str(error))
            return

        self.rfem_model_snapshot = snapshot
        model_path = self.rfem_model_var.get().strip()
        self.rfem_model_name_var.set(Path(model_path).name if model_path else "Ningún modelo seleccionado.")
        self.rfem_members_var.set(" ".join(str(no) for no in snapshot.get("miembros_tendon", [])))
        self.rfem_member_count_var.set(str(snapshot.get("cantidad_miembros_tendon", len(snapshot.get("miembros_tendon", [])))))
        self.rfem_cordones_count_var.set(str(snapshot.get("cantidad_cordones", snapshot.get("cantidad_miembros_tendon", len(snapshot.get("miembros_tendon", []))))))
        resumen_lectura = snapshot.get("resumen_lectura", {})
        if isinstance(resumen_lectura, dict):
            for key in AUTOLOAD_KEYS:
                value = resumen_lectura.get(key)
                if value is not None:
                    self.variables[key].set(str(value))

        tendon_ids_text = " ".join(str(no) for no in snapshot.get("miembros_tendon", [])) or "-"
        self.rfem_status_var.set(
            f"Modelo leído. Se aplicará sobre los members tendón con IDs: {tendon_ids_text}. Cantidad de members tendón: {snapshot.get('cantidad_miembros_tendon', 0)}. Cordones detectados: {snapshot.get('cantidad_cordones', 0)}."
        )
        self._save_settings()
        self._write_text(self.rfem_text, self._build_rfem_text(None))

    def apply_to_rfem(self) -> None:
        if self.current_result is None:
            self.calculate()
            if self.current_result is None:
                return

        try:
            adapter = self._build_rfem_adapter(require_members=False)
            if not self.rfem_members_var.get().strip():
                snapshot = adapter.leer_modelo_postensado(self.rfem_model_var.get().strip())
                self.rfem_model_snapshot = snapshot
                self.rfem_members_var.set(" ".join(str(no) for no in snapshot.get("miembros_tendon", [])))
                self.rfem_member_count_var.set(str(snapshot.get("cantidad_miembros_tendon", len(snapshot.get("miembros_tendon", [])))))
                self.rfem_cordones_count_var.set(str(snapshot.get("cantidad_cordones", snapshot.get("cantidad_miembros_tendon", len(snapshot.get("miembros_tendon", []))))))
            payloads = build_rfem_load_payload(self.current_result)
            rfem_result = adapter.aplicar_deformaciones_axiales(
                model_path=self.rfem_model_var.get().strip(),
                tendon_member_nos=self._parse_member_numbers(self.rfem_members_var.get()),
                payloads=payloads,
                strain_unit=self.rfem_unit_var.get().strip(),
                strain_scale=float(self.rfem_scale_var.get().strip()),
            )
        except Exception as error:
            self.rfem_status_var.set(f"No se pudo aplicar en RFEM: {error}")
            messagebox.showerror("Aplicación en RFEM", str(error))
            return

        if self.result_payload is None:
            self.result_payload = self.current_result.to_nested_dict()
        self.result_payload["rfem_real"] = rfem_result
        self._write_text(self.rfem_text, self._build_rfem_text(rfem_result))
        casos = rfem_result.get("casos", [])
        self.rfem_status_var.set(f"Aplicación exitosa en RFEM. Se generaron {len(casos)} estados sobre los tendones detectados.")
        self._save_settings()
        messagebox.showinfo("RFEM", "Los estados de postensado se aplicaron correctamente en RFEM.")

    def save_output(self) -> None:
        if self.result_payload is None:
            messagebox.showinfo("Sin resultados", "Primero debes ejecutar un cálculo.")
            return
        selected_file = filedialog.asksaveasfilename(
            title="Guardar resultados",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not selected_file:
            return
        try:
            write_result_file(selected_file, self.result_payload)
            self.output_path_var.set(f"Resultado guardado en: {selected_file}")
        except Exception as error:
            messagebox.showerror("No se pudo guardar", str(error))

    def export_csv(self) -> None:
        if self.result_payload is None:
            messagebox.showinfo("Sin resultados", "Primero debes ejecutar un cálculo.")
            return
        selected_file = filedialog.asksaveasfilename(
            title="Exportar resultados a CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not selected_file:
            return

        resumen = self.result_payload.get("resumen", {})
        perdidas = self.result_payload.get("perdidas", {})
        rfem = self.result_payload.get("rfem", {})
        rows = [
            ("tension_maxima_MPa", resumen.get("tension_maxima_MPa", "")),
            ("tension_inicial_MPa", resumen.get("tension_inicial_MPa", "")),
            ("tension_final_MPa", resumen.get("tension_final_MPa", "")),
            ("fuerza_inicial_por_tendon_kN", resumen.get("fuerza_inicial_por_tendon_kN", "")),
            ("fuerza_final_por_tendon_kN", resumen.get("fuerza_final_por_tendon_kN", "")),
            ("fuerza_inicial_total_kN", resumen.get("fuerza_inicial_total_kN", "")),
            ("fuerza_final_total_kN", resumen.get("fuerza_final_total_kN", "")),
            ("eta_fr", perdidas.get("eta_fr", "")),
            ("eta_anc", perdidas.get("eta_anc", "")),
            ("eta_el", perdidas.get("eta_el", "")),
            ("eta_rel", perdidas.get("eta_rel", "")),
            ("eta_flu", perdidas.get("eta_flu", "")),
            ("eta_ret", perdidas.get("eta_ret", "")),
            ("eta_total", perdidas.get("eta_total", "")),
            ("T0_percent", rfem.get("T0_percent", "")),
            ("Tinf_percent", rfem.get("Tinf_percent", "")),
            ("T0_por_mil", rfem.get("T0_por_mil", "")),
            ("Tinf_por_mil", rfem.get("Tinf_por_mil", "")),
        ]

        try:
            with open(selected_file, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["campo", "valor"])
                writer.writerows(rows)
            self.output_path_var.set(f"CSV exportado en: {selected_file}")
        except Exception as error:
            messagebox.showerror("No se pudo exportar", str(error))

    def _build_rfem_adapter(self, require_members: bool = True) -> Rfem6ApiAdapter:
        model_path = self.rfem_model_var.get().strip()
        if not model_path:
            raise ValueError("Debes indicar el modelo RFEM desde la interfaz.")
        if require_members:
            self._parse_member_numbers(self.rfem_members_var.get())
        raw_api_key = self.rfem_api_key_var.get().strip()
        if not raw_api_key:
            raise ValueError("Configura la API RFEM desde el menú Opciones antes de conectar.")
        is_direct_key = raw_api_key.lower().startswith("ak-")
        return Rfem6ApiAdapter(
            api_key_name=("default" if is_direct_key else (raw_api_key or "default")),
            api_key_value=(raw_api_key if is_direct_key else None),
            port=int(self.rfem_port_var.get().strip()),
        )

    def _build_losses_text(self, pérdidas: dict[str, float]) -> str:
        lines = ["Desglose para presentación", ""]
        for key, description in LOSS_DESCRIPTIONS:
            value = pérdidas.get(key, 0.0) * 100.0
            lines.append(f"{description:<24} {value:>7.2f} %")
        return "\n".join(lines)

    def _build_rfem_text(self, rfem_result: dict[str, object] | None) -> str:
        if self.result_payload is None:
            return "No hay resultados disponibles para RFEM."

        rfem = self.result_payload["rfem"]
        lines = [
            "Estados equivalentes para RFEM 6",
            "",
            f"T0 percent        = {rfem['T0_percent']:.6f} %",
            f"Tinf percent      = {rfem['Tinf_percent']:.6f} %",
            f"T0 por mil        = {rfem['T0_por_mil']:.6f} por mil",
            f"Tinf por mil      = {rfem['Tinf_por_mil']:.6f} por mil",
            f"epsilon_T0        = {rfem['T0_percent'] / 100.0:.8f}",
            f"epsilon_Tinf      = {rfem['Tinf_percent'] / 100.0:.8f}",
            "",
            f"Unidad activa GUI = {self.rfem_unit_var.get()}",
            f"Factor de escala  = {self.rfem_scale_var.get()}",
            f"Members tendón (IDs) = {self.rfem_members_var.get().strip() or '-'}",
            f"Cantidad members = {self.rfem_member_count_var.get().strip() or '-'}",
            f"Cantidad cordones = {self.rfem_cordones_count_var.get().strip() or '-'}",
        ]

        if self.rfem_model_snapshot is not None:
            material = self.rfem_model_snapshot.get("material_tendon", {})
            sección = self.rfem_model_snapshot.get("sección_tendon", {})
            lines.extend([
                "",
                "Lectura automática del modelo",
                f"Cantidad de members tendón = {self.rfem_model_snapshot.get('cantidad_miembros_tendon', '-')}",
                f"Cantidad cordones = {self.rfem_model_snapshot.get('cantidad_cordones', '-')}",
                f"Longitud media    = {self.rfem_model_snapshot.get('longitud_promedio_m', '-')}",
                f"Modelo soportado  = {self.rfem_model_snapshot.get('tipo_modelado_tendon', '-')}",
                f"Sup. candidatas   = {self.rfem_model_snapshot.get('superficies_tendon_candidatas', [])}",
                f"Material tendón   = {material.get('nombre', '-') if isinstance(material, dict) else '-'}",
                f"Ep del modelo     = {material.get('Ep_MPa', '-') if isinstance(material, dict) else '-'} MPa",
                f"fpk del modelo    = {material.get('fpk_MPa', '-') if isinstance(material, dict) else '-'} MPa",
                f"fp01k del modelo  = {material.get('fp01k_MPa', '-') if isinstance(material, dict) else '-'} MPa",
                f"Sección tendón    = {sección.get('nombre', '-') if isinstance(sección, dict) else '-'}",
                f"Ap del modelo     = {sección.get('Ap_mm2', '-') if isinstance(sección, dict) else '-'} mm2",
                f"mu_fric modelo    = {sección.get('mu_fric', '-') if isinstance(sección, dict) else '-'}",
                f"k_wobble modelo   = {sección.get('k_wobble', '-') if isinstance(sección, dict) else '-'}",
                f"Hormigón modelo   = {self.rfem_model_snapshot.get('material_hormigon', {}).get('nombre', '-') if isinstance(self.rfem_model_snapshot.get('material_hormigon', {}), dict) else '-'}",
                f"Ec del modelo     = {self.rfem_model_snapshot.get('material_hormigon', {}).get('Ec_MPa', '-') if isinstance(self.rfem_model_snapshot.get('material_hormigon', {}), dict) else '-'} MPa",
                f"fc del modelo     = {self.rfem_model_snapshot.get('material_hormigon', {}).get('fc_MPa', '-') if isinstance(self.rfem_model_snapshot.get('material_hormigon', {}), dict) else '-'} MPa",
                "Nota superficies  = No soportadas aún para aplicación automática",
            ])

        if rfem_result is not None:
            lines.extend([
                "",
                "Estado del envío a RFEM",
                f"Modo             = {rfem_result.get('modo_creacion', 'sin dato')}",
                f"Modelo           = {rfem_result.get('modelo', 'sin dato')}",
                f"Puerto           = {rfem_result.get('puerto', 'sin dato')}",
            ])
            casos = rfem_result.get("casos", [])
            if isinstance(casos, list):
                for caso in casos:
                    lines.append(f"Caso {caso.get('caso_carga_no')} -> {caso.get('estado_temporal')} -> e = {caso.get('deformacion_axial')}")

        return "\n".join(lines)

    def _mapping_from_form(self) -> dict[str, float]:
        mapping: dict[str, float] = {}
        integer_fields = {"n_tendons"}
        for key, _label in FIELD_LABELS:
            raw_value = self.variables[key].get().strip()
            if raw_value == "":
                raise ValueError(f"El campo '{key}' no puede estar vacío.")
            mapping[key] = int(float(raw_value)) if key in integer_fields else float(raw_value)
        return mapping

    @staticmethod
    def _parse_member_numbers(raw_value: str) -> list[int]:
        cleaned = raw_value.replace(",", " ").split()
        if not cleaned:
            raise ValueError("Debes indicar al menos un número de cordón o miembro para RFEM.")
        try:
            return [int(value) for value in cleaned]
        except ValueError as error:
            raise ValueError("Los cordones o miembros deben ser números enteros separados por espacios o comas.") from error

    @staticmethod
    def _write_text(widget: tk.Text, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state="disabled")

    def _settings_path(self) -> Path:
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "pt_losses_gui" / "settings.json"
        return Path.home() / ".pt_losses_gui_settings.json"

    def _load_settings(self) -> None:
        path = self._settings_path()
        try:
            if not path.exists():
                return
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.rfem_api_key_var.set(str(data.get("rfem_api_key", "")))
        self.rfem_model_var.set("")
        self.rfem_model_name_var.set("Ningún modelo seleccionado.")
        self.rfem_port_var.set(str(data.get("rfem_port", "9000")))

    def _save_settings(self) -> None:
        path = self._settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "rfem_api_key": self.rfem_api_key_var.get().strip(),
            "rfem_port": self.rfem_port_var.get().strip(),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _handle_close(self) -> None:
        try:
            self._save_settings()
        finally:
            self.root.destroy()

    def _resource_base(self) -> Path:
        if hasattr(sys, "_MEIPASS"):
            return Path(getattr(sys, "_MEIPASS"))
        return Path(__file__).resolve().parent

    def _assets_dirs(self) -> list[Path]:
        base = self._resource_base()
        return [
            base / "assets",
            base / "pt_losses" / "gui" / "assets",
            Path(__file__).resolve().parent / "assets",
        ]

    def _manual_path(self) -> Path | None:
        manual_name = "manual_uso_perdida_postensado_rfem6.html"
        project_dist = Path(__file__).resolve().parents[3] / "dist" / manual_name
        candidates = [
            self._resource_base() / manual_name,
            self._resource_base() / "assets" / manual_name,
            *(assets_dir / manual_name for assets_dir in self._assets_dirs()),
            project_dist,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _open_manual_html(self) -> None:
        manual_path = self._manual_path()
        if manual_path is None:
            messagebox.showerror(
                "Ayuda",
                "No se encontró el manual HTML. Verifica que el archivo 'manual_uso_perdida_postensado_rfem6.html' esté disponible.",
            )
            return
        try:
            webbrowser.open(manual_path.resolve().as_uri())
        except Exception as error:
            messagebox.showerror("Ayuda", f"No se pudo abrir el manual: {error}")

    def _logo_path(self) -> Path | None:
        for assets_dir in self._assets_dirs():
            preferred = assets_dir / "logo-dlubal.png"
            if preferred.exists():
                return preferred
            fallback = assets_dir / "logo.png"
            if fallback.exists():
                return fallback
        return None

    def _render_logo(self, parent: ttk.Frame, compact: bool) -> None:
        logo_path = self._logo_path()
        if logo_path is not None and logo_path.exists():
            try:
                image = tk.PhotoImage(file=str(logo_path))
                if compact:
                    max_width = 72
                    if image.width() > max_width:
                        scale = max(1, int(round(image.width() / max_width)))
                        image = image.subsample(scale, scale)
                self.logo_image = image
                ttk.Label(parent, image=self.logo_image, style="CardBody.TLabel").pack(anchor="e")
                return
            except tk.TclError:
                pass

        fallback = "Coloca tu logo en\nsrc/pt_losses/gui/assets/logo-dlubal.png"
        wrap = 220 if compact else 260
        ttk.Label(parent, text=fallback, style="Body.TLabel", wraplength=wrap, justify="right").pack(anchor="e")


def run() -> None:
    root = tk.Tk()
    PtLossesApp(root)
    root.mainloop()





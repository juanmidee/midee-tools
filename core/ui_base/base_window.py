import customtkinter as ctk
from core.branding import theme
from PIL import Image
import os
import csv
import json
import hashlib
from tkinter import filedialog
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm



APP_VERSION = "1.1"
ACTIVATION_SECRET = "CAMBIAR_ESTA_CLAVE_2026"


ABOUT_TEXT_ES = """MIDEE #3 Wind Tools
Versión 1.1

Propiedad intelectual de MIDEE#3.
Todos los derechos reservados.

Este software ha sido desarrollado con fines educativos y profesionales.

Todos los valores y procedimientos de cálculo deben ser verificados antes de su uso en un proyecto real.

MIDEE#3 no se responsabiliza por daños ocasionados por el mal uso de los documentos y programas utilizados.
"""

ABOUT_TEXT_EN = """MIDEE #3 Wind Tools
Version 1.1

Intellectual property of MIDEE#3.
All rights reserved.

This software has been developed for educational and professional purposes.

All calculated values and procedures must be independently verified before being used in a real engineering project.

MIDEE#3 is not responsible for any damage resulting from improper use of the documents or software tools provided.
"""

HELP_TEXT_ES = """Uso:

1) Ingrese velocidad del viento (m/s)
2) Ingrese densidad (kg/m³) o deje 1.225
3) Presione Calcular
4) Exporte resultados si lo desea

Fórmula:
q = 0.5 · ρ · V²
"""

HELP_TEXT_EN = """Usage:

1) Enter wind velocity (m/s)
2) Enter density (kg/m³) or keep 1.225
3) Click Calcular
4) Export results if needed

Formula:
q = 0.5 · ρ · V²
"""


class BaseWindow(ctk.CTk):

    def __init__(self, title="MIDEE #3 Wind Tools"):
        super().__init__()

        self.title(title)
        self.geometry("1100x700")
        self.minsize(900, 600)

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.configure(fg_color=theme.BACKGROUND_COLOR)

        self.license_data = None

        self.create_layout()        # 👈 PRIMERO crear UI
        self.initialize_license()   # 👈 DESPUÉS cargar licencia


    # =========================
    # ACTIVACIÓN
    # =========================

    def get_license_path(self):
        appdata = os.getenv("APPDATA")
        license_dir = os.path.join(appdata, "MIDEE_3")
        os.makedirs(license_dir, exist_ok=True)
        return os.path.join(license_dir, "license.json")

    def generate_activation_code(self, email):
        hash_value = hashlib.sha256((email + ACTIVATION_SECRET).encode()).hexdigest()
        return hash_value[:16].upper()

    def initialize_license(self):
        path = self.get_license_path()

        if os.path.exists(path):
            with open(path, "r") as f:
                self.license_data = json.load(f)

            # Actualizar bloque de miembro en sidebar
            if hasattr(self, "member_label") and self.license_data:
                self.member_label.configure(
                    text=(
                        f"Miembro MIDEE#3\n"
                        f"{self.license_data.get('name', '')}\n"
                        f"{self.license_data.get('email', '')}"
                    )
                )

            return

        self.show_activation_modal()


    def show_activation_modal(self):

        modal = ctk.CTkToplevel(self)
        modal.title("Activación - MIDEE #3 Wind Tools")
        modal.geometry("480x520")
        modal.resizable(False, False)
        modal.grab_set()
        modal.transient(self)

        frame = ctk.CTkFrame(modal)
        frame.pack(fill="both", expand=True, padx=30, pady=30)

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "branding",
            "logo-midee-3.png"
        )

        logo_image = ctk.CTkImage(
            light_image=Image.open(logo_path),
            size=(80, 80)
        )

        ctk.CTkLabel(frame, image=logo_image, text="").pack(pady=(0, 15))

        ctk.CTkLabel(
            frame,
            text=f"MIDEE #3 Wind Tools v{APP_VERSION}",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            frame,
            text="Activación requerida",
            font=("Segoe UI", 12)
        ).pack(pady=(0, 20))

        self.entry_name = ctk.CTkEntry(
            frame,
            placeholder_text="Nombre completo",
            width=300
        )
        self.entry_name.pack(pady=10)

        self.entry_email = ctk.CTkEntry(
            frame,
            placeholder_text="Email",
            width=300
        )
        self.entry_email.pack(pady=10)

        self.entry_code = ctk.CTkEntry(
            frame,
            placeholder_text="Código de activación",
            width=300
        )
        self.entry_code.pack(pady=10)

        self.activation_error = ctk.CTkLabel(
            frame,
            text="",
            text_color="red"
        )
        self.activation_error.pack(pady=5)

        # ---------------- ACTIVATE FUNCTION ----------------

        def activate():

            name = self.entry_name.get().strip()
            email = self.entry_email.get().strip()
            code = self.entry_code.get().strip().upper()

            if not name or not email or not code:
                self.activation_error.configure(
                    text="Todos los campos son obligatorios."
                )
                return

            expected = self.generate_activation_code(email)

            if code != expected:
                self.activation_error.configure(
                    text="Código inválido."
                )
                return

            self.license_data = {
                "name": name,
                "email": email,
                "code": code
            }

            with open(self.get_license_path(), "w") as f:
                json.dump(self.license_data, f)


            # Actualizar bloque miembro inmediatamente
            if hasattr(self, "member_label"):
                self.member_label.configure(
                    text=(
                        f"Miembro MIDEE#3\n"
                        f"{name}\n"
                        f"{email}"
                    )
                )

            # IMPORTANTE: mostrar ventana principal si estaba oculta
            try:
                self.deiconify()
            except:
                pass

            modal.destroy()

        # ---------------- BUTTON ----------------

        ctk.CTkButton(
            frame,
            text="Activar",
            command=activate,
            fg_color=theme.PRIMARY_COLOR
        ).pack(pady=20)

        # Si cierran manualmente sin activar → cerrar app
        modal.protocol("WM_DELETE_WINDOW", self.destroy)



    # =========================
    # LAYOUT
    # =========================

    def create_layout(self):

        self.sidebar = ctk.CTkFrame(self, width=250, fg_color=theme.PRIMARY_COLOR)
        self.sidebar.pack(side="left", fill="y")

        self.sidebar_content = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_content.pack(padx=20, pady=20, fill="both", expand=True)

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "branding",
            "logo-midee-3.png"
        )

        logo_image = ctk.CTkImage(light_image=Image.open(logo_path), size=(100, 100))
        ctk.CTkLabel(self.sidebar_content, image=logo_image, text="").pack(pady=(10, 20))

        ctk.CTkLabel(
            self.sidebar_content,
            text="MIDEE #3 Wind Tools",
            font=("Segoe UI", 18, "bold"),
            text_color=theme.WHITE
        ).pack()

        ctk.CTkLabel(
            self.sidebar_content,
            text=f"v{APP_VERSION}",
            font=("Segoe UI", 12),
            text_color="#D6EAF8"
        ).pack(pady=(0, 10))

        self.member_label = ctk.CTkLabel(
            self.sidebar_content,
            text="",
            font=("Segoe UI", 11),
            text_color=theme.WHITE,
            justify="left"
        )
        self.member_label.pack(pady=(5, 20), anchor="w")

        ctk.CTkFrame(self.sidebar_content, height=2, fg_color="#FFFFFF").pack(fill="x", pady=10)

        ctk.CTkButton(
            self.sidebar_content,
            text="Presión Dinámica",
            command=self.load_pressure_module,
            fg_color=theme.SECONDARY_COLOR
        ).pack(fill="x", pady=5)

        ctk.CTkButton(self.sidebar_content, text="Perfil V(z) 🔒", state="disabled").pack(fill="x", pady=5)
        ctk.CTkButton(self.sidebar_content, text="Perfil q(z) 🔒", state="disabled").pack(fill="x", pady=5)
        ctk.CTkButton(self.sidebar_content, text="Ráfagas Temporales 🔒", state="disabled").pack(fill="x", pady=5)

        self.main_container = ctk.CTkFrame(self, fg_color=theme.BACKGROUND_COLOR)
        self.main_container.pack(side="right", fill="both", expand=True)

        self.create_top_menu(self.main_container)

        self.main_frame = ctk.CTkFrame(self.main_container, fg_color=theme.BACKGROUND_COLOR)
        self.main_frame.pack(fill="both", expand=True)

    def create_top_menu(self, parent):

        top = ctk.CTkFrame(parent, height=45)
        top.pack(fill="x", padx=20, pady=(15, 0))
        top.pack_propagate(False)

        ctk.CTkButton(top, text="Archivo", command=self.open_file_menu_modal).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Ayuda", command=self.open_help_menu_modal).pack(side="left", padx=5)

        ctk.CTkLabel(
            top,
            text="MIDEE #3 Wind Tools",
            font=("Segoe UI", 12, "bold")
        ).pack(side="right", padx=15)

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    # =========================
    # MÓDULO PRESIÓN DINÁMICA
    # =========================

    def load_pressure_module(self):

        self.clear_main_frame()

        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=30)

        left_frame = ctk.CTkFrame(container, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))

        right_frame = ctk.CTkFrame(container, fg_color="transparent")
        right_frame.pack(side="right", fill="both", expand=True)

        # -------- INPUTS --------

        title = ctk.CTkLabel(
            left_frame,
            text="Parámetros de entrada",
            font=("Segoe UI", 18, "bold"),
            text_color=theme.TEXT_PRIMARY
        )
        title.pack(pady=(0, 20), anchor="w")

        # Velocidad
        velocity_row = ctk.CTkFrame(left_frame, fg_color="transparent")
        velocity_row.pack(pady=8, anchor="w")

        ctk.CTkLabel(
            velocity_row,
            text="Velocidad del viento:",
            font=("Segoe UI", 14),
            text_color=theme.TEXT_PRIMARY
        ).pack(side="left", padx=5)

        self.velocity_entry = ctk.CTkEntry(velocity_row, width=120)
        self.velocity_entry.pack(side="left", padx=5)

        ctk.CTkLabel(
            velocity_row,
            text="m/s",
            font=("Segoe UI", 14),
            text_color=theme.TEXT_PRIMARY
        ).pack(side="left", padx=5)

        # Densidad
        density_row = ctk.CTkFrame(left_frame, fg_color="transparent")
        density_row.pack(pady=8, anchor="w")

        ctk.CTkLabel(
            density_row,
            text="Densidad del aire:",
            font=("Segoe UI", 14),
            text_color=theme.TEXT_PRIMARY
        ).pack(side="left", padx=5)

        self.density_entry = ctk.CTkEntry(density_row, width=120)
        self.density_entry.pack(side="left", padx=5)

        ctk.CTkLabel(
            density_row,
            text="kg/m³",
            font=("Segoe UI", 14),
            text_color=theme.TEXT_PRIMARY
        ).pack(side="left", padx=5)

        # Botones
        button_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        button_frame.pack(pady=25, anchor="w")

        ctk.CTkButton(
            button_frame,
            text="Calcular",
            command=self.calculate_pressure,
            fg_color=theme.SECONDARY_COLOR,
            width=140
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Nuevo cálculo",
            command=self.reset_pressure_form,
            fg_color="#7F8C8D",
            width=140
        ).pack(side="left", padx=5)

        # -------- RESULTADOS --------

        result_title = ctk.CTkLabel(
            right_frame,
            text="Resultado",
            font=("Segoe UI", 18, "bold"),
            text_color=theme.TEXT_PRIMARY
        )
        result_title.pack(pady=(0, 20))

        self.result_label = ctk.CTkLabel(
            right_frame,
            text="- kN/m²",
            font=("Segoe UI", 36, "bold"),
            text_color=theme.PRIMARY_COLOR
        )
        self.result_label.pack(pady=10)

        self.conversion_label = ctk.CTkLabel(
            right_frame,
            text="",
            font=("Segoe UI", 14),
            text_color=theme.TEXT_PRIMARY,
            justify="left"
        )
        self.conversion_label.pack(pady=5)

        self.result_bar = ctk.CTkProgressBar(right_frame, width=350)
        self.result_bar.set(0)
        self.result_bar.pack(pady=(20, 5))

        self.scale_label = ctk.CTkLabel(
            right_frame,
            text="Escala dinámica: -",
            font=("Segoe UI", 12),
            text_color=theme.TEXT_SECONDARY
        )
        self.scale_label.pack(pady=(0, 10))

        self.formula_label = ctk.CTkLabel(
            right_frame,
            text="Fórmula: q = 0.5 · ρ · V²",
            font=("Segoe UI", 12, "italic"),
            text_color=theme.TEXT_SECONDARY
        )
        self.formula_label.pack(pady=(10, 0))

        ctk.CTkButton(
            right_frame,
            text="Exportar a CSV",
            command=self.export_to_csv,
            width=160
        ).pack(pady=15)

        pdf_btn = ctk.CTkButton(
            right_frame,
            text="Exportar a PDF",
            command=self.export_to_pdf,
            width=160
        )
        pdf_btn.pack(pady=5)

        self.velocity_entry.focus()

    # =========================
    # CÁLCULO
    # =========================

    def calculate_pressure(self):

        try:
            velocity = float(self.velocity_entry.get())
            density = float(self.density_entry.get()) if self.density_entry.get() else 1.225

            q = 0.5 * density * velocity ** 2

            q_pa = q
            q_n = q
            q_kn = q / 1000
            q_kg_m2 = q / 9.81

            self.result_label.configure(text=f"{q_kn:.4f} kN/m²")

            self.conversion_label.configure(
                text=(
                    f"{q_pa:.2f} Pa\n"
                    f"{q_n:.2f} N/m²\n"
                    f"{q_kn:.4f} kN/m²\n"
                    f"{q_kg_m2:.4f} kg/m²"
                )
            )

            # Escala dinámica
            if q_kn <= 1:
                max_scale = 1
            elif q_kn <= 5:
                max_scale = 5
            elif q_kn <= 10:
                max_scale = 10
            elif q_kn <= 20:
                max_scale = 20
            else:
                max_scale = round(q_kn * 1.2, 1)

            self.result_bar.set(q_kn / max_scale)

            self.scale_label.configure(
                text=f"Escala dinámica: 0 - {max_scale} kN/m²"
            )

            self.last_result = {
                "velocity": velocity,
                "density": density,
                "pa": q_pa,
                "n_m2": q_n,
                "kn_m2": q_kn,
                "kg_m2": q_kg_m2
            }

        except ValueError:
            self.result_label.configure(text="Valor inválido")
            self.result_bar.set(0)

    # =========================
    # RESET
    # =========================

    def reset_pressure_form(self):
        self.velocity_entry.delete(0, "end")
        self.density_entry.delete(0, "end")
        self.result_label.configure(text="- kN/m²")
        self.conversion_label.configure(text="")
        self.result_bar.set(0)
        self.scale_label.configure(text="Escala dinámica: -")
        self.velocity_entry.focus()

    # =========================
    # EXPORTAR CSV
    # =========================

    def export_to_csv(self):

        if not hasattr(self, "last_result"):
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )

        if not file_path:
            return

        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)

            writer.writerow(["MIDEE #3 Wind Tools - Cálculo de Presión Dinámica"])
            writer.writerow([f"Versión {APP_VERSION}"])
            writer.writerow([f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            writer.writerow([])

            writer.writerow(["DATOS DE ENTRADA"])
            writer.writerow(["Velocidad (m/s)", f"{self.last_result['velocity']:.2f}"])
            writer.writerow(["Densidad (kg/m³)", f"{self.last_result['density']:.3f}"])
            writer.writerow([])

            writer.writerow(["RESULTADOS"])
            writer.writerow(["Presión (Pa)", f"{self.last_result['pa']:.2f}"])
            writer.writerow(["Presión (N/m²)", f"{self.last_result['n_m2']:.2f}"])
            writer.writerow(["Presión (kN/m²)", f"{self.last_result['kn_m2']:.4f}"])
            writer.writerow(["Presión (kg/m²)", f"{self.last_result['kg_m2']:.4f}"])
            writer.writerow([])

            writer.writerow(["Fórmula aplicada"])
            writer.writerow(["q = 0.5 · ρ · V²"])

    #==========================
    # EXPORTAR A PDF
    #==========================
    def export_to_pdf(self):

        if not hasattr(self, "last_result"):
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )

        if not file_path:
            return

        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )

        elements = []

        styles = getSampleStyleSheet()
        normal = styles["Normal"]

        title_style = ParagraphStyle(
            "title",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor(theme.PRIMARY_COLOR),
            spaceAfter=10
        )

        section_style = ParagraphStyle(
            "section",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor(theme.PRIMARY_COLOR),
            spaceAfter=6
        )

        # Logo
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "branding",
            "logo-midee-3.png"
        )

        if os.path.exists(logo_path):
            elements.append(RLImage(logo_path, width=40 * mm, height=40 * mm))
            elements.append(Spacer(1, 10))

        # Encabezado
        elements.append(Paragraph("MIDEE #3 Wind Tools", title_style))
        elements.append(Paragraph(f"Versión {APP_VERSION}", normal))
        elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal))
        elements.append(Spacer(1, 15))

        # Usuario
        if self.license_data:
            elements.append(Paragraph("Usuario autorizado:", section_style))
            elements.append(Paragraph(self.license_data.get("name", ""), normal))
            elements.append(Paragraph(self.license_data.get("email", ""), normal))
            elements.append(Spacer(1, 15))

        # Datos entrada
        elements.append(Paragraph("Datos de entrada", section_style))
        elements.append(Paragraph(f"Velocidad (m/s): {self.last_result['velocity']:.2f}", normal))
        elements.append(Paragraph(f"Densidad (kg/m³): {self.last_result['density']:.3f}", normal))
        elements.append(Spacer(1, 15))

        # Resultados
        elements.append(Paragraph("Resultados", section_style))
        elements.append(Paragraph(f"Presión (Pa): {self.last_result['pa']:.2f}", normal))
        elements.append(Paragraph(f"Presión (N/m²): {self.last_result['n_m2']:.2f}", normal))
        elements.append(Paragraph(f"Presión (kN/m²): {self.last_result['kn_m2']:.4f}", normal))
        elements.append(Paragraph(f"Presión (kg/m²): {self.last_result['kg_m2']:.4f}", normal))
        elements.append(Spacer(1, 15))

        # Fórmula
        elements.append(Paragraph("Fórmula aplicada:", section_style))
        elements.append(Paragraph("q = 0.5 · ρ · V²", normal))
        elements.append(Spacer(1, 20))

        # Disclaimer
        disclaimer = """
        Todos los valores y procedimientos de cálculo deben ser verificados antes de su uso en un proyecto real.
        MIDEE#3 no se responsabiliza por daños ocasionados por el mal uso de los documentos y programas utilizados.
        """

        elements.append(Paragraph(disclaimer, styles["Italic"]))

        doc.build(elements)


    # =========================
    # MENÚES
    # =========================

    def open_file_menu_modal(self):

        modal = ctk.CTkToplevel(self)
        modal.title("Archivo")
        modal.geometry("300x180")
        modal.resizable(False, False)
        modal.grab_set()

        frame = ctk.CTkFrame(modal)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkButton(
            frame,
            text="Exportar CSV",
            command=lambda: (modal.destroy(), self.export_to_csv())
        ).pack(fill="x", pady=5)

        ctk.CTkButton(
            frame,
            text="Salir",
            command=self.destroy
        ).pack(fill="x", pady=5)

    def open_help_menu_modal(self):

        modal = ctk.CTkToplevel(self)
        modal.title("Ayuda")
        modal.geometry("300x180")
        modal.resizable(False, False)
        modal.grab_set()

        frame = ctk.CTkFrame(modal)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkButton(
            frame,
            text="Sobre / About",
            command=lambda: (modal.destroy(), self.show_about_modal())
        ).pack(fill="x", pady=5)

        ctk.CTkButton(
            frame,
            text="Ayuda / Help",
            command=lambda: (modal.destroy(), self.show_help_modal())
        ).pack(fill="x", pady=5)

    def show_about_modal(self):

        modal = ctk.CTkToplevel(self)
        modal.title("Sobre / About")
        modal.geometry("700x550")
        modal.resizable(False, False)
        modal.grab_set()

        frame = ctk.CTkScrollableFrame(modal)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="ESPAÑOL", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ctk.CTkLabel(frame, text=ABOUT_TEXT_ES, wraplength=640, justify="left").pack(anchor="w", pady=10)

        ctk.CTkLabel(frame, text="ENGLISH", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ctk.CTkLabel(frame, text=ABOUT_TEXT_EN, wraplength=640, justify="left").pack(anchor="w", pady=10)

    def show_help_modal(self):

        modal = ctk.CTkToplevel(self)
        modal.title("Ayuda / Help")
        modal.geometry("700x550")
        modal.resizable(False, False)
        modal.grab_set()

        frame = ctk.CTkScrollableFrame(modal)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="ESPAÑOL", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ctk.CTkLabel(frame, text=HELP_TEXT_ES, wraplength=640, justify="left").pack(anchor="w", pady=10)

        ctk.CTkLabel(frame, text="ENGLISH", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ctk.CTkLabel(frame, text=HELP_TEXT_EN, wraplength=640, justify="left").pack(anchor="w", pady=10)

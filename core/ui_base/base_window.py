import customtkinter as ctk
from core.branding import theme
from PIL import Image
import os
import csv
from tkinter import filedialog
from datetime import datetime


class BaseWindow(ctk.CTk):

    def __init__(self, title="MIDEE Tools"):
        super().__init__()

        self.title(title)
        self.geometry("1100x700")
        self.minsize(900, 600)

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.configure(fg_color=theme.BACKGROUND_COLOR)

        self.create_layout()

    # ==================================================
    # LAYOUT PRINCIPAL
    # ==================================================

    def create_layout(self):

        # ---------------- SIDEBAR ----------------
        self.sidebar = ctk.CTkFrame(
            self,
            width=250,
            fg_color=theme.PRIMARY_COLOR,
            corner_radius=0
        )
        self.sidebar.pack(side="left", fill="y")

        self.sidebar_content = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        )
        self.sidebar_content.pack(padx=20, pady=20, fill="both", expand=True)

        # Logo
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "branding",
            "logo-midee-3.png"
        )

        logo_image = ctk.CTkImage(
            light_image=Image.open(logo_path),
            size=(100, 100)
        )

        self.logo_label = ctk.CTkLabel(
            self.sidebar_content,
            image=logo_image,
            text=""
        )
        self.logo_label.pack(pady=(10, 30))

        # Producto
        self.product_label = ctk.CTkLabel(
            self.sidebar_content,
            text="MIDEE #3 Wind Tools",
            font=("Segoe UI", 18, "bold"),
            text_color=theme.WHITE
        )
        self.product_label.pack(pady=(0, 5))

        self.version_label = ctk.CTkLabel(
            self.sidebar_content,
            text="v1.0",
            font=("Segoe UI", 12),
            text_color="#D6EAF8"
        )
        self.version_label.pack(pady=(0, 30))

        # Separador
        self.separator = ctk.CTkFrame(
            self.sidebar_content,
            height=2,
            fg_color="#FFFFFF"
        )
        self.separator.pack(fill="x", pady=10)

        # -------- MÓDULOS --------

        # Activo
        self.btn_pressure = ctk.CTkButton(
            self.sidebar_content,
            text="Presión Dinámica",
            font=("Segoe UI", 14, "bold"),
            fg_color=theme.SECONDARY_COLOR,
            hover_color=theme.DARK_PRIMARY,
            text_color="white",
            corner_radius=8,
            command=self.load_pressure_module
        )
        self.btn_pressure.pack(fill="x", pady=5)

        # Bloqueados (futuras versiones)
        self.btn_profile_v = ctk.CTkButton(
            self.sidebar_content,
            text="Perfil V(z)  🔒",
            font=("Segoe UI", 14),
            fg_color="#7F8C8D",
            hover=False,
            text_color="white",
            state="disabled",
            corner_radius=8
        )
        self.btn_profile_v.pack(fill="x", pady=5)

        self.btn_profile_q = ctk.CTkButton(
            self.sidebar_content,
            text="Perfil q(z)  🔒",
            font=("Segoe UI", 14),
            fg_color="#7F8C8D",
            hover=False,
            text_color="white",
            state="disabled",
            corner_radius=8
        )
        self.btn_profile_q.pack(fill="x", pady=5)

        self.btn_gust = ctk.CTkButton(
            self.sidebar_content,
            text="Ráfagas Temporales  🔒",
            font=("Segoe UI", 14),
            fg_color="#7F8C8D",
            hover=False,
            text_color="white",
            state="disabled",
            corner_radius=8
        )
        self.btn_gust.pack(fill="x", pady=5)

        # ---------------- MAIN FRAME ----------------
        self.main_frame = ctk.CTkFrame(
            self,
            fg_color=theme.BACKGROUND_COLOR
        )
        self.main_frame.pack(side="right", fill="both", expand=True)

        self.content_label = ctk.CTkLabel(
            self.main_frame,
            text="Seleccione una herramienta",
            font=("Segoe UI", 16),
            text_color=theme.TEXT_PRIMARY
        )
        self.content_label.pack(pady=20)

    # ==================================================
    # UTILIDADES
    # ==================================================

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    # ==================================================
    # MÓDULO PRESIÓN DINÁMICA
    # ==================================================

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

        button_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        button_frame.pack(pady=25, anchor="w")

        calculate_btn = ctk.CTkButton(
            button_frame,
            text="Calcular",
            command=self.calculate_pressure,
            fg_color=theme.SECONDARY_COLOR,
            hover_color=theme.DARK_PRIMARY,
            width=140
        )
        calculate_btn.pack(side="left", padx=5)

        reset_btn = ctk.CTkButton(
            button_frame,
            text="Nuevo cálculo",
            fg_color="#7F8C8D",
            hover_color="#5D6D7E",
            command=self.reset_pressure_form,
            width=140
        )
        reset_btn.pack(side="left", padx=5)

        # -------- RESULTADO --------
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
            text="Fórmula:  q = 0.5 · ρ · V²",
            font=("Segoe UI", 12, "italic"),
            text_color=theme.TEXT_SECONDARY
        )
        self.formula_label.pack(pady=(10, 0))

        export_btn = ctk.CTkButton(
            right_frame,
            text="Exportar a CSV",
            command=self.export_to_csv,
            width=160
        )
        export_btn.pack(pady=15)

        self.velocity_entry.focus()

    # ==================================================
    # CÁLCULO
    # ==================================================

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
                text=f"Escala dinámica: 0 – {max_scale} kN/m²"
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

    # ==================================================
    # RESET
    # ==================================================

    def reset_pressure_form(self):
        self.velocity_entry.delete(0, "end")
        self.density_entry.delete(0, "end")
        self.result_label.configure(text="- kN/m²")
        self.conversion_label.configure(text="")
        self.result_bar.set(0)
        self.scale_label.configure(text="Escala dinámica: -")
        self.velocity_entry.focus()

    # ==================================================
    # EXPORTACIÓN
    # ==================================================

    def export_to_csv(self):

        if not hasattr(self, "last_result"):
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )

        if not file_path:
            return

        with open(file_path, mode="w", newline="") as file:
            writer = csv.writer(file)

            writer.writerow(["MIDEE Wind Tools - Presión Dinámica"])
            writer.writerow(["Fecha", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow([])
            writer.writerow(["Velocidad (m/s)", self.last_result["velocity"]])
            writer.writerow(["Densidad (kg/m³)", self.last_result["density"]])
            writer.writerow([])
            writer.writerow(["Resultado (Pa)", self.last_result["pa"]])
            writer.writerow(["Resultado (N/m²)", self.last_result["n_m2"]])
            writer.writerow(["Resultado (kN/m²)", self.last_result["kn_m2"]])
            writer.writerow(["Resultado (kg/m²)", self.last_result["kg_m2"]])

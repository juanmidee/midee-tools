from __future__ import annotations

from dataclasses import dataclass

from pt_losses.domain.models import LossesResult


RFEM_STRAIN_UNITS = ("percent", "adimensional", "permille")
RFEM_PRESTRESS_FORCE_UNITS = ("kN", "N")
RFEM_LOAD_MODES = ("axial_strain", "prestress_force")


@dataclass(frozen=True, slots=True)
class RfemLoadCasePayload:
    state_name: str
    axial_strain_percent: float
    axial_strain_permille: float
    prestress_force_kn: float
    prestress_stress_mpa: float

    def deformacion_axial(self, unidad: str = "percent") -> float:
        if unidad == "percent":
            return self.axial_strain_percent
        if unidad == "adimensional":
            return self.axial_strain_percent / 100.0
        if unidad == "permille":
            return self.axial_strain_permille
        raise ValueError("La unidad de deformacion debe ser 'percent', 'adimensional' o 'permille'.")

    def fuerza_pretensado(self, unidad: str = "kN") -> float:
        if unidad == "kN":
            return self.prestress_force_kn
        if unidad == "N":
            return self.prestress_force_kn * 1000.0
        raise ValueError("La unidad de pretensado debe ser 'kN' o 'N'.")


def build_rfem_load_payload(result: LossesResult) -> list[RfemLoadCasePayload]:
    return [
        RfemLoadCasePayload(
            state_name="T0",
            axial_strain_percent=result.rfem.t0_percent,
            axial_strain_permille=result.rfem.t0_permille,
            prestress_force_kn=result.initial_force_per_tendon_kn,
            prestress_stress_mpa=result.sigma_0_mpa,
        ),
        RfemLoadCasePayload(
            state_name="Tinf",
            axial_strain_percent=result.rfem.tinf_percent,
            axial_strain_permille=result.rfem.tinf_permille,
            prestress_force_kn=result.final_force_per_tendon_kn,
            prestress_stress_mpa=result.sigma_inf_mpa,
        ),
    ]

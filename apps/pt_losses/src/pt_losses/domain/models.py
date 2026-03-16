from __future__ import annotations

from dataclasses import dataclass

from pt_losses.domain.materials import ConcreteMaterial, PrestressingSteel
from pt_losses.domain.tendon_geometry import TendonGeometry


@dataclass(frozen=True, slots=True)
class LossesInput:
    steel: PrestressingSteel
    concrete: ConcreteMaterial
    geometry: TendonGeometry
    mu_tesado: float
    mu_fric: float
    k_wobble: float
    anchorage_slip_mm: float
    concrete_stress_at_tendon_mpa: float
    creep_coeff: float
    shrinkage_strain: float
    relaxation_loss_ratio: float

    def __post_init__(self) -> None:
        bounded_ratios = {
            "mu_tesado": self.mu_tesado,
            "mu_fric": self.mu_fric,
            "relaxation_loss_ratio": self.relaxation_loss_ratio,
        }
        for name, value in bounded_ratios.items():
            if not 0 <= value <= 1:
                raise ValueError(f"{name} debe estar entre 0 y 1.")

        if self.k_wobble < 0:
            raise ValueError("k_wobble no puede ser negativo.")
        if self.anchorage_slip_mm < 0:
            raise ValueError("anchorage_slip_mm no puede ser negativo.")
        if self.concrete_stress_at_tendon_mpa < 0:
            raise ValueError("concrete_stress_at_tendon no puede ser negativo.")
        if self.creep_coeff < 0:
            raise ValueError("creep_coeff no puede ser negativo.")
        if self.shrinkage_strain < 0:
            raise ValueError("shrinkage_strain no puede ser negativo.")

    @classmethod
    def from_mapping(cls, data: dict[str, float]) -> "LossesInput":
        return cls(
            steel=PrestressingSteel(
                elastic_modulus_mpa=float(data["Ep"]),
                characteristic_strength_mpa=float(data["fpk"]),
                proof_strength_mpa=float(data["fp01k"]),
            ),
            concrete=ConcreteMaterial(
                elastic_modulus_mpa=float(data["Ec"]),
                compressive_strength_mpa=float(data["fc"]),
            ),
            geometry=TendonGeometry(
                area_mm2=float(data["Ap"]),
                count=int(data["n_tendons"]),
                length_m=float(data["tendon_length"]),
                theta_total_rad=float(data["theta_total"]),
                eccentricity_m=float(data["eccentricity"]),
            ),
            mu_tesado=float(data["mu_tesado"]),
            mu_fric=float(data["mu_fric"]),
            k_wobble=float(data["k_wobble"]),
            anchorage_slip_mm=float(data["anchorage_slip_mm"]),
            concrete_stress_at_tendon_mpa=float(data["concrete_stress_at_tendon"]),
            creep_coeff=float(data["creep_coeff"]),
            shrinkage_strain=float(data["shrinkage_strain"]),
            relaxation_loss_ratio=float(data["relaxation_loss_ratio"]),
        )


@dataclass(frozen=True, slots=True)
class LossComponents:
    eta_fr: float
    eta_anc: float
    eta_el: float
    eta_rel: float
    eta_flu: float
    eta_ret: float
    eta_total: float


@dataclass(frozen=True, slots=True)
class RfemStrainState:
    t0_percent: float
    tinf_percent: float
    t0_permille: float
    tinf_permille: float


@dataclass(frozen=True, slots=True)
class LossesResult:
    sigma_max_mpa: float
    sigma_0_mpa: float
    sigma_inf_mpa: float
    losses: LossComponents
    rfem: RfemStrainState
    initial_force_per_tendon_kn: float
    initial_force_total_kn: float
    final_force_per_tendon_kn: float
    final_force_total_kn: float

    def to_dict(self) -> dict[str, float]:
        return {
            "tension_maxima_MPa": self.sigma_max_mpa,
            "tension_inicial_MPa": self.sigma_0_mpa,
            "tension_final_MPa": self.sigma_inf_mpa,
            "eta_fr": self.losses.eta_fr,
            "eta_anc": self.losses.eta_anc,
            "eta_el": self.losses.eta_el,
            "eta_rel": self.losses.eta_rel,
            "eta_flu": self.losses.eta_flu,
            "eta_ret": self.losses.eta_ret,
            "eta_total": self.losses.eta_total,
            "T0_percent": self.rfem.t0_percent,
            "Tinf_percent": self.rfem.tinf_percent,
            "T0_por_mil": self.rfem.t0_permille,
            "Tinf_por_mil": self.rfem.tinf_permille,
            "fuerza_inicial_por_tendon_kN": self.initial_force_per_tendon_kn,
            "fuerza_inicial_total_kN": self.initial_force_total_kn,
            "fuerza_final_por_tendon_kN": self.final_force_per_tendon_kn,
            "fuerza_final_total_kN": self.final_force_total_kn,
        }

    def to_nested_dict(self) -> dict[str, object]:
        return {
            "resumen": self.to_dict(),
            "perdidas": {
                "eta_fr": self.losses.eta_fr,
                "eta_anc": self.losses.eta_anc,
                "eta_el": self.losses.eta_el,
                "eta_rel": self.losses.eta_rel,
                "eta_flu": self.losses.eta_flu,
                "eta_ret": self.losses.eta_ret,
                "eta_total": self.losses.eta_total,
            },
            "rfem": {
                "T0_percent": self.rfem.t0_percent,
                "Tinf_percent": self.rfem.tinf_percent,
                "T0_por_mil": self.rfem.t0_permille,
                "Tinf_por_mil": self.rfem.tinf_permille,
            },
        }

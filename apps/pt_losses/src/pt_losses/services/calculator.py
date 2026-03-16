from __future__ import annotations

import math

from pt_losses.domain.models import LossComponents, LossesInput, LossesResult, RfemStrainState


MAX_TOTAL_LOSS_RATIO = 0.99


def calculate_losses(loss_input: LossesInput) -> LossesResult:
    sigma_max = loss_input.steel.sigma_max_mpa
    sigma_0 = loss_input.mu_tesado * sigma_max

    eta_fr = _calculate_friction_loss(loss_input)
    eta_anc = _safe_ratio(_calculate_anchorage_loss_mpa(loss_input, sigma_0), sigma_0)
    eta_el = _safe_ratio(_calculate_elastic_shortening_loss_mpa(loss_input), sigma_0)
    eta_flu = _safe_ratio(_calculate_creep_loss_mpa(loss_input), sigma_0)
    eta_ret = _safe_ratio(_calculate_shrinkage_loss_mpa(loss_input), sigma_0)
    eta_rel = loss_input.relaxation_loss_ratio

    eta_total = min(eta_fr + eta_anc + eta_el + eta_rel + eta_flu + eta_ret, MAX_TOTAL_LOSS_RATIO)
    sigma_inf = sigma_0 * (1.0 - eta_total)

    t0_percent = -(sigma_0 / loss_input.steel.elastic_modulus_mpa) * 100.0
    tinf_percent = -(sigma_inf / loss_input.steel.elastic_modulus_mpa) * 100.0

    initial_force_per_tendon_kn = _stress_to_force_kn(sigma_0, loss_input.geometry.area_mm2)
    final_force_per_tendon_kn = _stress_to_force_kn(sigma_inf, loss_input.geometry.area_mm2)

    return LossesResult(
        sigma_max_mpa=sigma_max,
        sigma_0_mpa=sigma_0,
        sigma_inf_mpa=sigma_inf,
        losses=LossComponents(
            eta_fr=eta_fr,
            eta_anc=eta_anc,
            eta_el=eta_el,
            eta_rel=eta_rel,
            eta_flu=eta_flu,
            eta_ret=eta_ret,
            eta_total=eta_total,
        ),
        rfem=RfemStrainState(
            t0_percent=t0_percent,
            tinf_percent=tinf_percent,
            t0_permille=t0_percent * 10.0,
            tinf_permille=tinf_percent * 10.0,
        ),
        initial_force_per_tendon_kn=initial_force_per_tendon_kn,
        initial_force_total_kn=initial_force_per_tendon_kn * loss_input.geometry.count,
        final_force_per_tendon_kn=final_force_per_tendon_kn,
        final_force_total_kn=final_force_per_tendon_kn * loss_input.geometry.count,
    )


def _calculate_friction_loss(loss_input: LossesInput) -> float:
    exponent = -(
        loss_input.mu_fric * loss_input.geometry.theta_total_rad
        + loss_input.k_wobble * loss_input.geometry.length_m
    )
    return 1.0 - math.exp(exponent)


def _calculate_anchorage_loss_mpa(loss_input: LossesInput, sigma_0: float) -> float:
    if sigma_0 <= 0:
        return 0.0
    return loss_input.steel.elastic_modulus_mpa * (
        loss_input.anchorage_slip_mm / loss_input.geometry.length_mm
    )


def _calculate_elastic_shortening_loss_mpa(loss_input: LossesInput) -> float:
    return loss_input.steel.elastic_modulus_mpa * (
        loss_input.concrete_stress_at_tendon_mpa / loss_input.concrete.elastic_modulus_mpa
    )


def _calculate_creep_loss_mpa(loss_input: LossesInput) -> float:
    return loss_input.steel.elastic_modulus_mpa * loss_input.creep_coeff * (
        loss_input.concrete_stress_at_tendon_mpa / loss_input.concrete.elastic_modulus_mpa
    )


def _calculate_shrinkage_loss_mpa(loss_input: LossesInput) -> float:
    return loss_input.steel.elastic_modulus_mpa * loss_input.shrinkage_strain


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _stress_to_force_kn(stress_mpa: float, area_mm2: float) -> float:
    return (stress_mpa * area_mm2) / 1000.0

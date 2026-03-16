import math
import unittest

from pt_losses.domain.models import LossesInput
from pt_losses.services.calculator import MAX_TOTAL_LOSS_RATIO, calculate_losses


def build_sample_input() -> LossesInput:
    return LossesInput.from_mapping(
        {
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
    )


class CalculatorTests(unittest.TestCase):
    def test_calculate_losses_returns_expected_values(self) -> None:
        result = calculate_losses(build_sample_input())

        self.assertAlmostEqual(result.sigma_max_mpa, 1488.0, places=6)
        self.assertAlmostEqual(result.sigma_0_mpa, 1116.0, places=6)
        self.assertAlmostEqual(result.losses.eta_fr, 0.07960283407205615, places=12)
        self.assertAlmostEqual(result.losses.eta_total, 0.3085085899227835, places=12)
        self.assertAlmostEqual(result.sigma_inf_mpa, 771.7044136461736, places=9)
        self.assertAlmostEqual(result.rfem.t0_percent, -0.5723076923076923, places=12)
        self.assertAlmostEqual(result.rfem.tinf_percent, -0.3957458531518839, places=12)
        self.assertAlmostEqual(result.initial_force_per_tendon_kn, 167.4, places=6)
        self.assertAlmostEqual(result.final_force_total_kn, 1389.0679445631124, places=9)

    def test_total_loss_is_capped(self) -> None:
        base = build_sample_input()
        overloaded = LossesInput(
            steel=base.steel,
            concrete=base.concrete,
            geometry=base.geometry,
            mu_tesado=base.mu_tesado,
            mu_fric=1.0,
            k_wobble=0.5,
            anchorage_slip_mm=100.0,
            concrete_stress_at_tendon_mpa=50.0,
            creep_coeff=3.0,
            shrinkage_strain=0.005,
            relaxation_loss_ratio=0.5,
        )

        result = calculate_losses(overloaded)

        self.assertTrue(math.isclose(result.losses.eta_total, MAX_TOTAL_LOSS_RATIO))
        self.assertAlmostEqual(result.sigma_inf_mpa, base.mu_tesado * base.steel.sigma_max_mpa * 0.01, places=6)

    def test_invalid_ratio_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            LossesInput.from_mapping(
                {
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
                    "mu_tesado": 1.2,
                    "mu_fric": 0.19,
                    "k_wobble": 0.0015,
                    "anchorage_slip_mm": 6.0,
                    "concrete_stress_at_tendon": 9.5,
                    "creep_coeff": 1.8,
                    "shrinkage_strain": 0.0002,
                    "relaxation_loss_ratio": 0.025,
                }
            )


if __name__ == "__main__":
    unittest.main()

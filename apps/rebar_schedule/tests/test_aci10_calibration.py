import unittest

from rebar_schedule.services.aci10_calibration import load_aci10_calibration


class Aci10CalibrationTests(unittest.TestCase):
    def test_loads_calibration_from_member_58_analysis(self) -> None:
        calibration = load_aci10_calibration()
        self.assertGreater(calibration.horizontal_span_ratio, 0.8)
        self.assertGreater(calibration.vertical_span_ratio, 0.8)
        self.assertGreater(calibration.crosstie_arc_radius_ratio, 0.05)
        self.assertGreater(calibration.outer_hook_ratio, 0.1)


if __name__ == "__main__":
    unittest.main()

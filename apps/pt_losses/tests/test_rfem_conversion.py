import unittest

from pt_losses.services.rfem_conversion import RfemLoadCasePayload


class RfemConversionTests(unittest.TestCase):
    def test_convierte_a_percent(self) -> None:
        payload = RfemLoadCasePayload(state_name="T0", axial_strain_percent=-0.55)
        self.assertAlmostEqual(payload.deformacion_axial("percent"), -0.55)

    def test_convierte_a_adimensional(self) -> None:
        payload = RfemLoadCasePayload(state_name="T0", axial_strain_percent=-0.55)
        self.assertAlmostEqual(payload.deformacion_axial("adimensional"), -0.0055)


if __name__ == "__main__":
    unittest.main()

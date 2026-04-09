import unittest

from pt_losses.services.rfem_conversion import RfemLoadCasePayload


class RfemConversionTests(unittest.TestCase):
    def _payload(self) -> RfemLoadCasePayload:
        return RfemLoadCasePayload(
            state_name="T0",
            axial_strain_percent=-0.55,
            axial_strain_permille=-5.5,
            prestress_force_kn=167.4,
            prestress_stress_mpa=1116.0,
        )

    def test_convierte_a_percent(self) -> None:
        payload = self._payload()
        self.assertAlmostEqual(payload.deformacion_axial("percent"), -0.55)

    def test_convierte_a_adimensional(self) -> None:
        payload = self._payload()
        self.assertAlmostEqual(payload.deformacion_axial("adimensional"), -0.0055)

    def test_convierte_a_permille(self) -> None:
        payload = self._payload()
        self.assertAlmostEqual(payload.deformacion_axial("permille"), -5.5)

    def test_convierte_fuerza_pretensado_a_kn(self) -> None:
        payload = self._payload()
        self.assertAlmostEqual(payload.fuerza_pretensado("kN"), 167.4)

    def test_convierte_fuerza_pretensado_a_n(self) -> None:
        payload = self._payload()
        self.assertAlmostEqual(payload.fuerza_pretensado("N"), 167400.0)


if __name__ == "__main__":
    unittest.main()

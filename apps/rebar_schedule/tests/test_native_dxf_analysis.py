import unittest
from pathlib import Path

from rebar_schedule.services.native_dxf_analysis import analyze_native_rfem_dxf


class NativeDxfAnalysisTests(unittest.TestCase):
    def test_analyzes_member_58_native_dxf(self) -> None:
        source = Path("build/member-58.dxf")
        payload = analyze_native_rfem_dxf(str(source))

        self.assertIn("Stirrup Ø10", payload["layers"])
        self.assertIn("Rebar Ø16", payload["layers"])
        self.assertGreater(payload["total_entidades"], 100)
        self.assertGreater(payload["ventana_seccion"]["ancho"], 0.1)
        self.assertGreater(payload["ventana_seccion"]["alto"], 0.1)
        self.assertEqual(payload["subformas_seccion"]["cerco_principal"]["layer"], "Stirrup Ø10")
        self.assertEqual(payload["subformas_seccion"]["cruceta_horizontal"]["layer"], "Stirrup Ø6")
        self.assertEqual(payload["subformas_seccion"]["cruceta_vertical"]["layer"], "Stirrup Ø6")


if __name__ == "__main__":
    unittest.main()

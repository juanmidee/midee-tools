import unittest
from pathlib import Path

from rebar_schedule.services.native_dxf_patterns import extract_native_section_patterns


class NativeDxfPatternsTests(unittest.TestCase):
    def test_extracts_pattern_pieces_from_member_58(self) -> None:
        payload = extract_native_section_patterns(
            str(Path("build/member-58.dxf")),
            analysis_path=str(Path("build/member-58.analysis.json")),
        )

        pieces = payload["patrones"]
        self.assertIn("cerco_principal", pieces)
        self.assertIn("cruceta_horizontal", pieces)
        self.assertIn("cruceta_vertical", pieces)
        self.assertGreater(len(pieces["cerco_principal"]["primitivas_locales"]), 8)
        self.assertGreater(len(pieces["cruceta_horizontal"]["primitivas_locales"]), 2)
        self.assertGreater(len(pieces["cruceta_vertical"]["primitivas_locales"]), 2)
        self.assertLess(
            pieces["cerco_principal"]["cantidad_primitivas_unicas"],
            pieces["cerco_principal"]["cantidad_primitivas_brutas"],
        )
        self.assertLess(
            pieces["cruceta_horizontal"]["cantidad_primitivas_unicas"],
            pieces["cruceta_horizontal"]["cantidad_primitivas_brutas"],
        )
        self.assertLess(
            pieces["cruceta_vertical"]["cantidad_primitivas_unicas"],
            pieces["cruceta_vertical"]["cantidad_primitivas_brutas"],
        )


if __name__ == "__main__":
    unittest.main()

import unittest

from rebar_schedule.adapters.rfem_client import RfemRebarAdapter


class ProbeHelpersTests(unittest.TestCase):
    def test_has_active_model_id_handles_basic_payloads(self) -> None:
        self.assertTrue(RfemRebarAdapter._has_active_model_id({"name": "Modelo"}))
        self.assertTrue(RfemRebarAdapter._has_active_model_id({"no": 1}))
        self.assertFalse(RfemRebarAdapter._has_active_model_id({}))
        self.assertFalse(RfemRebarAdapter._has_active_model_id(None))

    def test_element_label_prefers_comment_over_name(self) -> None:
        class Dummy:
            comment = "C1/A1"
            name = "Member 1"

        self.assertEqual(RfemRebarAdapter._element_label(Dummy(), fallback="fallback"), "C1/A1")

    def test_resolve_longitudinal_quantity_and_diameter_doubles_symmetric_count(self) -> None:
        class DummyRow:
            bar_count_symmetrical = 3
            bar_diameter_symmetrical = 0.02

        count, diameter, code, _label = RfemRebarAdapter()._resolve_longitudinal_quantity_and_diameter(DummyRow())
        self.assertEqual(count, 6)
        self.assertEqual(diameter, 0.02)
        self.assertEqual(code, "simetrica")


if __name__ == "__main__":
    unittest.main()

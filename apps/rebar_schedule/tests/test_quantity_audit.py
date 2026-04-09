import unittest

from rebar_schedule.domain.models import ReinforcementItem
from rebar_schedule.services.quantity_audit import build_quantity_audit


class QuantityAuditTests(unittest.TestCase):
    def test_builds_simple_quantity_audit(self) -> None:
        items = [
            ReinforcementItem(
                source_type="member",
                source_id=1,
                host_label="Member 1",
                bar_mark="M1-L1",
                diameter_mm=16.0,
                steel_grade="Calidad 60 | ACI 318-19",
                material_no=2,
                shape_code="LONGITUDINAL",
                count=4,
                cut_length_mm=3000.0,
                segments_mm=[3000.0],
                longitudinal_layout_code="uniformemente_alrededor",
                longitudinal_layout_label="Conjunto uniforme alrededor",
            ),
            ReinforcementItem(
                source_type="member",
                source_id=1,
                host_label="Member 1",
                bar_mark="M1-S1",
                diameter_mm=10.0,
                steel_grade="Calidad 60 | ACI 318-19",
                material_no=2,
                shape_code="STIRRUP_CLOSED",
                count=10,
                cut_length_mm=1000.0,
                segments_mm=[1000.0],
                spacing_mm=100.0,
            ),
        ]
        payload = build_quantity_audit("Modelo simple", items)
        self.assertEqual(payload["resumen"]["total_items"], 2)
        self.assertEqual(payload["items"][0]["diametro_mm"], 16.0)
        self.assertEqual(payload["items"][0]["cantidad"], 4)
        self.assertEqual(payload["criterio_pesos"]["formula"], "kg/m = d_mm^2 / 162")


if __name__ == "__main__":
    unittest.main()

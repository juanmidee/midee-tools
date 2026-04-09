import unittest

from rebar_schedule.domain.models import ReinforcementItem
from rebar_schedule.services.schedule_builder import build_schedule


class ScheduleBuilderTests(unittest.TestCase):
    def test_builds_schedule_with_expected_totals(self) -> None:
        items = [
            ReinforcementItem(
                source_type="member",
                source_id=1,
                host_label="V1",
                bar_mark="V1-01",
                diameter_mm=16,
                steel_grade="ADN 420",
                shape_code="STRAIGHT",
                count=4,
                cut_length_mm=6000,
                segments_mm=[6000],
            ),
            ReinforcementItem(
                source_type="surface",
                source_id=2,
                host_label="S1",
                bar_mark="S1-X1",
                diameter_mm=10,
                steel_grade="ADN 420",
                shape_code="STRAIGHT",
                count=10,
                cut_length_mm=3000,
                segments_mm=[3000],
            ),
        ]

        schedule = build_schedule("Proyecto Demo", items)

        self.assertEqual(schedule.total_bars, 14)
        self.assertEqual(len(schedule.rows), 2)
        self.assertGreater(schedule.total_weight_kg, 0.0)
        self.assertEqual(schedule.rows[0].workshop_shape_code, "ACI-01")
        self.assertEqual(schedule.rows[0].workshop_shape_family, "barra")
        self.assertIsNone(schedule.rows[0].longitudinal_layout_code)

    def test_preserves_longitudinal_layout_metadata(self) -> None:
        items = [
            ReinforcementItem(
                source_type="member",
                source_id=58,
                host_label="Member 58",
                bar_mark="M58-L1",
                diameter_mm=15.875,
                steel_grade="Calidad 60 | ACI 318-19",
                material_no=2,
                longitudinal_layout_code="uniformemente_alrededor",
                longitudinal_layout_label="Conjunto uniforme alrededor",
                shape_code="LONGITUDINAL",
                count=8,
                cut_length_mm=3600,
                segments_mm=[3600],
            )
        ]

        schedule = build_schedule("Proyecto Demo", items)

        self.assertEqual(schedule.rows[0].longitudinal_layout_code, "uniformemente_alrededor")
        self.assertEqual(schedule.rows[0].longitudinal_layout_label, "Conjunto uniforme alrededor")

    def test_uses_rfem_weight_override_when_available(self) -> None:
        items = [
            ReinforcementItem(
                source_type="member",
                source_id=10,
                host_label="V-101",
                bar_mark="M10-L1",
                diameter_mm=20.0,
                steel_grade="Calidad 60 | ACI 318-19",
                shape_code="LONGITUDINAL",
                count=3,
                cut_length_mm=4450.0,
                segments_mm=[4450.0],
                unit_weight_override_kg_m=2.466,
                total_weight_override_kg=32.925,
            )
        ]

        schedule = build_schedule("Proyecto Demo", items)

        self.assertAlmostEqual(schedule.rows[0].unit_weight_kg_m, 2.466, places=3)
        self.assertAlmostEqual(schedule.rows[0].total_weight_kg, 32.925, places=3)


if __name__ == "__main__":
    unittest.main()

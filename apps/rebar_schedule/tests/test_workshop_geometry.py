import unittest

from rebar_schedule.domain.models import RebarScheduleRow
from rebar_schedule.services.workshop_geometry import build_shape_geometry, line_angle_degrees


class WorkshopGeometryTests(unittest.TestCase):
    def _sample_uniform_beam_row(self) -> RebarScheduleRow:
        return RebarScheduleRow(
            source_type="member",
            source_id="MS6",
            host_label="24,28 | Barras continuas",
            bar_mark="MS6-L1",
            shape_code="LONGITUDINAL",
            diameter_mm=19.05,
            steel_grade="Calidad 60 | ACI 318-19",
            material_no=2,
            workshop_shape_code="ACI-01",
            workshop_shape_name="Barra recta",
            workshop_shape_family="barra",
            count=6,
            cut_length_mm=5690.0,
            total_length_m=34.14,
            unit_weight_kg_m=2.24,
            total_weight_kg=76.48,
            segments_mm=[5690.0],
            bending_diameter_mm=118.0,
            hook_detail="3 -> 3",
            stirrup_type=None,
            direction=None,
            spacing_mm=None,
            section_width_mm=200.0,
            section_height_mm=400.0,
            concrete_cover_mm=30.0,
            crossties_active=None,
            longitudinal_layout_code="uniformemente_alrededor",
            longitudinal_layout_label="Conjunto uniforme alrededor",
            notes=None,
        )

    def _sample_stirrup_row(self) -> RebarScheduleRow:
        return RebarScheduleRow(
            source_type="member",
            source_id=58,
            host_label="Member 58",
            bar_mark="58-1",
            shape_code="STIRRUP_CLOSED",
            diameter_mm=9.5,
            steel_grade="Calidad 60 | ACI 318-19",
            material_no=2,
            workshop_shape_code="ACI-10",
            workshop_shape_name="Estribo cerrado de 2 ramas con gancho de 135 grados",
            workshop_shape_family="estribo",
            count=7,
            cut_length_mm=1720.0,
            total_length_m=12.03,
            unit_weight_kg_m=0.56,
            total_weight_kg=6.7,
            segments_mm=[1720.0],
            bending_diameter_mm=60.0,
            hook_detail=None,
            stirrup_type="STIRRUP_TYPE_TWO_LEGGED_CLOSED_HOOK_135",
            direction=None,
            spacing_mm=100.0,
            section_width_mm=300.0,
            section_height_mm=300.0,
            concrete_cover_mm=30.0,
            crossties_active=True,
            notes=None,
        )

    def _sample_simple_stirrup_row(self) -> RebarScheduleRow:
        row = self._sample_stirrup_row()
        row.crossties_active = False
        return row

    def test_builds_aci10_geometry_with_single_outer_hook(self) -> None:
        drawing = build_shape_geometry(
            self._sample_stirrup_row(),
            x=0.0,
            row_top=0.0,
            width=9.4,
            height=3.55,
            shape_layer="BBARRAS",
            text_layer="BTEXTO",
        )
        self.assertIsNotNone(drawing)
        assert drawing is not None
        outer_hooks = [
            line
            for line in drawing.lines
            if abs(abs(line_angle_degrees(line)) - 135.0) < 1.0 and line.x1 > line.x2 and line.y1 > line.y2
        ]
        self.assertEqual(len(outer_hooks), 1)

    def test_adds_label_135_and_spacing(self) -> None:
        drawing = build_shape_geometry(
            self._sample_stirrup_row(),
            x=0.0,
            row_top=0.0,
            width=9.4,
            height=3.55,
            shape_layer="BBARRAS",
            text_layer="BTEXTO",
        )
        assert drawing is not None
        values = [text.value for text in drawing.texts]
        self.assertIn("135%%d", values)
        self.assertIn("c/10", values)
        self.assertEqual(sum(1 for value in values if value == "135%%d"), 1)

    def test_adds_eight_longitudinal_bars_when_there_are_crossties(self) -> None:
        drawing = build_shape_geometry(
            self._sample_stirrup_row(),
            x=0.0,
            row_top=0.0,
            width=9.4,
            height=3.55,
            shape_layer="BBARRAS",
            text_layer="BTEXTO",
        )
        assert drawing is not None
        self.assertEqual(len(drawing.circles), 8)

    def test_adds_four_longitudinal_bars_without_crossties(self) -> None:
        drawing = build_shape_geometry(
            self._sample_simple_stirrup_row(),
            x=0.0,
            row_top=0.0,
            width=9.4,
            height=3.55,
            shape_layer="BBARRAS",
            text_layer="BTEXTO",
        )
        assert drawing is not None
        self.assertEqual(len(drawing.circles), 4)

    def test_builds_rectangular_uniform_longitudinal_section_for_beam_sets(self) -> None:
        drawing = build_shape_geometry(
            self._sample_uniform_beam_row(),
            x=0.0,
            row_top=0.0,
            width=9.4,
            height=3.55,
            shape_layer="BBARRAS",
            text_layer="BTEXTO",
        )
        self.assertIsNone(drawing)

    def test_builds_circular_stirrup_section_with_twelve_bars(self) -> None:
        row = self._sample_simple_stirrup_row()
        row.section_shape_code = "circular"
        row.section_width_mm = 350.0
        row.section_height_mm = 350.0
        row.count = 12
        drawing = build_shape_geometry(
            row,
            x=0.0,
            row_top=0.0,
            width=9.4,
            height=3.55,
            shape_layer="BBARRAS",
            text_layer="BTEXTO",
        )
        assert drawing is not None
        self.assertEqual(len(drawing.circles), 13)


if __name__ == "__main__":
    unittest.main()

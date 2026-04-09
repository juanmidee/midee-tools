import unittest

from rebar_schedule.domain.shape_catalog import (
    get_workshop_shape,
    list_workshop_shapes,
    map_rfem_to_workshop_shape,
)


class ShapeCatalogTests(unittest.TestCase):
    def test_lists_catalog_entries(self) -> None:
        shapes = list_workshop_shapes()
        self.assertGreaterEqual(len(shapes), 8)
        self.assertEqual(shapes[0].code, "ACI-01")

    def test_maps_closed_stirrup_135_from_rfem(self) -> None:
        shape = map_rfem_to_workshop_shape(
            shape_code="STIRRUP_CLOSED",
            stirrup_type="STIRRUP_TYPE_TWO_LEGGED_CLOSED_HOOK_135",
            hook_detail=None,
            crossties_active=True,
        )
        self.assertEqual(shape.code, "ACI-10")
        self.assertIn("135", shape.name_es)

    def test_maps_hooked_bar_from_hook_detail(self) -> None:
        shape = map_rfem_to_workshop_shape(
            shape_code="LONGITUDINAL",
            stirrup_type=None,
            hook_detail="Gancho 90",
            crossties_active=False,
        )
        self.assertEqual(shape.code, "ACI-02")

    def test_can_resolve_shape_by_code(self) -> None:
        shape = get_workshop_shape("ACI-20")
        self.assertEqual(shape.family, "cruceta")
        self.assertIn("Cruceta", shape.name_es)


if __name__ == "__main__":
    unittest.main()

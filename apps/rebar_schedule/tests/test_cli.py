import json
import tempfile
import unittest
from pathlib import Path

from rebar_schedule.cli.main import run


class CliTests(unittest.TestCase):
    def test_generates_json_and_dxf_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            snapshot = base / "snapshot.json"
            output_json = base / "schedule.json"
            output_dxf = base / "schedule.dxf"

            snapshot.write_text(
                json.dumps(
                    {
                        "project_name": "Proyecto CLI",
                        "items": [
                            {
                                "source_type": "member",
                                "source_id": 1,
                                "host_label": "V1",
                                "bar_mark": "V1-01",
                                "diameter_mm": 12,
                                "steel_grade": "ADN 420",
                                "shape_code": "STRAIGHT",
                                "count": 3,
                                "cut_length_mm": 4500,
                                "segments_mm": [4500],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            exit_code = run(
                [
                    "--snapshot",
                    str(snapshot),
                    "--json-output",
                    str(output_json),
                    "--dxf-output",
                    str(output_dxf),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_json.exists())
            self.assertTrue(output_dxf.exists())
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["proyecto"], "Proyecto CLI")


if __name__ == "__main__":
    unittest.main()

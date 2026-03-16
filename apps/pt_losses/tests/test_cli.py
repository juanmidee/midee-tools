import json
import tempfile
import unittest
from pathlib import Path

from pt_losses.cli.main import run


class CliTests(unittest.TestCase):
    def test_cli_writes_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.json"
            output_path = Path(temp_dir) / "output.json"
            input_path.write_text(
                json.dumps(
                    {
                        "Ep": 195000.0,
                        "Ec": 34000.0,
                        "fpk": 1860.0,
                        "fp01k": 1640.0,
                        "fc": 45.0,
                        "Ap": 150.0,
                        "n_tendons": 12,
                        "tendon_length": 32.5,
                        "theta_total": 0.18,
                        "eccentricity": 0.22,
                        "mu_tesado": 0.75,
                        "mu_fric": 0.19,
                        "k_wobble": 0.0015,
                        "anchorage_slip_mm": 6.0,
                        "concrete_stress_at_tendon": 9.5,
                        "creep_coeff": 1.8,
                        "shrinkage_strain": 0.0002,
                        "relaxation_loss_ratio": 0.025,
                    }
                ),
                encoding="utf-8",
            )

            exit_code = run(
                ["--entrada", str(input_path), "--salida", str(output_path), "--exportar-rfem-stub"]
            )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertGreater(
                payload["resumen"]["tension_inicial_MPa"],
                payload["resumen"]["tension_final_MPa"],
            )
            self.assertEqual(payload["rfem_stub"]["estado"], "simulado")

    def test_cli_exige_argumentos_para_rfem_real(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.json"
            input_path.write_text(
                json.dumps(
                    {
                        "Ep": 195000.0,
                        "Ec": 34000.0,
                        "fpk": 1860.0,
                        "fp01k": 1640.0,
                        "fc": 45.0,
                        "Ap": 150.0,
                        "n_tendons": 12,
                        "tendon_length": 32.5,
                        "theta_total": 0.18,
                        "eccentricity": 0.22,
                        "mu_tesado": 0.75,
                        "mu_fric": 0.19,
                        "k_wobble": 0.0015,
                        "anchorage_slip_mm": 6.0,
                        "concrete_stress_at_tendon": 9.5,
                        "creep_coeff": 1.8,
                        "shrinkage_strain": 0.0002,
                        "relaxation_loss_ratio": 0.025,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                run(["--entrada", str(input_path), "--aplicar-en-rfem"])


if __name__ == "__main__":
    unittest.main()

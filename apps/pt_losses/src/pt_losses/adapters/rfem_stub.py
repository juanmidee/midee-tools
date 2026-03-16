from __future__ import annotations

from dataclasses import dataclass

from pt_losses.services.rfem_conversion import RfemLoadCasePayload


@dataclass(slots=True)
class Rfem6AdapterStub:
    """Adaptador simulado para una futura integracion con RFEM 6."""

    endpoint_name: str = "rfem6-stub"

    def export_axial_strain_states(
        self,
        tendon_id: str,
        payloads: list[RfemLoadCasePayload],
    ) -> dict[str, object]:
        return {
            "estado": "simulado",
            "endpoint": self.endpoint_name,
            "id_tendon": tendon_id,
            "cargas": [
                {
                    "estado_temporal": payload.state_name,
                    "deformacion_axial_percent": payload.axial_strain_percent,
                }
                for payload in payloads
            ],
        }

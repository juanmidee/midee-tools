from __future__ import annotations

from dataclasses import dataclass

from pt_losses.domain.models import LossesResult


@dataclass(frozen=True, slots=True)
class RfemLoadCasePayload:
    state_name: str
    axial_strain_percent: float

    def deformacion_axial(self, unidad: str = "percent") -> float:
        if unidad == "percent":
            return self.axial_strain_percent
        if unidad == "adimensional":
            return self.axial_strain_percent / 100.0
        raise ValueError("La unidad de deformacion debe ser 'percent' o 'adimensional'.")


def build_rfem_load_payload(result: LossesResult) -> list[RfemLoadCasePayload]:
    return [
        RfemLoadCasePayload(state_name="T0", axial_strain_percent=result.rfem.t0_percent),
        RfemLoadCasePayload(state_name="Tinf", axial_strain_percent=result.rfem.tinf_percent),
    ]

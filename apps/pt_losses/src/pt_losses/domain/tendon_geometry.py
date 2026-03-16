from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TendonGeometry:
    """Tendon geometry and layout data."""

    area_mm2: float
    count: int
    length_m: float
    theta_total_rad: float
    eccentricity_m: float

    def __post_init__(self) -> None:
        if self.area_mm2 <= 0:
            raise ValueError("Ap debe ser mayor que cero.")
        if self.count <= 0:
            raise ValueError("n_tendons debe ser mayor que cero.")
        if self.length_m <= 0:
            raise ValueError("tendon_length debe ser mayor que cero.")
        if self.theta_total_rad < 0:
            raise ValueError("theta_total no puede ser negativo.")
        if self.eccentricity_m < 0:
            raise ValueError("eccentricity no puede ser negativo.")

    @property
    def length_mm(self) -> float:
        return self.length_m * 1000.0

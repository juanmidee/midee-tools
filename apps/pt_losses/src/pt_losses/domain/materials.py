from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PrestressingSteel:
    """Prestressing steel properties in MPa."""

    elastic_modulus_mpa: float
    characteristic_strength_mpa: float
    proof_strength_mpa: float

    def __post_init__(self) -> None:
        if self.elastic_modulus_mpa <= 0:
            raise ValueError("Ep debe ser mayor que cero.")
        if self.characteristic_strength_mpa <= 0:
            raise ValueError("fpk debe ser mayor que cero.")
        if self.proof_strength_mpa <= 0:
            raise ValueError("fp01k debe ser mayor que cero.")

    @property
    def sigma_max_mpa(self) -> float:
        return min(0.80 * self.characteristic_strength_mpa, 0.94 * self.proof_strength_mpa)


@dataclass(frozen=True, slots=True)
class ConcreteMaterial:
    """Concrete properties in MPa."""

    elastic_modulus_mpa: float
    compressive_strength_mpa: float

    def __post_init__(self) -> None:
        if self.elastic_modulus_mpa <= 0:
            raise ValueError("Ec debe ser mayor que cero.")
        if self.compressive_strength_mpa <= 0:
            raise ValueError("fc debe ser mayor que cero.")

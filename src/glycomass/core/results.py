from pydantic import BaseModel


class Spectrum(BaseModel):
    """Isotope-peak stick spectrum (intensity normalized to 100)."""

    mz: list[float]
    intensity: list[float]


class MassResult(BaseModel):
    """Result of a mass calculation."""

    mono_mz: float
    most_abundant_mz: float
    composition: str
    spectrum: Spectrum

from pydantic import BaseModel, Field


class Spectrum(BaseModel):
    """Spectrum samples with relative intensity normalized to 100."""

    mz: list[float]
    intensity: list[float]


class MassResult(BaseModel):
    """Result of a mass calculation."""

    mono_mz: float
    most_abundant_mz: float
    composition: str
    spectrum: Spectrum = Field(description="Discrete theoretical isotope peaks.")
    profile: Spectrum | None = Field(
        default=None, description="Gaussian display profile; min/max downsampled to at most 12,000 points. Not raw acquisition data."
    )

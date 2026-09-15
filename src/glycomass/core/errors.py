class GlycomassError(ValueError):
    """Base class for glycomass domain errors."""


class NegativeIonSodiumError(GlycomassError):
    """Sodium adduct requested in negative-ion mode (charge <= 0)."""


class InvalidCompositionError(GlycomassError):
    """Malformed custom composition, or a composition with negative or no atoms."""

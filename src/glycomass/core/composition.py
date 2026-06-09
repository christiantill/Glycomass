from __future__ import annotations

from dataclasses import dataclass

ELEMENTS = ("C", "H", "N", "O", "S")


@dataclass(frozen=True)
class Composition:
    """An elemental composition over C, H, N, O, S. Counts may be negative
    (e.g. deamidation, disulfide bridges subtract atoms)."""

    C: int = 0
    H: int = 0
    N: int = 0
    O: int = 0  # noqa: E741
    S: int = 0

    @property
    def counts(self) -> dict[str, int]:
        return {e: getattr(self, e) for e in ELEMENTS}

    def __add__(self, other: Composition) -> Composition:
        return Composition(**{e: getattr(self, e) + getattr(other, e) for e in ELEMENTS})

    def __sub__(self, other: Composition) -> Composition:
        return Composition(**{e: getattr(self, e) - getattr(other, e) for e in ELEMENTS})

    def __mul__(self, n: int) -> Composition:
        return Composition(**{e: getattr(self, e) * n for e in ELEMENTS})

    __rmul__ = __mul__

    def formula(self) -> str:
        """Legacy display format, e.g. 'C34 H53 N7 O15 S0' (C H N O S order)."""
        return " ".join(f"{e}{getattr(self, e)}" for e in ELEMENTS)

    def to_brainpy(self) -> dict[str, int]:
        """Atom dict for brainpy.isotopic_variants()."""
        return self.counts

from __future__ import annotations

import re
from dataclasses import dataclass

from glycomass.core.errors import InvalidCompositionError

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


CUSTOM_COMPOSITION_MAX_LENGTH = 64
CUSTOM_COMPOSITION_MAX_ATOMS = 10_000
_DELTA_SHAPE = re.compile(r"(?:[+-]?[A-Z][a-z]?\d*)+")
_DELTA_TOKEN = re.compile(r"([+-]?)([A-Z][a-z]?)(\d*)")


def canonical_composition_text(text: str) -> str:
    """Remove whitespace and map Unicode minus signs to ASCII."""
    return re.sub(r"\s+", "", text).replace("\u2212", "-")


def parse_composition_delta(text: str) -> Composition:
    """Parse a signed elemental delta such as 'C2H5O', '-C2-H6' or 'C2H5O-H2O'.

    A sign applies to every following element until the next sign, so '-H2O'
    removes water. Omitted counts mean 1 and repeated elements are summed.
    """
    compact = canonical_composition_text(text)
    if not compact:
        return Composition()
    if len(compact) > CUSTOM_COMPOSITION_MAX_LENGTH:
        raise InvalidCompositionError(
            f"Custom modification is limited to {CUSTOM_COMPOSITION_MAX_LENGTH} characters."
        )
    if not _DELTA_SHAPE.fullmatch(compact):
        raise InvalidCompositionError(
            f"Could not read custom modification '{text.strip()}'. "
            "Use element symbols with optional counts and signs, e.g. C2H5O or -C2-H6."
        )
    counts = dict.fromkeys(ELEMENTS, 0)
    sign = 1
    for sign_text, element, count in _DELTA_TOKEN.findall(compact):
        if sign_text:
            sign = -1 if sign_text == "-" else 1
        if element not in counts:
            raise InvalidCompositionError(
                f"Unsupported element '{element}' in custom modification; use C, H, N, O, S."
            )
        counts[element] += sign * int(count or 1)
        if abs(counts[element]) > CUSTOM_COMPOSITION_MAX_ATOMS:
            raise InvalidCompositionError(
                f"Custom modification changes {element} by more than "
                f"{CUSTOM_COMPOSITION_MAX_ATOMS:,} atoms."
            )
    return Composition(**counts)

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from glycomass.core.constants import AMINO_ACIDS


def normalize_sequence(value: object) -> str:
    """Accept whitespace formatting and lowercase, but never discard residue typos."""
    if not isinstance(value, str):
        raise ValueError("Sequence must be text.")
    sequence = "".join(value.split())
    if not sequence or not sequence.isascii() or any(aa not in AMINO_ACIDS for aa in sequence.upper()):
        raise ValueError("Sequence must contain only supported amino-acid letters (ACDEFGHIKLMNPQRSTVWY).")
    return sequence.upper()


PeptideSequence = Annotated[str, BeforeValidator(normalize_sequence), Field(min_length=1, max_length=100)]
ProteinSequence = Annotated[str, BeforeValidator(normalize_sequence), Field(min_length=1, max_length=100000)]



class PeptideRequest(BaseModel):
    sequence: PeptideSequence
    hex: int = 0
    hexnac: int = 0
    fuc: int = 0
    sia: int = 0
    charge: int = 1
    carbamidomethyl: bool = False
    deamidation: int = 0


class ProteinRequest(BaseModel):
    sequence: ProteinSequence
    hex: int = 0
    hexnac: int = 0
    fuc: int = 0
    sia: int = 0
    charge: int = 1
    deamidation: int = 0
    disulfide_bridges: int = 0
    resolution: str = "medium"


class GlycanRequest(BaseModel):
    hex: int = 0
    hexnac: int = 0
    fuc: int = 0
    sia: int = 0
    charge: int = 1
    sodium: bool = False
    modification: str = "None"

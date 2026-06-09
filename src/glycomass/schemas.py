from pydantic import BaseModel


class PeptideRequest(BaseModel):
    sequence: str
    hex: int = 0
    hexnac: int = 0
    fuc: int = 0
    sia: int = 0
    charge: int = 1
    carbamidomethyl: bool = False
    deamidation: int = 0


class ProteinRequest(BaseModel):
    sequence: str
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

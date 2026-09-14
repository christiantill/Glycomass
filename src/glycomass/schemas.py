from pydantic import BaseModel, Field


class PeptideRequest(BaseModel):
    sequence: str = Field(min_length=1, max_length=100)
    hex: int = 0
    hexnac: int = 0
    fuc: int = 0
    sia: int = 0
    charge: int = 1
    carbamidomethyl: bool = False
    deamidation: int = 0


class ProteinRequest(BaseModel):
    sequence: str = Field(min_length=1, max_length=100000)
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

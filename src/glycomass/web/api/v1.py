from fastapi import APIRouter, HTTPException

from glycomass.core import (
    MassResult,
    glycan_mass,
    peptide_mass,
    protein_mass,
)
from glycomass.core.errors import GlycomassError
from glycomass.schemas import GlycanRequest, PeptideRequest, ProteinRequest

router = APIRouter(prefix="/api/v1", tags=["calculate"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/calculate/peptide", response_model=MassResult)
def calculate_peptide(req: PeptideRequest) -> MassResult:
    return peptide_mass(
        req.sequence, hex=req.hex, hexnac=req.hexnac, fuc=req.fuc, sia=req.sia,
        charge=req.charge, carbamidomethyl=req.carbamidomethyl, deamidation=req.deamidation,
    )


@router.post("/calculate/protein", response_model=MassResult)
def calculate_protein(req: ProteinRequest) -> MassResult:
    try:
        return protein_mass(
            req.sequence, hex=req.hex, hexnac=req.hexnac, fuc=req.fuc, sia=req.sia,
            charge=req.charge, deamidation=req.deamidation,
            disulfide_bridges=req.disulfide_bridges, resolution=req.resolution,
        )
    except GlycomassError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown resolution: {req.resolution}") from exc


@router.post("/calculate/glycan", response_model=MassResult)
def calculate_glycan(req: GlycanRequest) -> MassResult:
    try:
        return glycan_mass(
            hex=req.hex, hexnac=req.hexnac, fuc=req.fuc, sia=req.sia,
            charge=req.charge, sodium=req.sodium, modification=req.modification,
            custom_modification=req.custom_modification,
        )
    except GlycomassError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

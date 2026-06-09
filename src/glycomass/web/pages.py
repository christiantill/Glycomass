from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from glycomass.core import NegativeIonSodiumError, glycan_mass, peptide_mass, protein_mass

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.get("/peptide", response_class=HTMLResponse)
def peptide_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "peptide.html")


@router.post("/peptide", response_class=HTMLResponse)
def peptide_result(
    request: Request,
    sequence: str = Form(...),
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), carbamidomethyl: bool = Form(False), deamidation: int = Form(0),
) -> HTMLResponse:
    result = peptide_mass(
        sequence, hex=hex, hexnac=hexnac, fuc=fuc, sia=sia,
        charge=charge, carbamidomethyl=carbamidomethyl, deamidation=deamidation,
    )
    return templates.TemplateResponse(request, "_result.html", {"result": result})


@router.get("/protein", response_class=HTMLResponse)
def protein_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "protein.html")


@router.post("/protein", response_class=HTMLResponse)
def protein_result(
    request: Request,
    sequence: str = Form(...),
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), deamidation: int = Form(0),
    disulfide_bridges: int = Form(0), resolution: str = Form("medium"),
) -> HTMLResponse:
    result = protein_mass(
        sequence, hex=hex, hexnac=hexnac, fuc=fuc, sia=sia, charge=charge,
        deamidation=deamidation, disulfide_bridges=disulfide_bridges, resolution=resolution,
    )
    return templates.TemplateResponse(request, "_result.html", {"result": result})


@router.get("/glycan", response_class=HTMLResponse)
def glycan_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "glycan.html")


@router.post("/glycan", response_class=HTMLResponse)
def glycan_result(
    request: Request,
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), sodium: bool = Form(False), modification: str = Form("None"),
) -> HTMLResponse:
    try:
        result = glycan_mass(
            hex=hex, hexnac=hexnac, fuc=fuc, sia=sia,
            charge=charge, sodium=sodium, modification=modification,
        )
    except NegativeIonSodiumError as exc:
        return templates.TemplateResponse(request, "_error.html", {"message": str(exc)})
    return templates.TemplateResponse(request, "_result.html", {"result": result})

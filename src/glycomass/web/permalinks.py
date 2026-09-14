from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from glycomass.core import MassResult, glycan_mass, peptide_mass, protein_mass
from glycomass.db.models import Permalink

# Default form inputs per calculator — drive the empty pages AND fill missing keys
# during normalization. Values match the original Phase 2 template defaults.
DEFAULTS: dict[str, dict[str, Any]] = {
    "peptide": {
        "sequence": "PEPTIDE", "hex": 0, "hexnac": 0, "fuc": 0, "sia": 0,
        "charge": 1, "carbamidomethyl": False, "deamidation": 0,
    },
    "protein": {
        "sequence": "ACDEFGHIKLMNPQRSTVWY", "hex": 0, "hexnac": 0, "fuc": 0, "sia": 0,
        "charge": 5, "deamidation": 0, "disulfide_bridges": 0, "resolution": "medium",
    },
    "glycan": {
        "hex": 5, "hexnac": 4, "fuc": 0, "sia": 0,
        "charge": 1, "sodium": False, "modification": "None",
    },
}
TEMPLATES = {"peptide": "peptide.html", "protein": "protein.html", "glycan": "glycan.html"}


def normalize(kind: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize inputs so equivalent calculations hash identically: fill missing keys
    from DEFAULTS, drop unknown keys, upper-case the sequence (the calculators do too)."""
    out = {**DEFAULTS[kind], **{k: v for k, v in inputs.items() if k in DEFAULTS[kind]}}
    if "sequence" in out:
        out["sequence"] = str(out["sequence"]).upper()
    if kind == "glycan" and out["modification"] == "Peracetyl":
        out["modification"] = "Peracetly"  # preserve existing URLs and template value
    return out


def compute_slug(kind: str, inputs: dict[str, Any]) -> str:
    payload = json.dumps(
        {"kind": kind, **normalize(kind, inputs)}, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def compute_result(kind: str, inputs: dict[str, Any]) -> MassResult:
    i = normalize(kind, inputs)
    if kind == "peptide":
        return peptide_mass(
            i["sequence"], hex=i["hex"], hexnac=i["hexnac"], fuc=i["fuc"], sia=i["sia"],
            charge=i["charge"], carbamidomethyl=i["carbamidomethyl"], deamidation=i["deamidation"],
        )
    if kind == "protein":
        return protein_mass(
            i["sequence"], hex=i["hex"], hexnac=i["hexnac"], fuc=i["fuc"], sia=i["sia"],
            charge=i["charge"], deamidation=i["deamidation"],
            disulfide_bridges=i["disulfide_bridges"], resolution=i["resolution"],
        )
    return glycan_mass(
        hex=i["hex"], hexnac=i["hexnac"], fuc=i["fuc"], sia=i["sia"],
        charge=i["charge"], sodium=i["sodium"], modification=i["modification"],
    )


async def save_permalink(session: AsyncSession, kind: str, inputs: dict[str, Any]) -> str:
    norm = normalize(kind, inputs)
    slug = compute_slug(kind, norm)
    if await session.get(Permalink, slug) is None:
        session.add(Permalink(slug=slug, kind=kind, inputs=norm))
        try:
            await session.commit()
        except IntegrityError:  # concurrent insert of the same slug — fine
            await session.rollback()
    return slug

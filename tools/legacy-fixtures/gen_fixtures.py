"""Generate ground-truth fixtures from the DEPLOYED Glycomass mass-calc code.

Runs the real app/masscalc.py functions (peptidemass / proteinmass / glycanmass)
over a curated input matrix inside the pinned legacy stack (see Dockerfile), and
records monomz / mostab / composition. The base64 PNG (3rd return field) is a
rendering, not ground truth, so it is discarded.

These fixtures are the contract the rewrite must reproduce (within tolerance),
except for documented legacy bugs we intend to deliberately fix.
"""
import json
import os
import sys

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl")

REPO = os.environ.get("REPO", "/work")
# Import masscalc.py STANDALONE (not via the `app` package, which builds a Flask
# app at import time). masscalc.py's only non-stdlib top-level import is rq.
sys.path.insert(0, os.path.join(REPO, "app"))
import masscalc  # noqa: E402


def parse(ret):
    """Legacy return is 'monomz,mostab,plot_url,composition' (None on guard branch).

    composition has spaces but no commas; the base64 plot_url has no commas; the
    two leading floats are %.4f formatted -> splitting on ',' yields exactly 4 parts.
    """
    if ret is None:
        return None
    parts = ret.split(",")
    assert len(parts) == 4, "unexpected return shape: {!r}".format(parts)
    return {
        "monomz": float(parts[0]),
        "mostab": float(parts[1]),
        "composition": parts[3],
    }


# --- peptidemass(Peptide, Hex, HexNAc, Fuc, Sia, Charge, Carbamido, Deamidation) ---
PEPTIDE_ARGS = ["Peptide", "Hex", "HexNAc", "Fuc", "Sia", "Charge", "Carbamido", "Deamidation"]
PEPTIDE_CASES = [
    ("PEPTIDE", 0, 0, 0, 0, 1, 0, 0),                  # bare peptide, z=1
    ("PEPTIDE", 0, 0, 0, 0, 2, 0, 0),                  # z=2
    ("PEPTIDE", 0, 0, 0, 0, 3, 0, 0),                  # z=3
    ("GG", 0, 0, 0, 0, 1, 0, 0),                       # smallest
    ("MMMM", 0, 0, 0, 0, 1, 0, 0),                     # sulfur-heavy
    ("ACDEFGHIKLMNPQRSTVWY", 0, 0, 0, 0, 2, 0, 0),     # all 20 amino acids
    ("ACDEFGHIKLMNPQRSTVWY", 0, 0, 0, 0, 2, 1, 0),     # + carbamidomethyl on Cys
    ("NLTSVCWK", 5, 4, 1, 2, 2, 0, 0),                 # glycopeptide, Hex5HexNAc4Fuc1Sia2
    ("NLTSVCWK", 5, 4, 1, 2, 2, 1, 0),                 # + carbamidomethyl
    ("NLTSVCWK", 5, 4, 0, 0, 1, 0, 0),                 # Hex5HexNAc4, z=1
    ("PEPTIDE", 3, 2, 0, 0, 1, 0, 0),                  # small glycan
    ("NLTSVK", 0, 0, 0, 0, 1, 0, 1),                   # deamidation = 1
    ("NLTSVK", 0, 0, 0, 0, 1, 0, 2),                   # deamidation = 2
]

# --- proteinmass(Protein, Hex, HexNAc, Fuc, Sia, Charge, Deamidation, Disulfidebridges, resolution) ---
PROTEIN_ARGS = ["Protein", "Hex", "HexNAc", "Fuc", "Sia", "Charge", "Deamidation", "Disulfidebridges", "resolution"]
PROTEIN_CASES = [
    ("ACDEFGHIKLMNPQRSTVWY", 0, 0, 0, 0, 5, 0, 0, "low"),
    ("ACDEFGHIKLMNPQRSTVWY", 0, 0, 0, 0, 5, 0, 0, "medium"),
    ("ACDEFGHIKLMNPQRSTVWY", 0, 0, 0, 0, 10, 0, 0, "super high"),  # high z keeps grid small
    ("ACDEFGHIKLMNPQRSTVWY", 0, 0, 0, 0, 10, 0, 0, "low"),
    ("ACDEFGHIKLMNPQRSTVWY", 5, 4, 1, 2, 5, 0, 0, "medium"),       # glycoprotein
    ("ACDEFGHIKLMNPQRSTVWY", 0, 0, 0, 0, 5, 1, 0, "medium"),       # deamidation
    ("CCACCAGGKL", 0, 0, 0, 0, 3, 0, 0, "medium"),                 # 4 Cys, denatured (0 bridges)
    ("CCACCAGGKL", 0, 0, 0, 0, 3, 0, 1, "medium"),                 # 1 disulfide bridge
    ("CCACCAGGKL", 0, 0, 0, 0, 3, 0, 2, "medium"),                 # 2 disulfide bridges
    ("AG", 0, 0, 0, 0, 1, 0, 1, "low"),                            # bridges > Cys (legacy warning case)
]

# --- glycanmass(Hex, HexNAc, Fuc, Sia, Charge, Sodium, Modification) ---
GLYCAN_ARGS = ["Hex", "HexNAc", "Fuc", "Sia", "Charge", "Sodium", "Modification"]
GLYCAN_CASES = [
    (5, 4, 0, 0, 1, False, "None"),        # Hex5HexNAc4, no mod
    (5, 4, 1, 2, 1, False, "None"),        # full N-glycan
    (5, 4, 1, 2, 2, False, "None"),        # z=2
    (3, 2, 0, 0, 1, False, "None"),
    (1, 0, 0, 0, 1, False, "None"),        # single hexose
    (5, 4, 0, 0, 1, True, "None"),         # sodium adduct
    (5, 4, 0, 0, -1, False, "None"),       # negative ion, no sodium (computes)
    (5, 4, 0, 0, -1, True, "None"),        # GUARD: sodium + negative -> returns None
    (5, 4, 1, 2, 1, False, "Permethyl"),
    (5, 4, 1, 2, 1, False, "Peracetly"),   # (sic) matches legacy literal
    (5, 4, 1, 2, 1, False, "ReducedEnd"),
    (5, 4, 1, 2, 1, False, "Label_2AB"),
    (5, 4, 1, 2, 1, False, "Label_2AA"),
    (5, 4, 1, 2, 1, True, "Permethyl"),    # sodium + permethyl
]


def run_group(name, fn, argnames, cases):
    out = []
    for c in cases:
        inputs = dict(zip(argnames, c))
        rec = {"inputs": inputs}
        try:
            parsed = parse(fn(*c))
            if parsed is None:
                rec["result"] = None
                rec["note"] = "function returned None (guard branch hit)"
            else:
                rec.update(parsed)
        except Exception as exc:  # capture per-case; never abort the whole run
            rec["error"] = "{}: {}".format(type(exc).__name__, exc)
        print(name, inputs, "->", rec.get("monomz", rec.get("error", rec.get("note"))), flush=True)
        out.append(rec)
    return out


def versions():
    info = {"python": sys.version.split()[0]}
    for mod in ("numpy", "matplotlib", "brainpy"):
        try:
            info[mod] = __import__(mod).__version__
        except Exception as exc:
            info[mod] = "unknown ({})".format(exc)
    return info


def main():
    fixtures = {
        "_meta": {
            "description": "Ground-truth outputs of the deployed app/masscalc.py, captured "
                           "in the pinned legacy stack. The rewrite must reproduce these "
                           "(tolerance ~1e-3 on m/z) except documented legacy-bug fixes.",
            "source": "app/masscalc.py @ commit 83ecbbc (deployed)",
            "precision": "monomz/mostab are the app's %.4f display values; composition is exact.",
            "brainpy_pinned": "brain-isotopic-distribution @ "
                              "git+https://github.com/mobiusklein/brainpy.git@d27e726a67b086936990cbbcef74a827fc1542ff",
            "versions": versions(),
        },
        "peptidemass": run_group("peptidemass", masscalc.peptidemass, PEPTIDE_ARGS, PEPTIDE_CASES),
        "proteinmass": run_group("proteinmass", masscalc.proteinmass, PROTEIN_ARGS, PROTEIN_CASES),
        "glycanmass": run_group("glycanmass", masscalc.glycanmass, GLYCAN_ARGS, GLYCAN_CASES),
    }
    out_dir = os.path.join(REPO, "fixtures")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "legacy_masscalc.json")
    with open(out_path, "w") as fh:
        json.dump(fixtures, fh, indent=2)
        fh.write("\n")
    n = sum(len(fixtures[k]) for k in ("peptidemass", "proteinmass", "glycanmass"))
    print("\nWROTE {} fixtures -> {}".format(n, out_path), flush=True)


if __name__ == "__main__":
    main()

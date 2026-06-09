"""Generate a LARGE sharded grid of ground-truth fixtures from the deployed masscalc.

Usage (inside the pinned legacy py3.7 container):
    python tools/legacy-fixtures/gen_grid.py <category>

Categories: peptide_a peptide_b protein_a protein_b glycan_a glycan_b
Each writes fixtures/shards/<category>.json. Merge them with merge_grid (controller).

This expands the curated 37-case fixtures into ~800 cases for a comprehensive
golden parity check of the rewrite's core. Same capture rules as gen_fixtures.py
(monomz/mostab/composition; base64 PNG discarded; glycan guard -> result: null).
"""
import itertools
import json
import os
import sys

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl")

REPO = os.environ.get("REPO", "/work")
sys.path.insert(0, os.path.join(REPO, "app"))
import masscalc  # noqa: E402

PEPTIDE_ARGS = ["Peptide", "Hex", "HexNAc", "Fuc", "Sia", "Charge", "Carbamido", "Deamidation"]
PROTEIN_ARGS = ["Protein", "Hex", "HexNAc", "Fuc", "Sia", "Charge", "Deamidation", "Disulfidebridges", "resolution"]
GLYCAN_ARGS = ["Hex", "HexNAc", "Fuc", "Sia", "Charge", "Sodium", "Modification"]


def parse(ret):
    if ret is None:
        return None
    parts = ret.split(",")
    return {"monomz": float(parts[0]), "mostab": float(parts[1]), "composition": parts[3]}


def run(name, fn, argnames, cases):
    out = []
    for c in cases:
        rec = {"inputs": dict(zip(argnames, c))}
        try:
            res = parse(fn(*c))
            if res is None:
                rec["result"] = None
            else:
                rec.update(res)
        except Exception as exc:  # noqa: BLE001
            rec["error"] = "{}: {}".format(type(exc).__name__, exc)
        out.append(rec)
    print(name, len(out), "cases", flush=True)
    return out


# ---- grids ----
PEP_A = ["PEPTIDE", "NLTSVCWK", "ACDEFGHIKLMNPQRSTVWY", "GGGGGGK", "MCMCMCK",
         "STNVTKR", "ELVISLIVESK", "NKTRPF", "HKMWYFC", "CCCAAAKKR"]
PEP_B = ["NLTSVCWK", "SVSELPCFR", "EEQYNSTYR", "LCPDCPLLAPLNDSR", "MMMCCCK"]
PROT_A = ["ACDEFGHIKLMNPQRSTVWY", "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ",
          "CCACCAGGKLNVTSEDR", "GHIKLMNPQRSTVWYACDEFG"]
PROT_B = ["ACDEFGHIKLMNPQRSTVWY", "CCACCAGGKL", "MKTAYIAKQRQ"]


def cases_for(category):
    if category == "peptide_a":
        return ("peptidemass", masscalc.peptidemass, PEPTIDE_ARGS, [
            (seq, h, n, f, s, z, 0, 0)
            for seq in PEP_A
            for (h, n, f, s) in [(0, 0, 0, 0), (5, 4, 1, 2)]
            for z in (1, 2, 3)
        ])
    if category == "peptide_b":
        return ("peptidemass", masscalc.peptidemass, PEPTIDE_ARGS, [
            (seq, h, n, f, s, z, carb, deam)
            for seq in PEP_B
            for (h, n, f, s) in [(5, 4, 0, 0), (3, 2, 0, 0), (6, 5, 1, 3)]
            for z in (1, 2)
            for carb in (0, 1)
            for deam in (0, 1)
        ])
    if category == "protein_a":
        return ("proteinmass", masscalc.proteinmass, PROTEIN_ARGS, [
            (seq, h, n, f, s, z, 0, br, res)
            for seq in PROT_A
            for (h, n, f, s) in [(0, 0, 0, 0), (5, 4, 1, 2)]
            for z in (3, 5, 10)
            for br in (0, 1)
            for res in ("low", "medium")
        ])
    if category == "protein_b":
        return ("proteinmass", masscalc.proteinmass, PROTEIN_ARGS, [
            (seq, 0, 0, 0, 0, z, 0, br, "super high")
            for seq in PROT_B
            for z in (8, 10, 15)
            for br in (0, 1, 2)
        ])
    if category == "glycan_a":
        return ("glycanmass", masscalc.glycanmass, GLYCAN_ARGS, [
            (h, n, f, s, z, False, "None")
            for h in (3, 4, 5, 6, 7)
            for n in (2, 3, 4, 5)
            for f in (0, 1)
            for s in (0, 1, 2)
            for z in (1, 2)
        ])
    if category == "glycan_b":
        mods = [
            (h, n, f, s, 1, False, mod)
            for h in (4, 5, 6)
            for n in (3, 4)
            for f in (0, 1)
            for s in (0, 1, 2)
            for mod in ("Permethyl", "Peracetly", "ReducedEnd", "Label_2AB", "Label_2AA")
        ]
        sodium = [
            (h, n, f, s, z, True, "None")
            for h in (4, 5, 6)
            for n in (3, 4)
            for f in (0, 1)
            for s in (0, 1, 2)
            for z in (1, 2)
        ]
        return ("glycanmass", masscalc.glycanmass, GLYCAN_ARGS, mods + sodium)
    raise SystemExit("unknown category: {}".format(category))


def main():
    category = sys.argv[1]
    group, fn, argnames, cases = cases_for(category)
    records = run(category, fn, argnames, cases)
    out_dir = os.path.join(REPO, "fixtures", "shards")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "{}.json".format(category))
    with open(out_path, "w") as fh:
        json.dump({"group": group, "category": category, "records": records}, fh, indent=2)
        fh.write("\n")
    print("WROTE", len(records), "->", out_path, flush=True)


if __name__ == "__main__":
    main()

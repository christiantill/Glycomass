"""Single source of truth for elemental compositions.

Ported verbatim from the deployed app/masscalc.py; pinned by fixtures/legacy_masscalc.json.
"""
from glycomass.core.composition import Composition as C

WATER = C(C=0, H=2, N=0, O=1, S=0)

# Amino-acid RESIDUE compositions (peptide = sum(residues) + 1 WATER).
AMINO_ACIDS: dict[str, C] = {
    "A": C(C=3, H=5, N=1, O=1, S=0),
    "R": C(C=6, H=12, N=4, O=1, S=0),
    "N": C(C=4, H=6, N=2, O=2, S=0),
    "D": C(C=4, H=5, N=1, O=3, S=0),
    "C": C(C=3, H=5, N=1, O=1, S=1),
    "Q": C(C=5, H=8, N=2, O=2, S=0),
    "E": C(C=5, H=7, N=1, O=3, S=0),
    "G": C(C=2, H=3, N=1, O=1, S=0),
    "H": C(C=6, H=7, N=3, O=1, S=0),
    "I": C(C=6, H=11, N=1, O=1, S=0),
    "L": C(C=6, H=11, N=1, O=1, S=0),
    "K": C(C=6, H=12, N=2, O=1, S=0),
    "M": C(C=5, H=9, N=1, O=1, S=1),
    "F": C(C=9, H=9, N=1, O=1, S=0),
    "P": C(C=5, H=7, N=1, O=1, S=0),
    "S": C(C=3, H=5, N=1, O=2, S=0),
    "T": C(C=4, H=7, N=1, O=2, S=0),
    "W": C(C=11, H=10, N=2, O=1, S=0),
    "Y": C(C=9, H=9, N=1, O=2, S=0),
    "V": C(C=5, H=9, N=1, O=1, S=0),
}
CARBAMIDOMETHYL_CYS = C(C=5, H=8, N=2, O=2, S=1)  # Cys + carbamidomethyl

# Per-count modifiers.
DEAMIDATION = C(C=0, H=-1, N=-1, O=1, S=0)       # added Deamidation times
DISULFIDE_BRIDGE = C(C=0, H=2, N=0, O=0, S=0)    # SUBTRACTED per bridge (-2 H)

# Native (underivatized) monosaccharide RESIDUE compositions.
HEX = C(C=6, H=10, N=0, O=5, S=0)
HEXNAC = C(C=8, H=13, N=1, O=5, S=0)
FUC = C(C=6, H=10, N=0, O=4, S=0)
SIA = C(C=11, H=17, N=1, O=8, S=0)

# Permethylated monosaccharides + reducing-end add group.
HEX_PERMETHYL = C(C=9, H=16, N=0, O=5, S=0)
HEXNAC_PERMETHYL = C(C=11, H=19, N=1, O=5, S=0)
FUC_PERMETHYL = C(C=8, H=14, N=0, O=4, S=0)
SIA_PERMETHYL = C(C=16, H=27, N=1, O=8, S=0)
PERMETHYL_ADD = C(C=2, H=4, N=0, O=0, S=0)

# Peracetylated monosaccharides + reducing-end add group.
HEX_PERACETYL = C(C=12, H=16, N=0, O=8, S=0)
HEXNAC_PERACETYL = C(C=12, H=17, N=1, O=7, S=0)
FUC_PERACETYL = C(C=10, H=14, N=0, O=6, S=0)
SIA_PERACETYL = C(C=17, H=23, N=1, O=11, S=0)
PERACETYL_ADD = C(C=4, H=4, N=0, O=2, S=0)

# Reducing-end labels (added to the native glycan).
REDUCED_END = C(C=0, H=2, N=0, O=0, S=0)
LABEL_2AB = C(C=7, H=8, N=2, O=0, S=0)
LABEL_2AA = C(C=7, H=7, N=1, O=1, S=0)
# Procainamide (C13H21N3O) by reductive amination: + label - H2O (Schiff base) + H2
# (reduction) = + C13H21N3, +219.1735 Da monoisotopic (Waters app note 720004212).
LABEL_PROCAINAMIDE = C(C=13, H=21, N=3, O=0, S=0)

# Sodium adduct shift constants (m/z): swap a proton for Na+.
SODIUM_MASS = 22.989770
PROTON_MASS = 1.0

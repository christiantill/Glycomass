"""Glycopeptide-identifier constants (ported from the legacy script)."""
# Monoisotopic mass of one HexNAc residue, C8H13NO5 = 203.0794 Da. The legacy script
# used 203.0866 (≈+0.0072 Da off, ~7 ppm at 1 kDa) and was internally inconsistent with
# HEXNAC_DIFF below, which is centred on the correct value. There is no identifier ground
# truth, so we use the chemically-correct residue mass.
HEXNAC_RESIDUE = 203.0794       # Da, one HexNAc (monoisotopic C8H13NO5)
PROTON = 1.007276466621         # Da (accurate proton mass; distinct from core.constants.PROTON_MASS=1.0)
HEXNAC_DIFF = (203.02, 203.12)  # m/z window for a single-HexNAc peak spacing
MIN_FRAGMENT_MZ = 700.0         # ignore Pep+HexNAc candidates below this
OXONIUM_HEXNACHEX = (366.125, 366.16)   # HexNAc+Hex oxonium
OXONIUM_HEXNACHEX2 = (657.16, 657.29)
FILTER_WINDOWS = ((292.0, 292.5), (366.1, 367.3), (657.0, 658.5))

"""Glycopeptide-identifier constants (ported from the legacy script)."""
HEXNAC_RESIDUE = 203.0866       # Da, one HexNAc
PROTON = 1.007276466621         # Da
HEXNAC_DIFF = (203.02, 203.12)  # m/z window for a single-HexNAc peak spacing
MIN_FRAGMENT_MZ = 700.0         # ignore Pep+HexNAc candidates below this
OXONIUM_HEXNACHEX = (366.125, 366.16)   # HexNAc+Hex oxonium
OXONIUM_HEXNACHEX2 = (657.16, 657.29)
FILTER_WINDOWS = ((292.0, 292.5), (366.1, 367.3), (657.0, 658.5))

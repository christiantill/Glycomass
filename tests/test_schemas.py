from glycomass.schemas import GlycanRequest, PeptideRequest, ProteinRequest


def test_peptide_request_defaults():
    r = PeptideRequest(sequence="PEPTIDE")
    assert r.charge == 1 and r.hex == 0 and r.carbamidomethyl is False and r.deamidation == 0


def test_protein_request_resolution_default():
    assert ProteinRequest(sequence="ACDE").resolution == "medium"


def test_glycan_request_defaults():
    r = GlycanRequest(hex=5, hexnac=4)
    assert r.charge == 1 and r.sodium is False and r.modification == "None"

import json

from smiles_converter.features import (
    build_feature_json,
    calculate_payload_sha256,
    validate_feature_json,
)


def test_ethanol_privacy_mode():
    data = build_feature_json(
        "CCO",
        include_canonical_smiles=False,
        strict_environment=False,
    )

    validate_feature_json(
        data,
        require_canonical_smiles=False,
    )

    p = data["payload"]

    assert "canonical_smiles" not in p
    assert len(p["descriptor_names"]) == len(p["descriptors"])
    assert len(p["fingerprints"]["atompair"]) == 2048
    assert len(p["fingerprints"]["maccs"]) == 167
    assert len(p["fingerprints"]["morgan_r2"]) == 2048
    assert len(p["fingerprints"]["morgan_r3"]) == 2048
    assert len(p["graph"]["atom_x"]) == 3
    assert len(p["graph"]["atom_x"][0]) == 40
    assert len(p["graph"]["bond_x"][0]) == 13
    assert data["sha256"] == calculate_payload_sha256(p)


def test_ethanol_complete_mode():
    data = build_feature_json(
        "CCO",
        include_canonical_smiles=True,
        strict_environment=False,
    )

    validate_feature_json(
        data,
        require_canonical_smiles=True,
    )

    assert data["payload"]["canonical_smiles"] == "CCO"

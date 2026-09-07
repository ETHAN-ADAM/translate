#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
smiles转化器 - molecular feature backend

Produces the molecular-feature JSON used by the IC50 model.

Feature set:
- RDKit full descriptors (expected: 217 with RDKit 2026.03.5)
- Morgan radius 2 / ECFP4: 2048 bits
- Morgan radius 3 / ECFP6: 2048 bits
- AtomPair: 2048 bits
- MACCS: 167 bits
- Directed D-MPNN graph
  - atom_x: 40 features per atom
  - bond_x: 13 features per directed bond
  - edge_index
  - rev_edge
- rdkit_version
- schema
- sha256

"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Dict, List

import numpy as np
from rdkit import Chem, DataStructs, rdBase
from rdkit.Chem import Descriptors, MACCSkeys, rdFingerprintGenerator

SCHEMA = "ic50-v431-molecular-features-1"
EXPECTED_RDKIT_VERSION = "2026.03.5"
EXPECTED_DESCRIPTOR_COUNT = 217

FP_CONFIG = {
    "morgan_r2": 2048,
    "morgan_r3": 2048,
    "atompair": 2048,
    "maccs": 167,
}

ATOM_NUM_CHOICES = [1, 5, 6, 7, 8, 9, 14, 15, 16, 17, 35, 53]
DEGREE_CHOICES = [0, 1, 2, 3, 4, 5]
FORMAL_CHARGE_CHOICES = [-2, -1, 0, 1, 2]

HYBRIDIZATION_CHOICES = [
    Chem.rdchem.HybridizationType.SP,
    Chem.rdchem.HybridizationType.SP2,
    Chem.rdchem.HybridizationType.SP3,
    Chem.rdchem.HybridizationType.SP3D,
    Chem.rdchem.HybridizationType.SP3D2,
]

CHIRAL_CHOICES = [
    Chem.rdchem.ChiralType.CHI_UNSPECIFIED,
    Chem.rdchem.ChiralType.CHI_TETRAHEDRAL_CW,
    Chem.rdchem.ChiralType.CHI_TETRAHEDRAL_CCW,
]

BOND_TYPE_CHOICES = [
    Chem.rdchem.BondType.SINGLE,
    Chem.rdchem.BondType.DOUBLE,
    Chem.rdchem.BondType.TRIPLE,
    Chem.rdchem.BondType.AROMATIC,
]

STEREO_CHOICES = [
    Chem.rdchem.BondStereo.STEREONONE,
    Chem.rdchem.BondStereo.STEREOZ,
    Chem.rdchem.BondStereo.STEREOE,
    Chem.rdchem.BondStereo.STEREOCIS,
    Chem.rdchem.BondStereo.STEREOTRANS,
]


def one_hot_with_other(value, choices) -> List[float]:
    out = [1.0 if value == choice else 0.0 for choice in choices]
    out.append(1.0 if value not in choices else 0.0)
    return out


def bitvect_to_list(fp, nbits: int) -> List[int]:
    arr = np.zeros((nbits,), dtype=np.uint8)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return arr.astype(int).tolist()


def safe_descriptor_value(fn, mol) -> float:
    try:
        value = float(fn(mol))
        return value if math.isfinite(value) else float("nan")
    except Exception:
        return float("nan")


def canonicalize_smiles(smiles: str) -> str:
    smiles = str(smiles).strip()
    if not smiles:
        raise ValueError("SMILES 不能为空。")

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"无效 SMILES：{smiles}")

    return Chem.MolToSmiles(
        mol,
        canonical=True,
        isomericSmiles=True,
    )


def atom_features(atom: Chem.Atom) -> np.ndarray:
    feat: List[float] = []

    feat += one_hot_with_other(atom.GetAtomicNum(), ATOM_NUM_CHOICES)
    feat += one_hot_with_other(atom.GetDegree(), DEGREE_CHOICES)
    feat += one_hot_with_other(atom.GetFormalCharge(), FORMAL_CHARGE_CHOICES)
    feat += one_hot_with_other(atom.GetHybridization(), HYBRIDIZATION_CHOICES)
    feat += one_hot_with_other(atom.GetChiralTag(), CHIRAL_CHOICES)

    feat += [
        float(atom.GetIsAromatic()),
        float(atom.IsInRing()),
        float(atom.GetTotalNumHs(includeNeighbors=True)) / 4.0,
        float(atom.GetMass()) / 200.0,
    ]

    arr = np.asarray(feat, dtype=np.float32)
    if arr.shape != (40,):
        raise RuntimeError(f"atom_x 应为 40 维，实际为 {arr.shape[0]} 维。")

    return arr


def bond_features(bond: Chem.Bond) -> np.ndarray:
    feat: List[float] = []
    feat += one_hot_with_other(bond.GetBondType(), BOND_TYPE_CHOICES)
    feat += one_hot_with_other(bond.GetStereo(), STEREO_CHOICES)
    feat += [
        float(bond.GetIsConjugated()),
        float(bond.IsInRing()),
    ]

    arr = np.asarray(feat, dtype=np.float32)
    if arr.shape != (13,):
        raise RuntimeError(f"bond_x 应为 13 维，实际为 {arr.shape[0]} 维。")

    return arr


def mol_to_graph(mol: Chem.Mol) -> Dict[str, Any]:
    if mol.GetNumAtoms() == 0:
        raise ValueError("分子中没有原子。")

    atom_x = np.stack(
        [atom_features(atom) for atom in mol.GetAtoms()],
        axis=0,
    ).astype(np.float32)

    srcs: List[int] = []
    dsts: List[int] = []
    bond_rows: List[np.ndarray] = []
    rev: List[int] = []

    for bond in mol.GetBonds():
        a = bond.GetBeginAtomIdx()
        b = bond.GetEndAtomIdx()
        bf = bond_features(bond)

        e1 = len(srcs)
        srcs.append(a)
        dsts.append(b)
        bond_rows.append(bf)

        e2 = len(srcs)
        srcs.append(b)
        dsts.append(a)
        bond_rows.append(bf)

        rev.extend([e2, e1])

    if not srcs:
        edge_index = np.zeros((2, 0), dtype=np.int64)
        proto = Chem.MolFromSmiles("CC").GetBondWithIdx(0)
        bond_x = np.zeros((0, len(bond_features(proto))), dtype=np.float32)
        rev_edge = np.zeros((0,), dtype=np.int64)
    else:
        edge_index = np.asarray([srcs, dsts], dtype=np.int64)
        bond_x = np.stack(bond_rows, axis=0).astype(np.float32)
        rev_edge = np.asarray(rev, dtype=np.int64)

    return {
        "atom_x": atom_x.tolist(),
        "bond_x": bond_x.tolist(),
        "edge_index": edge_index.tolist(),
        "rev_edge": rev_edge.tolist(),
    }


def build_descriptors(mol: Chem.Mol):
    spec = [(str(name), fn) for name, fn in Descriptors._descList]
    names = [name for name, _ in spec]
    values = [safe_descriptor_value(fn, mol) for _, fn in spec]
    return names, values


def build_fingerprints(mol: Chem.Mol) -> Dict[str, List[int]]:
    morgan_r2 = rdFingerprintGenerator.GetMorganGenerator(
        radius=2,
        fpSize=FP_CONFIG["morgan_r2"],
    )
    morgan_r3 = rdFingerprintGenerator.GetMorganGenerator(
        radius=3,
        fpSize=FP_CONFIG["morgan_r3"],
    )
    atompair = rdFingerprintGenerator.GetAtomPairGenerator(
        fpSize=FP_CONFIG["atompair"],
    )

    return {
        "atompair": bitvect_to_list(
            atompair.GetFingerprint(mol),
            FP_CONFIG["atompair"],
        ),
        "maccs": bitvect_to_list(
            MACCSkeys.GenMACCSKeys(mol),
            FP_CONFIG["maccs"],
        ),
        "morgan_r2": bitvect_to_list(
            morgan_r2.GetFingerprint(mol),
            FP_CONFIG["morgan_r2"],
        ),
        "morgan_r3": bitvect_to_list(
            morgan_r3.GetFingerprint(mol),
            FP_CONFIG["morgan_r3"],
        ),
    }


def calculate_payload_sha256(payload: Dict[str, Any]) -> str:
    payload_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=True,
    ).encode("utf-8")
    return hashlib.sha256(payload_bytes).hexdigest()


def build_feature_json(
    smiles: str,
    strict_environment: bool = True,
) -> Dict[str, Any]:
    """
    Build the complete feature JSON.

    strict_environment=True enforces:
    - 217 descriptors
    - RDKit 2026.03.5

    This is recommended for production IC50-model compatibility.
    """
    canonical = canonicalize_smiles(smiles)
    mol = Chem.MolFromSmiles(canonical)

    if mol is None:
        raise ValueError("RDKit 无法重新构建 canonical molecule。")

    descriptor_names, descriptor_values = build_descriptors(mol)

    if strict_environment:
        if len(descriptor_names) != EXPECTED_DESCRIPTOR_COUNT:
            raise RuntimeError(
                f"RDKit descriptor 数量不匹配："
                f"期望 {EXPECTED_DESCRIPTOR_COUNT}，实际 {len(descriptor_names)}。"
            )
        if rdBase.rdkitVersion != EXPECTED_RDKIT_VERSION:
            raise RuntimeError(
                f"RDKit 版本不匹配：期望 {EXPECTED_RDKIT_VERSION}，"
                f"实际 {rdBase.rdkitVersion}。"
            )

    payload: Dict[str, Any] = {
        "descriptor_names": descriptor_names,
        "descriptors": descriptor_values,
        "fingerprint_sizes": {
            "atompair": FP_CONFIG["atompair"],
            "maccs": FP_CONFIG["maccs"],
            "morgan_r2": FP_CONFIG["morgan_r2"],
            "morgan_r3": FP_CONFIG["morgan_r3"],
        },
        "fingerprints": build_fingerprints(mol),
        "graph": mol_to_graph(mol),
        "rdkit_version": rdBase.rdkitVersion,
        "schema": SCHEMA,
    }

    return {
        "payload": payload,
        "sha256": calculate_payload_sha256(payload),
    }


def validate_feature_json(data: Dict[str, Any]) -> None:
    if "payload" not in data or "sha256" not in data:
        raise AssertionError("缺少 payload 或 sha256。")

    payload = data["payload"]

    required = {
        "descriptor_names",
        "descriptors",
        "fingerprint_sizes",
        "fingerprints",
        "graph",
        "rdkit_version",
        "schema",
    }
    missing = required - set(payload)
    if missing:
        raise AssertionError(f"缺少字段：{sorted(missing)}")

    if len(payload["descriptor_names"]) != len(payload["descriptors"]):
        raise AssertionError("descriptor_names 与 descriptors 长度不一致。")

    expected_fp = {
        "atompair": 2048,
        "maccs": 167,
        "morgan_r2": 2048,
        "morgan_r3": 2048,
    }

    for name, size in expected_fp.items():
        if len(payload["fingerprints"][name]) != size:
            raise AssertionError(
                f"{name} 长度错误："
                f"{len(payload['fingerprints'][name])} != {size}"
            )

    graph = payload["graph"]
    if graph["atom_x"] and len(graph["atom_x"][0]) != 40:
        raise AssertionError("atom_x 不是 40 维。")
    if graph["bond_x"] and len(graph["bond_x"][0]) != 13:
        raise AssertionError("bond_x 不是 13 维。")

    expected_sha = calculate_payload_sha256(payload)
    if data["sha256"] != expected_sha:
        raise AssertionError("SHA256 校验失败。")


def environment_report() -> Dict[str, Any]:
    descriptor_count = len(Descriptors._descList)
    return {
        "rdkit_version": rdBase.rdkitVersion,
        "expected_rdkit_version": EXPECTED_RDKIT_VERSION,
        "descriptor_count": descriptor_count,
        "expected_descriptor_count": EXPECTED_DESCRIPTOR_COUNT,
        "compatible": (
            rdBase.rdkitVersion == EXPECTED_RDKIT_VERSION
            and descriptor_count == EXPECTED_DESCRIPTOR_COUNT
        ),
    }

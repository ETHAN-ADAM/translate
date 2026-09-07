#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from rdkit import Chem


@dataclass
class MoleculeRow:
    name: str
    smiles: str


def is_valid_smiles(text: str) -> bool:
    text = str(text).strip()
    if not text:
        return False
    try:
        return Chem.MolFromSmiles(text) is not None
    except Exception:
        return False


def safe_filename(text: str, fallback: str = "molecule") -> str:
    text = re.sub(r'[<>:"/\\|?*\r\n\t]+', "_", str(text)).strip(" ._")
    return text[:100] or fallback


def parse_pasted_smiles(text: str) -> List[MoleculeRow]:
    """
    Supported:
      CCO
      CCN

    or:
      ethanol<TAB>CCO
      ethylamine<TAB>CCN

    or:
      CCO<TAB>ethanol
    """
    result: List[MoleculeRow] = []
    index = 1

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        if is_valid_smiles(line):
            result.append(MoleculeRow(f"molecule_{index:04d}", line))
            index += 1
            continue

        parts = None
        if "\t" in line:
            parts = [part.strip() for part in line.split("\t", 1)]
        elif "," in line:
            parts = [part.strip() for part in line.split(",", 1)]
        elif ";" in line:
            parts = [part.strip() for part in line.split(";", 1)]

        if parts and len(parts) == 2:
            a, b = parts
            a_valid = is_valid_smiles(a)
            b_valid = is_valid_smiles(b)

            if a_valid and not b_valid:
                result.append(MoleculeRow(b or f"molecule_{index:04d}", a))
                index += 1
                continue

            if b_valid:
                result.append(MoleculeRow(a or f"molecule_{index:04d}", b))
                index += 1
                continue

        # keep invalid row so GUI can show it
        result.append(MoleculeRow(f"molecule_{index:04d}", line))
        index += 1

    return result


def _detect_delimiter(text: str) -> str:
    if "\t" in text:
        return "\t"
    if text.count(",") >= text.count(";"):
        return ","
    return ";"


def read_smiles_table(path: Path) -> List[MoleculeRow]:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    if not raw.strip():
        raise ValueError("输入文件为空。")

    delimiter = _detect_delimiter(raw[:5000])
    rows = list(csv.reader(raw.splitlines(), delimiter=delimiter))

    if not rows:
        raise ValueError("没有读取到任何数据。")

    header = [str(x).strip() for x in rows[0]]
    normalized = [x.lower().replace(" ", "_") for x in header]

    smiles_aliases = {
        "smiles",
        "isomeric_smiles",
        "molecule_smiles",
        "structure",
    }
    name_aliases = {
        "name",
        "id",
        "compound",
        "compound_name",
        "molecule",
        "molecule_id",
        "compound_id",
        "title",
    }

    smiles_idx: Optional[int] = None
    name_idx: Optional[int] = None

    for i, col in enumerate(normalized):
        if smiles_idx is None and col in smiles_aliases:
            smiles_idx = i
        if name_idx is None and col in name_aliases:
            name_idx = i

    start_row = 1

    if smiles_idx is None:
        width = max(len(row) for row in rows[:50])
        best_idx = None
        best_score = -1

        for i in range(width):
            values = [
                row[i].strip()
                for row in rows[:30]
                if i < len(row) and row[i].strip()
            ]
            if not values:
                continue

            score = sum(is_valid_smiles(value) for value in values[:20])
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx is None or best_score <= 0:
            raise ValueError("无法识别 SMILES 列。")

        smiles_idx = best_idx

        if smiles_idx < len(rows[0]) and is_valid_smiles(rows[0][smiles_idx]):
            start_row = 0

    result: List[MoleculeRow] = []
    index = 1

    for row in rows[start_row:]:
        if smiles_idx >= len(row):
            continue

        smiles = row[smiles_idx].strip()
        if not smiles:
            continue

        name = ""
        if name_idx is not None and name_idx < len(row):
            name = row[name_idx].strip()

        if not name:
            name = f"molecule_{index:04d}"

        result.append(MoleculeRow(name=name, smiles=smiles))
        index += 1

    if not result:
        raise ValueError("文件中没有可用的 SMILES。")

    return result


def save_json(data: dict, path: Path, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        if pretty:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=True,
            )
        else:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=True,
            )

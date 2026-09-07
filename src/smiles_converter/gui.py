#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from typing import List

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from rdkit import Chem

from . import __app_name__, __version__
from .features import (
    build_feature_json,
    canonicalize_smiles,
    environment_report,
    validate_feature_json,
)
from .io_utils import (
    MoleculeRow,
    is_valid_smiles,
    parse_pasted_smiles,
    read_smiles_table,
    safe_filename,
    save_json,
)


APP_NAME = __app_name__


class SmilesConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{__version__}")
        self.geometry("1040x780")
        self.minsize(920, 680)

        self.include_canonical = tk.BooleanVar(value=False)
        self.pretty_json = tk.BooleanVar(value=False)
        self.strict_environment = tk.BooleanVar(value=True)
        self.batch_output_mode = tk.StringVar(value="individual")

        self.status_var = tk.StringVar(value="就绪：所有计算均在本机离线完成")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.file_path_var = tk.StringVar()

        self.imported_rows: List[MoleculeRow] = []
        self.result_queue = queue.Queue()

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(
            root,
            text=APP_NAME,
            font=("TkDefaultFont", 21, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            root,
            text="SMILES → 完整分子特征 JSON | 完全离线 | 不上传分子结构",
        ).pack(anchor="w", pady=(2, 10))

        env = environment_report()
        env_text = (
            f"RDKit {env['rdkit_version']} | "
            f"Descriptors {env['descriptor_count']} | "
            f"{'环境匹配' if env['compatible'] else '环境不匹配'}"
        )
        self.env_label = ttk.Label(root, text=env_text)
        self.env_label.pack(anchor="w", pady=(0, 10))

        settings = ttk.LabelFrame(root, text="输出与兼容性设置", padding=10)
        settings.pack(fill="x", pady=(0, 10))

        ttk.Checkbutton(
            settings,
            text='包含 "canonical_smiles"',
            variable=self.include_canonical,
        ).pack(side="left", padx=(0, 18))

        ttk.Checkbutton(
            settings,
            text="美化 JSON",
            variable=self.pretty_json,
        ).pack(side="left", padx=(0, 18))

        ttk.Checkbutton(
            settings,
            text="严格锁定模型环境（推荐）",
            variable=self.strict_environment,
        ).pack(side="left")

        ttk.Label(
            settings,
            text="默认隐私模式：不写入 canonical_smiles",
        ).pack(side="right")

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        tab_single = ttk.Frame(notebook, padding=14)
        tab_paste = ttk.Frame(notebook, padding=14)
        tab_file = ttk.Frame(notebook, padding=14)

        notebook.add(tab_single, text="单个 SMILES")
        notebook.add(tab_paste, text="多个 SMILES")
        notebook.add(tab_file, text="CSV / TSV / TXT")

        self._build_single_tab(tab_single)
        self._build_batch_tab(tab_paste)
        self._build_file_tab(tab_file)

        ttk.Separator(root).pack(fill="x", pady=(12, 8))

        self.progress = ttk.Progressbar(
            root,
            variable=self.progress_var,
            maximum=100.0,
            mode="determinate",
        )
        self.progress.pack(fill="x", pady=(0, 8))

        bottom = ttk.Frame(root)
        bottom.pack(fill="x")

        ttk.Label(bottom, textvariable=self.status_var).pack(side="left")
        ttk.Label(
            bottom,
            text=f"{APP_NAME} v{__version__}",
        ).pack(side="right")

    def _build_single_tab(self, parent):
        ttk.Label(
            parent,
            text="输入一个 SMILES",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(anchor="w")

        self.single_text = tk.Text(parent, height=5, wrap="word")
        self.single_text.pack(fill="x", pady=(8, 8))

        examples = ttk.Frame(parent)
        examples.pack(fill="x")

        ttk.Button(
            examples,
            text="示例：乙醇 CCO",
            command=lambda: self._set_single("CCO"),
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            examples,
            text="示例：苯 c1ccccc1",
            command=lambda: self._set_single("c1ccccc1"),
        ).pack(side="left")

        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(16, 0))

        ttk.Button(
            actions,
            text="验证 SMILES",
            command=self._validate_single,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            actions,
            text="生成并保存 JSON",
            command=self._export_single,
        ).pack(side="left")

        self.single_info = tk.Text(
            parent,
            height=15,
            wrap="word",
            state="disabled",
        )
        self.single_info.pack(fill="both", expand=True, pady=(14, 0))

    def _build_batch_tab(self, parent):
        ttk.Label(
            parent,
            text="一次输入多个 SMILES",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            parent,
            text=(
                "支持每行一个 SMILES；也支持“名称<TAB>SMILES”"
                "或“SMILES<TAB>名称”。"
            ),
        ).pack(anchor="w", pady=(2, 8))

        self.batch_text = tk.Text(parent, height=17, wrap="none")
        self.batch_text.pack(fill="both", expand=True)

        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(10, 0))

        ttk.Button(
            controls,
            text="填入示例",
            command=self._fill_batch_example,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            controls,
            text="检查全部 SMILES",
            command=self._check_batch_text,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            controls,
            text="批量生成",
            command=self._export_batch_text,
        ).pack(side="left")

        self._build_output_modes(parent)

    def _build_file_tab(self, parent):
        ttk.Label(
            parent,
            text="导入 CSV / TSV / TXT",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            parent,
            text="优先识别 SMILES 列；没有标准列名时会自动猜测。",
        ).pack(anchor="w", pady=(2, 10))

        line = ttk.Frame(parent)
        line.pack(fill="x")

        ttk.Entry(
            line,
            textvariable=self.file_path_var,
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            line,
            text="选择文件",
            command=self._choose_file,
        ).pack(side="left", padx=(8, 0))

        self.file_preview = tk.Text(
            parent,
            height=18,
            wrap="none",
            state="disabled",
        )
        self.file_preview.pack(fill="both", expand=True, pady=(12, 0))

        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(10, 0))

        ttk.Button(
            actions,
            text="重新读取",
            command=self._load_file,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            actions,
            text="批量生成",
            command=self._export_file_rows,
        ).pack(side="left")

        self._build_output_modes(parent)

    def _build_output_modes(self, parent):
        box = ttk.LabelFrame(parent, text="批量输出方式", padding=8)
        box.pack(fill="x", pady=(12, 0))

        ttk.Radiobutton(
            box,
            text="每个分子单独 JSON",
            variable=self.batch_output_mode,
            value="individual",
        ).pack(side="left", padx=(0, 18))

        ttk.Radiobutton(
            box,
            text="一个 JSONL",
            variable=self.batch_output_mode,
            value="jsonl",
        ).pack(side="left", padx=(0, 18))

        ttk.Radiobutton(
            box,
            text="一个 JSON 数组",
            variable=self.batch_output_mode,
            value="array",
        ).pack(side="left")

    def _set_single(self, value: str):
        self.single_text.delete("1.0", "end")
        self.single_text.insert("1.0", value)

    def _fill_batch_example(self):
        self.batch_text.delete("1.0", "end")
        self.batch_text.insert(
            "1.0",
            "乙醇\tCCO\n乙胺\tCCN\n苯\tc1ccccc1\n",
        )

    def _set_single_info(self, text: str):
        self.single_info.configure(state="normal")
        self.single_info.delete("1.0", "end")
        self.single_info.insert("1.0", text)
        self.single_info.configure(state="disabled")

    def _validate_single(self):
        smiles = self.single_text.get("1.0", "end").strip()
        if not smiles:
            messagebox.showwarning(APP_NAME, "请输入 SMILES。")
            return

        try:
            canonical = canonicalize_smiles(smiles)
            mol = Chem.MolFromSmiles(canonical)
            self._set_single_info(
                "验证成功\n\n"
                f"原子数：{mol.GetNumAtoms()}\n"
                f"化学键数：{mol.GetNumBonds()}\n"
                f"内部 canonical SMILES：{canonical}\n\n"
                "默认隐私模式下，该字段不会写入 JSON。"
            )
        except Exception as exc:
            self._set_single_info(f"验证失败：{exc}")
            messagebox.showerror(APP_NAME, str(exc))

    def _export_single(self):
        smiles = self.single_text.get("1.0", "end").strip()
        if not smiles:
            messagebox.showwarning(APP_NAME, "请输入 SMILES。")
            return

        filename = filedialog.asksaveasfilename(
            title="保存分子特征 JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("所有文件", "*.*")],
        )
        if not filename:
            return

        try:
            self.status_var.set("正在计算分子特征...")
            self.update_idletasks()

            data = build_feature_json(
                smiles,
                include_canonical_smiles=bool(self.include_canonical.get()),
                strict_environment=bool(self.strict_environment.get()),
            )
            validate_feature_json(
                data,
                require_canonical_smiles=bool(self.include_canonical.get()),
            )
            save_json(
                data,
                Path(filename),
                pretty=bool(self.pretty_json.get()),
            )

            payload = data["payload"]
            self._set_single_info(
                "生成成功\n\n"
                f"Descriptors：{len(payload['descriptors'])}\n"
                f"AtomPair：{len(payload['fingerprints']['atompair'])}\n"
                f"MACCS：{len(payload['fingerprints']['maccs'])}\n"
                f"ECFP4：{len(payload['fingerprints']['morgan_r2'])}\n"
                f"ECFP6：{len(payload['fingerprints']['morgan_r3'])}\n"
                f"Graph atoms：{len(payload['graph']['atom_x'])}\n"
                f"Directed edges：{len(payload['graph']['rev_edge'])}\n"
                f"RDKit：{payload['rdkit_version']}\n"
                f"SHA256：{data['sha256']}\n\n"
                f"保存位置：{filename}"
            )
            self.status_var.set("完成")
            messagebox.showinfo(APP_NAME, "JSON 已成功生成。")

        except Exception as exc:
            self.status_var.set("生成失败")
            messagebox.showerror(APP_NAME, str(exc))

    def _validate_rows(self, rows):
        invalid = []
        valid = 0

        for i, row in enumerate(rows, start=1):
            if is_valid_smiles(row.smiles):
                valid += 1
            else:
                invalid.append((i, row.name, row.smiles))

        return valid, invalid

    def _check_batch_text(self):
        rows = parse_pasted_smiles(
            self.batch_text.get("1.0", "end")
        )
        if not rows:
            messagebox.showwarning(APP_NAME, "没有检测到任何 SMILES。")
            return

        valid, invalid = self._validate_rows(rows)

        if not invalid:
            messagebox.showinfo(
                APP_NAME,
                f"共 {len(rows)} 个分子，全部有效。",
            )
            return

        preview = "\n".join(
            f"第 {i} 条：{name} | {smiles}"
            for i, name, smiles in invalid[:10]
        )
        messagebox.showwarning(
            APP_NAME,
            f"有效：{valid}\n无效：{len(invalid)}\n\n{preview}",
        )

    def _export_batch_text(self):
        rows = parse_pasted_smiles(
            self.batch_text.get("1.0", "end")
        )
        self._start_batch(rows)

    def _choose_file(self):
        filename = filedialog.askopenfilename(
            title="选择包含 SMILES 的文件",
            filetypes=[
                ("表格文本", "*.csv *.tsv *.txt"),
                ("CSV", "*.csv"),
                ("TSV/TXT", "*.tsv *.txt"),
                ("所有文件", "*.*"),
            ],
        )
        if not filename:
            return

        self.file_path_var.set(filename)
        self._load_file()

    def _load_file(self):
        filename = self.file_path_var.get().strip()
        if not filename:
            return

        try:
            rows = read_smiles_table(Path(filename))
            self.imported_rows = rows

            preview = ["名称\tSMILES"]
            preview.extend(
                f"{row.name}\t{row.smiles}"
                for row in rows[:100]
            )
            if len(rows) > 100:
                preview.append(f"... 共 {len(rows)} 条")

            self.file_preview.configure(state="normal")
            self.file_preview.delete("1.0", "end")
            self.file_preview.insert("1.0", "\n".join(preview))
            self.file_preview.configure(state="disabled")

            valid, invalid = self._validate_rows(rows)
            self.status_var.set(
                f"已读取 {len(rows)} 条：有效 {valid}，无效 {len(invalid)}"
            )

        except Exception as exc:
            self.imported_rows = []
            messagebox.showerror(APP_NAME, str(exc))

    def _export_file_rows(self):
        if not self.imported_rows:
            self._load_file()

        if self.imported_rows:
            self._start_batch(self.imported_rows)

    def _start_batch(self, rows):
        if not rows:
            messagebox.showwarning(APP_NAME, "没有可处理的数据。")
            return

        valid, invalid = self._validate_rows(rows)
        if invalid:
            preview = "\n".join(
                f"第 {i} 条：{name} | {smiles}"
                for i, name, smiles in invalid[:10]
            )
            messagebox.showerror(
                APP_NAME,
                f"检测到 {len(invalid)} 个无效 SMILES。\n"
                "请修正后再生成。\n\n"
                f"{preview}",
            )
            return

        mode = self.batch_output_mode.get()

        if mode == "individual":
            target = filedialog.askdirectory(
                title="选择 JSON 输出文件夹"
            )
        elif mode == "jsonl":
            target = filedialog.asksaveasfilename(
                title="保存 JSONL",
                defaultextension=".jsonl",
                filetypes=[("JSON Lines", "*.jsonl")],
            )
        else:
            target = filedialog.asksaveasfilename(
                title="保存 JSON 数组",
                defaultextension=".json",
                filetypes=[("JSON", "*.json")],
            )

        if not target:
            return

        include_canonical = bool(self.include_canonical.get())
        pretty = bool(self.pretty_json.get())
        strict = bool(self.strict_environment.get())

        self.progress_var.set(0.0)
        self.status_var.set(f"正在处理 {len(rows)} 个分子...")

        thread = threading.Thread(
            target=self._batch_worker,
            args=(
                rows,
                mode,
                Path(target),
                include_canonical,
                pretty,
                strict,
            ),
            daemon=True,
        )
        thread.start()

    def _batch_worker(
        self,
        rows,
        mode,
        target,
        include_canonical,
        pretty,
        strict,
    ):
        try:
            if mode == "individual":
                target.mkdir(parents=True, exist_ok=True)
                used_names = {}

                for index, row in enumerate(rows, start=1):
                    data = build_feature_json(
                        row.smiles,
                        include_canonical_smiles=include_canonical,
                        strict_environment=strict,
                    )
                    validate_feature_json(
                        data,
                        require_canonical_smiles=include_canonical,
                    )

                    base = safe_filename(
                        row.name,
                        f"molecule_{index:04d}",
                    )
                    count = used_names.get(base, 0) + 1
                    used_names[base] = count

                    filename = (
                        f"{base}.json"
                        if count == 1
                        else f"{base}_{count}.json"
                    )

                    save_json(
                        data,
                        target / filename,
                        pretty=pretty,
                    )
                    self.result_queue.put(
                        ("progress", index, len(rows))
                    )

            elif mode == "jsonl":
                target.parent.mkdir(parents=True, exist_ok=True)

                with target.open("w", encoding="utf-8") as f:
                    for index, row in enumerate(rows, start=1):
                        data = build_feature_json(
                            row.smiles,
                            include_canonical_smiles=include_canonical,
                            strict_environment=strict,
                        )
                        validate_feature_json(
                            data,
                            require_canonical_smiles=include_canonical,
                        )

                        record = {"name": row.name, **data}
                        f.write(
                            json.dumps(
                                record,
                                ensure_ascii=False,
                                sort_keys=True,
                                separators=(",", ":"),
                                allow_nan=True,
                            )
                        )
                        f.write("\n")

                        self.result_queue.put(
                            ("progress", index, len(rows))
                        )

            else:
                output = []

                for index, row in enumerate(rows, start=1):
                    data = build_feature_json(
                        row.smiles,
                        include_canonical_smiles=include_canonical,
                        strict_environment=strict,
                    )
                    validate_feature_json(
                        data,
                        require_canonical_smiles=include_canonical,
                    )

                    output.append({"name": row.name, **data})
                    self.result_queue.put(
                        ("progress", index, len(rows))
                    )

                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("w", encoding="utf-8") as f:
                    if pretty:
                        json.dump(
                            output,
                            f,
                            ensure_ascii=False,
                            sort_keys=True,
                            indent=2,
                            allow_nan=True,
                        )
                    else:
                        json.dump(
                            output,
                            f,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                            allow_nan=True,
                        )

            self.result_queue.put(
                ("done", len(rows), str(target))
            )

        except Exception as exc:
            self.result_queue.put(("error", str(exc)))

    def _poll_queue(self):
        try:
            while True:
                msg = self.result_queue.get_nowait()

                if msg[0] == "progress":
                    _, current, total = msg
                    pct = current / max(total, 1) * 100.0
                    self.progress_var.set(pct)
                    self.status_var.set(
                        f"正在处理：{current}/{total} ({pct:.1f}%)"
                    )

                elif msg[0] == "done":
                    _, total, target = msg
                    self.progress_var.set(100.0)
                    self.status_var.set(
                        f"完成：已处理 {total} 个分子"
                    )
                    messagebox.showinfo(
                        APP_NAME,
                        f"批量转换完成。\n\n"
                        f"分子数：{total}\n"
                        f"输出：{target}",
                    )

                elif msg[0] == "error":
                    self.progress_var.set(0.0)
                    self.status_var.set("批量转换失败")
                    messagebox.showerror(APP_NAME, msg[1])

        except queue.Empty:
            pass

        self.after(100, self._poll_queue)


def main():
    app = SmilesConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()

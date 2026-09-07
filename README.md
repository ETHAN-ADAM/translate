# smiles转化器

**smiles转化器** 是一个完全离线的 SMILES → 分子特征 JSON 图形界面工具。

它用于把 SMILES 转换为与 IC50 模型输入一致的分子特征，包括：

- RDKit full descriptors（目标环境：217 项）
- Morgan radius 2 / ECFP4：2048 bit
- Morgan radius 3 / ECFP6：2048 bit
- AtomPair：2048 bit
- MACCS：167 bit
- D-MPNN 分子图
  - `atom_x`：40 维
  - `bond_x`：13 维
  - `edge_index`
  - `rev_edge`
- `rdkit_version`
- `schema`
- `sha256`

默认隐私模式下 **不输出 `canonical_smiles`**。GUI 中可手动勾选后输出。

---

## 1. 终端用户下载

GitHub Actions 构建后会生成：

### Windows

```text
smiles转化器.exe
```

直接双击运行，不需要安装 Python、Conda 或 RDKit。

### macOS

```text
smiles转化器.app
```

GitHub Release 中以 ZIP 形式提供。

### Linux

```text
smiles转化器-Linux-x86_64
```

---

## 2. 输入方式

### 单个 SMILES

例如：

```text
CCO
```

### 多个 SMILES：每行一个

```text
CCO
CCN
c1ccccc1
```

### 多个 SMILES：名称 + SMILES

建议使用 Tab：

```text
乙醇    CCO
乙胺    CCN
苯      c1ccccc1
```

也支持：

```text
CCO    乙醇
CCN    乙胺
```

### CSV

推荐：

```csv
name,SMILES
ethanol,CCO
ethylamine,CCN
benzene,c1ccccc1
```

程序会优先寻找 `SMILES` 列；没有标准列名时会尝试自动识别。

---

## 3. 批量输出

软件支持三种批量输出：

1. 每个分子单独一个 `.json`
2. 所有分子合并成一个 `.jsonl`
3. 所有分子合并成一个 JSON 数组

---

## 4. canonical_smiles

默认：

```text
☐ 包含 "canonical_smiles"
```

此时输出中完全没有该字段。

勾选后：

```text
☑ 包含 "canonical_smiles"
```

程序会添加 canonical SMILES，并重新计算 `sha256`。

---

## 5. 为什么默认锁定 RDKit 环境

训练/参考 JSON 使用：

```text
RDKit 2026.03.5
217 descriptors
```

因此软件默认启用：

```text
严格锁定模型环境（推荐）
```

如果 RDKit 版本或 descriptor 数量与参考环境不同，会阻止输出，从而避免生成“格式看似相同但特征定义可能不一致”的 JSON。

---

## 6. 完全离线

源码中没有网络请求。

终端用户运行打包后的软件时，不需要：

- Internet
- Python
- Conda
- RDKit
- numpy
- 命令行

SMILES 和计算出的分子特征都只在本机处理。

---

# 开发者说明

## 7. 仓库结构

```text
smiles-converter-github/
├── .github/
│   └── workflows/
│       └── build.yml
├── examples/
│   └── example_smiles.csv
├── scripts/
│   ├── build_windows.cmd
│   ├── build_windows.ps1
│   ├── build_macos.sh
│   └── build_linux.sh
├── src/
│   ├── main.py
│   └── smiles_converter/
│       ├── __init__.py
│       ├── features.py
│       ├── gui.py
│       └── io_utils.py
├── tests/
│   └── test_features.py
├── environment.yml
├── requirements.txt
├── .gitignore
├── SECURITY.md
└── README.md
```

---

## 8. 本地运行源码

推荐 Conda：

```bash
conda env create -f environment.yml
conda activate smiles-converter
```

运行：

```bash
set PYTHONPATH=src
python src/main.py
```

Linux/macOS：

```bash
export PYTHONPATH=src
python src/main.py
```

---

## 9. Windows 本机构建 EXE

打开 PowerShell：

```powershell
conda activate smiles-converter
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

生成：

```text
dist\smiles转化器.exe
```

也可以：

```text
scripts\build_windows.cmd
```

> 注意：从浏览器下载的 `.cmd/.ps1` 可能被 Windows 标记为来自 Internet。
> 对开发者而言，推荐在 Git 仓库中 clone 后运行，或直接使用 GitHub Actions 自动构建。

---

## 10. GitHub Actions 自动构建

直接把本仓库上传 GitHub 后：

```text
Actions
→ Build cross-platform releases
→ Run workflow
```

会分别在：

- Windows Runner
- macOS Runner
- Linux Runner

构建对应的软件。

Windows 产物明确为：

```text
smiles转化器.exe
```

---

## 11. 发布 GitHub Release

创建 tag：

```bash
git tag v1.0.0
git push origin v1.0.0
```

workflow 会自动把三个系统的构建产物加入对应 GitHub Release。

---

## 12. Windows 未签名提醒

GitHub Actions 生成的 `.exe` 默认没有商业代码签名。

因此第一次下载时 Windows SmartScreen / Smart App Control 可能提示“未知发布者”或阻止未签名程序。

这是签名/信誉问题，不表示程序包含网络功能。

如果以后正式商业发布，建议为 Windows EXE 配置 Authenticode 代码签名证书。

---

## 13. 运行测试

```bash
export PYTHONPATH=src
pytest -q
```

Windows PowerShell：

```powershell
$env:PYTHONPATH="src"
pytest -q
```

---

## 14. 隐私设计

默认 JSON：

```json
{
  "payload": {
    "descriptor_names": [],
    "descriptors": [],
    "fingerprint_sizes": {},
    "fingerprints": {},
    "graph": {},
    "rdkit_version": "2026.03.5",
    "schema": "ic50-v431-molecular-features-1"
  },
  "sha256": "..."
}
```

默认不包含：

```json
"canonical_smiles"
```

---

## 15. License

当前仓库**没有自动附加开源许可证**。

在公开发布前，请根据你希望别人如何使用、修改、再分发本软件决定是否添加 MIT、Apache-2.0、GPL 或商业许可证。

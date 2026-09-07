# smiles转化器

## 安装

### Windows

进入 GitHub 仓库的 `Actions`，运行 `Build cross-platform releases`，下载生成的：

```text
smiles转化器.exe
```

双击即可运行，不需要安装 Python、Conda 或 RDKit。

### macOS

在 GitHub Actions 构建完成后下载 macOS 版本，解压后运行：

```text
smiles转化器.app
```

### Linux

在 GitHub Actions 构建完成后下载：

```text
smiles转化器-Linux-x86_64
```

赋予执行权限后运行：

```bash
chmod +x smiles转化器-Linux-x86_64
./smiles转化器-Linux-x86_64
```

### 源码运行

```bash
conda env create -f environment.yml
conda activate smiles-converter
```

Windows：

```powershell
$env:PYTHONPATH="src"
python src/main.py
```

macOS / Linux：

```bash
export PYTHONPATH=src
python src/main.py
```

## 使用

### 单个 SMILES

在“单个 SMILES”页面输入：

```text
CCO
```

点击“生成并保存 JSON”。

### 多个 SMILES

每行输入一个：

```text
CCO
CCN
c1ccccc1
```

也可以使用名称和 SMILES：

```text
乙醇    CCO
乙胺    CCN
苯      c1ccccc1
```

### CSV / TSV / TXT

推荐 CSV：

```csv
name,SMILES
ethanol,CCO
ethylamine,CCN
benzene,c1ccccc1
```

软件支持三种批量输出：

1. 每个分子单独一个 JSON
2. 合并为一个 JSONL
3. 合并为一个 JSON 数组

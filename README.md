# smiles转化器

## 1.0.1：预测系统1.0兼容性与打包修复

- 默认输出 `cardiac-ic50-1.0-features-1`，对应心脏离子通道 IC50 智能预测系统1.0。
- JSON 不含 `canonical_smiles`；缺失描述符使用 `null`，不写入 `NaN` / `Infinity`。SHA256 根据最终 payload 重新计算。
- 将 RDKit 的外部 Data 目录一起打包，启动时使用内置数据路径；正常状态应为 `RDKit 2026.03.5 | Descriptors 217 | 环境匹配`。
- Windows、macOS、Linux 构建均运行成品自检：隔离 Python/Conda 路径，比较9个公开示例的完整输出与源码结果，并核对预测系统1.0参考哈希。自检失败则不发布产物。
- 每个 Actions 构建包包含 `win32-validation.json`、`darwin-validation.json` 或 `linux-validation.json` 验证报告。旧 Actions 任务中的 EXE 不会自动更新，请下载此修复之后成功构建的产物。

已有旧格式 JSON 应使用新版从原 SMILES 重新生成，不要只手改 schema；否则 SHA256 校验也会失败。预测系统1.0每次导入一个分子对象，批量导出请选择“每个分子单独 JSON”，不要上传 JSONL 或 JSON 数组。

系统1.0的当前图格式不能唯一恢复 E/Z 双键立体信息或“其他”原子类别，新版会提示改用预测系统的 SMILES 输入，不会静默丢弃这些信息。

运行回归测试：`PYTHONPATH=src pytest -q`（PowerShell 使用 `$env:PYTHONPATH="src"; pytest -q`）。

## 安装

### Windows

#### 方法一：直接下载 GitHub Actions 构建好的 EXE

1. 打开本项目的 GitHub 仓库。
2. 点击页面顶部的 `Actions`。
3. 左侧选择 `Build cross-platform releases`。
4. 打开最新一次绿色勾号的成功任务。
5. 滚动到页面最下方的 `Artifacts`。
6. 点击并下载：

```text
smilestranlates-win
```

7. 下载后得到一个 ZIP 压缩包，先解压。
8. 解压后可以看到：

```text
smilestranlates-win.exe
```

9. 双击 `smilestranlates-win.exe` 即可启动软件。

使用这个 EXE 时，不需要另外安装 Python、Conda、RDKit 或 numpy。

#### 如果 Windows 阻止运行

如果出现 SmartScreen 或“未知发布者”提示，说明这个 GitHub 自动构建的 EXE 没有商业数字签名。

如果系统允许继续运行，可以在文件属性或系统安全提示中确认后运行。正式公开发布时，建议再给 EXE 添加代码签名。

#### 方法二：从源码运行

先安装 Miniconda 或 Anaconda。

打开 PowerShell，进入项目目录后执行：

```powershell
conda env create -f environment.yml
conda activate smiles-converter
$env:PYTHONPATH="src"
python src/main.py
```

#### Windows 本地生成 EXE

创建好 Conda 环境后执行：

```powershell
conda activate smiles-converter
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

构建完成后生成：

```text
dist\smilestranlates-win.exe
```

### macOS

#### 方法一：下载构建好的应用

1. 打开 GitHub 仓库。
2. 点击 `Actions`。
3. 进入最新一次成功的 `Build cross-platform releases`。
4. 在 `Artifacts` 下载：

```text
smilestranslate-mac
```

5. 解压下载文件。
6. 解压后得到：

```text
smilestranslate-mac.app
```

7. 可以直接双击运行，也可以拖入 `Applications` 文件夹。

#### 如果 macOS 阻止打开

第一次运行未签名应用时，macOS 可能阻止启动。

进入：

```text
System Settings
→ Privacy & Security
```

找到被阻止的 `smilestranslate-mac.app`，选择：

```text
Open Anyway
```

然后再次确认打开。

#### 从源码运行

终端执行：

```bash
conda env create -f environment.yml
conda activate smiles-converter
export PYTHONPATH=src
python src/main.py
```

#### 本地构建 macOS 应用

```bash
conda activate smiles-converter
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

生成：

```text
dist/smilestranslate-mac.app
```

### Linux

#### 方法一：下载构建好的 Linux 文件

1. 打开 GitHub 仓库。
2. 点击 `Actions`。
3. 进入最新成功的 `Build cross-platform releases`。
4. 在 `Artifacts` 下载：

```text
smilestranslate-Linux-x86_64
```

5. 解压下载文件。
6. 打开终端，进入文件所在目录。
7. 添加执行权限：

```bash
chmod +x smilestranslate-Linux-x86_64
```

8. 运行：

```bash
./smilestranslate-Linux-x86_64
```

#### 从源码运行

```bash
conda env create -f environment.yml
conda activate smiles-converter
export PYTHONPATH=src
python src/main.py
```

#### 本地构建 Linux 版本

```bash
conda activate smiles-converter
chmod +x scripts/build_linux.sh
./scripts/build_linux.sh
```

生成：

```text
dist/smilestranslate-Linux-x86_64
```
## 使用

### 单个 SMILES

1. 打开软件。
2. 进入 `单个 SMILES` 页面。
3. 输入 SMILES，例如：

```text
CCO
```

4. 可以先点击：

```text
验证 SMILES
```

5. 点击：

```text
生成并保存 JSON
```

6. 选择保存文件夹和文件名。
7. 软件会生成对应 JSON。

### 多个 SMILES

1. 打开 `多个 SMILES` 页面。
2. 每行输入一个 SMILES，例如：

```text
CCO
CCN
c1ccccc1
```

也可以输入名称和 SMILES：

```text
乙醇    CCO
乙胺    CCN
苯      c1ccccc1
```

建议名称与 SMILES 之间使用 Tab 分隔。

3. 点击：

```text
检查全部 SMILES
```

4. 确认没有无效 SMILES。
5. 选择批量输出方式。
6. 点击：

```text
批量生成
```

### CSV / TSV / TXT

1. 打开 `CSV / TSV / TXT` 页面。
2. 点击：

```text
选择文件
```

3. 推荐 CSV 文件格式：

```csv
name,SMILES
ethanol,CCO
ethylamine,CCN
benzene,c1ccccc1
```

4. 软件读取完成后会显示预览。
5. 点击：

```text
批量生成
```

### 批量输出格式

可以选择：

```text
每个分子单独一个 JSON
一个 JSONL
一个 JSON 数组
```

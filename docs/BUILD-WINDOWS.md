# Windows 构建指南（Inventory.exe）

本指南写给需要自己构建 Windows 版本的开发者。普通店主只想运行程序的话，请看 [Windows 使用指南](USER-GUIDE-WINDOWS.md)。`Inventory.exe` 已经自带运行环境，使用者不需要安装 Python。

## 1. 为什么必须在 Windows 或 Windows CI 上构建

PyInstaller 不是交叉编译工具。它会把**当前系统**的 Python 运行时、依赖库和启动器一起打进可执行文件。在 Linux 或 macOS 上执行同一个 spec，只能得到对应系统的程序，改扩展名也变不成 Windows exe。

所以本项目的 `Inventory.exe` 必须在 Windows 上构建。推荐直接使用 GitHub Actions 的 `windows-latest` 构建机，见第 4 节。

## 2. 环境要求

| 项目 | 版本 | 说明 |
|---|---|---|
| 操作系统 | Windows 10 / 11，64 位 | 不支持 32 位 Windows |
| Python | 3.10，64 位 | 请按此版本准备，其他版本未做验证 |
| Node.js | 22.12 或更高 | CI 使用 Node 22 |
| npm | 随 Node.js 安装 | 用于构建前端 |
| Git | 任意较新版本 | 用于获取代码 |
| PowerShell | 5.1 或更高 | 本指南的命令均在此环境测试设计 |

构建过程需要能访问 npm 仓库和 PyPI。如果公司网络有代理，请提前配置好 `npm` 与 `pip` 的代理。

## 3. 本地 Windows 构建

以下命令都在仓库根目录执行。

### 3.1 获取代码

```powershell
git clone <你的仓库地址> inventory
cd inventory
```

建议把仓库放在纯英文、无空格的路径，例如 `C:\inventory-build`。原因见 5.3 节。

### 3.2 构建前端

```powershell
cd frontend
npm ci
npm run build
cd ..
```

`npm ci` 会按 `package-lock.json` 安装依赖，比 `npm install` 更适合可重复构建。构建完成后，前端静态文件位于 `frontend\dist`，打包时会被收进 exe。

### 3.3 创建虚拟环境并安装后端依赖

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements-exe.txt
```

`backend\requirements-exe.txt` 已经固定了 PyInstaller 6.22.3 和全部运行依赖；**不需要**再单独执行 `pip install pyinstaller`。

如果 PowerShell 提示禁止运行脚本，可只对当前窗口放宽策略：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

也可以在传统命令提示符里执行 `.venv\Scripts\activate.bat`。

### 3.4 打包

保持虚拟环境已激活，在仓库根目录执行：

```powershell
pyinstaller --clean --noconfirm packaging/app.spec
```

如果只想用最小参数，也可以执行 `pyinstaller packaging/app.spec`。日常构建建议保留 `--clean --noconfirm`，避免缓存和旧产物干扰。

产物是单文件：`dist\Inventory.exe`。

`packaging/app.spec` 已经写明关键选项：

- `console=True`：保留控制台窗口，便于查看日志和停止服务
- `upx=False`：禁用 UPX 压缩
- 前端 `frontend/dist` 以数据文件形式打进 exe
- 版本信息来自 `packaging/version_info.txt`

不要在命令行额外追加 `--onefile` 或 `--windowed`，这些选项与 spec 重复或冲突，容易产生意料之外的结果。

### 3.5 本地验证

先确认文件存在：

```powershell
Test-Path .\dist\Inventory.exe
```

再用不自动打开浏览器的方式启动，便于观察日志：

```powershell
$env:INVENTORY_NO_BROWSER=1
.\dist\Inventory.exe
```

另开一个 PowerShell 窗口检查健康接口：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

返回内容中的 `data.status` 应为 `healthy`。随后在浏览器打开 http://localhost:8000 检查登录页。

首次运行会在 exe 同级生成 `config.ini`、`data\` 和 `static\images\`。停止时在控制台按 `Ctrl+C`，或直接关闭控制台窗口。验证结束后可清理环境变量：

```powershell
Remove-Item Env:\INVENTORY_NO_BROWSER
```

本地构建通过只代表依赖和路径基本正确。Windows 防火墙、单实例、中文目录运行等情况，仍建议在真机上再点一遍。

## 4. 使用 GitHub Actions 构建（推荐）

仓库包含 `.github/workflows/build-windows.yml`。它在 `windows-latest` 上完成前端构建、依赖安装和 PyInstaller 打包，不依赖本地环境。CI 运行前后端回归，并启动实际 EXE 验证迁移、登录和页面；手机摄像头、系统防火墙及交互仍需真机验收。

### 4.1 触发方式

手动触发：

1. 打开 GitHub 仓库页面
2. 进入 **Actions**
3. 在左侧选择 Windows 构建工作流（对应文件 `build-windows.yml`）
4. 点击 **Run workflow**，选择分支后运行

打标签触发：推送 `v` 开头的标签即可，例如：

```bash
git tag v0.1.0
git push origin v0.1.0
```

### 4.2 下载产物

运行成功后，打开该次运行详情页，在页面底部 **Artifacts** 区域下载 Windows 构建压缩包，解压后可得到 `dist\Inventory.exe`。

Artifact 有保留期限，过期会被清理。正式发布时请及时下载并另行归档。CI 只负责构建和测试，不会替你做代码签名。

## 5. 常见问题

### 5.1 启动时报 ModuleNotFoundError，或某个接口 500

PyInstaller 靠静态分析收集依赖，动态导入的模块可能被漏掉。典型报错是：

```text
ModuleNotFoundError: No module named 'xxx'
```

处理方式：

1. 在 `packaging/app.spec` 的 `hiddenimports` 列表里补上缺失的模块
2. 重新执行 `pyinstaller --clean --noconfirm packaging/app.spec`
3. 如果是 `PackageNotFoundError` 一类缺少包元数据的问题，在 spec 里用 `copy_metadata("包名")` 补上

不要用“运行时再 pip 安装”的办法绕过，exe 里没有 pip。补完后请把改动保留在 spec 中，让本地构建和 CI 使用同一份配置。

### 5.2 杀毒软件（杀软）误报

PyInstaller 单文件程序需要先把自身解压到临时目录再运行，加上本期没有代码签名，容易被杀毒软件标成可疑文件。常见表现是文件刚生成就被隔离，或者双击后被删除。

建议这样处理：

- 优先使用自己构建或 CI 产出的文件，不要用来路不明的 exe
- 核对文件哈希，确认与构建产物一致：

```powershell
Get-FileHash .\dist\Inventory.exe -Algorithm SHA256
```

- 确认可信后，在 Windows 安全中心为该文件或构建目录添加排除项
- 也可以把样本提交给杀毒厂商，按误报申诉

不建议为了运行程序而长期关闭实时防护。代码签名能明显减少这类误报，但本期不提供签名，见 5.6 节。

### 5.3 路径含中文、空格或其他非 ASCII 字符

构建目录尽量使用纯英文和数字，例如 `C:\inventory-build`。`C:\Users\张三\Desktop\进销存` 这类路径可能在 PyInstaller 收集文件或解压临时目录时出问题，而且报错往往不直观。

运行目录方面，建议在 Windows 上手动把 exe 放到中文目录启动验证。为减少疑难问题，仍建议把程序放在纯英文路径下。

### 5.4 onefile 启动慢

`--onefile` 每次启动都要把运行时解压到 `%TEMP%` 下的临时目录，首次启动通常需要 10 到 30 秒，杀毒软件扫描时可能更久。这段时间控制台可能看起来没有反应，属于正常现象。

- 耐心等待，不要连续双击
- 重复启动会检测到已有实例，直接打开浏览器后退出，不会启动第二份服务
- 服务运行期间不要手动清理 `%TEMP%` 里的临时目录
- 如果以后对启动速度要求更高，可以评估改为 onedir 目录分发，但本期发布仍是单文件

### 5.5 为什么禁用 UPX

spec 中设置了 `upx=False`。UPX 能压缩可执行文件体积，但会带来三个问题：更容易被杀毒软件误报、启动时多一次解压、个别 DLL 压缩后可能损坏。单文件体积大一些，换来的是更稳定的运行和更少的误报，因此不要为了减小体积重新开启 UPX。

### 5.6 代码签名与 SmartScreen

本期发布**不包含代码签名**。没有签名证书的 exe 在首次下载或复制到新电脑后，可能触发 Windows SmartScreen 提示。使用者需要点击“更多信息”，再点“仍要运行”。具体步骤见 [Windows 使用指南](USER-GUIDE-WINDOWS.md)。

本期也不提供安装器、自动更新和托盘图标。分发方式就是直接提供 `Inventory.exe`。

## 6. 构建产物说明

- `dist\Inventory.exe`：单文件程序，内含 Python 运行时、后端代码、前端静态文件和依赖
- `config.ini`：首次运行时在 exe 同级生成，保存端口、账号默认值和密钥
- `data\`：首次运行时生成，存放 SQLite 数据库
- `static\images\`：首次运行时生成，存放上传的商品图片

`config.ini`、`data\`、`static\` 都不在 exe 内部，升级时只替换 exe 即可保留数据。`build\`、`dist\` 和 `.venv\` 属于构建中间产物，不要提交到仓库。

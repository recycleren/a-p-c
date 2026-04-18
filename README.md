<div align="center">



## 集成 CLIProxyAPI 管理
- **[CLI Proxy API Management Center](https://github.com/router-for-me/CLIProxyAPI)**


## 技术栈

- **后端**: `Python 3.10+`, `FastAPI`, `SQLAlchemy`
- **前端**: `Vanilla JS`, `WebSocket`
- **数据**: `SQLite` / `PostgreSQL`
- **并发**: `asyncio` + `ThreadPoolExecutor`

## 快速开始

### 1. 环境准备
确保已安装 Python 3.10 或更高版本。

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置环境
复制 `.env.example` 为 `.env` 后按需修改:

```bash
cp .env.example .env
```

### 3. 运行项目
```bash
python webui.py
```

访问 `http://localhost:8000` 即可进入管理面板。

进入系统设置页添加 CPA 服务，即可使用。

### 4. 桌面版运行

如果你想以桌面窗口方式运行，而不是手动打开浏览器：

```bash
pip install pywebview
python desktop.py
```

桌面模式会：
- 后台自动启动本地 FastAPI 服务
- 使用 `pywebview` 打开内嵌窗口
- 默认仅监听 `127.0.0.1`
- 默认使用本地 SQLite，无需配置 `.env`

## 桌面版打包

### macOS 桌面版打包

请在 **macOS** 上执行：

```bash
chmod +x scripts/build_macos_dmg.sh
./scripts/build_macos_dmg.sh
```

打包完成后产物位于：

- `dist/CPA-Codex-Manager.app`
- `dist/CPA-Codex-Manager.dmg`


### Windows 桌面版打包

请在 **Windows 系统** 上执行：

```bat
scripts\build_windows.bat
```

打包完成后产物通常位于：

- `dist\CPA-Codex-Manager\CPA-Codex-Manager.exe`






## 免责声明

本项目仅供学习、研究和技术交流使用，请遵守 OpenAI 相关服务条款。

因使用本项目产生的任何风险和后果，由使用者自行承担。

## Star History

<p align="center">
  <a href="https://www.star-history.com/#maoleio/CAP-Codex-Manager&Date">
    <img src="https://api.star-history.com/svg?repos=maoleio/CAP-Codex-Manager&type=Date" alt="Star History Chart" />
  </a>
</p>

---
**CPA-Codex-Manager** - 让 CLIProxyAPI 号池管理变得优雅而自动化。

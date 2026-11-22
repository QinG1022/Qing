# Qing · 本地 AI 文档助手

> 一个跑在自己电脑上的单用户 AI 助手：聊天式界面，支持上传 PDF / 图片 / 文本，
> 提取内容后作为上下文与在线大模型对话。
> **不需要数据库服务、不需要 Redis、不需要 GPU。**

这个仓库是毕业设计项目的重构版。原始版本用 Celery + Redis + Flask-Login，
依赖约 2 GB；重构后是单进程、纯本地、依赖约 200 MB。

---

## 特性

| | |
|---|---|
| **聊天式界面** | 流式输出（SSE）、Markdown 渲染（表格 / 列表 / 公式）、复制与重新生成、停止生成 |
| **文档处理** | PDF 文本提取、图片识别、纯文本直读；整页拖放、缩略图预览、点击放大 |
| **多会话** | 会话列表与自动标题、按会话重建上下文（不串话）、删除会话 |
| **多模型** | 拉取服务商模型列表、按用途分类、**切换前自动验证可用性** |
| **图片识别** | 三种后端可选：视觉模型 / DeepSeek OCR / 本地 Tesseract |
| **用量可见** | 每条回复显示 token 消耗，底部显示本次会话累计 |
| **单用户** | 无注册登录，API Key 只保存在本机 `config.json` |
| **界面** | 浅色 / 深色主题、动态背景（极光 + 粒子 + 光标高光） |

---

## 快速开始

### 1. 准备 Python

需要 **Python 3.10+**。如果系统里没有，改 `run.bat` 顶部这一行：

```bat
set "DSH_PY=你的 python.exe 路径"
```

### 2. 安装依赖

依赖装在项目内的 `pydeps/` 目录，**不污染全局环境**：

```bat
python -m pip install --target pydeps -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 配置

复制 `config.example.json` 为 `config.json`，填入 API Key：

```json
{
  "provider": "siliconflow",
  "base_url": "https://api.siliconflow.cn/v1",
  "model": "deepseek-ai/DeepSeek-V3",
  "api_key": "sk-...",
  "ocr_provider": "vision",
  "ocr_model": "Qwen/Qwen3-VL-8B-Instruct"
}
```

也可以不手动改——首次启动会跳到 `/setup` 页面，在界面里填；
之后所有配置都能在对话页的「模型与 API 设置」里改。

### 4. 启动

```bat
run.bat
```

浏览器打开 `http://127.0.0.1:5000`。
自检：`check.bat`（应显示 `ALL OK`）。

---

## 配置说明

### 对话模型

支持任意 OpenAI 兼容接口，`base_url` 填到 `/v1` 为止：

| 服务商 | base_url | 备注 |
|---|---|---|
| 硅基流动 | `https://api.siliconflow.cn/v1` | 有免费额度，模型多 |
| DeepSeek 官方 | `https://api.deepseek.com/v1` | |
| OpenAI | `https://api.openai.com/v1` | |
| 本地 Ollama | `http://127.0.0.1:11434/v1` | `api_key` 随便填 |

配置优先级：`config.json` > 环境变量 > 默认值。

### 图片识别

`ocr_provider` 三选一：

| 值 | 走什么 | 计费 | 说明 |
|---|---|---|---|
| `vision`（默认） | 视觉模型（复用对话的 Key） | 走 token | 适合截图、表格、拍照文档 |
| `deepseek` | DeepSeek 官方 OCR 接口 | 约 ¥0.0016 / 页 | 需要单独的 `ocr_api_key` |
| `tesseract` | 本地 Tesseract | 免费 | 需要自行安装 exe 与中文语言包 |

`vision` 模式下把 `ocr_model` 设成任意支持看图的模型即可，
例如 `Qwen/Qwen3-VL-8B-Instruct`（够用）、`Qwen/Qwen3-VL-30B-A3B-Instruct`（更准）。

---

## 目录结构

```
app.py                 主程序：页面路由、文件处理、配置接口
modules/
  task_runner.py       进程内任务队列（替代 Celery）
  settings_store.py    config.json 读写 + 模型能力缓存
  database.py          SQLAlchemy 模型 + 单用户替身
  tasks.py             PDF 生成 / 识别 / 提取任务
  ocr_processor.py     三种 OCR 后端的分发（vision / deepseek / tesseract）
  ai_chat/
    ai_routes.py       对话 / 会话 / 分析接口
    deepseek_client.py OpenAI 兼容客户端（含 usage 透传）
templates/             chat.html / home.html / setup.html
static/                css / js / 图标字体
data/app.db            SQLite（会话与消息）
pydeps/                依赖（git 忽略）
```

---

## 已知限制

| 限制 | 说明 |
|---|---|
| 附件不入库 | 刷新后缩略图与结果卡片消失；消息里仍保留「含附件内容」的文字 |
| 长文档截断 | 附件正文超过 6000 字会被截断，更长的内容模型看不到 |
| 上下文只取最近 20 条 | 更早的对话不会参与推理 |
| 分类靠模型名推断 | `/models` 没有能力元数据；确切能力需用「检测看图」实测 |
| Windows 优先 | 启动脚本是 `.bat`；Linux / macOS 直接用 `python app.py` |

---

## 技术说明

### 为什么不用 Celery

原来的架构要起 Redis + worker + Flask 三个进程。单人使用完全没必要——
`modules/task_runner.py` 用 `ThreadPoolExecutor` 模拟了 Celery 的 `.delay()`
和 `AsyncResult` 接口，`app.py` 的调用点一行都不用改。

### 为什么保留 users 表

`database.py` 里的 `LocalUser` 替身让 18 处 `current_user.is_authenticated`
无需修改。删表要改动的地方远比保留一个固定 id=1 的用户多。

### 上下文如何重建

每次请求都从数据库读最近 20 条消息 + 本轮输入，重建 `client.messages`。
不要依赖客户端对象累积历史——那会导致不同会话互相污染、重启后失忆。

### 图片识别为什么默认走视觉模型

传统 OCR（Tesseract）只输出纯文本，表格结构全丢；视觉模型能直接输出 Markdown 表格，
对截图、拍照、倾斜文档的容忍度也高得多，而且复用对话已有的 Key，无需额外开通服务。

图片压缩用 `Image.resize()` 而不是 `thumbnail()`：后者会触发 `draft()` 缩放路径，
Pillow 该路径历史上出过多个堆溢出漏洞（CVE-2026-112403 等），即使已修复也没必要走。

### 切换模型前为什么要实测

服务商的 `/models` 只返回名字，不说明能力。名字推断只能给个大概，
所以点选模型时会先发一个 `max_tokens=1` 的请求：能通才切换，失败就保持原模型并提示原因。
验证结果记录在 `config.json` 的 `model_caps` 里，菜单中显示 ✓ / ✕。

---

## 开发

```bat
pip install pytest pytest-html
python -m pytest tests -q
```

静态资源带 `?v=<修改时间>` 版本号，HTML 响应设置为不缓存——
改完 CSS / JS / 模板后普通刷新即可看到效果，无需重启或强制刷新。

---

## License

个人项目，未指定许可证。

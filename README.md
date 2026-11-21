# Qing · 本地 AI 文档助手

> 一个跑在自己电脑上的单用户 AI 助手：聊天式界面，支持上传 PDF / 图片 / 文本，
> 提取内容后作为上下文与在线大模型对话。**不需要数据库服务、不需要 Redis、不需要 GPU。**

这个仓库是毕业设计项目的重构版。原始版本用 Celery + Redis + Flask-Login，
依赖约 2 GB；重构后是单进程、纯本地、依赖约 200 MB。

---

## 特性

| | |
|---|---|
| **聊天式界面** | 流式输出（SSE）、Markdown 渲染（表格/公式/列表）、消息复制与重新生成 |
| **文档处理** | PDF 文本提取、图片 OCR、纯文本直读；拖放上传，处理进度可见 |
| **多会话** | 会话列表、按会话重建上下文（不会串话）、自动生成标题 |
| **多模型** | 拉取服务商模型列表并分类（纯文本 / 识图 / 语音 / 向量…），支持任意 OpenAI 兼容接口 |
| **能力探测** | 一键检测当前模型是否支持图像输入 |
| **单用户** | 无注册登录，API Key 只保存在本机 `config.json` |
| **界面** | 浅色/深色主题、动态背景（极光 + 粒子 + 光标高光） |

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

复制 `config.example.json` 为 `config.json`，填入你的 API Key：

```json
{
  "provider": "siliconflow",
  "base_url": "https://api.siliconflow.cn/v1",
  "model": "deepseek-ai/DeepSeek-V3",
  "api_key": "sk-..."
}
```

也可以不手动改——首次启动会跳到 `/setup` 页面，在界面里填。

### 4. 启动

```bat
run.bat
```

浏览器打开 `http://127.0.0.1:5000`。

自检：`check.bat`（16 项检查，应显示 `ALL OK`）。

---

## 配置说明

支持任意 OpenAI 兼容接口，`base_url` 填到 `/v1` 为止：

| 服务商 | base_url | 备注 |
|---|---|---|
| 硅基流动 | `https://api.siliconflow.cn/v1` | 有免费额度，模型多 |
| DeepSeek 官方 | `https://api.deepseek.com/v1` | |
| OpenAI | `https://api.openai.com/v1` | |
| 本地 Ollama | `http://127.0.0.1:11434/v1` | `api_key` 随便填 |

配置优先级：`config.json` > 环境变量 > 默认值。

---

## 目录结构

```
app.py                 主程序：页面路由、文件处理、配置接口
modules/
  task_runner.py       进程内任务队列（替代 Celery）
  settings_store.py    config.json 读写
  database.py          SQLAlchemy 模型 + 单用户替身
  tasks.py             PDF 生成 / OCR / 提取任务
  ocr_processor.py     Tesseract 封装
  ai_chat/
    ai_routes.py       对话 / 会话 / 分析接口
    deepseek_client.py OpenAI 兼容客户端
templates/             chat.html / home.html / setup.html
static/                css / js / 图标字体
data/app.db            SQLite（会话与消息）
pydeps/                依赖（git 忽略）
```

---

## 已知限制

| 限制 | 说明 |
|---|---|
| 图片 OCR 依赖 Tesseract | 未安装时图片会处理失败；PDF 文本提取不受影响 |
| 附件不入库 | 刷新后提取结果卡片消失，但内容仍在消息上下文里 |
| 长文档截断 | 附件内容超过 6000 字会被截断 |
| Windows 优先 | 启动脚本是 `.bat`；Linux/macOS 直接用 `python app.py` |

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

---

## License

个人项目，未指定许可证。

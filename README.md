# 智能文档处理系统

## 📌 项目简介
这是一个基于Flask框架的智能文档处理系统，主要技术特性包括：

- 🚀 异步任务架构：Celery + Redis实现高并发任务处理
- 🔒 安全防护：集成Flask-Talisman提供HTTPS安全标头
- 🤖 多模型支持：同时接入DeepSeek API和本地部署的Qwen1.5/DeepSeek-R1模型
- 📄 自动化流程：实现从图像预处理→OCR识别→PDF生成的完整流水线
- 📊 智能管理：采用deque数据结构实现最近6条操作记录的LRU缓存机制

## 🚀 核心功能
### 文档处理
- 📄 PDF 文档生成与下载
- 📝 PDF 文本内容提取
- 📜 历史记录管理（最近6条）

### 图像处理
- 🖼️ 图像批量处理与优化
- 🔍 OCR 图像文字识别

### AI 对话
- 🤖 支持多种 AI 模型
  - DeepSeek API（在线）
  - DeepSeek-R1（本地）
  - Qwen1.5（本地）
- 📄 支持文件分析功能
  - 上传TXT/PDF文件进行智能分析
  - 基于文件内容提问

## 🛠️ 技术架构
### 后端技术
- **Web框架**: Flask
- **任务队列**: Celery + Redis
- **图像处理**: Pillow, pytesseract
- **PDF处理**: ReportLab, PyPDF2, PyMuPDF
- **安全防护**: Flask-Talisman
- **数据结构**: Collections.deque

### AI 模型支持
- DeepSeek API
- 本地部署的 DeepSeek-R1 模型
- 本地部署的 Qwen1.5 模型

### 前端架构
- 模块化 JavaScript 和 CSS
  - 图像处理模块
  - PDF 处理模块
  - AI 对话模块
  - OCR 处理模块

## 📋 快速开始

### 环境要求
- Python 3.8+
- Redis 服务器
- Tesseract OCR 引擎
- CUDA 环境（可选，用于 GPU 加速）
- 本地 AI 模型（可选）

### 安装步骤

1. **配置虚拟环境**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **安装必要组件**
   - Redis: [下载地址](https://github.com/microsoftarchive/redis/releases)
   - Tesseract-OCR: [下载地址](https://github.com/UB-Mannheim/tesseract/wiki)
   - 本地 AI 模型（可选）:
     - [DeepSeek-R1](https://huggingface.co/deepseek-ai/deepseek-coder-1.3b-base)
     - [Qwen1.5](https://huggingface.co/Qwen/Qwen1.5-0.5B-Chat)

3. **创建必要目录**
   ```bash
   mkdir -p uploads pdfs log
   ```

### 启动服务
1. **启动 Redis**
   ```bash
   net start Redis
   redis-cli ping  # 验证连接
   ```

2. **启动 Celery**
   ```bash
   celery -A modules.tasks worker --loglevel=info --pool=solo
   ```

3. **启动 Flask**
   ```bash
   python app.py
   ```

4. **访问系统**
   打开浏览器访问 http://localhost:5000

## 📖 使用指南

### 文档处理
1. 上传图片或输入文本
2. 设置生成参数
3. 提交任务
4. 下载生成的文件

### 图像处理
1. 上传图片
2. 选择处理选项
3. 查看处理结果

### PDF 提取
1. 上传 PDF 文件
2. 点击提取按钮
3. 查看提取结果

### AI 对话
1. 选择 AI 模型
2. 输入问题
3. 等待回复

## 🧪 测试
```bash
# 字体检查
python fonts/font_check.py

# 运行测试
python -m pytest tests/

# 生成测试报告
python -m pytest --html=report.html tests/
```

## ❓ 常见问题
1. **Redis 服务问题**
   - 检查服务状态
   - 验证端口占用
   - 重新安装服务

2. **Celery 错误**
   - 确认使用 `--pool=solo`
   - 检查 Redis 连接
   - 验证虚拟环境

3. **OCR 问题**
   - 检查环境变量
   - 验证安装路径
   - 测试 Tesseract

4. **AI 模型问题**
   - 验证模型路径
   - 检查 CUDA 配置
   - 确认系统资源

## 🛑 关闭服务
1. 停止 Flask 和 Celery（Ctrl+C）
2. 关闭 Redis：`net stop Redis`
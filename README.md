# 智能文档处理与AI交互系统

## 📌 项目简介
这是一个基于Flask框架的智能文档处理与AI交互系统，主要技术特性包括：

- 🚀 **异步任务架构**：Celery + Redis实现高并发任务处理
- 🔒 **安全防护**：集成Flask-Talisman提供HTTPS安全标头
- 💾 **数据持久化**：SQLite数据库存储用户信息和历史记录
- 👤 **用户管理系统**：支持用户注册、登录和会话持久化
- 🤖 **多模型支持**：同时接入DeepSeek API和本地部署的Qwen1.5/DeepSeek-R1模型
- 📄 **自动化流程**：实现从图像预处理→OCR识别→PDF生成的完整流水线
- 📊 **智能历史管理**：数据库存储用户历史操作，保持记录持久化

## 🚀 核心功能

### 文档处理
- 📄 PDF 文档生成与下载
- 📝 PDF 文本内容提取
- 📜 历史记录持久化存储与管理

### 图像处理
- 🖼️ 图像批量处理与优化
- 🔍 OCR 图像文字识别
- 🔄 文字识别结果历史记录

### 用户系统
- 👥 用户注册和登录功能
- 🔐 安全的密码哈希存储
- 📱 会话持久化，保持登录状态
- 📋 个人历史记录管理

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
- **数据库**: SQLite, Flask-SQLAlchemy
- **用户管理**: Flask-Login, Flask-Session
- **任务队列**: Celery + Redis
- **图像处理**: Pillow, pytesseract
- **PDF处理**: ReportLab, PyPDF2, PyMuPDF
- **安全防护**: Flask-Talisman, SHA-256密码哈希
- **数据结构**: Collections.deque (用于缓存)

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
  - 用户认证模块

## 📋 快速开始

### 环境要求
- Python 3.8+
- Redis 服务器
- Tesseract OCR 引擎
- SQLite 数据库支持
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
   mkdir -p uploads pdfs log data session
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

### 用户功能
1. 点击右上角"登录"按钮
2. 新用户选择"注册"，填写用户信息
3. 已有账户直接登录
4. 登录后可查看个人历史记录

### 文档处理
1. 上传图片或输入文本
2. 设置生成参数
3. 提交任务
4. 下载生成的文件
5. 查看操作历史记录

### 图像处理
1. 上传图片
2. 选择处理选项
3. 查看处理结果
4. OCR识别结果自动保存到历史记录

### PDF 提取
1. 上传 PDF 文件
2. 点击提取按钮
3. 查看提取结果
4. 提取文本自动保存到历史记录

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

1. **用户登录问题**
   - 浏览器刷新后登录状态丢失：确保SESSION_TYPE配置正确，session目录有写入权限
   - 密码无法登录：确认用户名大小写正确，密码至少8位包含字母和数字
   - 历史记录不显示：检查数据库连接和用户ID关联

2. **Redis 服务问题**
   - 检查服务状态：`sc query Redis`
   - 验证端口占用：`netstat -ano | findstr 6379`
   - 重新安装服务：`redis-server --service-install`

3. **数据库问题**
   - 数据库文件权限：确保data目录可写
   - 连接错误：检查SQLAlchemy连接字符串
   - 迁移问题：检查表结构是否正确初始化

4. **Celery 错误**
   - 确认使用 `--pool=solo`（Windows环境）
   - 检查 Redis 连接
   - 验证虚拟环境激活状态

5. **OCR 问题**
   - 检查环境变量TESSDATA_PREFIX
   - 验证tesseract.exe路径
   - 确认中文语言包chi_sim已安装

6. **AI 模型问题**
   - 验证模型路径
   - 检查 CUDA 配置
   - 确认系统资源充足

## 🛑 关闭服务
1. 停止 Flask 和 Celery（Ctrl+C）
2. 关闭 Redis：`net stop Redis`
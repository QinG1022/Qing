# 智能文档处理与AI交互系统

## 📌 项目简介

这是一个基于Flask框架的智能文档处理与AI交互系统，融合了现代Web技术与人工智能，提供全方位的文档处理服务，主要技术特性包括：

- 🚀 **异步任务架构**：Celery + Redis实现高并发任务处理，确保系统稳定性
- 🔒 **安全防护机制**：集成Flask-Talisman提供HTTPS安全标头，防止XSS攻击
- 💾 **数据持久化存储**：SQLite数据库存储用户信息和历史记录，确保数据不丢失
- 👤 **完整用户体系**：支持用户注册、登录和会话持久化，管理个人历史记录
- 🤖 **多AI模型支持**：同时接入DeepSeek API和本地部署的Qwen1.5/DeepSeek-R1模型
- 📄 **文档处理流水线**：实现从图像预处理→OCR识别→PDF生成的完整流程
- 📊 **智能历史管理**：多级历史记录系统，分类存储不同类型的操作历史
- 🔄 **智能文件分析**：支持上传TXT/PDF文件进行AI分析和提问

## 🚀 核心功能

### 文档处理功能

- 📄 PDF文档智能生成与下载
- 📝 PDF文本内容智能提取
- 📸 图像批量处理与优化
- 🔍 OCR图像文字识别与转换
- 📋 多类型历史记录持久化存储
- 🔄 跨会话历史记录同步

### AI交互功能

- 🤖 支持多种AI模型切换使用
  - DeepSeek API在线模型
  - 本地DeepSeek-R1-Distill-1.5B模型
  - 本地Qwen1.5-0.5B-Chat模型
- 💬 智能对话与问答系统
- 📑 文档智能分析功能
  - 支持上传TXT/PDF文件进行分析
  - 基于文档内容进行提问
- 🔄 对话历史记录管理
- 📊 多会话支持与管理

### 用户系统

- 👥 用户注册和登录功能
- 🔐 安全的密码哈希存储
- 📱 会话持久化，保持登录状态
- 👤 个人信息管理
- 📋 个人历史记录查看与删除
- 🔒 用户数据隔离存储

## 🛠️ 技术架构

### 后端技术栈

- **Web框架**: Flask 3.0.2
- **安全组件**: Flask-Talisman, pyOpenSSL
- **数据库**: SQLite, Flask-SQLAlchemy
- **用户管理**: Flask-Login, Flask-Session
- **任务队列**: Celery 5.3.6 + Redis 5.0.1
- **图像处理**: Pillow 11.1.0, pytesseract 0.3.10
- **PDF处理**: ReportLab 4.1.0, PyPDF2, PyMuPDF
- **AI技术**: Transformers, Accelerate, BitsAndBytes
- **测试框架**: Pytest 8.0.0, pytest-html

### AI模型架构

- **在线模型**: DeepSeek API
- **本地模型**:
  - DeepSeek-R1-Distill-1.5B (轻量级版本)
  - Qwen1.5-0.5B-Chat (超轻量级版本)
- **自动模型选择机制**:
  - 网络状态感知
  - 资源占用自适应
  - 自动降级机制

### 前端架构

- **核心技术**: HTML5, CSS3, JavaScript ES6+
- **模块组织**:
  - 图像处理模块
  - PDF处理模块
  - AI对话模块
  - 用户认证模块
  - 历史记录管理模块

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
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

2. **安装必要组件**

   - Redis: [下载地址](https://github.com/microsoftarchive/redis/releases)
   - Tesseract-OCR: [下载地址](https://github.com/UB-Mannheim/tesseract/wiki)
   - 本地 AI 模型（可选）:
     - [DeepSeek-R1-Distill-1.5B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B)
     - [Qwen1.5-0.5B-Chat](https://huggingface.co/Qwen/Qwen1.5-0.5B-Chat)

3. **创建必要目录**

   ```bash
   mkdir -p uploads pdfs log data session
   ```

4. **环境配置**
   创建 .env 文件，配置API密钥和模型路径：

   ```
   # 测试模式（跳过模型加载）
   SKIP_MODEL_LOADING=True

   # DeepSeek API 配置
   DEEPSEEK_BASE_URL=https://api.siliconflow.cn/v1
   DEEPSEEK_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
   DEEPSEEK_API_KEY=你的API密钥

   # 本地模型配置（可选）
   DEEPSEEK_LOCAL_MODEL_PATH=D:/path/to/DeepSeek-R1-Distill-1.5B
   QWEN_LOCAL_MODEL_PATH=D:/path/to/Qwen1.5-0.5B-Chat
   ```

### 启动服务

1. **启动 Redis**

   ```bash
   # Windows
   net start Redis  
   # 验证连接
   redis-cli ping

   # Linux/Mac
   redis-server &
   redis-cli ping
   ```

2. **启动 Celery**

   ```bash
   # Windows
   celery -A modules.tasks worker --loglevel=info --pool=solo
   
   # Linux/Mac
   celery -A modules.tasks worker --loglevel=info
   ```

3. **启动 Flask**

   ```bash
   python app.py
   ```

4. **访问系统**
   打开浏览器访问 http://localhost:5000 或 http://127.0.0.1:5000

## 📖 使用指南

### 用户功能

1. **账号管理**
   - 点击右上角"登录"按钮
   - 新用户选择"注册"，填写用户信息
     - 用户名：4-20个字符
     - 密码：至少8位，包含字母和数字
     - 邮箱：有效的邮箱格式
   - 已有账户直接登录
   - 登录后可查看个人资料和历史记录

2. **文档生成**
   - 输入文本内容和/或上传图片
   - 设置生成参数
   - 提交任务
   - 下载生成的PDF文件
   - 查看生成历史记录

3. **图像处理**
   - 上传单张或多张图片
   - 选择处理选项（增强/OCR/批处理）
   - 查看处理结果
   - 下载处理后的图片或识别文本

4. **PDF处理**
   - 上传PDF文件
   - 选择提取全文或特定页面
   - 查看提取结果
   - 复制或下载提取的文本

5. **AI对话**
   - 选择AI模型（DeepSeek/Qwen）
   - 直接对话或上传文件分析
   - 查看对话历史
   - 管理多个会话

## 🧪 测试

```bash
# 检查字体安装
python fonts/font_check.py

# 运行全部测试
python -m pytest tests/

# 生成HTML测试报告
python -m pytest --html=report.html tests/

# 运行特定测试
python -m pytest tests/test_image_processor.py -v
python -m pytest tests/test_pdf_generator.py -v
python -m pytest tests/test_database.py -v
```

## ❓ 常见问题排查

1. **用户登录问题**
   - 浏览器刷新后登录状态丢失：确保SESSION_TYPE配置正确，session目录有写入权限
   - 密码无法登录：确认用户名大小写正确，密码至少8位包含字母和数字
   - 历史记录不显示：检查数据库连接和用户ID关联

2. **Redis服务问题**
   - Windows检查服务状态：`sc query Redis`
   - 验证端口占用：`netstat -ano | findstr 6379`
   - 重新安装服务：`redis-server --service-install`
   - Linux检查状态：`systemctl status redis` 或 `ps aux | grep redis`

3. **数据库问题**
   - 数据库文件权限：确保data目录可写
   - 连接错误：检查SQLAlchemy连接字符串
   - 迁移问题：检查表结构是否正确初始化

4. **Celery错误**
   - Windows环境确认使用 `--pool=solo`
   - 检查Redis连接是否正常
   - 验证虚拟环境是否正确激活

5. **OCR问题**
   - 检查环境变量TESSDATA_PREFIX是否设置
   - 验证tesseract.exe路径是否在系统PATH中
   - 确认中文语言包chi_sim已安装
   - 测试命令：`tesseract --version`和`tesseract --list-langs`

6. **AI模型问题**
   - 验证模型路径是否存在且正确
   - 检查系统内存是否足够（最低4GB）
   - 检查.env文件配置是否正确
   - 检查网络连接状态（使用在线API时）

## 🛑 关闭服务

1. 停止Flask应用（按Ctrl+C）
2. 停止Celery工作进程（按Ctrl+C）
3. 关闭Redis服务：
   - Windows: `net stop Redis`
   - Linux/Mac: `redis-cli shutdown`
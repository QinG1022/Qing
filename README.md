# 文档处理Web服务

## 📌 项目概述
这是一个基于Flask的Web应用程序，提供智能文档处理服务，包括图像处理、PDF文档生成功能和AI对话功能。该应用支持异步任务处理、图像优化、文本提取以及历史记录管理等功能，可用于文档数字化和管理场景。

## 🚀 主要功能
- 📄 PDF文档生成与下载
- 🖼️ 图像批量处理与优化
- 🔍 OCR图像文字识别
- 📝 PDF文本内容提取
- 📜 历史记录管理（保存处理结果）
- 🔤 字体管理与检查
- ⏱️ 基于Celery的异步任务处理
- 🤖 AI对话（基于DeepSeek API）

## 🛠️ 技术栈
- **Web框架**: Flask
- **任务队列**: Celery + Redis
- **图像处理**: Pillow, pytesseract (OCR功能)
- **PDF处理**: ReportLab, PyPDF2, PyMuPDF
- **安全防护**: Flask-Talisman
- **数据结构**: Collections.deque (历史记录)

## 📋 安装说明

### 前置要求
- Python 3.8+
- Redis服务器
- Tesseract OCR引擎（用于OCR功能）
- DeepSeek API密钥（用于AI对话功能）

### Windows环境安装步骤
1. **克隆代码库**:
   ```bash
   git clone https://github.com/QinG1022/Qing.git
   cd Qing
   ```

2. **创建并激活虚拟环境**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

4. **安装Redis for Windows**:
   - 下载地址：https://github.com/microsoftarchive/redis/releases
   - 选择：Redis-x64-xxx.msi
   - 安装时勾选"Add to PATH"和"Install service"

5. **安装Tesseract-OCR**:
   - 下载地址：https://github.com/UB-Mannheim/tesseract/wiki
   - 选择：tesseract-ocr-w64-setup-xxx.exe
   - 添加到系统环境变量Path

6. **创建必要的目录**:
   ```bash
   mkdir -p uploads pdfs log
   ```

## 🚀 启动应用
1. **启动Redis服务**:
   ```bash
   # 方法1: Windows服务（推荐）
   net start Redis
   
   # 方法2: 命令行启动
   redis-server
   
   # 验证Redis连接
   redis-cli ping  # 应返回PONG
   ```

2. **启动Celery工作进程**:
   ```bash
   # Windows环境必须使用--pool=solo
   .\venv\Scripts\activate
   celery -A modules.tasks worker --loglevel=info --pool=solo
   ```

3. **启动Flask应用**:
   ```bash
   # 新开一个终端
   .\venv\Scripts\activate
   python app.py
   ```

4. **访问应用**:
   浏览器打开 http://localhost:5000

## 📖 使用指南

### PDF文档生成
1. 访问主页
2. 上传需要处理的图片或输入文本内容
3. 设置生成参数
4. 提交任务
5. 等待处理完成后下载生成的文件

### 图像处理与OCR
1. 选择"文档生成与图片处理"标签页
2. 上传需要处理的图片
3. 勾选"对图片进行文字识别"选项
4. 点击"处理图片"按钮
5. 查看识别结果，可选择合并到文本编辑区

### PDF文本提取
1. 选择"提取PDF文本"标签页
2. 上传需要处理的PDF文件
3. 点击"提取文本"按钮
4. 查看或复制提取的文本内容

### 历史记录功能
- 系统自动保存最近6条处理结果
- 点击"复制"按钮复制内容
- 点击"插入"按钮将内容插入到文本编辑区
- 点击单条记录右上角的删除按钮删除该记录
- 点击"清空"按钮清空所有历史记录

## 🧪 测试与验证

1. **字体检查**（必需）:
   ```bash
   python fonts/font_check.py
   ```

2. **运行所有测试**:
   ```bash
   python -m pytest tests/
   ```

3. **生成HTML测试报告**:
   ```bash
   python -m pytest --html=report.html tests/
   ```

4. **忽略废弃警告运行PDF测试**（推荐）:
   ```bash
   python -m pytest tests/test_pdf_generator.py -v -W ignore::DeprecationWarning
   python -m pytest tests/test_pdf_extractor.py -v -W ignore::DeprecationWarning
   ```

## 📁 目录结构
- `app.py`: 主应用入口
- `modules/`: 功能模块目录
  - `tasks.py`: Celery异步任务定义
  - `image_processor.py`: 图像处理模块
  - `pdf_generator.py`: PDF生成模块
  - `pdf_extractor.py`: PDF文本提取模块
  - `ocr_processor.py`: OCR处理模块
  - `ai_routes.py`: AI对话路由模块
  - `deepseek_client.py`: DeepSeek API客户端
- `celeryconfig.py`: Celery配置
- `templates/`: HTML模板
- `static/`: 静态资源文件
  - `css/`: 样式文件
  - `js/`: JavaScript文件
- `tests/`: 测试用例
  - `test_image_processor.py`: 图像处理测试
  - `test_pdf_generator.py`: PDF生成测试
  - `test_pdf_extractor.py`: PDF文本提取测试
  - `test_integration.py`: 集成测试
  - `test_history.py`: 历史记录功能单元测试
  - `test_history_integration.py`: 历史记录功能集成测试
- `tools/`: 工具脚本
  - `clean_test_reports.py`: 清理测试报告的工具

## ❓ 常见问题

1. **Redis服务无法启动**
   - 检查服务是否已安装：services.msc
   - 检查端口占用：`netstat -ano | findstr 6379`
   - 重新安装Redis

2. **Celery报错**
   - 确保使用 `--pool=solo`（Windows环境必需）
   - 检查Redis连接
   - 查看是否已激活虚拟环境

3. **OCR无法使用**
   - 检查环境变量Path是否包含Tesseract路径
   - 重启终端或电脑
   - 测试命令：`tesseract --version`

4. **端口被占用**
   ```bash
   # 查找占用端口的进程
   netstat -ano | findstr 5000
   # 结束进程
   taskkill /F /PID <进程ID>
   ```

## 🛑 关闭服务
  - 在Flask和Celery终端按 Ctrl+C
  - 关闭Redis: `net stop Redis`

### AI对话
1. 选择"AI对话"标签页
2. 在输入框中输入您的问题
3. 点击发送按钮
4. 等待AI助手回复

5. **AI对话无响应**
   - 检查.env文件中是否正确配置DeepSeek API密钥
   - 确认网络连接正常
   - 查看浏览器控制台是否有错误信息
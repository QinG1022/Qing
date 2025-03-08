# 文档处理Web服务

## 项目概述
这是一个基于Flask的Web应用程序，提供文档处理服务，包括图像处理和PDF文档生成功能。该应用支持异步任务处理、图像优化、文本提取以及历史记录管理等功能，可用于文档数字化和管理场景。

## 主要功能
- PDF文档生成与下载
- 图像批量处理与优化
- OCR图像文字识别
- PDF文本内容提取
- 历史记录管理（保存处理结果）
- 字体管理与检查
- 基于Celery的异步任务处理

## 技术栈
- **Web框架**: Flask
- **任务队列**: Celery + Redis
- **图像处理**: Pillow, pytesseract (OCR功能)
- **PDF处理**: ReportLab, PyPDF2, PyMuPDF
- **安全防护**: Flask-Talisman
- **数据结构**: Collections.deque (历史记录)

## 安装说明

### 前置要求
- Python 3.8+
- Redis服务器
- 对于OCR功能，需要安装Tesseract OCR引擎

### 安装步骤
1. 克隆代码库：
```bash
git clone https://github.com/QinG1022/Qing.git
#进入项目目录
cd <project-directory>
```

2. 创建并激活虚拟环境：
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 创建必要的目录：
```bash
mkdir -p uploads pdfs
```

5. 配置环境变量（创建.env文件）:
```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your_secret_key
```

## 运行应用

1. 启动Redis服务器：
```bash
# 根据您的系统不同，启动方式可能不同
redis-server
```

2. 启动Celery工作进程：
```bash
# Linux/Mac
celery -A modules.tasks worker --loglevel=info
# Windows
celery -A modules.tasks worker --loglevel=info --pool=solo
```

3. 启动Flask应用：
```bash
flask run
# 或者
python app.py
```

4. 访问应用：
浏览器打开 http://localhost:5000

## 使用指南

### PDF生成
1. 访问主页
2. 上传需要处理的图片或输入文本内容
3. 设置生成参数
4. 提交任务
5. 等待处理完成后下载生成的文件

### 图像处理与OCR
1. 在处理选项中选择"图像处理"
2. 上传需要处理的图片
3. 勾选"对图片进行文字识别"选项
4. 点击"处理图片"按钮
5. 查看识别结果，可选择合并到文本编辑区

### PDF文本提取
1. 在处理选项中选择"PDF文本提取"
2. 上传需要处理的PDF文件
3. 点击"提取文本"按钮
4. 查看或复制提取的文本内容

### 历史记录功能
1. 查看最近的处理结果：系统会自动保存最近6条处理结果
2. 历史记录包含三种类型：
   - 用户输入文本
   - OCR图像识别结果
   - PDF文本提取结果
3. 每条历史记录包含：类型、时间戳、来源和内容
4. 管理历史记录：
   - 点击"复制"按钮复制内容
   - 点击"插入"按钮将内容插入到文本编辑区
   - 点击单条记录右上角的删除按钮删除该记录
   - 点击"清空"按钮清空所有历史记录

## 目录结构
- `app.py`: 主应用入口
- `modules/`: 功能模块目录
  - `tasks.py`: Celery异步任务定义
  - `image_processor.py`: 图像处理模块
  - `pdf_generator.py`: PDF生成模块
  - `pdf_extractor.py`: PDF文本提取模块
  - `ocr_processor.py`: OCR处理模块
- `celeryconfig.py`: Celery配置
- `templates/`: HTML模板
- `static/`: 静态资源文件
  - `css/`: 样式文件
  - `js/`: JavaScript文件
- `Fonts/`: 字体文件目录
- `config/`: 配置文件目录
- `tests/`: 测试用例
  - `test_image_processor.py`: 图像处理测试
  - `test_pdf_generator.py`: PDF生成测试
  - `test_pdf_extractor.py`: PDF文本提取测试
  - `test_integration.py`: 集成测试
  - `test_history.py`: 历史记录功能单元测试
  - `test_history_integration.py`: 历史记录功能集成测试
- `tools/`: 工具脚本
  - `clean_test_reports.py`: 清理测试报告的工具

### 测试与报告
1. 运行单元测试：
```bash
python -m pytest tests/
```

2. 生成HTML测试报告：
```bash
python -m pytest --html=report.html tests/
```

3. 清理测试报告：
```bash
python tools/clean_test_reports.py
```

4. 运行特定模块测试：
```bash
# 图像处理测试
python -m pytest tests/test_image_processor.py -v

# PDF生成测试
python -m pytest tests/test_pdf_generator.py -v

# PDF提取器测试
python -m pytest tests/test_pdf_extractor.py -v

# 集成测试
python -m pytest tests/test_integration.py -v

# 历史记录测试
python -m pytest tests/test_history.py -v
python -m pytest tests/test_history_integration.py -v
```

## 历史记录API
- `GET /history`: 获取所有历史记录
- `DELETE /history/<record_id>`: 删除指定ID的历史记录
- `DELETE /history`: 清空所有历史记录

## 注意事项
- 历史记录默认限制为6条，超出会自动删除最旧的记录
- 图片OCR需要安装Tesseract OCR引擎
- 在Windows环境下启动Celery时必须使用`--pool=solo`参数
- 本应用使用Redis作为Celery的消息代理和结果后端

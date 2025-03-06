# 文档处理Web服务

## 项目概述
这是一个基于Flask的Web应用程序，提供文档处理服务，包括图像处理和PDF文档生成功能。该应用支持异步任务处理、图像优化以及文本提取等功能，可用于文档数字化和管理场景。

## 主要功能
- PDF文档生成与下载
- 图像批量处理与优化
- PDF文本内容提取
- 字体管理与检查
- 基于Celery的异步任务处理

## 技术栈
- **Web框架**: Flask
- **任务队列**: Celery + Redis
- **图像处理**: Pillow, pytesseract (OCR功能)
- **PDF生成**: ReportLab, PyPDF2
- **安全防护**: Flask-Talisman

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
celery -A tasks worker --loglevel=info
```

3. 启动Flask应用：
```bash
flask run
```

4. 访问应用：
浏览器打开 http://localhost:5000

## 使用指南

### PDF生成
1. 访问主页
2. 上传需要处理的图片或文档
3. 设置生成参数
4. 提交任务
5. 等待处理完成后下载生成的文件

### 图像处理
1. 在处理选项中选择"图像处理"
2. 上传需要处理的图片
3. 选择处理方式（优化、转换等）
4. 提交处理请求
5. 下载处理结果

## 目录结构
- `app.py`: 主应用入口
- `tasks.py`: Celery异步任务定义
- `celeryconfig.py`: Celery配置
- `modules/`: 功能模块目录
  - `image_processor.py`: 图像处理模块
  - `pdf_generator.py`: PDF生成模块
- `templates/`: HTML模板
- `static/`: 静态资源文件
- `Fonts/`: 字体文件目录
- `config/`: 配置文件目录
- `tests/`: 测试用例
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

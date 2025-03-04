"""
Flask 主程序
Version: 2.0
Last Modified: 2024-03-20

功能描述:
    - 提供Web服务接口
    - 处理文件上传和下载
    - 管理异步任务
    - 提供RESTful API
    - 实现安全控制

主要组件:
    - Flask: Web框架
    - Celery: 异步任务队列
    - Talisman: 安全中间件
    - Redis: 消息代理和结果后端
"""

import os
import logging
import shutil
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, abort, send_from_directory
from werkzeug.utils import secure_filename
from celery import Celery
from modules.image_processor import ImageProcessor
from modules.pdf_generator import PDFGenerator
from flask_talisman import Talisman
from celery.result import AsyncResult
from tasks import celery, generate_pdf, process_images_task

# ================ 应用配置 ================
# 内容安全策略(CSP)配置
csp = {
    'default-src': ['\'self\''],      # 默认只允许同源资源
    'img-src': [                       # 图片源策略
        '\'self\'',                    # - 允许同源
        'data:',                       # - 允许Data URL
        'blob:'                        # - 允许Blob URL
    ],
    'script-src': [                    # 脚本源策略
        '\'self\'',                    # - 允许同源
        '\'unsafe-inline\''            # - 允许内联脚本
    ],
    'style-src': [                     # 样式源策略
        '\'self\'',                    # - 允许同源
        '\'unsafe-inline\'',            # - 允许内联样式
        'https://fonts.googleapis.com'  # - 允许从Google Fonts加载样式
    ],
    'font-src': [                      # 字体源策略
        '\'self\'',                    # - 允许同源
        'https://fonts.gstatic.com'    # - 允许从Google Fonts加载字体
    ]
}

# Flask应用初始化
app = Flask(__name__)
Talisman(app, force_https=False, content_security_policy=csp)

# 应用核心配置
app.config.update(
    # 文件存储配置
    UPLOAD_FOLDER=Path("uploads"),     # 上传文件目录
    PDF_FOLDER=Path("pdfs"),           # PDF文件目录
    MAX_CONTENT_LENGTH=20 * 1024 * 1024,  # 最大上传限制(20MB)
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'webp'},  # 允许的图片格式
    
    # Celery配置
    CELERY_BROKER_URL='redis://localhost:6379/0',       # 消息队列
    CELERY_RESULT_BACKEND='redis://localhost:6379/0'    # 结果存储
)

# ================ 日志配置 ================
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('app_audit.log'),   # 文件日志
        logging.StreamHandler()                  # 控制台日志
    ]
)
# 调整Werkzeug日志级别
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# ================ 安全中间件 ================
@app.before_request
def security_check():
    """
    请求预处理安全检查
    
    检查项目:
    1. 目录访问权限验证
    2. 上传文件类型验证
    3. 请求大小限制验证
    
    异常:
        403: 目录访问被拒绝
        400: 非法文件类型
        413: 请求体过大
    """
    # 1. 目录权限验证
    required_dirs = [
        app.config['UPLOAD_FOLDER'],
        PDFGenerator.FONT_DIR
    ]
    for dir_path in required_dirs:
        if not os.access(dir_path, os.R_OK):
            abort(403, f"目录访问被拒绝：{dir_path}")

    # 2. 文件类型验证
    if request.files:
        for file in request.files.getlist('imageUpload'):
            if '.' not in file.filename or \
               file.filename.rsplit('.', 1)[1].lower() not in app.config['ALLOWED_EXTENSIONS']:
                abort(400, "非法文件类型")

    # 3. 请求大小验证
    max_limit = app.config['MAX_CONTENT_LENGTH']
    if request.content_length is not None and request.content_length > max_limit:
        abort(413, f"请求过大（最大允许 {max_limit//1024//1024}MB）")

# ================ 路由处理 ================
@app.route('/')
def index():
    """
    首页路由
    返回: 渲染后的index.html模板
    """
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def handle_generate():
    """
    文档生成处理端点
    
    功能:
        1. 接收文本内容和图片文件
        2. 处理上传的图片
        3. 启动异步PDF生成任务
    
    请求体:
        - content: 文本内容 (可选)
        - images: 图片文件列表 (可选)
        - processType: 处理类型 (默认: 'direct')
    
    返回:
        - 成功: JSON响应 (202)
            {
                "task_id": "任务ID",
                "status_url": "状态查询URL",
                "message": "处理状态信息"
            }
        - 失败: JSON错误信息 (500)
    """
    temp_dir = None
    try:
        # 获取请求数据
        text_content = request.form.get('content', '').strip()
        files = request.files.getlist('images')
        process_type = request.form.get('processType', 'direct')
        
        # 处理图片文件
        image_paths = []
        if files and any(f.filename for f in files):
            # 创建临时目录
            temp_dir = app.config['UPLOAD_FOLDER'] / f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            logging.info(f"处理图片文件: {[f.filename for f in files]}")
            try:
                # 批量处理图片
                image_paths = ImageProcessor.process_batch(files, temp_dir)
                # 验证处理后的图片路径
                valid_paths = []
                for p in image_paths:
                    abs_path = Path(p).absolute()
                    if abs_path.exists():
                        valid_paths.append(str(abs_path))
                        logging.info(f"有效图片路径: {abs_path}")
                image_paths = valid_paths
                
                if not valid_paths and not text_content:
                    raise ValueError("没有有效的图片或文本内容")
                    
                logging.info(f"成功处理了 {len(image_paths)} 张图片")
            except Exception as e:
                logging.error(f"图片处理失败: {str(e)}", exc_info=True)
                if not text_content:
                    raise

        # 启动异步PDF生成任务
        task = generate_pdf.delay(
            text_content=text_content,
            image_paths=image_paths,
            output_dir=str(app.config['PDF_FOLDER'].absolute())
        )

        logging.info(f"创建任务成功，ID: {task.id}")
        return jsonify({
            "task_id": task.id,
            "status_url": f"/tasks/{task.id}",
            "message": "任务已创建，正在处理..."
        }), 202

    except Exception as e:
        logging.error(f"处理失败: {str(e)}", exc_info=True)
        # 清理临时目录
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir)
        return jsonify({"error": str(e)}), 500

@app.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """
    任务状态查询端点
    
    参数:
        task_id: 任务ID
    
    返回:
        JSON响应:
        - 成功完成:
            {
                'status': 'SUCCESS',
                'result': 结果数据,
                'message': '成功信息'
            }
        - 处理中:
            {
                'status': 任务状态,
                'current': 当前进度,
                'total': 总进度,
                'message': '进度信息'
            }
        - 失败:
            {
                'status': 'FAILURE',
                'error': '错误信息',
                'message': '失败信息'
            }
    """
    try:
        task = AsyncResult(task_id, app=celery)
        
        if task.state == 'SUCCESS':
            result = task.result
            if isinstance(result, dict):  # OCR任务结果
                response = {
                    'status': 'SUCCESS',
                    'result': result,
                    'message': 'OCR处理完成！'
                }
            elif isinstance(result, str):  # PDF生成任务结果
                if Path(app.config['PDF_FOLDER'] / result).exists():
                    response = {
                        'status': 'SUCCESS',
                        'result': result,
                        'message': '生成成功！'
                    }
                else:
                    response = {
                        'status': 'FAILURE',
                        'error': '文件生成失败',
                        'message': '生成失败'
                    }
            else:
                response = {
                    'status': 'FAILURE',
                    'error': '未知的结果类型',
                    'message': '处理失败'
                }
        else:
            response = {
                'status': task.state,
                'current': 0,
                'total': 1,
                'message': '处理中...' if task.state == 'PROCESSING' else '任务等待中...'
            }
            if task.state == 'FAILURE':
                response.update({
                    'error': str(task.result),
                    'message': '处理失败'
                })
            
        logging.info(f"任务 {task_id} 状态: {response}")
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"获取任务状态失败: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'ERROR',
            'error': str(e),
            'message': '状态查询失败'
        }), 500

@app.route('/download/<filename>')
def download_file(filename):
    """
    文件下载端点
    
    参数:
        filename: 要下载的文件名
    
    返回:
        - 成功: 文件下载响应
        - 失败: 404错误
    
    安全措施:
        1. 验证文件存在性
        2. 限制访问目录
        3. 指定MIME类型
    """
    try:
        pdf_dir = app.config['PDF_FOLDER']
        file_path = pdf_dir / filename
        
        if not file_path.exists():
            logging.error(f"文件不存在: {file_path}")
            abort(404)
            
        logging.info(f"正在下载文件: {file_path}")
        return send_from_directory(
            directory=str(pdf_dir),
            path=filename,
            as_attachment=True,
            mimetype='application/pdf'
        )
    except Exception as e:
        logging.error(f"文件下载失败: {str(e)}", exc_info=True)
        abort(404)

@app.route('/process-images', methods=['POST'])
def process_images():
    """
    图片OCR处理端点
    
    功能:
        1. 接收上传的图片文件
        2. 创建临时存储目录
        3. 处理图片并启动OCR任务
    
    请求体:
        - images: 图片文件列表
    
    返回:
        - 成功: JSON响应 (202)
            {
                "task_id": "任务ID",
                "status_url": "状态查询URL",
                "message": "处理状态信息"
            }
        - 失败: JSON错误信息 (400/500)
    
    错误处理:
        - 400: 未上传图片
        - 500: 处理过程异常
    """
    try:
        # 验证图片上传
        files = request.files.getlist('images')
        if not files:
            return jsonify({"error": "未上传图片"}), 400

        # 创建临时目录
        temp_dir = app.config['UPLOAD_FOLDER'] / f"ocr_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 处理图片并启动OCR任务
        try:
            image_paths = ImageProcessor.process_batch(files, temp_dir)
            if not image_paths:
                return jsonify({"error": "图片处理失败"}), 400

            task = process_images_task.delay([str(p) for p in image_paths])
            
            return jsonify({
                "task_id": task.id,
                "status_url": f"/tasks/{task.id}",
                "message": "开始处理图片..."
            }), 202

        except Exception as e:
            logging.error(f"图片处理失败: {str(e)}")
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logging.error(f"请求处理失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ================ 主程序入口 ================
if __name__ == '__main__':
    try:
        # 初始化系统目录
        for dir_path in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER']]:
            dir_path.mkdir(parents=True, exist_ok=True)
            os.chmod(str(dir_path), 0o755)  # 设置目录权限
        
        # 服务器配置
        host = '127.0.0.1'
        port = 5000
        
        # 启动提示信息
        print("\n" + "="*50)
        print(" 智能文档生成系统服务已启动")
        print(f" 请在浏览器中访问: http://{host}:{port}")
        print("="*50 + "\n")
        
        # 启动开发服务器
        app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False
        )
    except Exception as e:
        print(f"启动失败: {str(e)}")
        logging.error(f"服务器启动异常: {str(e)}", exc_info=True)
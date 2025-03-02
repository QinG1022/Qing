"""
Flask 主程序
功能: 提供Web服务、文件处理和API接口
作者: [您的名字]
版本: 2.0
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
from tasks import celery, generate_pdf, process_images_task  # 添加process_images_task导入

# 定义内容安全策略(CSP)
csp = {
    'default-src': ['\'self\''],  # 默认只允许同源资源
    'img-src': ['\'self\'', 'data:', 'blob:'],  # 允许图片从同源、Data URL和Blob加载
    'script-src': ['\'self\'', '\'unsafe-inline\''],  # 允许内联脚本
    'style-src': ['\'self\'', '\'unsafe-inline\'']  # 允许内联样式
}

app = Flask(__name__)
Talisman(app, force_https=False, content_security_policy=csp)

# 应用配置
app.config.update(
    UPLOAD_FOLDER=Path("uploads"),  # 上传文件存储目录
    PDF_FOLDER=Path("pdfs"),  # PDF文件存储目录
    MAX_CONTENT_LENGTH=20 * 1024 * 1024,  # 最大上传限制：20MB
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'webp'},  # 允许的图片格式
    CELERY_BROKER_URL='redis://localhost:6379/0',  # Celery消息队列
    CELERY_RESULT_BACKEND='redis://localhost:6379/0'  # Celery结果存储
)

# 高级日志配置
logging.basicConfig(
    level=logging.WARNING,  # 将 INFO 改为 WARNING
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('app_audit.log'),
        logging.StreamHandler()
    ]
)

# 修改Werkzeug日志级别
logging.getLogger('werkzeug').setLevel(logging.ERROR)  # 添加这行

@app.before_request
def security_check():
    """安全验证三要素（修复版）"""
    # 1. 文件权限验证（保持不变）
    required_dirs = [
        app.config['UPLOAD_FOLDER'],
        PDFGenerator.FONT_DIR
    ]
    for dir_path in required_dirs:
        if not os.access(dir_path, os.R_OK):
            abort(403, f"目录访问被拒绝：{dir_path}")

    # 2. 文件类型验证（保持不变）
    if request.files:
        for file in request.files.getlist('imageUpload'):
            if '.' not in file.filename or \
               file.filename.rsplit('.', 1)[1].lower() not in app.config['ALLOWED_EXTENSIONS']:
                abort(400, "非法文件类型")

    # --- 修复区域：处理NoneType问题 ---
    # 3. 请求大小验证（安全增强版）
    max_limit = app.config['MAX_CONTENT_LENGTH']
    
    # 方法一：显式类型检查
    if request.content_length is not None and request.content_length > max_limit:
        abort(413, f"请求过大（最大允许 {max_limit//1024//1024}MB）")

    # 或方法二：短路逻辑优先处理None情况
    # content_length = request.content_length or 0
    # if content_length > max_limit:
    #    abort(413, "请求超过大小限制")

@app.route('/')
def index():
    """智能文档中心"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def handle_generate():
    """异步文档生成端点"""
    temp_dir = None
    try:
        text_content = request.form.get('content', '').strip()
        files = request.files.getlist('images')
        process_type = request.form.get('processType', 'direct')
        
        image_paths = []
        if files and any(f.filename for f in files):  # 确保有实际的文件
            # 创建唯一的临时目录
            temp_dir = app.config['UPLOAD_FOLDER'] / f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            logging.info(f"处理图片文件: {[f.filename for f in files]}")
            try:
                image_paths = ImageProcessor.process_batch(files, temp_dir)
                # 确保使用绝对路径，并检查文件存在
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
                if not text_content:  # 如果没有文本内容，则抛出异常
                    raise

        # 启动异步任务
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
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir)
        return jsonify({"error": str(e)}), 500

@app.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """改进的任务状态查看接口"""
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
    """改进的文件下载接口"""
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
    """图片OCR处理端点"""
    try:
        files = request.files.getlist('images')
        if not files:
            return jsonify({"error": "未上传图片"}), 400

        # 创建临时目录存储上传的图片
        temp_dir = app.config['UPLOAD_FOLDER'] / f"ocr_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 处理上传的图片
        try:
            image_paths = ImageProcessor.process_batch(files, temp_dir)
            if not image_paths:
                return jsonify({"error": "图片处理失败"}), 400

            # 启动OCR任务
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

if __name__ == '__main__':
    try:
        # 确保目录存在并有正确权限
        pdf_dir = app.config['PDF_FOLDER']
        pdf_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(str(pdf_dir), 0o755)
        
        upload_dir = app.config['UPLOAD_FOLDER']
        upload_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(str(upload_dir), 0o755)
        
        # 添加服务器启动提示信息
        host = '127.0.0.1'
        port = 5000
        print("\n" + "="*50)
        print(" 智能文档生成系统服务已启动")
        print(f" 请在浏览器中访问: http://{host}:{port}")
        print("="*50 + "\n")
        
        # 开发环境：使用普通HTTP
        app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False
        )
    except Exception as e:
        print(f"启动失败: {str(e)}")
        logging.error(f"服务器启动异常: {str(e)}", exc_info=True)
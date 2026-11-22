"""
Flask 主程序
功能: 提供Web服务、文件处理和API接口
描述: 提供PDF生成、OCR识别和PDF文本提取功能
"""
import os
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from flask import (Flask, render_template, request, jsonify, abort, send_from_directory,
                   session, flash, redirect, url_for)
from werkzeug.utils import secure_filename
from modules.image_processor import ImageProcessor
from modules.pdf_generator import PDFGenerator
from flask_talisman import Talisman
from modules.task_runner import AsyncResult
from modules.tasks import celery, generate_pdf, process_images_task, extract_pdf_text  # noqa: F401
import time
from collections import deque
from modules.ai_chat.ai_routes import ai_bp, reset_client
from modules.settings_store import (load_config, save_config, public_config, is_configured,
                                      record_cap)
import re
import json
import uuid
import random
import threading
import threading
from modules.database import (db, User, History, init_db, add_history_record,
                              delete_history_record, clear_user_history, get_user_history,
                              current_user, LOCAL_USER_ID)

# 定义内容安全策略(CSP)
csp = {
    'default-src': ['\'self\''],  # 默认只允许同源资源
    'img-src': ['\'self\'', 'data:', 'blob:'],  # 允许图片从同源、Data URL和Blob加载
    'script-src': ['\'self\'', '\'unsafe-inline\''],  # 允许内联脚本
    'style-src': ['\'self\'', '\'unsafe-inline\'','https://fonts.googleapis.com'],  # 允许内联样式
    'font-src': ['\'self\'', 'https://fonts.gstatic.com']  # 允许字体从Google Fonts加载  
}

app = Flask(__name__)
# 密钥：优先环境变量，否则生成一次并保存在 data/secret_key
# （硬编码在源码里的密钥等于公开——任何拿到代码的人都能伪造会话）
def _load_secret_key():
    env_key = os.getenv('SECRET_KEY')
    if env_key:
        return env_key
    key_file = Path('data') / 'secret_key'
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if key_file.exists():
        return key_file.read_text(encoding='utf-8').strip()
    import secrets
    key = secrets.token_hex(32)
    key_file.write_text(key, encoding='utf-8')
    logging.warning("已生成本地 SECRET_KEY 并保存到 data/secret_key")
    return key


app.secret_key = _load_secret_key()
Talisman(app, force_https=False, content_security_policy=csp)  # 添加安全头，但不强制HTTPS

# 注册AI蓝图
app.register_blueprint(ai_bp, url_prefix='/ai')

# 会话：单用户模式下不再需要 Flask-Session 的文件存储，
# 直接用 Flask 自带的签名 Cookie 会话（只用来放少量临时标记）。
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# 应用配置
app.config.update(
    UPLOAD_FOLDER=Path("uploads"),  # 上传文件存储目录
    PDF_FOLDER=Path("pdfs"),  # PDF文件存储目录
    MAX_CONTENT_LENGTH=20 * 1024 * 1024,  # 最大上传限制：20MB
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'webp', 'pdf'},  # 允许的文件格式
    MAX_HISTORY_ITEMS=10  # 历史记录最大保存条数
)

# 确保运行所需目录存在。
# 这些目录原来只在 __main__ 里创建，导致 before_request 的权限检查会把
# 所有请求 403 掉（用 WSGI 启动时必现）。
for _dir in [app.config['UPLOAD_FOLDER'], app.config['PDF_FOLDER'], Path('log'), Path('data')]:
    Path(_dir).mkdir(parents=True, exist_ok=True)

# 创建一个双端队列用于存储历史记录，maxlen参数限制队列最大长度
history_records = deque(maxlen=app.config['MAX_HISTORY_ITEMS'])
         
# 高级日志配置
# 注意：FileHandler 不会自动建目录，log/ 不存在会直接抛 FileNotFoundError
Path('log').mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.WARNING,  # 日志级别：INFO，记录所有信息、警告和错误，WARNING，记录警告和错误
    format='%(asctime)s [%(levelname)s] %(message)s',  # 日志格式：时间 [级别] 消息
    handlers=[
        logging.FileHandler('log/app_audit.log'),  # 文件处理器：记录到log/app_audit.log
        logging.StreamHandler()  # 流处理器：同时输出到控制台
    ]
)

# 修改Werkzeug日志级别，减少不必要的请求日志
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# 程序启动日志
logging.warning("应用程序启动 - 历史记录容量: %d", app.config['MAX_HISTORY_ITEMS'])

# 单用户模式：不再初始化 Flask-Login，current_user 由 modules.database 提供替身。
# 初始化SQLite数据库（内部会确保 id=1 的本地用户存在）
init_db(app)

@app.route('/')
def index():
    """
    主页：未配置 API Key 时先去 /setup，配置好之后进聊天界面。
    旧的三个面板界面保留在 /legacy，方便对照。
    """
    if not is_configured():
        return redirect(url_for('setup_page'))
    return render_template('chat.html')


@app.route('/home')
def home_page():
    """入口页（主界面）：品牌 + 大输入框 + 快捷入口。"""
    return render_template('home.html')


@app.route('/legacy')
def legacy_index():
    """旧界面（三面板），暂留作对照。"""
    return render_template('index.html')

@app.route('/welcome')
def welcome():
    """
    欢迎页面路由
    功能：显示系统欢迎页面
    返回：welcome.html模板渲染结果
    """
    return render_template('welcome.html')

@app.before_request
def security_check():
    """
    请求前安全检查
    作用：在处理任何请求前执行安全验证
    验证内容：
        1. 文件权限检查：确保必要目录可访问
        2. 文件类型验证：检查上传文件的扩展名
        3. 请求大小验证：确保请求不超过最大限制
    返回：如不符合安全要求，直接中断请求
    """
    # 1. 文件权限验证
    required_dirs = [
        app.config['UPLOAD_FOLDER'], # 上传文件目录  
        PDFGenerator.FONT_DIR       # 字体目录      
    ]
    for dir_path in required_dirs:           # 遍历必需目录
        if not Path(dir_path).exists():      # 目录缺失时先尝试自愈
            try:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        if not os.access(dir_path, os.R_OK): # 检查目录是否可读
            abort(403, f"目录访问被拒绝：{dir_path}") # 抛出403错误

    # 2. 文件类型验证
    if request.files:    # 如果请求包含文件  
        for file in request.files.getlist('imageUpload'):   # 获取上传的图片文件列表  
            if '.' not in file.filename or \
               file.filename.rsplit('.', 1)[1].lower() not in app.config['ALLOWED_EXTENSIONS']: # 检查文件类型是否合法  
                abort(400, "非法文件类型")  # 抛出400错误  

    # 3. 请求大小验证
    max_limit = app.config['MAX_CONTENT_LENGTH'] # 最大请求大小限制  
    
    # 显式类型检查，避免NoneType错误
    if request.content_length is not None and request.content_length > max_limit: # 检查请求大小是否超过限制  
        abort(413, f"请求过大（最大允许 {max_limit//1024//1024}MB）") # 抛出413错误     

@app.route('/generate', methods=['POST'])
def handle_generate():
    """
    文档生成接口
    功能：接收用户提交的文本和图片，异步生成PDF文档
    请求方法：POST
    参数：
        - content: 文本内容
        - images: 上传的图片文件（可多个）
        - processType: 处理类型
    处理流程：
        1. 验证输入参数
        2. 处理上传的图片
        3. 创建异步任务生成PDF
        4. 将文本内容添加到历史记录
    返回：
        - 成功：任务ID和状态URL（HTTP 202）
        - 失败：错误信息（HTTP 400/500）
    """
    temp_dir = None # 临时目录  
    try:
        text_content = request.form.get('content', '').strip() # 获取文本内容   
        files = request.files.getlist('images') # 获取上传的图片文件列表  

         # 检查必须至少包含文本内容或图片
        if not text_content and not any(f.filename for f in files):
            return jsonify({"error": "必须提供文档内容或上传图片"}), 400
        
        process_type = request.form.get('processType', 'direct') # 获取处理类型     
        
        # 如果有文本内容，添加到历史记录
        if text_content:
            # 为来源添加一些描述性信息
            source = '用户输入文本'
            if len(text_content) > 50:
                # 为长文本添加一部分预览
                preview = text_content[:50].replace('\n', ' ') + '...'
                source = f'用户输入：{preview}'
            else:
                source = f'用户输入：{text_content}'
                
            # 生成唯一ID    
            record_id = f"text_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 保存到历史记录
            user_id = current_user.id if current_user.is_authenticated else None
            
            if user_id:
                # 已登录用户，保存到数据库
                add_history_record(
                    record_id=record_id,
                    record_type='TEXT',
                    content=text_content,
                    source=source,
                    user_id=user_id
                )
            else:
                # 匿名用户，保存到会话
                anonymous_history = session.get('anonymous_history', [])
                history_item = {
                    'id': record_id,
                    'type': 'TEXT',
                    'content': text_content,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'source': source
                }
                anonymous_history.insert(0, history_item)  # 添加到列表前端
                
                # 保持历史记录不超过最大限制
                if len(anonymous_history) > app.config['MAX_HISTORY_ITEMS']:
                    anonymous_history = anonymous_history[:app.config['MAX_HISTORY_ITEMS']]
                
                session['anonymous_history'] = anonymous_history
            
            logging.info(f"添加用户输入文本到历史记录，ID: {record_id}")
            
        image_paths = []                                # 图片路径列表  
        if files and any(f.filename for f in files):    # 确保有实际的文件
            # 创建唯一的临时目录
            temp_dir = app.config['UPLOAD_FOLDER'] / f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
            temp_dir.mkdir(parents=True, exist_ok=True) # 创建临时目录  
            
            logging.info(f"处理图片文件: {[f.filename for f in files]}")
            try:
                # 批量处理上传的图片
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

        # 启动异步任务生成PDF
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
        }), 202  # 202 Accepted表示请求已接受但尚未处理完成

    except Exception as e:
        logging.error(f"处理失败: {str(e)}", exc_info=True)
        # 清理临时目录
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir)
        return jsonify({"error": str(e)}), 500

@app.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """
    任务状态查询接口
    功能：查询指定任务ID的处理状态和结果
    请求方法：GET
    参数：
        - task_id: 任务ID（URL参数）
    处理流程：
        1. 获取任务对象
        2. 根据任务状态返回相应信息
        3. 对于成功完成的OCR或PDF提取任务，将结果添加到历史记录
    返回：
        - 任务状态、进度和结果信息（JSON格式）
    """
    try:
        task = AsyncResult(task_id, app=celery)
        
        if task.state == 'SUCCESS':
            result = task.result
            if isinstance(result, dict):  # OCR任务或PDF文本提取任务
                # 处理不同的状态码
                status = result.get('status', 'UNKNOWN')
                if status == 'success':
                    # 判断任务类型并添加到历史记录
                    if 'results' in result and len(result['results']) > 0:
                        # 确定任务类型
                        task_type = 'UNKNOWN'
                        source = '未知来源'
                        content_text = ''
                        
                        # OCR任务结果处理 - 每个结果项都有text字段
                        if all(isinstance(item, dict) and 'text' in item and 'confidence' in item for item in result['results']):
                            task_type = 'OCR'
                            source = '图片识别'
                            # 合并所有OCR文本
                            content_text = '\n\n'.join([item.get('text', '') for item in result['results'] if item.get('text')])
                        
                        # PDF提取任务结果处理 - 结果中有pages和filename字段
                        elif len(result['results']) == 1 and 'pages' in result['results'][0] and 'filename' in result['results'][0]:
                            task_type = 'PDF'
                            filename = result['results'][0].get('filename', '未知文件')
                            source = f'PDF提取：{filename}'
                            pdf_result = result['results'][0]
                            # 合并所有页面文本
                            if 'pages' in pdf_result and pdf_result['pages']:
                                content_text = '\n\n'.join([f"第{page.get('page_num')}页:\n{page.get('text', '')}" 
                                                     for page in pdf_result['pages'] if page.get('text')])
                            else:
                                content_text = pdf_result.get('text', '')
                        
                        # 添加到历史记录中
                        if content_text and task_type != 'UNKNOWN':
                            # 生成唯一ID
                            record_id = f"{task_type.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            
                            # 保存到历史记录
                            user_id = current_user.id if current_user.is_authenticated else None
                            
                            if user_id:
                                # 已登录用户，保存到数据库
                                add_history_record(
                                    record_id=record_id,
                                    record_type=task_type,
                                    content=content_text,
                                    source=source,
                                    user_id=user_id
                                )
                            else:
                                # 匿名用户，保存到会话
                                anonymous_history = session.get('anonymous_history', [])
                                history_item = {
                                    'id': record_id,
                                    'type': task_type,
                                    'content': content_text,
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'source': source
                                }
                                anonymous_history.insert(0, history_item)  # 添加到列表前端
                                
                                # 保持历史记录不超过最大限制
                                if len(anonymous_history) > app.config['MAX_HISTORY_ITEMS']:
                                    anonymous_history = anonymous_history[:app.config['MAX_HISTORY_ITEMS']]
                                
                                session['anonymous_history'] = anonymous_history
                            
                            logging.info(f"添加{task_type}历史记录成功，来源：{source}，任务ID: {task_id}")
                    
                    response = {
                        'status': 'SUCCESS',
                        'result': result,
                        'message': 'OCR处理完成！' if 'text' in result else 'PDF文本提取完成！'
                    }
                elif status == 'warning':
                    response = {
                        'status': 'WARNING',
                        'result': result,
                        'message': result.get('message', 'OCR处理有警告')
                    }
                elif status == 'error':
                    response = {
                        'status': 'FAILURE',
                        'error': result.get('message', '未知错误'),
                        'message': '处理失败'
                    }
                else:
                    response = {
                        'status': 'UNKNOWN',
                        'result': result,
                        'message': '未知状态'
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
            
        logging.info(f"任务 {task_id} 状态: {response.get('status')}, 消息: {response.get('message', '无消息')}")
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
    文件下载接口
    功能：提供PDF文件下载
    请求方法：GET
    参数：
        - filename: 文件名（URL参数）
    安全措施：
        - 验证文件是否存在
        - 使用send_from_directory确保安全下载
    返回：
        - 成功：文件下载响应
        - 失败：404错误
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
    图片OCR处理接口
    功能：接收图片文件并进行OCR识别
    请求方法：POST
    参数：
        - images: 上传的图片文件（可多个）
    处理流程：
        1. 验证上传的文件
        2. 创建临时目录存储图片
        3. 批量处理图片
        4. 创建异步OCR任务
    返回：
        - 成功：任务ID和状态URL（HTTP 202）
        - 失败：错误信息（HTTP 400/500）
    """
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

@app.route('/extract-pdf', methods=['POST'])
def extract_pdf():
    """
    PDF文本提取接口
    功能：从PDF文件中提取文本内容
    请求方法：POST
    参数：
        - pdfs: 上传的PDF文件（可多个）
    处理流程：
        1. 验证上传的文件
        2. 创建临时目录存储PDF
        3. 保存上传的PDF文件
        4. 创建异步文本提取任务
    返回：
        - 成功：任务ID和状态URL（HTTP 202）
        - 失败：错误信息（HTTP 400/500）
    """
    try:
        files = request.files.getlist('pdfs')
        if not files:
            return jsonify({"error": "未上传PDF文件"}), 400

        # 创建临时目录存储上传的PDF文件
        temp_dir = app.config['UPLOAD_FOLDER'] / f"pdf_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 处理上传的PDF文件
        try:
            # 保存PDF文件
            pdf_paths = []
            for file in files:
                if file and file.filename and file.filename.lower().endswith('.pdf'):
                    # 生成安全文件名
                    secure_name = secure_filename(file.filename)
                    timestamp = int(time.time() * 1000)
                    filename = f"pdf_{timestamp}_{secure_name}"
                    file_path = temp_dir / filename
                    file.save(file_path)
                    pdf_paths.append(str(file_path))
                else:
                    return jsonify({"error": "不支持的文件格式，请上传PDF文件"}), 400

            if not pdf_paths:
                return jsonify({"error": "未找到有效的PDF文件"}), 400

            # 启动提取任务
            task = extract_pdf_text.delay(pdf_paths)
            
            return jsonify({
                "task_id": task.id,
                "status_url": f"/tasks/{task.id}",
                "message": "开始提取PDF文本..."
            }), 202

        except Exception as e:
            logging.error(f"PDF文件处理失败: {str(e)}")
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logging.error(f"请求处理失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/history', methods=['GET'])
def get_history():
    """
    获取历史记录接口
    功能：获取用户的历史操作记录
    请求方法：GET
    返回：
        - 成功：历史记录列表（JSON格式）
        - 失败：错误信息（HTTP 500）
    """
    try:
        history_list = []
        if current_user.is_authenticated:
            # 获取登录用户的历史记录
            history_list = get_user_history(current_user.id, app.config['MAX_HISTORY_ITEMS'])
        else:
            # 获取匿名用户的历史记录（从会话中）
            session_histories = session.get('anonymous_history', [])
            history_list = session_histories[:app.config['MAX_HISTORY_ITEMS']]
        
        logging.info(f"获取历史记录，总数: {len(history_list)}")
        return jsonify({
            "status": "success",
            "history": history_list,
            "count": len(history_list),
            "max_count": app.config['MAX_HISTORY_ITEMS']
        })
    except Exception as e:
        logging.error(f"获取历史记录失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/history/<record_id>', methods=['DELETE'])
def delete_history_record_route(record_id):
    """
    删除单条历史记录接口
    功能：删除指定ID的历史记录
    请求方法：DELETE
    参数：
        - record_id: 记录ID（URL参数）
    返回：
        - 成功：删除成功的消息和剩余记录数
        - 失败：错误信息（HTTP 404/500）
    """
    try:
        if current_user.is_authenticated:
            # 删除数据库中的记录
            success = delete_history_record(record_id)
        else:
            # 删除会话中的匿名记录
            found = False
            session_histories = session.get('anonymous_history', [])
            for i, record in enumerate(session_histories):
                if record.get('id') == record_id:
                    del session_histories[i]
                    session['anonymous_history'] = session_histories
                    found = True
                    success = True
                    break
            if not found:
                success = False
        
        if success:
            logging.info(f"删除历史记录，ID: {record_id}")
            return jsonify({
                "status": "success", 
                "message": "历史记录已删除",
                "count": len(get_user_history(current_user.id) if current_user.is_authenticated else session.get('anonymous_history', []))
            })
        else:
            return jsonify({"error": "未找到指定的历史记录"}), 404
            
    except Exception as e:
        logging.error(f"删除历史记录失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/history', methods=['DELETE'])
def clear_history():
    """
    清空历史记录接口
    功能：删除所有历史记录
    请求方法：DELETE
    返回：
        - 成功：清空成功的消息
        - 失败：错误信息（HTTP 500）
    """
    try:
        if current_user.is_authenticated:
            # 清空数据库中当前用户的历史记录
            clear_user_history(current_user.id)
        else:
            # 清空会话中的匿名历史记录
            session['anonymous_history'] = []
        
        logging.info("清空所有历史记录")
        return jsonify({
            "status": "success", 
            "message": "所有历史记录已清空"
        })
    except Exception as e:
        logging.error(f"清空历史记录失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/history', methods=['GET'])
def ai_history():
    """获取AI相关历史记录"""
    # 可从现有history_records中筛选AI类型记录
    ai_history_records = [record for record in history_records if record.get('type') in ['AI_CHAT']]
    return jsonify({"history": ai_history_records})

# 添加用户接口路由
# 单用户模式：注册 / 登录 / 登出接口已移除。
# 首次启动时由 /setup 配置 API Key，用户固定为 id=1 的本地用户。

@app.route('/api/logout', methods=['POST'])
def logout():
    """兼容旧前端：单用户模式没有登录态，直接返回成功。"""
    return jsonify({'success': True, 'message': '单用户模式无需登录'})

# 添加PDF文本提取任务回调处理器
@app.route('/api/callback/pdf-extract/<task_id>', methods=['POST'])
def handle_pdf_extract_callback(task_id):
    """
    处理PDF文本提取任务的回调
    """
    try:
        data = request.get_json()
        status = data.get('status')
        if status == 'SUCCESS':
            # 任务成功完成
            result = data.get('result', {})
            
            # 取第一个文件的文本（简化处理，实际应用可能需要处理多个文件）
            if result.get('status') == 'success' and result.get('results'):
                pdf_result = result['results'][0]  # 获取第一个PDF结果
                
                # 构建历史记录数据
                source = f"PDF提取：{pdf_result['filename']}"
                record_id = str(uuid.uuid4())
                
                # 保存到历史记录
                user_id = current_user.id if current_user.is_authenticated else None
                
                if user_id:
                    # 已登录用户，保存到数据库
                    add_history_record(
                        record_id=record_id,
                        record_type='PDF',
                        content=pdf_result['text'],
                        source=source,
                        user_id=user_id
                    )
                else:
                    # 匿名用户，保存到会话
                    anonymous_history = session.get('anonymous_history', [])
                    history_item = {
                        'id': record_id,
                        'type': 'PDF',
                        'content': pdf_result['text'],
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': source
                    }
                    anonymous_history.insert(0, history_item)  # 添加到列表前端
                    
                    # 保持历史记录不超过最大限制
                    if len(anonymous_history) > app.config['MAX_HISTORY_ITEMS']:
                        anonymous_history = anonymous_history[:app.config['MAX_HISTORY_ITEMS']]
                    
                    session['anonymous_history'] = anonymous_history
                
                logging.info(f"添加PDF历史记录成功，来源：{source}，任务ID: {task_id}")
            
            return jsonify({"status": "success", "message": "PDF文本提取完成！"})
        else:
            # 任务失败
            error_message = data.get('error', '未知错误')
            logging.error(f"PDF提取任务失败，任务ID: {task_id}, 错误: {error_message}")
            return jsonify({"status": "error", "message": f"PDF文本提取失败: {error_message}"})
            
    except Exception as e:
        logging.error(f"处理PDF提取回调时出错: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/user-profile', methods=['GET'])
def get_user_profile():
    """获取当前登录用户的资料信息"""
    try:
        # 检查用户是否已登录
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'message': '用户未登录'
            }), 401
            
        # 获取用户对象
        user = User.query.get(current_user.id)
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
            
        # 格式化注册时间
        register_time = user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None
            
        # 返回用户资料
        return jsonify({
            'success': True,
            'user': {
                'username': user.username,
                'email': user.email,
                'register_time': register_time
            }
        })
    except Exception as e:
        logging.error(f"获取用户资料时发生错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    """单用户模式：永远视为已登录，返回本地用户信息。"""
    try:
        user = User.query.get(LOCAL_USER_ID)
        if not user:
            return jsonify({'authenticated': False})
        register_time = user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None
        return jsonify({
            'authenticated': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'register_time': register_time
            }
        })
    except Exception as e:
        logging.error(f"检查认证状态出错: {str(e)}", exc_info=True)
        return jsonify({'authenticated': False})

@app.route('/setup')
def setup_page():
    """首次配置页：填写服务商 / Base URL / API Key / 模型名。"""
    return render_template('setup.html')


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """读取当前配置（Key 打码）。"""
    return jsonify({
        'success': True,
        'configured': is_configured(),
        'settings': public_config()
    })


@app.route('/api/settings', methods=['POST'])
def update_settings():
    """保存配置。改完立即重建 AI 客户端，不需要重启进程。"""
    data = request.get_json(silent=True) or {}

    # 校验：避免把配置写坏（比如自检或误操作传进 example.com）
    base_url = (data.get('base_url') or '').strip()
    if base_url and not (base_url.startswith('http://') or base_url.startswith('https://')):
        return jsonify({'success': False, 'message': 'Base URL 必须以 http:// 或 https:// 开头'}), 400
    if 'model' in data and not (data.get('model') or '').strip():
        return jsonify({'success': False, 'message': '模型名不能为空'}), 400

    if not (data.get('api_key') or is_configured()):
        return jsonify({'success': False, 'message': '请填写 API Key'}), 400

    try:
        save_config(data)
        reset_client()
        logging.warning("配置已更新，AI 客户端将在下次请求时重建")
        return jsonify({'success': True, 'settings': public_config()})
    except Exception as e:
        logging.error(f"保存配置失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/settings/test', methods=['POST'])
def test_settings():
    """用当前（或刚填写的）配置发一次最小请求，验证 Key 是否可用。"""
    data = request.get_json(silent=True) or {}
    cfg = load_config()
    api_key = (data.get('api_key') or cfg.get('api_key') or '').strip()
    base_url = (data.get('base_url') or cfg.get('base_url') or '').strip()
    model = (data.get('model') or cfg.get('model') or '').strip()

    if not api_key:
        return jsonify({'success': False, 'message': '请先填写 API Key'}), 400

    try:
        from openai import OpenAI
        # 加超时并禁用自动重试：出问题要快速失败，而不是让浏览器等到超时
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=15, max_retries=0)
        client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': 'ping'}],
            max_tokens=1
        )
        record_cap(model, chat=True)
        return jsonify({'success': True, 'message': '连接成功', 'model': model})
    except Exception as e:
        record_cap(model, chat=False)
        return jsonify({'success': False, 'message': f'连接失败：{str(e)[:200]}'}), 400


# ---------------------------------------------------------------------------
# 模型分类：按名字推断用途。
# 这只是启发式判断（平台不提供能力元数据），用于给用户一个大概的方向。
# ---------------------------------------------------------------------------
MODEL_KINDS = {
    'text': '纯文本',
    'vision': '识图',
    'ocr': 'OCR',
    'audio': '语音',
    'embedding': '向量',
    'rerank': '重排',
    'image': '生图',
    'video': '视频',
}

# 顺序即优先级：越具体越靠前
_KIND_RULES = [
    ('rerank', ('rerank',)),
    ('embedding', ('embed', 'bge-', 'gte-', 'm3e', 'text2vec')),
    ('audio', ('audio', 'whisper', 'tts', 'speech', 'asr', 'sensevoice', 'cosyvoice')),
    # OCR 专用模型：图片/文档 -> 文字
    ('ocr', ('ocr',)),
    ('image', ('flux', 'stable-diffusion', 'sd3', 'kolors', 'seedream', 'dall-e', 'imagen',
               'z-image', 'qwen-image', 'moss-image', 'hunyuan-image', 'seededit')),
    ('video', ('video', 'cogvideo', 'hunyuanvideo', 'wan2', 'seedance', 'kling')),
    ('vision', ('vl', 'vision', '4v', 'internvl', 'llava', 'minicpm-v', 'qvq', 'omni',
                'gpt-4o', 'gemini', 'glm-4.5v', 'step-1v')),
]


def classify_model(model_id):
    """按模型名猜用途，猜不出就当纯文本。"""
    mid = (model_id or '').lower()
    for kind, markers in _KIND_RULES:
        if any(marker in mid for marker in markers):
            return kind
    return 'text'


@app.route('/api/settings/models', methods=['POST'])
def list_models():
    """用当前 Key 拉取服务商实际可用的模型列表（OpenAI 兼容的 /models）。"""
    data = request.get_json(silent=True) or {}
    cfg = load_config()
    api_key = (data.get('api_key') or cfg.get('api_key') or '').strip()
    base_url = (data.get('base_url') or cfg.get('base_url') or '').strip()

    if not api_key:
        return jsonify({'success': False, 'message': '请先填写 API Key'}), 400

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=20, max_retries=0)
        resp = client.models.list()
        ids = sorted({m.id for m in (resp.data or [])})
        if not ids:
            return jsonify({'success': False, 'message': '服务商没有返回任何模型'}), 400

        models = []
        summary = {}
        for model_id in ids:
            kind = classify_model(model_id)
            models.append({'id': model_id, 'kind': kind, 'label': MODEL_KINDS.get(kind, kind)})
            summary[kind] = summary.get(kind, 0) + 1

        return jsonify({
            'success': True,
            'count': len(ids),
            'models': models,
            'summary': summary,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败：{str(e)[:200]}'}), 400


# 1x1 透明 PNG，约 70 字节，用来探测模型是否接受图像输入
_PROBE_PIXEL = (
    'data:image/png;base64,'
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
)

# 这些关键字说明"模型不认识图像输入"，而不是网络/鉴权问题
_VISION_MARKERS = ('image', 'vision', 'multimodal', 'content', 'invalid', 'unsupported', 'not support')


@app.route('/api/settings/probe-vision', methods=['POST'])
def probe_vision():
    """用一张 1x1 图片探测当前模型是否支持图像输入。

    返回 supported=True/False，message 说明原因。
    探测成本约 1 个 token。
    """
    data = request.get_json(silent=True) or {}
    cfg = load_config()
    api_key = (data.get('api_key') or cfg.get('api_key') or '').strip()
    base_url = (data.get('base_url') or cfg.get('base_url') or '').strip()
    model = (data.get('model') or cfg.get('model') or '').strip()

    if not api_key:
        return jsonify({'success': False, 'message': '请先填写 API Key'}), 400
    if not model:
        return jsonify({'success': False, 'message': '请先选择模型'}), 400

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=25, max_retries=0)
        client.chat.completions.create(
            model=model,
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': '这张图里有什么？'},
                    {'type': 'image_url', 'image_url': {'url': _PROBE_PIXEL}},
                ],
            }],
            max_tokens=4,
        )
        record_cap(model, vision=True)
        return jsonify({
            'success': True, 'supported': True, 'model': model,
            'message': '支持图像输入（多模态）',
        })
    except Exception as e:
        detail = str(e)[:200]
        low = detail.lower()
        looks_like_no_vision = any(marker in low for marker in _VISION_MARKERS)
        if looks_like_no_vision:
            record_cap(model, vision=False)
        return jsonify({
            'success': True,
            'supported': False,
            'model': model,
            'message': ('这是纯文本模型，不接受图片' if looks_like_no_vision
                        else '探测失败：' + detail),
        })


@app.context_processor
def inject_asset_version():
    """模板里用 asset_ver('css/chat.css') 拿到文件的修改时间，作为缓存版本号。"""
    def asset_ver(rel_path):
        try:
            f = Path(app.static_folder) / rel_path
            return int(f.stat().st_mtime)
        except Exception:
            return 0
    return {'asset_ver': asset_ver}


@app.after_request
def add_cache_control(response):
    """添加缓存控制头"""
    # API 和 HTML 页面都不缓存：
    # - API 带登录态，必须 no-store
    # - HTML 里内嵌了 ?v= 版本号和模板结构，缓存住会导致改动看不到
    if request.path.startswith('/api/') or (response.mimetype or '').startswith('text/html'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

def cleanup_old_files(days=7):
    """删除上传目录和生成目录里超过 N 天的文件。启动时调用一次。"""
    import time as _time
    cutoff = _time.time() - days * 86400
    removed = 0
    for folder in (app.config.get('UPLOAD_FOLDER'), app.config.get('PDF_FOLDER')):
        if not folder:
            continue
        for f in Path(folder).glob('*'):
            try:
                if f.is_file() and f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
            except Exception:
                pass
    if removed:
        logging.warning("%s 清理了 %d 个过期文件（超过 %d 天）", "启动时", removed, days)
    return removed


if __name__ == '__main__':
    # 默认只绑本机：单用户本地应用不需要对外监听（也避免 Windows 防火墙弹窗）
    host = os.getenv('QING_HOST', '127.0.0.1')
    try:
        port = int(os.getenv('QING_PORT', '5000'))
    except ValueError:
        port = 5000

    for _dir in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER'], Path('data'), Path('log')]:
        Path(_dir).mkdir(parents=True, exist_ok=True)

    cleanup_old_files(7)

    print('=' * 56)
    print(' Qing 已启动')
    print(f'   本机访问 : http://127.0.0.1:{port}')
    if host == '0.0.0.0':
        print(f'   局域网   : http://<本机IP>:{port}')
    print('   Ctrl+C   : 停止服务')
    print('=' * 56, flush=True)

    try:
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
    except OSError as e:
        print(f'\n[启动失败] 无法监听 {host}:{port}：{e}')
        print('  常见原因：端口被占用。换一个端口再试：')
        print('    set QING_PORT=5001')
        print('    run.bat')
        try:
            input('按回车退出...')
        except EOFError:
            pass
    except KeyboardInterrupt:
        print('\n已停止')
        logging.error(f"服务器启动异常: {str(e)}", exc_info=True)
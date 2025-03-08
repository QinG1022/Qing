import pytest
import os
import sys
import json
from pathlib import Path
import logging
from io import BytesIO
from PIL import Image

# 添加项目根目录到 Python 路径，确保能够导入app模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, history_records  # 导入Flask应用和历史记录队列

@pytest.fixture
def client():
    """
    创建测试客户端夹具(fixture)
    
    这个集成测试夹具会:
    1. 配置Flask应用为测试模式
    2. 设置测试用的临时目录
    3. 确保目录存在
    4. 清空历史记录，确保干净的测试环境
    5. 测试后清理临时文件
    """
    app.config['TESTING'] = True  # 启用测试模式
    app.config['PDF_FOLDER'] = Path("test_pdfs")  # 设置测试PDF目录
    app.config['UPLOAD_FOLDER'] = Path("test_uploads")  # 设置测试上传目录
    
    # 确保测试目录存在，避免权限错误
    for folder in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER']]:
        folder.mkdir(parents=True, exist_ok=True)
        
    # 清空历史记录，确保每个测试从干净的状态开始
    history_records.clear()
    
    # 创建并返回测试客户端
    with app.test_client() as client:
        yield client
        
        # 测试完成后清理测试文件
        for folder in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER']]:
            if folder.exists():
                for file in folder.glob('*'):
                    if file.is_file():
                        file.unlink()  # 删除测试文件

@pytest.fixture
def test_image():
    """
    创建用于测试的内存图片
    
    返回:
        BytesIO: 包含测试图片数据的内存对象，可用于模拟文件上传
    """
    # 创建一个简单的纯红色测试图片
    img = Image.new('RGB', (100, 100), color = 'red')
    img_io = BytesIO()  # 创建内存流对象
    img.save(img_io, 'PNG')  # 将图片保存为PNG格式
    img_io.seek(0)  # 重置指针位置到开始
    return img_io  # 返回可用于上传的内存流对象

@pytest.fixture
def test_pdf():
    """
    准备测试用PDF文件
    
    功能:
    1. 检查测试PDF是否存在
    2. 如果不存在，创建一个简单的测试PDF
    3. 返回该PDF的内存对象以供测试使用
    
    返回:
        BytesIO: 包含测试PDF数据的内存对象，可用于模拟文件上传
    """
    # 定义测试PDF文件路径
    pdf_path = project_root / 'tests' / 'test_data' / 'test.pdf'
    
    # 确保test_data目录存在
    test_data_dir = project_root / 'tests' / 'test_data'
    if not test_data_dir.exists():
        test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 如果测试PDF不存在，创建一个简单的PDF文件
    if not pdf_path.exists():
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path))  # 创建PDF画布
        c.drawString(100, 750, "测试PDF文件内容")  # 添加文本内容
        c.save()  # 保存PDF
    
    # 读取PDF内容到内存
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    # 创建内存流对象
    pdf_file = BytesIO(pdf_data)
    pdf_file.name = 'test.pdf'  # 设置文件名
    return pdf_file  # 返回可用于上传的内存流对象

def test_ocr_adds_to_history(client, test_image):
    """
    测试OCR处理后是否正确添加历史记录
    
    测试步骤:
    1. 清空历史记录
    2. 模拟上传图片并进行OCR处理
    3. 模拟OCR任务完成
    4. 验证历史记录中是否包含OCR结果
    
    参数:
        client: Flask测试客户端
        test_image: 测试图片内存对象
    """
    # 清空历史记录
    history_records.clear()
    
    # 准备图片上传数据
    test_image.name = 'test.png'
    data = {
        'images': (test_image, 'test.png')
    }
    
    # 使用unittest.mock模拟OCR处理功能
    from unittest.mock import patch
    with patch('modules.ocr_processor.OCRProcessor.process_batch') as mock_ocr:
        # 设置模拟的OCR结果
        mock_ocr.return_value = [{
            'image_path': 'test.png',
            'text': '测试OCR文本结果',  # 模拟OCR识别出的文本
            'confidence': 0.9  # 模拟置信度
        }]
        
        # 发送处理图片请求
        response = client.post('/process-images', data=data, content_type='multipart/form-data')
        
        # 检查响应状态
        assert response.status_code == 202  # 确认请求被接受（异步处理）
        
        # 从响应中获取任务ID
        response_data = json.loads(response.data)
        task_id = response_data['task_id']
        
        # 模拟异步任务完成
        with patch('app.AsyncResult') as mock_result:
            # 设置模拟的任务结果
            mock_result.return_value.state = 'SUCCESS'  # 模拟任务状态为成功
            mock_result.return_value.result = {
                'status': 'success',
                'results': [{
                    'text': '测试OCR文本结果',
                    'confidence': 0.9,
                    'path': 'test.png'
                }]
            }
            
            # 获取任务状态，这将触发历史记录的添加
            response = client.get(f'/tasks/{task_id}')
            assert response.status_code == 200  # 确认请求成功
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证历史记录中添加了OCR结果
    assert data['count'] > 0  # 确认有记录
    # 查找包含OCR结果文本的记录
    found_ocr_record = False
    for record in data['history']:
        if record['type'] == 'OCR' and '测试OCR文本结果' in record['content']:
            found_ocr_record = True
            break
    
    # 确认找到了OCR记录
    assert found_ocr_record, "历史记录中未找到OCR结果"

def test_pdf_extract_adds_to_history(client, test_pdf):
    """
    测试PDF文本提取后是否正确添加历史记录
    
    测试步骤:
    1. 清空历史记录
    2. 模拟上传PDF并进行文本提取
    3. 模拟PDF提取任务完成
    4. 验证历史记录中是否包含PDF提取结果
    
    参数:
        client: Flask测试客户端
        test_pdf: 测试PDF内存对象
    """
    # 清空历史记录
    history_records.clear()
    
    # 准备PDF上传数据
    data = {
        'pdfs': (test_pdf, 'test.pdf')
    }
    
    # 使用unittest.mock模拟PDF提取功能
    from unittest.mock import patch
    with patch('modules.pdf_extractor.PDFExtractor.process_batch') as mock_extract:
        # 设置模拟的PDF提取结果
        mock_extract.return_value = [{
            'filename': 'test.pdf',
            'text': '测试PDF提取文本结果',  # 模拟提取的文本
            'total_pages': 1,  # 模拟页数
            'pages': [
                {
                    'page_num': 1,
                    'text': '测试PDF提取文本结果',
                    'page_size': 'A4'
                }
            ]
        }]
        
        # 发送提取PDF请求
        response = client.post('/extract-pdf', data=data, content_type='multipart/form-data')
        
        # 检查响应状态
        assert response.status_code == 202  # 确认请求被接受（异步处理）
        
        # 从响应中获取任务ID
        response_data = json.loads(response.data)
        task_id = response_data['task_id']
        
        # 模拟异步任务完成
        with patch('app.AsyncResult') as mock_result:
            # 设置模拟的任务结果
            mock_result.return_value.state = 'SUCCESS'  # 模拟任务状态为成功
            mock_result.return_value.result = {
                'status': 'success',
                'results': [{
                    'filename': 'test.pdf',
                    'text': '测试PDF提取文本结果',
                    'total_pages': 1,
                    'pages': [
                        {
                            'page_num': 1,
                            'text': '测试PDF提取文本结果',
                            'page_size': 'A4'
                        }
                    ]
                }]
            }
            
            # 获取任务状态，这将触发历史记录的添加
            response = client.get(f'/tasks/{task_id}')
            assert response.status_code == 200  # 确认请求成功
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证历史记录中添加了PDF提取结果
    assert data['count'] > 0  # 确认有记录
    # 查找包含PDF提取结果文本的记录
    found_pdf_record = False
    for record in data['history']:
        if record['type'] == 'PDF' and '测试PDF提取文本结果' in record['content']:
            found_pdf_record = True
            break
    
    # 确认找到了PDF记录
    assert found_pdf_record, "历史记录中未找到PDF提取结果"

def test_text_input_adds_to_history(client):
    """
    测试用户文本输入是否正确添加到历史记录
    
    测试步骤:
    1. 清空历史记录
    2. 提交包含文本内容的表单
    3. 验证历史记录中是否包含用户输入的文本
    
    参数:
        client: Flask测试客户端
    """
    # 清空历史记录
    history_records.clear()
    
    # 准备文本内容数据
    data = {
        'content': '用户输入的测试文本'
    }
    
    # 发送生成文档请求
    response = client.post('/generate', data=data)
    
    # 检查响应状态
    assert response.status_code == 202  # 确认请求被接受（异步处理）
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证历史记录中添加了用户输入文本
    assert data['count'] > 0  # 确认有记录
    # 查找包含用户输入文本的记录
    found_text_record = False
    for record in data['history']:
        if record['type'] == 'TEXT' and '用户输入的测试文本' in record['content']:
            found_text_record = True
            break
    
    # 确认找到了文本记录
    assert found_text_record, "历史记录中未找到用户输入文本" 
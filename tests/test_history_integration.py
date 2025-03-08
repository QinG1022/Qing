import pytest
import os
import sys
import json
from pathlib import Path
import logging
from io import BytesIO
from PIL import Image

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, history_records

@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    app.config['PDF_FOLDER'] = Path("test_pdfs")
    app.config['UPLOAD_FOLDER'] = Path("test_uploads")
    
    # 确保测试目录存在
    for folder in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER']]:
        folder.mkdir(parents=True, exist_ok=True)
        
    # 清空历史记录，确保测试环境干净
    history_records.clear()
    
    with app.test_client() as client:
        yield client
        
        # 清理测试文件
        for folder in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER']]:
            if folder.exists():
                for file in folder.glob('*'):
                    if file.is_file():
                        file.unlink()

@pytest.fixture
def test_image():
    """创建测试图片"""
    img = Image.new('RGB', (100, 100), color = 'red')
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

@pytest.fixture
def test_pdf():
    """准备测试PDF文件路径"""
    pdf_path = project_root / 'tests' / 'test_data' / 'test.pdf'
    
    # 如果test_data目录不存在，创建它
    test_data_dir = project_root / 'tests' / 'test_data'
    if not test_data_dir.exists():
        test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 如果没有测试PDF，创建一个简单的测试PDF文件
    if not pdf_path.exists():
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path))
        c.drawString(100, 750, "测试PDF文件内容")
        c.save()
    
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    pdf_file = BytesIO(pdf_data)
    pdf_file.name = 'test.pdf'
    return pdf_file

def test_ocr_adds_to_history(client, test_image):
    """测试OCR处理后是否添加历史记录"""
    # 清空历史记录
    history_records.clear()
    
    # 上传并处理图片
    test_image.name = 'test.png'
    data = {
        'images': (test_image, 'test.png')
    }
    
    # 创建模拟OCR结果
    from unittest.mock import patch
    with patch('modules.ocr_processor.OCRProcessor.process_batch') as mock_ocr:
        # 模拟OCR结果
        mock_ocr.return_value = [{
            'image_path': 'test.png',
            'text': '测试OCR文本结果',
            'confidence': 0.9
        }]
        
        # 发送处理图片请求
        response = client.post('/process-images', data=data, content_type='multipart/form-data')
        
        # 检查响应状态
        assert response.status_code == 202
        
        # 从响应中获取任务ID
        response_data = json.loads(response.data)
        task_id = response_data['task_id']
        
        # 模拟任务完成
        with patch('app.AsyncResult') as mock_result:
            # 设置模拟的任务结果
            mock_result.return_value.state = 'SUCCESS'
            mock_result.return_value.result = {
                'status': 'success',
                'results': [{
                    'text': '测试OCR文本结果',
                    'confidence': 0.9,
                    'path': 'test.png'
                }]
            }
            
            # 获取任务状态
            response = client.get(f'/tasks/{task_id}')
            assert response.status_code == 200
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证历史记录中添加了OCR结果
    assert data['count'] > 0
    found_ocr_record = False
    for record in data['history']:
        if record['type'] == 'OCR' and '测试OCR文本结果' in record['content']:
            found_ocr_record = True
            break
    
    assert found_ocr_record, "历史记录中未找到OCR结果"

def test_pdf_extract_adds_to_history(client, test_pdf):
    """测试PDF文本提取后是否添加历史记录"""
    # 清空历史记录
    history_records.clear()
    
    # 上传并提取PDF文本
    data = {
        'pdfs': (test_pdf, 'test.pdf')
    }
    
    # 创建模拟PDF提取结果
    from unittest.mock import patch
    with patch('modules.pdf_extractor.PDFExtractor.process_batch') as mock_extract:
        # 模拟PDF提取结果
        mock_extract.return_value = [{
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
        
        # 发送提取PDF请求
        response = client.post('/extract-pdf', data=data, content_type='multipart/form-data')
        
        # 检查响应状态
        assert response.status_code == 202
        
        # 从响应中获取任务ID
        response_data = json.loads(response.data)
        task_id = response_data['task_id']
        
        # 模拟任务完成
        with patch('app.AsyncResult') as mock_result:
            # 设置模拟的任务结果
            mock_result.return_value.state = 'SUCCESS'
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
            
            # 获取任务状态
            response = client.get(f'/tasks/{task_id}')
            assert response.status_code == 200
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证历史记录中添加了PDF提取结果
    assert data['count'] > 0
    found_pdf_record = False
    for record in data['history']:
        if record['type'] == 'PDF' and '测试PDF提取文本结果' in record['content']:
            found_pdf_record = True
            break
    
    assert found_pdf_record, "历史记录中未找到PDF提取结果"

def test_text_input_adds_to_history(client):
    """测试文本输入是否添加历史记录"""
    # 清空历史记录
    history_records.clear()
    
    # 提交文本内容
    data = {
        'content': '用户输入的测试文本'
    }
    
    # 发送生成文档请求
    response = client.post('/generate', data=data)
    
    # 检查响应状态
    assert response.status_code == 202
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证历史记录中添加了用户输入文本
    assert data['count'] > 0
    found_text_record = False
    for record in data['history']:
        if record['type'] == 'TEXT' and '用户输入的测试文本' in record['content']:
            found_text_record = True
            break
    
    assert found_text_record, "历史记录中未找到用户输入文本" 
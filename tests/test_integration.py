import pytest
import os
import sys
from pathlib import Path
import logging
from PIL import Image
from io import BytesIO
import shutil

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app
from tasks import celery, generate_pdf

@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    app.config['PDF_FOLDER'] = Path("test_pdfs")
    app.config['UPLOAD_FOLDER'] = Path("test_uploads")
    
    # 确保测试目录存在
    for folder in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER']]:
        folder.mkdir(parents=True, exist_ok=True)
    
    with app.test_client() as client:
        yield client
        
    # 改进的清理逻辑
    try:
        # 使用 shutil.rmtree 递归删除目录
        for folder in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER']]:
            if folder.exists():
                shutil.rmtree(folder, ignore_errors=True)
    except Exception as e:
        logging.warning(f"清理测试目录失败: {e}")

@pytest.fixture(autouse=True)
def cleanup_files():
    """每次测试后清理临时文件"""
    yield
    # 清理可能遗留的临时文件
    temp_dirs = [
        Path("test_pdfs"),
        Path("test_uploads"),
        Path("pdfs"),
        Path("uploads"),
        Path("cache")
    ]
    for dir_path in temp_dirs:
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path, ignore_errors=True)
            except Exception as e:
                logging.warning(f"清理{dir_path}失败: {e}")

@pytest.fixture
def test_image():
    """创建测试用图片"""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return img_io

def test_complete_flow(client, test_image):
    """测试完整的文档生成流程"""
    # 1. 提交生成请求
    response = client.post(
        '/generate',
        data={
            'content': '这是测试文档内容\n包含多行文本\n\n这是新段落',
            'images': (test_image, 'test.jpg')
        },
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 202
    data = response.get_json()
    assert 'task_id' in data
    task_id = data['task_id']
    
    # 2. 轮询任务状态
    max_retries = 10
    while max_retries > 0:
        status_response = client.get(f'/tasks/{task_id}')
        assert status_response.status_code == 200
        status_data = status_response.get_json()
        
        if status_data['status'] == 'SUCCESS':
            # 3. 下载生成的PDF
            pdf_name = status_data['result']
            download_response = client.get(f'/download/{pdf_name}')
            assert download_response.status_code == 200
            assert download_response.mimetype == 'application/pdf'
            assert len(download_response.data) > 0
            return
            
        elif status_data['status'] == 'FAILURE':
            pytest.fail(f"任务失败: {status_data.get('error')}")
            
        max_retries -= 1
        import time
        time.sleep(1)
    
    pytest.fail("任务超时")

def test_empty_content(client):
    """测试空内容错误处理"""
    response = client.post(
        '/generate',
        data={'content': ''},
        content_type='multipart/form-data'
    )
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_invalid_image(client):
    """测试无效图片处理"""
    invalid_image = BytesIO(b'not an image')
    response = client.post(
        '/generate',
        data={
            'content': '测试内容',
            'images': (invalid_image, 'bad.jpg')
        },
        content_type='multipart/form-data'
    )
    assert response.status_code == 202  # 应该接受请求但不处理无效图片

def test_images_only(client, test_image):
    """测试仅上传图片（无文字内容）的成功场景""" 
    response = client.post(
        '/generate',
        data={'images': (test_image, 'test.jpg')}, 
        content_type='multipart/form-data'
    )
    assert response.status_code == 202 
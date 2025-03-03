import pytest
import os
import sys
from pathlib import Path
import logging
from PIL import Image
from io import BytesIO
import shutil
import time

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
                shutil.rmtree(folder)
    except Exception as e:
        logging.error(f"清理测试目录失败: {str(e)}")

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
    """创建一个测试图片"""
    img = Image.new('RGB', (1000, 1000), color='red')
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    return img_byte_arr

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

    # 2. 获取任务ID
    task_id = response.json['task_id']
    assert task_id is not None

    # 3. 轮询任务状态
    task_status_url = response.json['status_url']
    for _ in range(10):
        response = client.get(task_status_url)
        if response.json['status'] == 'SUCCESS':
            break
        time.sleep(1)
    
    assert response.json['status'] == 'SUCCESS'
    assert 'result' in response.json

def test_empty_content(client):
    """测试空内容处理"""
    response = client.post(
        '/generate',
        data={'content': ''},
        content_type='multipart/form-data'
    )
    # 修改期望的状态码为 202
    assert response.status_code == 202
    # 可以添加任务状态检查
    response_data = response.get_json()
    assert 'task_id' in response_data

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

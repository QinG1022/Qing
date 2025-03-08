"""
应用集成测试模块
功能: 测试整个应用的端到端流程
版本: 1.0
最后更新: 2024-03-06
描述: 通过HTTP请求测试应用各个端点的功能集成，验证完整业务流程的正确性
"""
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
from modules.tasks import celery, generate_pdf

@pytest.fixture
def client():
    """
    创建Flask测试客户端
    
    功能:
        配置一个用于测试的Flask客户端环境
        
    配置内容:
        - 启用测试模式
        - 设置测试专用的PDF和上传文件目录
        - 确保测试目录存在
        
    清理行为:
        测试结束后自动清理所有测试目录
        
    返回:
        FlaskClient: Flask测试客户端对象
    """
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
    """
    每次测试后自动清理临时文件
    
    功能:
        确保测试完成后清理所有临时文件和目录
        
    作用:
        - 防止测试间的状态污染
        - 减少磁盘空间占用
        - 确保每次测试从干净的环境开始
        
    清理对象:
        所有测试生成的临时目录和文件
    """
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
    """
    创建测试用图片
    
    功能:
        生成一个用于测试的简单红色JPEG图片
        
    返回:
        BytesIO: 内存中的图片数据流，可直接用于模拟文件上传
    """
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return img_io

def test_complete_flow(client, test_image):
    """
    测试完整的文档生成流程
    
    测试步骤:
        1. 提交包含文本和图片的生成请求
        2. 检查异步任务创建是否成功
        3. 轮询任务状态直到完成
        4. 获取并验证生成的PDF文件
        
    验证内容:
        - 请求创建成功 (HTTP 202)
        - 获取任务ID成功
        - 任务最终完成 (SUCCESS状态)
        - 能够下载生成的PDF文件
        - PDF文件有实际内容
    """
    # 1. 提交生成请求
    response = client.post(
        '/generate',
        data={
            'content': '这是测试文档内容\n包含多行文本\n\n这是新段落',
            'images': (test_image, 'test.jpg')
        },
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 202, "请求应返回202 Accepted状态码"
    data = response.get_json()
    assert 'task_id' in data, "响应应包含任务ID"
    task_id = data['task_id']
    
    # 2. 轮询任务状态
    max_retries = 10
    while max_retries > 0:
        status_response = client.get(f'/tasks/{task_id}')
        assert status_response.status_code == 200, "状态查询应返回200状态码"
        status_data = status_response.get_json()
        
        if status_data['status'] == 'SUCCESS':
            # 3. 下载生成的PDF
            pdf_name = status_data['result']
            download_response = client.get(f'/download/{pdf_name}')
            assert download_response.status_code == 200, "PDF下载应返回200状态码"
            assert download_response.mimetype == 'application/pdf', "下载的文件应为PDF类型"
            assert len(download_response.data) > 0, "PDF文件不应为空"
            return
            
        elif status_data['status'] == 'FAILURE':
            pytest.fail(f"任务失败: {status_data.get('error')}")
            
        max_retries -= 1
        import time
        time.sleep(1)
    
    pytest.fail("任务超时，未能在规定时间内完成")

def test_empty_content(client):
    """
    测试空内容错误处理
    
    测试目标:
        验证当提交空内容时应用能正确返回错误
        
    预期结果:
        - 返回400错误状态码
        - 响应中包含错误信息
    """
    response = client.post(
        '/generate',
        data={'content': ''},
        content_type='multipart/form-data'
    )
    assert response.status_code == 400, "空内容应返回400错误"
    data = response.get_json()
    assert 'error' in data, "响应中应包含错误信息"

def test_invalid_image(client):
    """
    测试无效图片处理
    
    测试目标:
        验证当上传无效图片时系统的容错能力
        
    预期结果:
        - 请求应被接受（状态码202）
        - 系统应忽略无效图片而不是完全失败
    """
    invalid_image = BytesIO(b'not an image')
    response = client.post(
        '/generate',
        data={
            'content': '测试内容',
            'images': (invalid_image, 'bad.jpg')
        },
        content_type='multipart/form-data'
    )
    assert response.status_code == 202, "即使图片无效，请求也应被接受"

def test_images_only(client, test_image):
    """
    测试仅上传图片（无文字内容）的成功场景
    
    测试目标:
        验证系统可以处理只有图片没有文本的情况
        
    预期结果:
        - 请求被成功接受（状态码202）
        - 系统应创建只包含图片的PDF
    """ 
    response = client.post(
        '/generate',
        data={'images': (test_image, 'test.jpg')}, 
        content_type='multipart/form-data'
    )
    assert response.status_code == 202, "仅包含图片的请求应被接受" 
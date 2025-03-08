"""
图片处理器测试模块
功能: 测试图片处理器的各项功能
版本: 1.0
最后更新: 2024-03-06
描述: 包含对ImageProcessor类的各个方法的单元测试，验证图片处理的正确性和健壮性
"""
import os
import pytest
from pathlib import Path
from modules.image_processor import ImageProcessor
from io import BytesIO
from PIL import Image
from werkzeug.datastructures import FileStorage
import io

@pytest.fixture
def sample_image():
    """
    创建有效的测试图片
    
    功能:
        生成一个用于测试的有效图片文件对象
        
    返回:
        FileStorage: 模拟上传的图片文件对象，包含100x100像素的红色JPEG图片
    """
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    return FileStorage(
        stream=img_byte_arr,
        filename="test.jpg",
        content_type="image/jpeg"
    )

@pytest.fixture
def temp_dir(tmp_path):
    """
    创建临时目录
    
    功能:
        提供一个临时目录用于保存测试处理后的图片
        
    返回:
        Path: 临时目录路径
    """
    return tmp_path

def test_process_image(tmpdir):
    """
    测试单个图片处理（使用process方法）
    
    测试目标:
        验证ImageProcessor.process方法能正确处理单个图片
        
    验证内容:
        - 处理结果不为None
        - 生成的文件真实存在
        - 生成的文件格式为jpg
    """
    # 创建测试图片 - 大尺寸(1000x1000)测试图片缩放功能
    img = Image.new('RGB', (1000, 1000), color='red')
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    # 创建FileStorage对象模拟文件上传
    file_storage = FileStorage(
        stream=img_byte_arr,
        filename="test.jpg",
        content_type="image/jpeg"
    )

    save_dir = tmpdir.mkdir("images")
    
    # 调用被测试的方法
    processed_image_path = ImageProcessor.process(file_storage, save_dir)
    
    # 验证结果
    assert processed_image_path is not None
    assert Path(processed_image_path).exists()
    assert Path(processed_image_path).suffix == '.jpg'

def test_process_single(sample_image, temp_dir):
    """
    测试单个图片处理
    
    测试目标:
        使用fixture提供的样本图片验证process方法的处理能力
        
    验证内容:
        - 返回值不为None
        - 生成的文件存在
        - 文件扩展名为jpg
    """
    result = ImageProcessor.process(sample_image, temp_dir)
    assert result is not None
    assert Path(result).exists()
    assert Path(result).suffix == '.jpg'

def test_process_batch(sample_image, temp_dir):
    """
    测试批量处理图片
    
    测试目标:
        验证process_batch方法能正确处理图片列表
        
    验证内容:
        - 返回值为列表类型
        - 列表不为空
        - 所有处理结果的文件都存在
    """
    files = [sample_image]
    result = ImageProcessor.process_batch(files, temp_dir)
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(Path(p).exists() for p in result)

def test_empty_batch(temp_dir):
    """
    测试空文件列表
    
    测试目标:
        验证process_batch方法对空输入的处理能力
        
    验证内容:
        - 返回值为空列表
        - 不抛出异常
    """
    result = ImageProcessor.process_batch([], temp_dir)
    assert isinstance(result, list)
    assert len(result) == 0

def test_invalid_image(temp_dir):
    """
    测试无效图片
    
    测试目标:
        验证process方法对无效图片的错误处理能力
        
    验证内容:
        - 无效图片返回None
        - 不抛出未捕获的异常
    """
    invalid_image = FileStorage(
        stream=io.BytesIO(b"not an image"),
        filename="invalid.jpg",
        content_type="image/jpeg"
    )
    result = ImageProcessor.process(invalid_image, temp_dir)
    assert result is None  # 无效图片应该返回None
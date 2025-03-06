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
    """创建有效的测试图片"""
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
    return tmp_path

def test_process_image(tmpdir):
    """测试单个图片处理（使用 process 方法）"""
    # 创建测试图片
    img = Image.new('RGB', (1000, 1000), color='red')
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    # 创建 FileStorage 对象
    file_storage = FileStorage(
        stream=img_byte_arr,
        filename="test.jpg",
        content_type="image/jpeg"
    )

    save_dir = tmpdir.mkdir("images")
    
    # 使用 process 方法而不是 process_image
    processed_image_path = ImageProcessor.process(file_storage, save_dir)
    
    # 验证结果
    assert processed_image_path is not None
    assert Path(processed_image_path).exists()
    assert Path(processed_image_path).suffix == '.jpg'

def test_process_single(sample_image, temp_dir):
    """测试单个图片处理"""
    result = ImageProcessor.process(sample_image, temp_dir)
    assert result is not None
    assert Path(result).exists()
    assert Path(result).suffix == '.jpg'

def test_process_batch(sample_image, temp_dir):
    """测试批量处理图片"""
    files = [sample_image]
    result = ImageProcessor.process_batch(files, temp_dir)
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(Path(p).exists() for p in result)

def test_empty_batch(temp_dir):
    """测试空文件列表"""
    result = ImageProcessor.process_batch([], temp_dir)
    assert isinstance(result, list)
    assert len(result) == 0

def test_invalid_image(temp_dir):
    """测试无效图片"""
    invalid_image = FileStorage(
        stream=io.BytesIO(b"not an image"),
        filename="invalid.jpg",
        content_type="image/jpeg"
    )
    result = ImageProcessor.process(invalid_image, temp_dir)
    assert result is None  # 无效图片应该返回 None
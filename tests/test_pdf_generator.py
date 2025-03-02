import os
import sys
from pathlib import Path
import logging

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from modules.pdf_generator import PDFGenerator
from PIL import Image
from io import BytesIO

# 配置日志
logging.basicConfig(level=logging.INFO)

@pytest.fixture
def temp_test_dir(tmpdir):
    """创建临时测试目录"""
    test_dir = Path(tmpdir)
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir

@pytest.fixture
def sample_image(temp_test_dir):
    """创建测试用图片"""
    img_path = temp_test_dir / "test.jpg"
    img = Image.new('RGB', (100, 100), color='red')
    img.save(str(img_path))
    return img_path

@pytest.fixture
def sample_chinese_text():
    """创建测试用中文文本"""
    return """这是标题
    
第一段落内容。这里包含了一些中文文本。

第二段落包含以下内容：
1. 第一点
2. 第二点
   * 子项目1
   * 子项目2
"""

@pytest.fixture
def multiple_images(temp_test_dir):
    """创建多个测试图片"""
    images = []
    colors = ['red', 'blue', 'green']
    sizes = [(100, 100), (200, 150), (150, 200)]
    
    for i, (color, size) in enumerate(zip(colors, sizes)):
        img_path = temp_test_dir / f"test_{i}.jpg"
        img = Image.new('RGB', size, color=color)
        img.save(str(img_path))
        images.append(img_path)
    
    return images

def test_basic_pdf_generation(temp_test_dir, sample_image, sample_chinese_text):
    """测试基本的PDF生成功能"""
    # 准备测试数据
    text_content = "这是一个测试文档。\n包含多行文本。\n\n这是第二个段落。"
    image_paths = [sample_image]
    output_dir = temp_test_dir / "output"
    output_dir.mkdir(exist_ok=True)

    try:
        # 生成PDF
        filename = PDFGenerator.generate(text_content, image_paths, output_dir)
        pdf_path = output_dir / filename
        
        # 详细的验证
        assert pdf_path.exists(), f"PDF文件未生成: {pdf_path}"
        assert pdf_path.stat().st_size > 0, "PDF文件是空的"
        assert filename.endswith('.pdf'), "文件扩展名不正确"
        
        logging.info(f"生成的PDF文件: {pdf_path}")
        logging.info(f"文件大小: {pdf_path.stat().st_size} 字节")
        
    except Exception as e:
        logging.error(f"测试失败: {str(e)}", exc_info=True)
        pytest.fail(f"PDF生成失败: {str(e)}")

def test_pdf_with_multiple_images(temp_test_dir, multiple_images, sample_chinese_text):
    """测试多图片PDF生成"""
    output_dir = temp_test_dir / "output"
    output_dir.mkdir(exist_ok=True)

    try:
        filename = PDFGenerator.generate(
            text_content=sample_chinese_text,
            image_paths=multiple_images,
            output_dir=output_dir
        )
        
        pdf_path = output_dir / filename
        assert pdf_path.exists(), "PDF文件未生成"
        assert pdf_path.stat().st_size > 0, "PDF文件为空"
        
        logging.info(f"生成的多图片PDF: {pdf_path}")
        logging.info(f"文件大小: {pdf_path.stat().st_size} 字节")
        
    except Exception as e:
        logging.error(f"多图片测试失败: {str(e)}", exc_info=True)
        pytest.fail(f"多图片PDF生成失败: {str(e)}")

def test_pdf_generation_no_images(temp_test_dir, sample_chinese_text):
    """测试仅文本的PDF生成"""
    output_dir = temp_test_dir / "output"
    output_dir.mkdir(exist_ok=True)

    try:
        filename = PDFGenerator.generate(
            text_content=sample_chinese_text,
            image_paths=[],
            output_dir=output_dir
        )
        
        pdf_path = output_dir / filename
        assert pdf_path.exists(), "PDF文件未生成"
        assert pdf_path.stat().st_size > 0, "PDF文件为空"
        
        logging.info(f"生成的纯文本PDF: {pdf_path}")
        
    except Exception as e:
        logging.error(f"纯文本测试失败: {str(e)}", exc_info=True)
        pytest.fail(f"纯文本PDF生成失败: {str(e)}")

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-W', 'ignore::DeprecationWarning'])

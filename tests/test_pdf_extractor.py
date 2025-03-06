import os
import sys
from pathlib import Path
import logging
import tempfile

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from modules.pdf_extractor import PDFExtractor
import fitz  # PyMuPDF

# 配置日志
logging.basicConfig(level=logging.INFO)

@pytest.fixture
def temp_pdf_file():
    """创建一个临时的PDF文件用于测试"""
    # 创建临时文件
    fd, temp_path = tempfile.mkstemp(suffix='.pdf')
    os.close(fd)
    
    # 创建一个简单的PDF文件
    doc = fitz.open()
    page = doc.new_page()
    
    # 添加英文文本 (避免中文字体问题)
    page.insert_text(fitz.Point(100, 100), "Test PDF Document", fontsize=12)
    page.insert_text(fitz.Point(100, 150), "For testing PDFExtractor class", fontsize=10)
    
    # 保存PDF
    doc.save(temp_path)
    doc.close()
    
    yield Path(temp_path)
    
    # 测试结束后清理临时文件
    try:
        os.unlink(temp_path)
    except:
        pass

@pytest.fixture
def nonexistent_pdf_path():
    """返回不存在的PDF文件路径"""
    return Path(project_root) / "test_pdfs" / "nonexistent.pdf"

@pytest.fixture
def multiple_pdf_paths(temp_pdf_file):
    """返回多个PDF文件路径的列表"""
    # 使用临时创建的PDF文件和一个不存在的文件
    nonexistent = Path(project_root) / "test_pdfs" / "nonexistent.pdf"
    return [temp_pdf_file, nonexistent]

def test_extract_text_valid_pdf(temp_pdf_file):
    """测试从有效PDF文件中提取文本"""
    result = PDFExtractor.extract_text(temp_pdf_file)
    
    # 验证结果结构和内容
    assert 'filename' in result
    assert 'total_pages' in result
    assert 'text' in result
    assert 'pages' in result
    
    # 验证文件名正确
    assert result['filename'] == temp_pdf_file.name
    
    # 验证页数大于0
    assert result['total_pages'] > 0
    
    # 验证提取的文本不为空
    assert result['text']
    
    # 验证页面列表长度等于总页数
    assert len(result['pages']) == result['total_pages']
    
    # 验证每个页面都有页码和文本
    for page in result['pages']:
        assert 'page_num' in page
        assert 'text' in page
        
    # 验证预期的文本内容在提取结果中 (注意：不检查具体文本，只要有内容即可)
    assert len(result['text']) > 0

def test_extract_text_nonexistent_pdf(nonexistent_pdf_path):
    """测试从不存在的PDF文件中提取文本，应返回错误信息"""
    result = PDFExtractor.extract_text(nonexistent_pdf_path)
    
    # 验证结果包含错误信息
    assert 'error' in result
    assert 'FileNotFoundError' in result['error'] or '不存在' in result['error']
    
    # 验证其他字段为默认值
    assert result['filename'] == nonexistent_pdf_path.name
    assert result['total_pages'] == 0
    assert result['text'] == ""
    assert result['pages'] == []

def test_process_batch(multiple_pdf_paths):
    """测试批量处理PDF文件"""
    results = PDFExtractor.process_batch(multiple_pdf_paths)
    
    # 验证结果是一个列表
    assert isinstance(results, list)
    
    # 验证结果数量与输入文件数量相同
    assert len(results) == len(multiple_pdf_paths)
    
    # 验证第一个结果(应该是有效的)
    valid_result = results[0]
    assert 'filename' in valid_result
    assert 'total_pages' in valid_result
    assert valid_result['total_pages'] > 0
    assert len(valid_result['text']) > 0  # 只检查有内容，不检查具体文本
    
    # 验证第二个结果(应该包含错误)
    error_result = results[1]
    assert 'error' in error_result
    assert 'FileNotFoundError' in error_result['error'] or '不存在' in error_result['error']

def test_process_batch_empty_list():
    """测试处理空列表"""
    results = PDFExtractor.process_batch([])
    
    # 验证结果是一个空列表
    assert isinstance(results, list)
    assert len(results) == 0 
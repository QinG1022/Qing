"""
PDF提取器测试模块
功能: 测试PDF文本提取功能的正确性
版本: 1.0
最后更新: 2024-03-06
描述: 验证PDFExtractor类的各项功能，包括单文件处理、批量处理和错误处理
"""
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
    """
    创建一个临时的PDF文件用于测试
    
    功能:
        生成一个包含简单文本内容的测试PDF文件
        
    处理流程:
        1. 创建临时文件
        2. 使用PyMuPDF生成简单PDF内容
        3. 写入文本内容
        4. 测试完成后自动清理
        
    返回:
        Path: 临时PDF文件的路径
    """
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
    """
    返回不存在的PDF文件路径
    
    功能:
        提供一个确保不存在的PDF文件路径，用于测试错误处理
        
    返回:
        Path: 不存在的PDF文件路径
    """
    return Path(project_root) / "test_pdfs" / "nonexistent.pdf"

@pytest.fixture
def multiple_pdf_paths(temp_pdf_file):
    """
    返回多个PDF文件路径的列表
    
    功能:
        提供一个混合有效和无效PDF路径的列表，用于测试批量处理
        
    参数:
        temp_pdf_file: pytest fixture，一个有效的临时PDF文件
        
    返回:
        list: 包含一个有效路径和一个无效路径的列表
    """
    # 使用临时创建的PDF文件和一个不存在的文件
    nonexistent = Path(project_root) / "test_pdfs" / "nonexistent.pdf"
    return [temp_pdf_file, nonexistent]

def test_extract_text_valid_pdf(temp_pdf_file):
    """
    测试从有效PDF文件中提取文本
    
    测试目标:
        验证PDFExtractor能正确提取有效PDF的文本内容
        
    验证内容:
        - 返回结果结构符合预期
        - 文件名正确
        - 页数大于0
        - 文本内容不为空
        - 页面数量与报告的总页数一致
        - 每个页面包含必要的字段
    """
    result = PDFExtractor.extract_text(temp_pdf_file)
    
    # 验证结果结构和内容
    assert 'filename' in result, "结果应包含filename字段"
    assert 'total_pages' in result, "结果应包含total_pages字段"
    assert 'text' in result, "结果应包含text字段"
    assert 'pages' in result, "结果应包含pages字段"
    
    # 验证文件名正确
    assert result['filename'] == temp_pdf_file.name, "文件名应与源文件一致"
    
    # 验证页数大于0
    assert result['total_pages'] > 0, "PDF应至少包含一页"
    
    # 验证提取的文本不为空
    assert result['text'], "提取的文本不应为空"
    
    # 验证页面列表长度等于总页数
    assert len(result['pages']) == result['total_pages'], "页面列表长度应等于总页数"
    
    # 验证每个页面都有页码和文本
    for page in result['pages']:
        assert 'page_num' in page, "每个页面记录应包含页码"
        assert 'text' in page, "每个页面记录应包含文本"
        
    # 验证预期的文本内容在提取结果中 (注意：不检查具体文本，只要有内容即可)
    assert len(result['text']) > 0, "提取的文本应有内容"

def test_extract_text_nonexistent_pdf(nonexistent_pdf_path):
    """
    测试从不存在的PDF文件中提取文本
    
    测试目标:
        验证PDFExtractor对不存在文件的错误处理能力
        
    验证内容:
        - 返回结果包含错误信息
        - 错误类型正确
        - 其他字段设置为默认值
    """
    result = PDFExtractor.extract_text(nonexistent_pdf_path)
    
    # 验证结果包含错误信息
    assert 'error' in result, "对不存在文件应返回错误信息"
    assert 'FileNotFoundError' in result['error'] or '不存在' in result['error'], "错误类型应为FileNotFoundError"
    
    # 验证其他字段为默认值
    assert result['filename'] == nonexistent_pdf_path.name, "文件名应与输入路径一致"
    assert result['total_pages'] == 0, "页数应为0"
    assert result['text'] == "", "文本应为空字符串"
    assert result['pages'] == [], "页面列表应为空"

def test_process_batch(multiple_pdf_paths):
    """
    测试批量处理PDF文件
    
    测试目标:
        验证PDFExtractor能正确处理包含有效和无效PDF的混合列表
        
    验证内容:
        - 返回结果为列表类型
        - 结果数量与输入路径数量一致
        - 有效PDF文件被正确处理
        - 无效PDF文件返回适当的错误信息
    """
    results = PDFExtractor.process_batch(multiple_pdf_paths)
    
    # 验证结果是一个列表
    assert isinstance(results, list), "批量处理应返回列表"
    
    # 验证结果数量与输入文件数量相同
    assert len(results) == len(multiple_pdf_paths), "结果数量应与输入文件数量一致"
    
    # 验证第一个结果(应该是有效的)
    valid_result = results[0]
    assert 'filename' in valid_result, "有效PDF结果应包含filename字段"
    assert 'total_pages' in valid_result, "有效PDF结果应包含total_pages字段"
    assert valid_result['total_pages'] > 0, "有效PDF的页数应大于0"
    assert len(valid_result['text']) > 0, "有效PDF的文本应不为空"
    
    # 验证第二个结果(应该包含错误)
    error_result = results[1]
    assert 'error' in error_result, "无效PDF结果应包含错误信息"
    assert 'FileNotFoundError' in error_result['error'] or '不存在' in error_result['error'], "错误类型应为FileNotFoundError"

def test_process_batch_empty_list():
    """
    测试处理空列表
    
    测试目标:
        验证PDFExtractor对空输入的处理能力
        
    验证内容:
        - 返回结果为空列表
        - 不抛出异常
    """
    results = PDFExtractor.process_batch([])
    
    # 验证结果是一个空列表
    assert isinstance(results, list), "处理空列表应返回列表类型"
    assert len(results) == 0, "处理空列表应返回空列表" 
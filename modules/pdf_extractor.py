"""
PDF文本提取器模块
功能: 从PDF文件中提取文本内容
版本: 1.0
最后更新: 2024-03-06
描述: 该模块基于PyMuPDF(fitz)实现PDF文本提取功能，支持单文件和批量处理
"""
import os
import logging
from pathlib import Path
import fitz  # PyMuPDF库

logger = logging.getLogger(__name__)

class PDFExtractor:
    """
    PDF文本提取器
    
    负责从PDF文件中提取文本内容，包括:
    1. 单个PDF文件的文本提取
    2. 多个PDF文件的批量处理
    3. 分页文本提取和整合
    4. 错误处理和结果格式化
    """
    
    @classmethod
    def extract_text(cls, pdf_path):
        """
        从PDF文件中提取文本
        
        功能:
            1. 打开并验证PDF文件
            2. 按页提取文本内容
            3. 整合分页内容和统计信息
            
        参数:
            pdf_path (str/Path): PDF文件的路径
            
        返回:
            dict: 包含提取结果的字典，格式为:
                {
                    'filename': 文件名,
                    'total_pages': 总页数,
                    'text': 提取的完整文本内容,
                    'pages': 每页的文本内容列表，每项包含页码和文本
                }
                
        异常处理:
            - 文件不存在时抛出FileNotFoundError
            - 其他异常会被捕获并记录，返回包含错误信息的结果字典
        """
        try:
            # 确保文件存在
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
                
            # 打开PDF文件并获取基本信息
            with fitz.open(pdf_path) as doc:
                total_pages = len(doc)
                all_text = ""
                pages_content = []
                
                # 逐页提取文本内容
                for page_num, page in enumerate(doc):
                    text = page.get_text()
                    all_text += text
                    pages_content.append({
                        'page_num': page_num + 1,  # 页码从1开始
                        'text': text.strip()
                    })
                
                logger.info(f"成功从PDF提取 {total_pages} 页文本，共 {len(all_text)} 个字符")
                
                # 返回包含完整提取结果的字典
                return {
                    'filename': pdf_path.name,
                    'total_pages': total_pages,
                    'text': all_text,
                    'pages': pages_content
                }
        
        except Exception as e:
            logger.error(f"PDF文本提取失败: {str(e)}")
            # 返回错误信息，确保调用方能了解失败原因
            return {
                'filename': Path(pdf_path).name if pdf_path else "未知文件",
                'error': str(e),
                'text': "",
                'total_pages': 0,
                'pages': []
            }
    
    @classmethod
    def process_batch(cls, pdf_paths):
        """
        批量处理多个PDF文件进行文本提取
        
        功能:
            对多个PDF文件进行依次处理，提取文本内容
            
        参数:
            pdf_paths (list): PDF文件路径列表
            
        返回:
            list: 文本提取结果列表，每项包含一个PDF的提取结果
            
        说明:
            - 任何单个文件处理失败不会影响整体处理流程
            - 对于处理失败的文件，会添加包含相应错误信息的结果
            - 空列表输入将返回空列表结果
        """
        results = []
        for path in pdf_paths:
            try:
                # 调用单文件处理方法
                result = cls.extract_text(path)
                results.append(result)
                logging.info(f"处理PDF文件 {path} 完成")
            except Exception as e:
                logging.error(f"处理PDF文件失败 {path}: {str(e)}")
                # 添加错误信息到结果列表
                results.append({
                    'filename': Path(path).name if path else "未知文件",
                    'error': str(e),
                    'text': "",
                    'total_pages': 0,
                    'pages': []
                })
        return results 
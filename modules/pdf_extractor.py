"""
PDF文本提取器
功能: 从PDF文件中提取文本内容
版本: 1.0
"""
import os
import logging
from pathlib import Path
import fitz  # PyMuPDF库

logger = logging.getLogger(__name__)

class PDFExtractor:
    """PDF文本提取器，从PDF文件中提取文本内容"""
    
    @classmethod
    def extract_text(cls, pdf_path):
        """从PDF文件中提取文本
        
        Args:
            pdf_path: PDF文件的路径
            
        Returns:
            dict: 包含提取结果的字典，格式为:
                {
                    'filename': 文件名,
                    'total_pages': 总页数,
                    'text': 提取的文本内容,
                    'pages': [每页的文本内容列表]
                }
        """
        try:
            # 确保文件存在
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
                
            # 打开PDF文件
            with fitz.open(pdf_path) as doc:
                total_pages = len(doc)
                all_text = ""
                pages_content = []
                
                # 提取每一页的文本
                for page_num, page in enumerate(doc):
                    text = page.get_text()
                    all_text += text
                    pages_content.append({
                        'page_num': page_num + 1,
                        'text': text.strip()
                    })
                
                logger.info(f"成功从PDF提取 {total_pages} 页文本，共 {len(all_text)} 个字符")
                
                return {
                    'filename': pdf_path.name,
                    'total_pages': total_pages,
                    'text': all_text,
                    'pages': pages_content
                }
        
        except Exception as e:
            logger.error(f"PDF文本提取失败: {str(e)}")
            return {
                'filename': Path(pdf_path).name if pdf_path else "未知文件",
                'error': str(e),
                'text': "",
                'total_pages': 0,
                'pages': []
            }
    
    @classmethod
    def process_batch(cls, pdf_paths):
        """批量处理多个PDF文件
        
        Args:
            pdf_paths: PDF文件路径列表
            
        Returns:
            list: 提取结果列表
        """
        results = []
        for path in pdf_paths:
            try:
                result = cls.extract_text(path)
                results.append(result)
                logging.info(f"处理PDF文件 {path} 完成")
            except Exception as e:
                logging.error(f"处理PDF文件失败 {path}: {str(e)}")
                results.append({
                    'filename': Path(path).name if path else "未知文件",
                    'error': str(e),
                    'text': "",
                    'total_pages': 0,
                    'pages': []
                })
        return results 
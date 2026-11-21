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
            pdf_path = Path(pdf_path)                                 # 路径    
            if not pdf_path.exists():                                 # 如果文件不存在    
                raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")   # 抛出文件不存在异常    
                
            # 打开PDF文件并获取基本信息
            with fitz.open(pdf_path) as doc:    # 打开PDF文件    
                total_pages = len(doc)          # 总页数    
                all_text = ""                   # 文本内容    
                pages_content = []              # 页码和文本内容列表    
                
                # 逐页提取文本内容
                for page_num, page in enumerate(doc):   # 逐页提取文本内容    
                    text = page.get_text()              # 获取文本内容    
                    all_text += text                    # 添加到文本内容    
                    pages_content.append({
                        'page_num': page_num + 1,       # 页码从1开始
                        'text': text.strip()            # 去除空白字符    
                    })
                
                logger.info(f"成功从PDF提取 {total_pages} 页文本，共 {len(all_text)} 个字符") # 打印提取结果    
                
                # 返回包含完整提取结果的字典
                return {
                    'filename': pdf_path.name,      # 文件名    
                    'total_pages': total_pages,     # 总页数    
                    'text': all_text,               # 文本内容    
                    'pages': pages_content          # 页码和文本内容列表    
                }
        
        except Exception as e:                             # 处理异常    
            logger.error(f"PDF文本提取失败: {str(e)}")      # 打印提取失败信息    

            # 返回错误信息，确保调用方能了解失败原因
            return {
                'filename': Path(pdf_path).name if pdf_path else "未知文件", # 文件名    
                'error': str(e),            # 错误信息    
                'text': "",                 # 文本内容    
                'total_pages': 0,           # 总页数    
                'pages': []                 # 页码和文本内容列表    
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
        results = []                # 结果列表    
        for path in pdf_paths:      # 逐个处理PDF文件    
            try:                    # 处理异常    
                # 调用单文件处理方法
                result = cls.extract_text(path)         # 提取文本    
                results.append(result)                  # 添加到结果列表    
                logging.info(f"处理PDF文件 {path} 完成") # 打印处理完成信息    
            except Exception as e:                      # 处理异常    
                logging.error(f"处理PDF文件失败 {path}: {str(e)}") # 打印处理失败信息    
                
                # 添加错误信息到结果列表    
                results.append({
                    'filename': Path(path).name if path else "未知文件",    # 文件名    
                    'error': str(e),                                       # 错误信息    
                    'text': "",                                            # 文本内容    
                    'total_pages': 0,                                      # 总页数    
                    'pages': []                                            # 页码和文本内容列表    
                })
        return results                                                     # 返回结果列表       
"""
Celery异步任务模块
功能: 处理耗时操作，如PDF生成和OCR识别
版本: 1.6
最后更新: 2024-03-06
描述: 该模块提供了异步执行耗时任务的功能，包括PDF生成、OCR文字识别和PDF文本提取
"""
import os
import sys
from pathlib import Path
from celery import Celery
import logging

# 配置日志系统
#logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Celery应用实例并设置名称
celery = Celery('bishe')
celery.config_from_object('config.celeryconfig')   # 从celeryconfig.py导入配置

# 确保可以导入自定义模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目内部模块
from modules.pdf_generator import PDFGenerator
from modules.ocr_processor import OCRProcessor
from modules.pdf_extractor import PDFExtractor

@celery.task(bind=True)   
def generate_pdf(self, text_content, image_paths, output_dir):
    """
    异步PDF生成任务
    
    功能：将文本内容和图片合并生成PDF文档
    
    参数:
        self: Celery任务实例
        text_content (str): 要添加到PDF的文本内容
        image_paths (list): 图片文件路径列表
        output_dir (str): PDF输出目录
        
    返回:
        str: 生成的PDF文件名
        
    异常:
        ValueError: 当文本和图片都为空时
        Exception: 其他处理过程中的异常
    """
    try:
        logger.info(f"开始生成PDF - 文本长度: {len(text_content) if text_content else 0}, 图片数量: {len(image_paths)}")
        logger.info(f"图片路径: {image_paths}")
        logger.info(f"输出目录: {output_dir}")

        # 检查输入参数，如果文本和图片都为空，则抛出异常  
        if not text_content and not image_paths:
            raise ValueError("请提供文本内容或图片，不能都为空")

        # 确保所有图片路径都存在
        valid_images = []
        if image_paths:                     # 如果图片路径存在，遍历图片路径 
            for img_path in image_paths:
                img_path = Path(img_path)   # 将图片路径转换为Path对象  
                if img_path.exists():       # 如果图片路径存在，将图片路径添加到有效图片列表中 
                    valid_images.append(str(img_path))
                    logger.info(f"有效图片: {img_path}")
                else:
                    logger.warning(f"图片不存在: {img_path}")

            if not valid_images and not text_content:     # 如果图片路径不存在且文本内容为空，则抛出异常 
                raise ValueError("没有有效的图片文件且无文本内容")  

        # 调用PDF生成器生成文档
        try:
            filename = PDFGenerator.generate(
                text_content=text_content if text_content else "",  # 如果文本内容为空，则设置为空字符串  
                image_paths=valid_images,   # 如果图片路径存在，则使用有效图片路径  
                output_dir=output_dir       # 如果输出目录存在，则使用输出目录  
            )
            logger.info(f"PDF生成成功: {filename}") 
            return filename 
        except Exception as e:
            logger.error(f"PDF生成失败: {e}", exc_info=True)
            raise                                               # 抛出异常  
        
    except Exception as e:
        logger.error(f"任务执行失败: {str(e)}", exc_info=True)
        raise

@celery.task(bind=True)
def process_images_task(self, image_paths): 
    """
    处理图片OCR任务
    
    功能：对图片进行光学字符识别（OCR），提取图片中的文字
    
    参数:
        self: Celery任务实例
        image_paths (list): 要处理的图片路径列表
        
    返回:
        dict: 包含以下键的字典:
            - status (str): 处理状态，可能值: "success", "warning", "error"
            - message (str): 状态描述信息
            - results (list): OCR结果列表，每项包含:
                - text (str): 识别的文本
                - path (str): 图片路径
                - confidence (float): 识别置信度
    """
    try:
        # 更新任务状态为处理中
        self.update_state(state='PROCESSING', meta={
            'message': '正在进行OCR识别...'
        })
        
        # 验证图片路径是否存在
        valid_paths = []
        for path in image_paths:
            if os.path.exists(path):
                valid_paths.append(path)
                logger.info(f"准备处理图片: {path}")
            else:
                logger.warning(f"图片不存在: {path}")
                
        # 如果有效图片路径列表为空 
        if not valid_paths:                              
            logger.warning("没有有效的图片路径")
            return {
                'status': 'warning',
                'message': '没有有效的图片',
                'results': []
            }

        # 调用OCR处理器进行批量处理
        results = OCRProcessor.process_batch(valid_paths)
        logger.info(f"OCR处理结果数量: {len(results) if results else 0}")  
        
        # 即使结果为空也不抛出异常，而是返回警告状态
        if not results:
            logger.warning("OCR处理未返回结果")
            return {
                'status': 'warning',
                'message': 'OCR未能识别出内容',
                'results': []
            }

        # 处理和格式化识别结果
        processed_results = []  
        for result in results:      # 遍历OCR处理结果    
            if result:              # 确保result不为None  
                processed_results.append({ 
                    'text': result.get('text', '').strip() or "未能识别出文字",  # 如果识别结果为空，则设置为未能识别出文字  
                    'path': result.get('image_path', ''),
                    'confidence': result.get('confidence')
                })
                logger.info(f"处理结果: 路径={result.get('image_path')}, 文本长度={len(result.get('text', ''))}")

        logger.info(f"成功处理 {len(processed_results)} 张图片的OCR")
        return {
            'status': 'success',            # 返回成功状态  
            'results': processed_results    # 返回处理结果  
        }
         # 返回处理结果     
    except Exception as e:
        logger.error(f"OCR处理失败: {str(e)}", exc_info=True)
        # 返回错误信息而不是抛出异常，避免任务失败
        return {
            'status': 'error',
            'message': f'OCR处理异常: {str(e)}',
            'results': []
        }

@celery.task(bind=True, name='extract_pdf_text')  
def extract_pdf_text(self, pdf_paths): 
    """
    处理PDF文本提取任务
    
    功能：从PDF文件中提取文本内容，支持多文件批量处理
    
    参数:
        self: Celery任务实例
        pdf_paths (list): 要处理的PDF文件路径列表
        
    返回:
        dict: 包含以下键的字典:
            - status (str): 处理状态，可能值: "success", "warning", "error"
            - message (str): 状态描述信息
            - results (list): PDF处理结果列表，每项包含:
                - filename (str): PDF文件名
                - total_pages (int): 总页数
                - text_length (int): 提取文本的总字符数
                - text (str): 提取的全文本
                - pages (list): 各页内容，每项包含页码和文本
            - stats (dict): 统计信息，包括总文件数、总页数和总字符数
    """
    try:
        # 更新任务状态为处理中
        self.update_state(state='PROCESSING', meta={
            'message': '正在提取PDF文本...'
        })
        
        # 验证PDF文件路径是否存在
        valid_paths = []
        for path in pdf_paths:
            if os.path.exists(path):
                valid_paths.append(path)
                logger.info(f"准备处理PDF文件: {path}")
            else:
                logger.warning(f"PDF文件不存在: {path}")
        
        if not valid_paths:
            logger.warning("没有有效的PDF文件路径") 
            return {
                'status': 'warning',
                'message': '没有有效的PDF文件',
                'results': []
            }

        # 调用PDF提取器进行批量处理
        results = PDFExtractor.process_batch(valid_paths) 
        logger.info(f"PDF处理结果数量: {len(results) if results else 0}") 
        
        # 处理和汇总提取结果
        processed_results = []  
        total_pages = 0         # 总页数  
        total_chars = 0         # 总字符数  
        
        for result in results:  # 遍历PDF处理结果  
            if result:          # 确保result不为None  
                text_length = len(result.get('text', ''))   # 提取文本长度  
                pages = result.get('total_pages', 0)
                total_pages += pages 
                total_chars += text_length  
                # 处理和汇总提取结果    
                processed_results.append({
                    'filename': result.get('filename', '未知文件'), 
                    'total_pages': pages, 
                    'text_length': text_length, 
                    'text': result.get('text', ''),     # 提取文本  
                    'pages': result.get('pages', [])    # 各页内容  
                })
                
                logger.info(f"处理结果: 文件={result.get('filename')}, 页数={pages}, 文本长度={text_length}")

        logger.info(f"成功处理 {len(processed_results)} 个PDF文件，共 {total_pages} 页，{total_chars} 个字符") 
        return {
            'status': 'success',    # 返回成功状态  
            'message': f"成功提取 {len(processed_results)} 个PDF文件的文本",
            'results': processed_results,
            'stats': {                      # 返回统计信息  
                'total_files': len(processed_results),  # 总文件数  
                'total_pages': total_pages, # 总页数  
                'total_chars': total_chars  # 总字符数  
            }
        }
        # 返回处理结果      
    except Exception as e:
        logger.error(f"PDF处理失败: {str(e)}", exc_info=True)   
        # 返回错误信息而不是抛出异常，避免任务失败
        return {
            'status': 'error',
            'message': f'PDF处理异常: {str(e)}', 
            'results': [] 
        }

from celery import shared_task

class AIProcessor:
    """AI处理器，处理聊天功能"""
    
    @staticmethod
    def generate_chat_response(prompt: str):
        """生成聊天回复"""
        from .ai_chat.ai_routes import ai_clients, default_model
        client = ai_clients.get(default_model)
        if not client:
            raise ValueError(f"默认AI模型 {default_model} 不可用")
        
        # 添加用户消息
        client.add_message("user", prompt)
        
        # 生成响应
        response = client.generate_response(stream=False)
        
        # 处理响应
        return response

@shared_task(bind=True)
def process_chat_task(self, prompt: str):
    try:
        response = AIProcessor.generate_chat_response(prompt)
        
        # 错误处理
        if isinstance(response, dict) and "error" in response:
            return {"status": "error", "message": response["error"]}
            
        from .ai_chat.ai_routes import ai_clients, default_model
        client = ai_clients.get(default_model)
        
        # 格式化响应
        result = client.format_response(response)
        client.add_message("assistant", result)
        
        return {
            "status": "success",
            "type": "chat",
            "content": result
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
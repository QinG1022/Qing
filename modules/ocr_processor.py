"""
OCR文字识别处理器模块
功能: 对图像进行光学字符识别(OCR)，提取图像中的文字
版本: 1.2
最后更新: 2024-03-06
描述: 该模块基于Tesseract OCR引擎实现图像文字识别功能，支持中文识别和批量处理
"""
import os
import sys
from PIL import Image
import logging
from pathlib import Path

try:
    import pytesseract
except ImportError:
    logging.error("pytesseract 未安装，请执行: pip install pytesseract")
    raise

class OCRProcessor:
    """
    OCR文字识别处理器
    
    提供图像文字识别功能，包括:
    1. Tesseract OCR引擎检查和配置
    2. 单个图像的文字识别
    3. 批量图像的文字识别
    4. 错误处理和结果格式化
    """
    
    @classmethod
    def check_tesseract(cls):
        """
        检查Tesseract OCR引擎安装和配置状态
        
        功能:
            1. 检查环境变量设置
            2. 检查Tesseract可执行文件路径
            3. 验证中文语言包安装状态
            
        返回:
            bool: 检查通过返回True
            
        异常:
            RuntimeError: Tesseract未正确安装或配置时抛出
            EnvironmentError: 环境变量未设置时抛出
        """
        try:
            # 检查环境变量
            if not os.environ.get('TESSDATA_PREFIX'):
                # 尝试设置默认路径
                default_path = r"C:\Program Files\Tesseract-OCR\tessdata"    
                if os.path.exists(default_path):                 # 如果路径存在    
                    os.environ['TESSDATA_PREFIX'] = default_path # 设置环境变量    
                else:                                           # 如果路径不存在    
                    raise EnvironmentError("TESSDATA_PREFIX 环境变量未设置") # 抛出环境变量未设置异常    

            # 检查Tesseract可执行文件
            if sys.platform.startswith('win'):          # 如果是Windows系统    
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # 设置Tesseract可执行文件路径    

            # 测试OCR功能和中文语言包
            test_text = pytesseract.get_languages()     # 获取语言列表    
            if 'chi_sim' not in test_text:              # 如果中文语言包不存在    
                raise RuntimeError("中文语言包未安装")    # 抛出中文语言包未安装异常    

            return True

        except Exception as e:                          # 处理异常    
            logging.error(f"Tesseract检查失败: {str(e)}") # 打印检查失败信息    
            raise RuntimeError(f"OCR系统未就绪: {str(e)}") # 抛出OCR系统未就绪异常    

    @classmethod
    def process_image(cls, image_path):
        """
        处理单个图片进行OCR识别
        
        功能:
            1. 打开并预处理图片
            2. 使用Tesseract进行OCR识别
            3. 处理识别结果
            
        参数:
            image_path (str/Path): 图片文件路径
            
        返回:
            dict: 包含识别结果的字典，格式为:
                {
                    'image_path': 图片路径,
                    'text': 识别的文本内容,
                    'confidence': 识别置信度
                }
                
        说明:
            - 即使识别失败也会返回结果字典，包含相应的错误信息
            - 首次调用时会自动检查Tesseract配置
        """
        # 首次使用时检查Tesseract
        if not hasattr(cls, '_tesseract_checked'):  # 如果Tesseract未检查    
            cls.check_tesseract()                   # 检查Tesseract       
            cls._tesseract_checked = True           # 设置检查标志    

        try:
            # 确保图片文件存在
            image_path = Path(image_path)                            # 图片路径    
            if not image_path.exists():                              # 如果图片不存在    
                raise FileNotFoundError(f"图片不存在: {image_path}") # 抛出图片不存在异常    

            # 打开并预处理图片
            with Image.open(image_path) as img:

                # 转换为RGB模式以确保兼容性
                if img.mode != 'RGB':                # 如果图片模式不是RGB    
                    img = img.convert('RGB')         # 转换为RGB模式    
                
                # 进行OCR识别，指定中文简体语言
                text = pytesseract.image_to_string(img, lang='chi_sim')
                
                # 处理识别结果，去除首尾空白
                text = text.strip()
                
                # 返回格式化结果，即使文本为空也返回结果
                return {
                    'image_path': str(image_path),                  # 图片路径    
                    'text': text if text else "图片未能识别出文字",  # 提供默认值    
                    'confidence': None                              # TODO: 添加置信度计算
                }

        except Exception as e:                                      # 处理异常    
            logging.error(f"OCR处理失败: {str(e)}")                 # 打印处理失败信息
            
            # 返回错误信息而不是None，确保调用方能获取详细错误信息
            return {
                'image_path': str(image_path) if image_path else "未知路径", # 图片路径    
                'text': f"图片处理错误: {str(e)}",                           # 错误信息    
                'confidence': 0                                             # 置信度    
            }

    @classmethod
    def process_batch(cls, image_paths):
        """
        批量处理图片进行OCR识别
        
        功能:
            对多张图片进行依次识别，汇总结果
            
        参数:
            image_paths (list): 图片路径列表
            
        返回:
            list: OCR识别结果列表，每项为一个结果字典
            
        说明:
            - 任何单张图片处理失败不会影响整体处理流程
            - 所有图片的处理结果都会被添加到结果列表中
            - 对于处理失败的图片，会添加相应的错误信息
        """
        results = []                                                # 结果列表    
        for path in image_paths:                                    # 逐个处理图片    
            try:                                                    # 处理异常    
                result = cls.process_image(path)                    # 处理图片  

                # 所有结果都添加到结果列表，包括可能的错误信息
                results.append(result)                              # 添加到结果列表    
                logging.info(f"处理图片 {path} 完成")                # 打印处理完成信息    
            except Exception as e:                                  # 处理异常    
                logging.error(f"处理图片失败 {path}: {str(e)}")      # 打印处理失败信息    

                # 添加错误信息到结果列表，确保调用方能处理异常情况
                results.append({
                    'image_path': str(path),                        # 图片路径    
                    'text': f"处理失败: {str(e)}",                  # 错误信息    
                    'confidence': 0                                # 置信度    
                })
        return results

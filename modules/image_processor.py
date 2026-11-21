"""
图片处理器模块
版本: 1.4
最后更新: 2024-03-20
功能: 提供图片处理、格式转换、尺寸调整和保存功能
描述: 该模块负责处理上传的图片，支持多种格式的图片转换、压缩和尺寸调整，
     确保生成的图片符合后续处理要求
"""
import os
import time
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor
import logging
from modules.pdf_generator import PDFGenerator

class ImageProcessor:
    """
    图片处理器类
    
    负责图片的预处理、格式转换、压缩和尺寸调整，支持批量处理
    主要功能包括:
    1. 将各种格式的图片转换为标准格式(JPEG)
    2. 压缩图片大小以减小文件体积
    3. 调整图片尺寸以适应PDF布局
    4. 处理透明图层，确保图片兼容性
    """
    
    # 支持的图片格式
    SUPPORTED_FORMATS = ['JPEG', 'PNG', 'WEBP']
    MAX_WORKERS = 4                                 # 并行处理线程数
    
    # 使用PDF生成器的尺寸限制
    MAX_WIDTH = PDFGenerator.IMAGE_MAX_WIDTH        # 最大宽度    
    MAX_HEIGHT = PDFGenerator.IMAGE_MAX_HEIGHT      # 最大高度    

    @classmethod
    def _calculate_image_size(cls, width, height):
        """
        计算图片的新尺寸
        
        按比例缩放图片，确保不超过最大宽度和高度
        
        参数:
            width (int): 原始图片宽度
            height (int): 原始图片高度
            
        返回:
            tuple: (新宽度, 新高度)
        """
        # 如果尺寸已经在限制范围内，则不做调整
        if width <= cls.MAX_WIDTH and height <= cls.MAX_HEIGHT:
            return width, height

        # 计算宽高缩放比例，取最小值保持纵横比
        width_ratio = cls.MAX_WIDTH / width                 # 宽度缩放比例    
        height_ratio = cls.MAX_HEIGHT / height              # 高度缩放比例    
        ratio = min(width_ratio, height_ratio)              # 取最小值保持纵横比    

        return int(width * ratio), int(height * ratio)      # 返回新尺寸     

    @classmethod
    def process_batch(cls, files, save_dir):
        """
        并行处理多个图片
        
        使用线程池并行处理多个图片文件，提高处理效率
        
        参数:
            files (list): 图片文件对象列表（通常来自request.files）
            save_dir (str/Path): 处理后图片的保存目录
            
        返回:
            list: 处理成功的图片路径列表
        """
        # 过滤空文件和无效文件
        valid_files = [f for f in files if f and f.filename]
        if not valid_files: 
            return []                                       # 如果没有有效文件，返回空列表
            
        # 创建线程池进行并行处理
        with ThreadPoolExecutor(max_workers=cls.MAX_WORKERS) as executor: 
            futures = [
                executor.submit(cls.process, file, save_dir)    # 提交处理任务    
                for file in valid_files                         # 遍历有效文件      
            ]
            
            # 收集处理结果
            results = []                                    # 结果列表    
            for future in futures:                          # 遍历处理结果    
                try:                                        # 处理异常    
                    result = future.result()                # 获取处理结果    
                    if result:                              # 如果结果存在    
                        results.append(result)              # 添加到结果列表    
                except Exception as e:                      # 处理异常    
                    logging.error(f"图片处理失败: {str(e)}") # 打印处理失败信息    
                    continue                                # 继续处理下一个文件    
                    
            return results                                  # 返回处理结果       

    @classmethod
    def process(cls, file_stream, save_dir):
        """
        处理单个图片
        
        对单个图片进行处理，包括格式转换、尺寸调整和品质优化
        
        参数:
            file_stream (FileStorage): 上传的图片文件对象
            save_dir (str/Path): 处理后图片的保存目录
            
        返回:
            Path/None: 处理成功返回保存的文件路径，失败返回None
            
        处理内容:
            1. 将RGBA/P模式图片转换为RGB（处理透明背景）
            2. 按需调整图片尺寸
            3. 转换为JPEG格式并优化存储
        """
        try:
            # 验证输入参数
            if not file_stream or not file_stream.filename:
                return None                                 # 如果文件流不存在或文件名不存在，返回None    

            # 确保目录存在
            valid_dir = Path(save_dir)
            valid_dir.mkdir(parents=True, exist_ok=True) 

            # 生成安全的文件名，避免路径注入风险
            orig_name = secure_filename(file_stream.filename)
            if not orig_name:
                return None                                 # 如果文件名不存在，返回None    

            # 添加时间戳确保文件名唯一
            timestamp = int(time.time() * 1000)                         # 时间戳    
            save_path = valid_dir / f"img_{timestamp}_{orig_name}"      # 保存路径    

            try:
                with Image.open(file_stream) as img:                                # 打开图片  

                    # 确保转换为RGB模式，处理透明图层
                    if img.mode in ('RGBA', 'P'):                                   # 如果图片模式是RGBA或P    
                        background = Image.new('RGB', img.size, (255, 255, 255))    # 创建白色背景
                        if img.mode == 'RGBA':                                      # 如果图片模式是RGBA    

                            # 使用alpha通道作为mask，将图片合成到白色背景上
                            background.paste(img, mask=img.split()[3])   
                        else:
                            background.paste(img)   # 将图片合成到白色背景上    
                        img = background            # 将图片设置为白色背景    
                    elif img.mode != 'RGB':         # 如果图片模式不是RGB    
                          
                        img = img.convert('RGB')    # 将图片转换为RGB模式    
                    
                    # 计算并调整尺寸，保持纵横比
                    new_width, new_height = cls._calculate_image_size(img.width, img.height) # 计算新尺寸    
                    if new_width != img.width or new_height != img.height:                   # 如果新尺寸与原尺寸不同    
                        # 使用LANCZOS算法进行高质量缩放
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS) # 使用LANCZOS算法进行高质量缩放    

                    # 统一保存为优化的JPEG格式
                    save_path = save_path.with_suffix('.jpg')
                    img.save( 
                        str(save_path),
                        'JPEG',
                        quality=85,       # 85%质量，平衡大小和清晰度
                        optimize=True,    # 优化存储
                        progressive=True  # 渐进式JPEG，适合网络传输
                    )
                    logging.info(f"成功保存图片: {save_path} ({new_width}x{new_height})") # 打印成功信息    
                    return save_path                                                     # 返回保存路径    

            except UnidentifiedImageError:                          # 处理无法识别的图片格式    
                logging.error(f"无法识别的图片格式: {orig_name}")     # 打印错误信息    
                return None                                         # 返回None    
                
        except Exception as e:                      # 处理其他异常       
            logging.error(f"图片处理异常: {str(e)}") # 打印错误信息    
            return None                             # 返回None    

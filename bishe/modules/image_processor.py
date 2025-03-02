"""
图片处理器（Windows路径兼容版）
Version: 1.4
Last Modified: 2024-03-20
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
    SUPPORTED_FORMATS = ['JPEG', 'PNG', 'WEBP']
    MAX_WORKERS = 4  # 并行处理线程数
    
    # 使用PDF生成器的尺寸限制
    MAX_WIDTH = PDFGenerator.IMAGE_MAX_WIDTH
    MAX_HEIGHT = PDFGenerator.IMAGE_MAX_HEIGHT

    @classmethod
    def _calculate_image_size(cls, width, height):
        """计算图片的新尺寸"""
        if width <= cls.MAX_WIDTH and height <= cls.MAX_HEIGHT:
            return width, height

        # 计算缩放比例
        width_ratio = cls.MAX_WIDTH / width
        height_ratio = cls.MAX_HEIGHT / height
        ratio = min(width_ratio, height_ratio)

        return int(width * ratio), int(height * ratio)

    @classmethod
    def process_batch(cls, files, save_dir):
        """并行处理多个图片，添加验证"""
        # 过滤空文件
        valid_files = [f for f in files if f and f.filename]
        if not valid_files:
            return []  # 如果没有有效文件，返回空列表
            
        with ThreadPoolExecutor(max_workers=cls.MAX_WORKERS) as executor:
            futures = [
                executor.submit(cls.process, file, save_dir)
                for file in valid_files
            ]
            
            results = []
            for future in futures:
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logging.error(f"图片处理失败: {str(e)}")
                    continue
                    
            return results

    @classmethod
    def process(cls, file_stream, save_dir):
        """优化的单图片处理，添加RGBA转换"""
        try:
            if not file_stream or not file_stream.filename:
                return None

            valid_dir = Path(save_dir)
            valid_dir.mkdir(parents=True, exist_ok=True)

            # 生成安全文件名
            orig_name = secure_filename(file_stream.filename)
            if not orig_name:
                return None

            timestamp = int(time.time() * 1000)
            save_path = valid_dir / f"img_{timestamp}_{orig_name}"

            try:
                with Image.open(file_stream) as img:
                    # 确保转换为RGB模式
                    if img.mode in ('RGBA', 'P'):
                        # 创建白色背景
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'RGBA':
                            background.paste(img, mask=img.split()[3])  # 使用alpha通道作为mask
                        else:
                            background.paste(img)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # 计算并调整尺寸
                    new_width, new_height = cls._calculate_image_size(img.width, img.height)
                    if new_width != img.width or new_height != img.height:
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # 保存优化后的图片
                    save_path = save_path.with_suffix('.jpg')
                    img.save(
                        str(save_path),
                        'JPEG',
                        quality=85,
                        optimize=True,
                        progressive=True
                    )
                    logging.info(f"成功保存图片: {save_path} ({new_width}x{new_height})")
                    return save_path

            except UnidentifiedImageError:
                logging.error(f"无法识别的图片格式: {orig_name}")
                return None
                
        except Exception as e:
            logging.error(f"图片处理异常: {str(e)}")
            return None

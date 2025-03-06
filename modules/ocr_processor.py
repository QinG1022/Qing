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
    @classmethod
    def check_tesseract(cls):
        """检查Tesseract是否正确安装和配置"""
        try:
            # 检查环境变量
            if not os.environ.get('TESSDATA_PREFIX'):
                # 尝试设置默认路径
                default_path = r"C:\Program Files\Tesseract-OCR\tessdata"
                if os.path.exists(default_path):
                    os.environ['TESSDATA_PREFIX'] = default_path
                else:
                    raise EnvironmentError("TESSDATA_PREFIX 环境变量未设置")

            # 检查Tesseract可执行文件
            if sys.platform.startswith('win'):
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

            # 测试OCR功能
            test_text = pytesseract.get_languages()
            if 'chi_sim' not in test_text:
                raise RuntimeError("中文语言包未安装")

            return True

        except Exception as e:
            logging.error(f"Tesseract检查失败: {str(e)}")
            raise RuntimeError(f"OCR系统未就绪: {str(e)}")

    @classmethod
    def process_image(cls, image_path):
        """处理单个图片的OCR"""
        # 首次使用时检查Tesseract
        if not hasattr(cls, '_tesseract_checked'):
            cls.check_tesseract()
            cls._tesseract_checked = True

        try:
            # 确保图片文件存在
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"图片不存在: {image_path}")

            # 打开并预处理图片
            with Image.open(image_path) as img:
                # 转换为RGB模式
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 进行OCR识别
                text = pytesseract.image_to_string(img, lang='chi_sim')
                
                # 处理识别结果
                text = text.strip()
                
                # 即使文本为空也返回结果，不再返回None
                return {
                    'image_path': str(image_path),
                    'text': text if text else "图片未能识别出文字",  # 如果文本为空，提供默认值
                    'confidence': None  # TODO: 添加置信度
                }

        except Exception as e:
            logging.error(f"OCR处理失败: {str(e)}")
            # 返回错误信息而不是None
            return {
                'image_path': str(image_path) if image_path else "未知路径",
                'text': f"图片处理错误: {str(e)}",
                'confidence': 0
            }

    @classmethod
    def process_batch(cls, image_paths):
        """批量处理图片OCR"""
        results = []
        for path in image_paths:
            try:
                result = cls.process_image(path)
                # 所有结果都添加到结果列表中，不再检查result是否为None
                # 因为process_image现在总是返回一个字典
                results.append(result)
                logging.info(f"处理图片 {path} 完成")
            except Exception as e:
                logging.error(f"处理图片失败 {path}: {str(e)}")
                # 添加错误信息到结果列表
                results.append({
                    'image_path': str(path),
                    'text': f"处理失败: {str(e)}",
                    'confidence': 0
                })
        return results

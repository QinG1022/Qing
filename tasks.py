"""
Celery异步任务模块
功能: 处理耗时操作，如PDF生成和OCR识别
作者: [您的名字]
版本: 1.5
"""
import os
import sys
from pathlib import Path
from celery import Celery
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Celery应用实例
celery = Celery('bishe')
celery.config_from_object('celeryconfig')

# 确保可以导入自定义模块
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.pdf_generator import PDFGenerator
from modules.ocr_processor import OCRProcessor

@celery.task(bind=True)
def generate_pdf(self, text_content, image_paths, output_dir):
    """异步PDF生成任务"""
    try:
        logger.info(f"开始生成PDF - 文本长度: {len(text_content) if text_content else 0}, 图片数量: {len(image_paths)}")
        logger.info(f"图片路径: {image_paths}")
        logger.info(f"输出目录: {output_dir}")

        # 检查输入参数
        if not text_content and not image_paths:
            raise ValueError("请提供文本内容或图片，不能都为空")

        # 确保所有图片路径都存在
        valid_images = []
        if image_paths:
            for img_path in image_paths:
                img_path = Path(img_path)
                if img_path.exists():
                    valid_images.append(str(img_path))
                    logger.info(f"有效图片: {img_path}")
                else:
                    logger.warning(f"图片不存在: {img_path}")

            if not valid_images and not text_content:
                raise ValueError("没有有效的图片文件且无文本内容")

        # 生成PDF
        try:
            filename = PDFGenerator.generate(
                text_content=text_content if text_content else "",
                image_paths=valid_images,
                output_dir=output_dir
            )
            logger.info(f"PDF生成成功: {filename}")
            return filename
        except Exception as e:
            logger.error(f"PDF生成失败: {e}", exc_info=True)
            raise
        
    except Exception as e:
        logger.error(f"任务执行失败: {str(e)}", exc_info=True)
        raise

@celery.task(bind=True)
def process_images_task(self, image_paths):
    """处理图片OCR任务"""
    try:
        self.update_state(state='PROCESSING', meta={
            'message': '正在进行OCR识别...'
        })
        
        # 验证图片路径
        valid_paths = []
        for path in image_paths:
            if os.path.exists(path):
                valid_paths.append(path)
            else:
                logger.warning(f"图片不存在: {path}")

        # 批量OCR处理
        results = OCRProcessor.process_batch(valid_paths)
        
        if not results:
            raise ValueError("OCR处理未返回有效结果")

        # 处理识别结果
        processed_results = []
        for result in results:
            if result and result.get('text'):
                processed_results.append({
                    'text': result['text'].strip(),
                    'path': result['image_path'],
                    'confidence': result.get('confidence')
                })

        logger.info(f"成功处理 {len(processed_results)} 张图片的OCR")
        return {
            'status': 'success',
            'results': processed_results
        }
        
    except Exception as e:
        logger.error(f"OCR处理失败: {str(e)}", exc_info=True)
        raise

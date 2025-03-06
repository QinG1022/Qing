"""
PDF文档生成器模块
功能: 根据文本和图片生成格式化PDF文档
作者: [您的名字]
版本: 1.8
"""
import os
import logging
import threading
import time
import shutil
from pathlib import Path
from datetime import datetime
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

# 导入PIL组件
from PIL import Image

# 导入ReportLab组件
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Image as PlatypusImage, Spacer
from reportlab.lib.units import inch
from reportlab.platypus.flowables import KeepTogether

# 导入字体工具
from fontTools.ttLib import TTFont as FontToolsFont

# 导入PDF处理工具
from PyPDF2 import PdfReader, PdfWriter

class PDFGenerator:
    """PDF文档生成器类
    
    负责处理PDF文档的生成，包括：
    1. 文本内容排版
    2. 图片处理和布局
    3. 字体管理
    4. 页面布局控制
    """
    
    # 配置常量
    FONT_DIR = Path(__file__).parent.parent / "fonts"  # 字体目录
    FONT_NAME = "simkai.ttf"  # 默认使用楷体
    REGISTERED_NAME = "SimKai"  # 字体注册名
    CACHE_DIR = Path(__file__).parent.parent / "cache"  # 缓存目录
    IMAGE_MAX_WIDTH = 400  # 图片最大宽度
    IMAGE_MAX_HEIGHT = 600  # 图片最大高度
    IMAGE_QUALITY = 85  # JPEG压缩质量
    FONT_SIZE = 12  # 默认字号
    LEADING = 14  # 行间距

    # 线程安全控制
    _font_lock = threading.Lock()
    _fonts_registered = False

    @classmethod
    def _validate_font(cls):
        """简化的字体验证"""
        try:
            # 确保字体目录存在
            cls.FONT_DIR.mkdir(parents=True, exist_ok=True)
            font_path = cls.FONT_DIR / cls.FONT_NAME
            
            # 如果字体文件不存在，从系统复制
            if not font_path.exists():
                system_font = Path(r"C:\Windows\Fonts\simkai.ttf")
                if system_font.exists():
                    shutil.copy2(system_font, font_path)
                else:
                    # 尝试其他可能的字体文件名
                    alternatives = [
                        r"C:\Windows\Fonts\SIMKAI.TTF",
                        r"C:\Windows\Fonts\仿宋_GB2312.ttf",
                        r"C:\Windows\Fonts\SIMFANG.TTF"
                    ]
                    for alt_font in alternatives:
                        if Path(alt_font).exists():
                            shutil.copy2(alt_font, font_path)
                            break
                    else:
                        raise FileNotFoundError("[FONT001] 系统中未找到合适的中文字体")

            # 基本验证
            if not font_path.exists():
                raise FileNotFoundError(f"[FONT002] 字体文件不存在: {font_path}")

            if not os.access(str(font_path), os.R_OK):
                raise PermissionError(f"[FONT003] 无法读取字体文件: {font_path}")

            # 简化的格式验证
            with open(font_path, 'rb') as f:
                magic = f.read(4)
                if magic not in {b'\x00\x01\x00\x00', b'true', b'typ1', b'OTTO'}:
                    raise ValueError("[FONT004] 不支持的字体格式")

            return font_path

        except Exception as e:
            logging.error(f"字体初始化失败: {str(e)}", exc_info=True)
            # 尝试使用系统默认字体
            try:
                from reportlab.pdfbase._fontdata import _fonts
                if 'SimSun' in _fonts:
                    logging.info("使用系统默认字体 SimSun")
                    cls.REGISTERED_NAME = 'SimSun'
                    return None
            except:
                pass
            raise RuntimeError(f"字体系统错误: {str(e)}") from e

    @classmethod
    def _calculate_image_size(cls, img):
        """计算图片在PDF中的安全显示尺寸
        
        Args:
            img: PIL.Image对象
            
        Returns:
            tuple: (width, height) 新的尺寸
        """
        # A4页面可用区域（考虑页边距）
        POINTS_PER_INCH = 72
        page_width, page_height = A4
        PAGE_WIDTH = page_width - 2 * POINTS_PER_INCH  # 减去左右边距
        PAGE_HEIGHT = page_height - 2 * POINTS_PER_INCH  # 减去上下边距
        
        # 计算最大安全尺寸（页面尺寸的80%）
        MAX_WIDTH = int(PAGE_WIDTH * 0.8)
        MAX_HEIGHT = int(PAGE_HEIGHT * 0.8)
        
        # 获取原始尺寸
        orig_width, orig_height = img.size
        
        # 计算缩放比例
        width_ratio = MAX_WIDTH / orig_width
        height_ratio = MAX_HEIGHT / orig_height
        ratio = min(width_ratio, height_ratio, 1.0)  # 不放大图片
        
        # 计算新尺寸
        new_width = int(orig_width * ratio)
        new_height = int(orig_height * ratio)
        
        # 确保尺寸不超过最大限制
        new_width = min(new_width, MAX_WIDTH)
        new_height = min(new_height, MAX_HEIGHT)
        
        logging.info(f"图片尺寸调整: {orig_width}x{orig_height} -> {new_width}x{new_height}")
        return new_width, new_height

    @classmethod
    def generate(cls, text_content, image_paths, output_dir):
        """生成PDF文档"""
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"document_{timestamp}.pdf"
            output_path = output_dir / filename
            
            # 注册字体
            font_path = cls._validate_font()
            with cls._font_lock:
                if not cls._fonts_registered:
                    pdfmetrics.registerFont(TTFont(cls.REGISTERED_NAME, str(font_path)))
                    cls._fonts_registered = True
            
            # 处理文本内容
            if text_content and text_content.strip():
                # 创建文本样式
                normal_style = ParagraphStyle(
                    'CustomNormal',
                    fontName=cls.REGISTERED_NAME,
                    fontSize=cls.FONT_SIZE,
                    leading=cls.LEADING,  # 行间距
                    wordWrap='CJK',  # 支持中文换行
                    allowWidows=0,
                    allowOrphans=0
                )
                
                # 创建段落对象
                paragraphs = []
                for line in text_content.split('\n'):
                    if line.strip():
                        paragraphs.append(Paragraph(line.strip(), normal_style))
                        paragraphs.append(Spacer(1, 5))  # 段落间距
                
                # 使用临时PDF存储文本内容
                temp_text_pdf = str(Path(output_dir) / f"temp_text_{timestamp}.pdf")
                doc = SimpleDocTemplate(
                    temp_text_pdf,
                    pagesize=A4,
                    leftMargin=50,
                    rightMargin=50,
                    topMargin=50,
                    bottomMargin=50
                )
                
                # 构建文档
                doc.build(paragraphs)
                
                # 准备合并PDF
                writer = PdfWriter()
                
                # 添加文本PDF页面
                temp_reader = PdfReader(temp_text_pdf)
                for page in temp_reader.pages:
                    writer.add_page(page)
                
                # 处理图片
                if image_paths:
                    # 创建图片PDF
                    img_pdf = str(Path(output_dir) / f"temp_img_{timestamp}.pdf")
                    c_img = canvas.Canvas(img_pdf, pagesize=A4)
                    page_width, page_height = A4
                    y_position = page_height - 50
                    
                    has_image_content = False
                    
                    for img_path in image_paths:
                        try:
                            img_path = Path(img_path)
                            if img_path.exists():
                                with Image.open(img_path) as img:
                                    # RGB转换
                                    if img.mode in ('RGBA', 'P'):
                                        background = Image.new('RGB', img.size, (255, 255, 255))
                                        if img.mode == 'RGBA':
                                            background.paste(img, mask=img.split()[3])
                                        else:
                                            background.paste(img)
                                        img = background
                                    elif img.mode != 'RGB':
                                        img = img.convert('RGB')

                                    # 计算图片尺寸
                                    img_width, img_height = img.size
                                    scale = min(
                                        (page_width - 100) / img_width,
                                        (page_height - 100) / img_height,
                                        1.0
                                    )
                                    width = img_width * scale
                                    height = img_height * scale

                                    # 如果当前页空间不够，创建新页面
                                    if y_position - height < 50:
                                        c_img.showPage()
                                        c_img.setFont(cls.REGISTERED_NAME, cls.FONT_SIZE)
                                        y_position = page_height - 50

                                    # 居中显示图片
                                    x_position = (page_width - width) / 2
                                    y_position -= height

                                    # 直接绘制图片
                                    c_img.drawImage(
                                        str(img_path),
                                        x_position,
                                        y_position,
                                        width=width,
                                        height=height
                                    )
                                    has_image_content = True
                                    y_position -= 20
                                    logging.info(f"成功添加图片到PDF: {img_path}")
                        except Exception as e:
                            logging.error(f"处理图片失败 {img_path}: {e}", exc_info=True)
                            continue

                    # 保存图片PDF
                    if has_image_content:
                        c_img.save()
                        
                        # 添加图片页面到主PDF
                        img_reader = PdfReader(img_pdf)
                        for page in img_reader.pages:
                            writer.add_page(page)
                        
                        # 清理临时图片PDF
                        try:
                            os.remove(img_pdf)
                        except:
                            pass
                
                # 写入最终PDF
                with open(str(output_path), 'wb') as f:
                    writer.write(f)
                
                # 清理临时PDF
                try:
                    os.remove(temp_text_pdf)
                except:
                    pass
                
                logging.info(f"成功生成包含完整文本和图片的PDF文件: {output_path}")
                return filename
            
            # 只处理图片的情况
            elif image_paths:
                # 创建PDF文档
                c = canvas.Canvas(str(output_path), pagesize=A4)
                page_width, page_height = A4
                
                # 设置字体
                c.setFont(cls.REGISTERED_NAME, cls.FONT_SIZE)
                
                # 处理图片
                y_position = page_height - 50
                has_content = False
                
                for img_path in image_paths:
                    try:
                        img_path = Path(img_path)
                        if img_path.exists():
                            with Image.open(img_path) as img:
                                # RGB转换
                                if img.mode in ('RGBA', 'P'):
                                    background = Image.new('RGB', img.size, (255, 255, 255))
                                    if img.mode == 'RGBA':
                                        background.paste(img, mask=img.split()[3])
                                    else:
                                        background.paste(img)
                                    img = background
                                elif img.mode != 'RGB':
                                    img = img.convert('RGB')

                                # 计算图片尺寸
                                img_width, img_height = img.size
                                scale = min(
                                    (page_width - 100) / img_width,
                                    (page_height - 100) / img_height,
                                    1.0
                                )
                                width = img_width * scale
                                height = img_height * scale

                                # 如果当前页空间不够，创建新页面
                                if y_position - height < 50:
                                    c.showPage()
                                    c.setFont(cls.REGISTERED_NAME, cls.FONT_SIZE)
                                    y_position = page_height - 50

                                # 居中显示图片
                                x_position = (page_width - width) / 2
                                y_position -= height

                                # 直接绘制图片
                                c.drawImage(
                                    str(img_path),
                                    x_position,
                                    y_position,
                                    width=width,
                                    height=height
                                )
                                has_content = True
                                y_position -= 20
                                logging.info(f"成功添加图片到PDF: {img_path}")
                                
                    except Exception as e:
                        logging.error(f"处理图片失败 {img_path}: {e}", exc_info=True)
                        continue

                if not has_content:
                    raise ValueError("没有有效的文本或图片内容")

                # 保存PDF
                c.save()
                logging.info(f"成功生成PDF文件: {output_path}")
                return filename
            else:
                raise ValueError("没有有效的文本或图片内容")

        except Exception as e:
            logging.error(f"PDF生成失败: {str(e)}", exc_info=True)
            raise

    @classmethod
    def _process_image(cls, img_path):
        """优化的图片处理"""
        try:
            cache_key = f"img_{hash(str(img_path))}.jpg"
            cache_path = cls.CACHE_DIR / cache_key
            
            # 检查缓存
            if cache_path.exists():
                return PlatypusImage(str(cache_path))
                
            with Image.open(img_path) as img:
                # 优化图片尺寸
                img_width, img_height = img.size
                if img_width > cls.IMAGE_MAX_WIDTH or img_height > cls.IMAGE_MAX_HEIGHT:
                    ratio = min(
                        cls.IMAGE_MAX_WIDTH/img_width, 
                        cls.IMAGE_MAX_HEIGHT/img_height
                    )
                    new_size = (int(img_width*ratio), int(img_height*ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # 保存到缓存
                img.save(
                    cache_path, 
                    'JPEG', 
                    quality=cls.IMAGE_QUALITY, 
                    optimize=True
                )
                
                return PlatypusImage(str(cache_path))
                
        except Exception as e:
            logging.warning(f"图片处理失败: {str(e)}")
            return None

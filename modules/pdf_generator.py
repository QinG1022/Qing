"""
PDF文档生成器模块
功能: 根据文本和图片生成格式化PDF文档
版本: 1.8
最后更新: 2024-03-06
描述: 该模块提供PDF文档的生成功能，支持文本排版、图片嵌入、字体管理和页面布局
"""
 # 导入必要的库
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

class PDFGenerator: # PDF文档生成器类   
    """
    PDF文档生成器类
    
    负责处理PDF文档的生成，包括：
    1. 文本内容排版
    2. 图片处理和布局
    3. 字体管理
    4. 页面布局控制
    """
    
    # 配置常量
    FONT_DIR = Path(__file__).parent.parent / "fonts"   # 字体目录
    FONT_NAME = "simkai.ttf"                            # 默认使用楷体
    REGISTERED_NAME = "SimKai"                          # 字体注册名
    CACHE_DIR = Path(__file__).parent.parent / "cache"  # 缓存目录
    IMAGE_MAX_WIDTH = 400                               # 图片最大宽度（像素）
    IMAGE_MAX_HEIGHT = 600                              # 图片最大高度（像素）
    IMAGE_QUALITY = 85                                  # JPEG压缩质量（百分比）
    FONT_SIZE = 12                                      # 默认字号（磅）
    LEADING = 14                                        # 行间距（磅）

    # 线程安全控制
    _font_lock = threading.Lock()   # 字体锁定对象        
    _fonts_registered = False       # 字体注册状态    
     # 验证和初始化字体设置     
    @classmethod
    def _validate_font(cls): 
        """
        验证和初始化字体设置
        
        功能:
            1. 检查字体文件是否存在
            2. 尝试从系统复制字体文件
            3. 验证字体文件权限和格式
            
        返回:
            Path/None: 字体文件路径，失败时使用备用字体返回None
            
        异常:
            RuntimeError: 字体初始化失败且无法使用备用字体时抛出
        """
        try:
            # 确保字体目录存在
            cls.FONT_DIR.mkdir(parents=True, exist_ok=True)
            font_path = cls.FONT_DIR / cls.FONT_NAME        # 字体文件路径    
            
            # 如果字体文件不存在，从系统复制
            if not font_path.exists():
                system_font = Path(r"C:\Windows\Fonts\simkai.ttf")  # 系统字体路径    
                if system_font.exists():
                    shutil.copy2(system_font, font_path)            # 复制字体文件到字体目录    
                else:
                    # 尝试其他可能的字体文件名
                    alternatives = [
                        r"C:\Windows\Fonts\SIMKAI.TTF",         # 备用字体路径    
                        r"C:\Windows\Fonts\仿宋_GB2312.ttf",    # 备用字体路径    
                        r"C:\Windows\Fonts\SIMFANG.TTF"         # 备用字体路径    
                    ]
                    for alt_font in alternatives:
                        if Path(alt_font).exists():
                            shutil.copy2(alt_font, font_path)   # 复制字体文件到字体目录    
                            break                               # 跳出循环        
                    else:
                        raise FileNotFoundError("[FONT001] 系统中未找到合适的中文字体") # 抛出字体文件不存在异常        

            # 基本验证
            if not font_path.exists():
                raise FileNotFoundError(f"[FONT002] 字体文件不存在: {font_path}") # 抛出字体文件不存在异常   
                 
            # 验证字体文件权限  
            if not os.access(str(font_path), os.R_OK):
                raise PermissionError(f"[FONT003] 无法读取字体文件: {font_path}") # 抛出字体文件权限异常        

            # 简化的格式验证
            with open(font_path, 'rb') as f:
                magic = f.read(4)                                                   # 读取字体文件前4个字节    
                if magic not in {b'\x00\x01\x00\x00', b'true', b'typ1', b'OTTO'}:   # 如果字体文件格式不支持      
                    raise ValueError("[FONT004] 不支持的字体格式")                    # 抛出字体文件格式异常        

            return font_path    # 返回字体文件路径     
        # 处理异常    
        except Exception as e:
            logging.error(f"字体初始化失败: {str(e)}", exc_info=True)   # 打印字体初始化失败信息        
            # 尝试使用系统默认字体
            try:
                from reportlab.pdfbase._fontdata import _fonts      # 导入字体数据    
                if 'SimSun' in _fonts:                              # 如果SimSun字体存在    
                    logging.info("使用系统默认字体 SimSun")           # 打印使用系统默认字体信息        
                    cls.REGISTERED_NAME = 'SimSun'                  # 设置注册名    
                    return None                                     # 返回None    
            except:
                pass                                                # 忽略异常     
            raise RuntimeError(f"字体系统错误: {str(e)}") from e    # 抛出字体系统错误异常         

    @classmethod
    def _calculate_image_size(cls, img):
        """
        计算图片在PDF中的最佳显示尺寸
        
        功能:
            根据原始图片尺寸和页面大小计算最佳显示尺寸
            
        参数:
            img (PIL.Image): PIL图像对象
            
        返回:
            tuple: (width, height) 新的尺寸（单位：点）
            
        说明:
            - 保持图片原始纵横比
            - 不会放大小图片，只会缩小大图片
            - 考虑A4页面大小和边距限制
        """
        # A4页面可用区域（考虑页边距）
        POINTS_PER_INCH = 72                                # 每英寸点数        
        page_width, page_height = A4                        # A4页面尺寸       
        PAGE_WIDTH = page_width - 2 * POINTS_PER_INCH       # 减去左右边距
        PAGE_HEIGHT = page_height - 2 * POINTS_PER_INCH     # 减去上下边距
        
        # 计算最大安全尺寸（页面尺寸的80%）
        MAX_WIDTH = int(PAGE_WIDTH * 0.8)   # 最大宽度    
        MAX_HEIGHT = int(PAGE_HEIGHT * 0.8) # 最大高度    
        
        # 获取原始尺寸
        orig_width, orig_height = img.size      
        
        # 计算缩放比例
        width_ratio = MAX_WIDTH / orig_width         # 宽度缩放比例    
        height_ratio = MAX_HEIGHT / orig_height      # 高度缩放比例    
        ratio = min(width_ratio, height_ratio, 1.0)  # 不放大图片，只缩小
        
        # 计算新尺寸
        new_width = int(orig_width * ratio)     # 计算新宽度    
        new_height = int(orig_height * ratio)   # 计算新高度    
        
        # 确保尺寸不超过最大限制
        new_width = min(new_width, MAX_WIDTH)    
        new_height = min(new_height, MAX_HEIGHT)    
        
        logging.info(f"图片尺寸调整: {orig_width}x{orig_height} -> {new_width}x{new_height}") # 打印图片尺寸调整信息    
        return new_width, new_height    # 返回新尺寸       

    @classmethod
    def generate(cls, text_content, image_paths, output_dir): 
        """
        生成PDF文档
        
        功能:
            根据文本内容和图片生成格式化的PDF文档
            
        参数:
            text_content (str): 要添加到PDF的文本内容
            image_paths (list): 图片文件路径列表
            output_dir (str/Path): PDF输出目录
            
        返回:
            str: 生成的PDF文件名
            
        异常:
            ValueError: 当文本和图片都为空时抛出
            
        处理流程:
            1. 注册并验证字体
            2. 处理文本内容排版
            3. 处理图片布局和嵌入
            4. 合并所有内容到一个PDF文件
        """
        try:
            output_dir = Path(output_dir)                   # 输出目录    
            output_dir.mkdir(parents=True, exist_ok=True)   # 确保输出目录存在    
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')     # 时间戳    
            filename = f"document_{timestamp}.pdf"                  # 文件名    
            output_path = output_dir / filename                     # 输出路径    
            
            # 注册字体
            font_path = cls._validate_font()        # 验证字体    
            with cls._font_lock:                    # 锁定字体    
                if not cls._fonts_registered:       # 如果字体未注册    
                    pdfmetrics.registerFont(TTFont(cls.REGISTERED_NAME, str(font_path)))    # 注册字体    
                    cls._fonts_registered = True    # 设置字体注册状态     
            
            # 处理文本内容
            if text_content and text_content.strip():
                # 创建文本样式
                normal_style = ParagraphStyle(      # 创建文本样式    
                    'CustomNormal',                 # 样式名称    
                    fontName=cls.REGISTERED_NAME,   # 字体名称    
                    fontSize=cls.FONT_SIZE,         # 字体大小    
                    leading=cls.LEADING,            # 行间距    
                    wordWrap='CJK',                 # 支持中文换行    
                    allowWidows=0,                  # 不允许 widows    
                    allowOrphans=0                  # 不允许 orphans    
                )
                
                # 创建段落对象
                paragraphs = []                             # 段落列表    
                for line in text_content.split('\n'):       # 遍历文本内容    
                    if line.strip():                        # 如果行不为空    
                        paragraphs.append(Paragraph(line.strip(), normal_style)) # 添加段落    
                        paragraphs.append(Spacer(1, 5))     # 段落间距
                
                # 使用临时PDF存储文本内容
                temp_text_pdf = str(Path(output_dir) / f"temp_text_{timestamp}.pdf")    # 临时文本PDF路径    
                doc = SimpleDocTemplate(            # 创建文档模板    
                    temp_text_pdf,                  # 临时文本PDF路径    
                    pagesize=A4,                    # 页面尺寸    
                    leftMargin=50,                  # 左边距    
                    rightMargin=50,                 # 右边距    
                    topMargin=50,                   # 上边距    
                    bottomMargin=50                 # 下边距    
                )
                
                # 构建文档
                doc.build(paragraphs)
                
                # 准备合并PDF
                writer = PdfWriter()
                
                # 添加文本PDF页面
                temp_reader = PdfReader(temp_text_pdf)
                for page in temp_reader.pages:  # 遍历临时文本PDF页面        
                    writer.add_page(page)       # 添加页面    
                
                # 处理图片
                if image_paths:
                    # 创建图片PDF
                    img_pdf = str(Path(output_dir) / f"temp_img_{timestamp}.pdf")   # 临时图片PDF路径    
                    c_img = canvas.Canvas(img_pdf, pagesize=A4)     # 创建图片PDF    
                    page_width, page_height = A4                    # 页面尺寸    
                    y_position = page_height - 50                   # 位置    
                    
                    has_image_content = False       # 图片内容标志    
                    
                    for img_path in image_paths:    # 遍历图片路径    
                        try:
                            img_path = Path(img_path)               # 图片路径    
                            if img_path.exists():                   # 如果图片路径存在    
                                with Image.open(img_path) as img:   # 打开图片    
                                    # RGB转换，处理透明通道
                                    if img.mode in ('RGBA', 'P'):   # 如果图片模式为RGBA或P    
                                        background = Image.new('RGB', img.size, (255, 255, 255))    # 创建背景    
                                        if img.mode == 'RGBA':      # 如果图片模式为RGBA    
                                            background.paste(img, mask=img.split()[3])  # 粘贴图片    
                                        else:
                                            background.paste(img)   # 粘贴图片    
                                        img = background            # 设置图片    
                                    elif img.mode != 'RGB':         # 如果图片模式不为RGB    
                                        img = img.convert('RGB')    # 转换图片模式    

                                    # 计算图片尺寸
                                    img_width, img_height = img.size        # 图片尺寸    
                                    scale = min(                            # 计算缩放比例    
                                        (page_width - 100) / img_width,     # 计算宽度缩放比例    
                                        (page_height - 100) / img_height,   # 计算高度缩放比例    
                                        1.0                                 # 最小缩放比例    
                                    )
                                    width = img_width * scale   # 计算宽度    
                                    height = img_height * scale # 计算高度    

                                    # 如果当前页空间不够，创建新页面
                                    if y_position - height < 50:        # 如果当前页空间不够    
                                        c_img.showPage()                # 创建新页面    
                                        c_img.setFont(cls.REGISTERED_NAME, cls.FONT_SIZE)   # 设置字体    
                                        y_position = page_height - 50   # 设置位置    

                                    # 居中显示图片
                                    x_position = (page_width - width) / 2   # 计算位置    
                                    y_position -= height                    # 设置位置     

                                    # 绘制图片到页面
                                    c_img.drawImage(
                                        str(img_path),  # 图片路径    
                                        x_position,     # 位置    
                                        y_position,     # 位置    
                                        width=width,    # 宽度    
                                        height=height   # 高度    
                                    )
                                    has_image_content = True    # 图片内容标志    
                                    y_position -= 20            # 图片之间的间距
                                    logging.info(f"成功添加图片到PDF: {img_path}")
                        except Exception as e:                  # 处理异常    
                            logging.error(f"处理图片失败 {img_path}: {e}", exc_info=True) 
                            continue

                    # 保存图片PDF
                    if has_image_content:
                        c_img.save()    # 保存图片PDF    
                        
                        # 添加图片页面到主PDF
                        img_reader = PdfReader(img_pdf) # 读取图片PDF    
                        for page in img_reader.pages:   # 遍历图片PDF页面    
                            writer.add_page(page)       # 添加页面    
                        
                        # 清理临时图片PDF
                        try:
                            os.remove(img_pdf)  # 删除临时图片PDF    
                        except:
                            pass
                
                # 写入最终PDF
                with open(str(output_path), 'wb') as f: # 打开输出路径    
                    writer.write(f)                     # 写入最终PDF    
                
                # 清理临时PDF
                try:
                    os.remove(temp_text_pdf)
                except:
                    pass
                
                logging.info(f"成功生成包含完整文本和图片的PDF文件: {output_path}")
                return filename             # 返回文件名    
            
            # 只处理图片的情况
            elif image_paths:
                # 创建PDF文档
                c = canvas.Canvas(str(output_path), pagesize=A4)    
                page_width, page_height = A4    # 页面尺寸    
                
                # 设置字体
                c.setFont(cls.REGISTERED_NAME, cls.FONT_SIZE)    
                
                # 处理图片
                y_position = page_height - 50   # 位置    
                has_content = False             # 内容标志    
                
                for img_path in image_paths:    # 遍历图片路径    
                    try:
                        img_path = Path(img_path)               # 图片路径    
                        if img_path.exists():                   # 如果图片路径存在    
                            with Image.open(img_path) as img:   # 打开图片   

                                # RGB转换，处理透明通道
                                if img.mode in ('RGBA', 'P'):   # 如果图片模式为RGBA或P    
                                    background = Image.new('RGB', img.size, (255, 255, 255))    # 创建背景    
                                    if img.mode == 'RGBA':      # 如果图片模式为RGBA    
                                        background.paste(img, mask=img.split()[3])  # 粘贴图片    
                                    else:
                                        background.paste(img)   # 粘贴图片    
                                    img = background            # 设置图片    
                                elif img.mode != 'RGB':         # 如果图片模式不为RGB    
                                    img = img.convert('RGB')    # 转换图片模式    

                                # 计算图片尺寸
                                img_width, img_height = img.size        # 图片尺寸    
                                scale = min(                            # 计算缩放比例    
                                    (page_width - 100) / img_width,     # 计算宽度缩放比例    
                                    (page_height - 100) / img_height,   # 计算高度缩放比例    
                                    1.0                                 # 最小缩放比例    
                                )
                                width = img_width * scale   # 计算宽度    
                                height = img_height * scale # 计算高度    

                                # 如果当前页空间不够，创建新页面
                                if y_position - height < 50:        # 如果当前页空间不够    
                                    c.showPage()                    # 创建新页面    
                                    c.setFont(cls.REGISTERED_NAME, cls.FONT_SIZE)   # 设置字体    
                                    y_position = page_height - 50   # 设置位置    

                                # 居中显示图片
                                x_position = (page_width - width) / 2   # 计算位置    
                                y_position -= height    # 设置位置     

                                # 绘制图片到页面
                                c.drawImage( 
                                    str(img_path),  # 图片路径    
                                    x_position,     # 位置    
                                    y_position,     # 位置    
                                    width=width,    # 宽度    
                                    height=height   # 高度    
                                )
                                has_content = True  # 内容标志    
                                y_position -= 20    # 图片之间的间距
                                logging.info(f"成功添加图片到PDF: {img_path}")
                                
                    except Exception as e:  # 处理异常    
                        logging.error(f"处理图片失败 {img_path}: {e}", exc_info=True)   # 打印处理图片失败信息    
                        continue            # 继续处理下一个图片    

                if not has_content:     # 如果没有内容    
                    raise ValueError("没有有效的文本或图片内容")    # 抛出没有有效文本或图片内容异常    

                # 保存PDF
                c.save()    
                logging.info(f"成功生成PDF文件: {output_path}")    # 打印成功生成PDF文件信息    
                return filename     # 返回文件名    
            else:                   # 如果文本和图片都为空    
                raise ValueError("没有有效的文本或图片内容")        # 抛出没有有效文本或图片内容异常    

        except Exception as e:      # 处理异常       
            logging.error(f"PDF生成失败: {str(e)}", exc_info=True) # 打印PDF生成失败信息    
            raise                   # 抛出异常    

    @classmethod 
    def _process_image(cls, img_path): 
        """
        优化图片处理
        
        功能:
            处理图片并优化其在PDF中的显示
            
        参数:
            img_path (str/Path): 图片文件路径
            
        返回:
            PlatypusImage/None: 处理后的图片对象，失败时返回None
            
        说明:
            - 使用缓存减少重复处理
            - 调整图片尺寸以适应PDF
            - 优化图片质量和格式
        """
        try:     
            cache_key = f"img_{hash(str(img_path))}.jpg"    # 缓存键    
            cache_path = cls.CACHE_DIR / cache_key          # 缓存路径    
            
            # 检查缓存，如果已处理过则直接返回
            if cache_path.exists():
                return PlatypusImage(str(cache_path))   # 返回处理后的图片对象    
                
            with Image.open(img_path) as img:   # 打开图片    
                # 优化图片尺寸
                img_width, img_height = img.size    # 图片尺寸    
                if img_width > cls.IMAGE_MAX_WIDTH or img_height > cls.IMAGE_MAX_HEIGHT:    # 如果图片宽度或高度超过最大限制    
                    ratio = min(    # 计算缩放比例    
                        cls.IMAGE_MAX_WIDTH/img_width,  # 计算宽度缩放比例    
                        cls.IMAGE_MAX_HEIGHT/img_height # 计算高度缩放比例    
                    )
                    new_size = (int(img_width*ratio), int(img_height*ratio))    # 计算新尺寸    
                    img = img.resize(new_size, Image.Resampling.LANCZOS)        # 调整图片尺寸    
                
                # 保存到缓存目录
                img.save(
                    cache_path,     # 缓存路径    
                    'JPEG',         # 保存格式    
                    quality=cls.IMAGE_QUALITY,  # 质量    
                    optimize=True   # 优化    
                )
                
                return PlatypusImage(str(cache_path))   # 返回处理后的图片对象    
                
        except Exception as e:  # 处理异常    
            logging.warning(f"图片处理失败: {str(e)}")  # 打印图片处理失败信息    
            return None         # 返回None    

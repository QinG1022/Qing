"""
OCR文字识别处理器模块
功能: 对图像进行光学字符识别(OCR)，提取图像中的文字
版本: 1.2
最后更新: 2024-03-06
描述: 该模块基于Tesseract OCR引擎实现图像文字识别功能，支持中文识别和批量处理
"""
import json
import logging
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from PIL import Image

# pytesseract 只在走本地 Tesseract 时才需要；走云端 OCR 时可以不装
try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None


def load_ocr_config():
    """读取 OCR 配置（惰性导入，避免模块级循环依赖）。"""
    try:
        from .settings_store import load_config
    except ImportError:
        from modules.settings_store import load_config
    return load_config()


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
            # Tesseract 路径：优先环境变量，其次默认安装路径，最后依赖 PATH
            if sys.platform.startswith('win'):
                candidates = [
                    os.environ.get('TESSERACT_CMD'),
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                ]
                found = next((p for p in candidates if p and os.path.exists(p)), None)
                if not found:
                    raise EnvironmentError(
                        "未找到 tesseract.exe。请安装 Tesseract-OCR，"
                        "或设置环境变量 TESSERACT_CMD 指向它"
                    )
                pytesseract.pytesseract.tesseract_cmd = found

            # 检查环境变量（tessdata 目录）
            if not os.environ.get('TESSDATA_PREFIX'):
                default_path = r"C:\Program Files\Tesseract-OCR\tessdata"
                if os.path.exists(default_path):
                    os.environ['TESSDATA_PREFIX'] = default_path
                else:
                    raise EnvironmentError("TESSDATA_PREFIX 环境变量未设置")

            # 测试OCR功能和中文语言包
            test_text = pytesseract.get_languages()     # 获取语言列表    
            if 'chi_sim' not in test_text:              # 如果中文语言包不存在    
                raise RuntimeError("中文语言包未安装")    # 抛出中文语言包未安装异常    

            return True

        except Exception as e:                          # 处理异常    
            logging.error(f"Tesseract检查失败: {str(e)}") # 打印检查失败信息    
            raise RuntimeError(f"OCR系统未就绪: {str(e)}") # 抛出OCR系统未就绪异常    

    # ------------------------------------------------------------------
    # 视觉模型后端：图片直接交给多模态模型，复用对话的 Key（走同一份额度）
    # ------------------------------------------------------------------
    OCR_PROMPT = (
        '你是一个 OCR 引擎，请把图片里的文字完整转写出来：\n'
        '1. 保留原有层级、列表、段落结构，用 Markdown 表达\n'
        '2. 表格用 Markdown 表格，不要用图片描述代替\n'
        '3. 只输出转写结果，不要解释、不要总结、不要加"以下是"之类的开场白\n'
        '4. 如果图片里确实没有文字，用一句话客观描述图片内容'
    )

    @staticmethod
    def _encode_image(path, max_side=1600, quality=85):
        """把图片压成 base64 JPEG，控制 token 和请求体大小。"""
        import base64
        import io

        with Image.open(path) as img:
            img = img.convert('RGB')
            w, h = img.size
            scale = min(1.0, max_side / max(w, h))
            if scale < 1.0:
                # 用 resize 而不是 thumbnail：不经过 draft() 那条历史漏洞路径
                img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                                 Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality)
        return base64.b64encode(buf.getvalue()).decode('ascii')

    @classmethod
    def _process_with_vision(cls, image_path, cfg):
        """用视觉模型识别单张图片。"""
        path = Path(image_path)
        try:
            if not path.exists():
                raise FileNotFoundError(f'图片不存在: {path}')

            key = (cfg.get('api_key') or '').strip()
            if not key:
                raise RuntimeError('未配置对话 API Key（vision 模式需要复用它）')

            model = (cfg.get('ocr_model') or 'Qwen/Qwen3-VL-8B-Instruct').strip()
            base_url = (cfg.get('base_url') or '').strip() or None
            b64 = cls._encode_image(path)

            from openai import OpenAI
            client = OpenAI(api_key=key, base_url=base_url, timeout=120, max_retries=0)
            resp = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': cls.OCR_PROMPT},
                        {'type': 'image_url',
                         'image_url': {'url': 'data:image/jpeg;base64,' + b64}},
                    ],
                }],
            )

            text = (resp.choices[0].message.content or '').strip()
            usage = getattr(resp, 'usage', None)
            if usage:
                logging.info(
                    '视觉识别完成 model=%s tokens=%s/%s',
                    model, getattr(usage, 'prompt_tokens', '?'),
                    getattr(usage, 'completion_tokens', '?'),
                )

            return {
                'image_path': str(path),
                'text': text if text else '图片未能识别出文字',
                'confidence': None,
            }
        except Exception as e:
            logging.error(f"视觉识别失败: {e}")
            return {
                'image_path': str(path),
                'text': f'图片处理错误: {e}',
                'confidence': 0,
            }

    # ------------------------------------------------------------------
    # 云端 OCR（DeepSeek）：不需要本地 Tesseract
    # 文档：POST https://api.deepseek.com/v1/tools/ocr
    # ------------------------------------------------------------------
    @staticmethod
    def _multipart_body(file_path, purpose):
        """手工拼 multipart/form-data，避免为此引入 requests/httpx 依赖。"""
        boundary = '----QingOcr' + uuid.uuid4().hex
        path = Path(file_path)
        filename = path.name
        ctype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        data = path.read_bytes()

        parts = [
            (f'--{boundary}\r\n'
             f'Content-Disposition: form-data; name="purpose"\r\n\r\n'
             f'{purpose}\r\n').encode('utf-8'),
            (f'--{boundary}\r\n'
             f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
             f'Content-Type: {ctype}\r\n\r\n').encode('utf-8'),
            data,
            f'\r\n--{boundary}--\r\n'.encode('utf-8'),
        ]
        return b''.join(parts), f'multipart/form-data; boundary={boundary}'

    @classmethod
    def _ocr_deepseek(cls, image_path, cfg):
        """调用 DeepSeek OCR，返回纯文本。失败抛 RuntimeError（带可读原因）。"""
        base = (cfg.get('ocr_base_url') or 'https://api.deepseek.com').rstrip('/')
        url = base + ('/tools/ocr' if base.endswith('/v1') else '/v1/tools/ocr')
        key = (cfg.get('ocr_api_key') or '').strip()
        if not key:
            raise RuntimeError('未配置 OCR 的 API Key（config.json 里的 ocr_api_key）')

        purpose = (cfg.get('ocr_purpose') or 'text_recognition').strip()
        body, ctype = cls._multipart_body(image_path, purpose)

        req = urllib.request.Request(url, data=body, method='POST', headers={
            'Authorization': 'Bearer ' + key,
            'Content-Type': ctype,
            'Content-Length': str(len(body)),
            'Accept': 'application/json',
        })

        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8', errors='replace')[:300]
            hints = {
                400: '文件无法解析或格式不支持',
                401: 'API Key 无效',
                402: '账户余额不足',
                408: '上传超时',
                413: '文件超过 100 MiB',
                429: '并发识别数超过 15 个，稍后重试',
                500: '服务端处理失败',
                503: '服务繁忙，请稍后重试',
                504: '识别超时（上限 180 秒）',
            }
            raise RuntimeError(f'OCR 接口返回 {e.code}：{hints.get(e.code, detail)}') from e

        try:
            data = json.loads(raw.strip() or '{}')
        except json.JSONDecodeError as e:
            raise RuntimeError(f'OCR 返回无法解析：{raw[:120]}') from e

        if 'error' in data:
            msg = (data.get('error') or {}).get('message', '未知错误')
            raise RuntimeError(f'OCR 识别失败：{msg}')

        pages = data.get('pages') or []
        if not pages:
            raise RuntimeError('OCR 没有返回任何页面')

        texts = [(p.get('text') or '').strip() for p in pages]
        if len(texts) == 1:
            return texts[0]
        return '\n\n'.join(f'第{i + 1}页:\n{t}' for i, t in enumerate(texts))

    @classmethod
    def _process_with_deepseek(cls, image_path, cfg):
        """云端 OCR 的单个文件处理，返回与 Tesseract 一致的字典。"""
        path = Path(image_path)
        try:
            if not path.exists():
                raise FileNotFoundError(f'图片不存在: {path}')
            text = cls._ocr_deepseek(path, cfg)
            return {
                'image_path': str(path),
                'text': text if text else '图片未能识别出文字',
                'confidence': None,
            }
        except Exception as e:
            logging.error(f"云端 OCR 失败: {e}")
            return {
                'image_path': str(path),
                'text': f'图片处理错误: {e}',
                'confidence': 0,
            }

    @classmethod
    def backend(cls):
        """当前使用的 OCR 后端名，供自检和界面显示。"""
        return (load_ocr_config().get('ocr_provider') or 'tesseract').strip().lower()

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
        # 选择后端：配置里写 deepseek 就走云端，否则走本地 Tesseract
        cfg = load_ocr_config()
        provider = (cfg.get('ocr_provider') or 'tesseract').strip().lower()

        if provider == 'vision':
            return cls._process_with_vision(image_path, cfg)

        if provider == 'deepseek':
            return cls._process_with_deepseek(image_path, cfg)

        if pytesseract is None:
            return {
                'image_path': str(image_path),
                'text': '图片处理错误: 未安装 pytesseract，且 OCR 后端不是 deepseek',
                'confidence': 0,
            }

        # 首次使用时检查Tesseract
        if not hasattr(cls, '_tesseract_checked'):
            cls.check_tesseract()
            cls._tesseract_checked = True

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

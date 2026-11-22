"""运行期配置：存在项目根目录的 config.json，可在界面里修改，改完立即生效。

优先级：config.json > 环境变量(.env) > 内置默认值
这样既支持"界面里填 Key"，也兼容原来的 .env 用法。
"""
import json
import logging
import os
from pathlib import Path

LOGGER = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / 'config.json'

DEFAULTS = {
    # 对话模型
    'provider': 'siliconflow',
    'base_url': 'https://api.siliconflow.cn/v1',
    'model': 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B',
    'api_key': '',
    # 图片识别后端，三选一：
    #   vision    = 用视觉模型看图（复用对话的 Key，走同一份额度）← 默认
    #   deepseek  = DeepSeek 官方 OCR 接口（按页计费，需单独充值）
    #   tesseract = 本地 Tesseract（需安装 exe）
    'ocr_provider': 'vision',
    # 视觉模型：8B 最便宜且够用；要更强可换 Qwen3-VL-30B-A3B / 32B
    'ocr_model': 'Qwen/Qwen3-VL-8B-Instruct',
    # 只有 ocr_provider=deepseek 时才会用到下面两项
    'ocr_base_url': 'https://api.deepseek.com',
    'ocr_api_key': '',
    # deepseek 用：text_recognition 纯文本 / rich_layout_recognition 保留版面
    'ocr_purpose': 'text_recognition',
    # 实测过的模型能力缓存：{"模型id": {"chat": true, "vision": false, "at": 时间戳}}
    'model_caps': {},
}

# 环境变量到配置项的映射（兼容旧的 .env 用法）
ENV_KEYS = {
    'base_url': 'DEEPSEEK_BASE_URL',
    'model': 'DEEPSEEK_MODEL',
    'api_key': 'DEEPSEEK_API_KEY',
    # OCR 可以单独用一个 Key；没设时下面会回退到 DEEPSEEK_API_KEY
    'ocr_api_key': 'DEEPSEEK_OCR_API_KEY',
    'ocr_base_url': 'DEEPSEEK_OCR_BASE_URL',
}

# 允许界面修改的字段及类型
EDITABLE = {
    'provider': str, 'base_url': str, 'model': str, 'api_key': str,
    'ocr_provider': str, 'ocr_model': str, 'ocr_base_url': str,
    'ocr_api_key': str, 'ocr_purpose': str,
}


def load_config():
    """读取配置：文件 > 环境变量 > 默认值。任何异常都退回默认值。"""
    cfg = dict(DEFAULTS)

    # 环境变量先垫一层（文件里的值会覆盖它）
    for field, env_name in ENV_KEYS.items():
        env_val = os.getenv(env_name)
        if env_val:
            cfg[field] = env_val

    # OCR 没单独配 Key 时，只有「对话接口和 OCR 接口在同一域名」才复用对话的 Key。
    # 否则拿硅基流动的 Key 去请求 api.deepseek.com 只会得到 401。
    if not cfg.get('ocr_api_key'):
        from urllib.parse import urlparse
        chat_host = urlparse(cfg.get('base_url') or '').netloc.lower()
        ocr_host = urlparse(cfg.get('ocr_base_url') or '').netloc.lower()
        if chat_host and chat_host == ocr_host:
            cfg['ocr_api_key'] = cfg.get('api_key', '')

    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                for field, value in saved.items():
                    # 空字符串视为未设置，保留下层的环境变量/默认值
                    if value not in (None, ''):
                        cfg[field] = value
    except Exception as e:
        LOGGER.error(f"读取 config.json 失败，使用默认配置: {str(e)}")

    return cfg


def save_config(patch):
    """合并写入 config.json，返回写入后的完整配置。"""
    cfg = load_config()
    for field, caster in EDITABLE.items():
        if field in patch:
            value = patch[field]
            cfg[field] = caster(value).strip() if isinstance(value, str) else caster(value)

    payload = {k: cfg[k] for k in DEFAULTS}
    tmp = CONFIG_FILE.with_suffix('.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_FILE)
    LOGGER.warning("配置已更新（model=%s, base_url=%s）", cfg['model'], cfg['base_url'])
    return cfg


def is_configured():
    """是否已填过 API Key。"""
    return bool(load_config().get('api_key'))


def record_cap(model_id, **caps):
    """记录一次实测结果（如 chat=True / vision=False），供界面显示。"""
    if not model_id:
        return
    import time as _time
    cfg = load_config()
    table = dict(cfg.get('model_caps') or {})
    entry = dict(table.get(model_id) or {})
    entry.update(caps)
    entry['at'] = int(_time.time())
    table[model_id] = entry

    payload = {k: cfg.get(k) for k in DEFAULTS}
    payload['model_caps'] = table
    tmp = CONFIG_FILE.with_suffix('.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_FILE)


def public_config():
    """给前端看的配置：Key 打码，只回显是否已设置。"""
    cfg = load_config()
    key = cfg.get('api_key') or ''
    masked = ''
    if key:
        masked = key[:4] + '*' * max(4, len(key) - 8) + key[-4:] if len(key) > 8 else '*' * len(key)
    ocr_key = cfg.get('ocr_api_key') or ''
    ocr_masked = ''
    if ocr_key:
        ocr_masked = (ocr_key[:4] + '*' * max(4, len(ocr_key) - 8) + ocr_key[-4:]
                      if len(ocr_key) > 8 else '*' * len(ocr_key))

    return {
        'provider': cfg.get('provider', ''),
        'base_url': cfg.get('base_url', ''),
        'model': cfg.get('model', ''),
        'api_key_set': bool(key),
        'api_key_masked': masked,
        'ocr_provider': cfg.get('ocr_provider', ''),
        'ocr_model': cfg.get('ocr_model', ''),
        'ocr_base_url': cfg.get('ocr_base_url', ''),
        'ocr_purpose': cfg.get('ocr_purpose', ''),
        'ocr_api_key_set': bool(ocr_key),
        'ocr_api_key_masked': ocr_masked,
        'model_caps': cfg.get('model_caps') or {},
    }

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
    'provider': 'siliconflow',
    'base_url': 'https://api.siliconflow.cn/v1',
    'model': 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B',
    'api_key': '',
}

# 环境变量到配置项的映射（兼容旧的 .env 用法）
ENV_KEYS = {
    'base_url': 'DEEPSEEK_BASE_URL',
    'model': 'DEEPSEEK_MODEL',
    'api_key': 'DEEPSEEK_API_KEY',
}

# 允许界面修改的字段及类型
EDITABLE = {'provider': str, 'base_url': str, 'model': str, 'api_key': str}


def load_config():
    """读取配置：文件 > 环境变量 > 默认值。任何异常都退回默认值。"""
    cfg = dict(DEFAULTS)

    # 环境变量先垫一层（文件里的值会覆盖它）
    for field, env_name in ENV_KEYS.items():
        env_val = os.getenv(env_name)
        if env_val:
            cfg[field] = env_val

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


def public_config():
    """给前端看的配置：Key 打码，只回显是否已设置。"""
    cfg = load_config()
    key = cfg.get('api_key') or ''
    masked = ''
    if key:
        masked = key[:4] + '*' * max(4, len(key) - 8) + key[-4:] if len(key) > 8 else '*' * len(key)
    return {
        'provider': cfg.get('provider', ''),
        'base_url': cfg.get('base_url', ''),
        'model': cfg.get('model', ''),
        'api_key_set': bool(key),
        'api_key_masked': masked,
    }

from openai import OpenAI
from flask import Response, stream_with_context
import json
import os
from dotenv import load_dotenv
from ..settings_store import load_config

# 加载.env文件中的环境变量（作为 config.json 的兜底）
load_dotenv()

class DeepSeekClient:
    def __init__(self, api_key=None, base_url=None, model=None):
        cfg = load_config()
        self.base_url = base_url or cfg.get('base_url')
        self.model = model or cfg.get('model')
        self.api_key = api_key or cfg.get('api_key')
        if not self.api_key:
            raise ValueError("未配置 API Key：请在 /setup 页面填写，或在 .env 中设置 DEEPSEEK_API_KEY")
        if not self.base_url:
            raise ValueError("未配置 base_url：请在 /setup 页面填写")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.messages = [{"role": "system", "content": "You are a helpful assistant."}]
    
    def add_message(self, role, content):
        """添加对话历史"""
        self.messages.append({"role": role, "content": content
        })
    
    def clear_history(self):
        """清空对话历史"""
        self.messages = [{"role": "system", "content": "You are a helpful assistant."}]
    
    def generate_response(self, stream=False, **kwargs):
        """生成响应（支持流式/非流式）"""
        try:
            # 验证API密钥
            if not self.api_key:
                raise ValueError("DeepSeek API密钥未配置")

            # 验证消息历史
            if not self.messages:
                raise ValueError("对话历史为空")

            # 流式请求要求服务端在最后一个 chunk 里回传 token 用量，
            # 前端用它显示消耗。服务端不支持时该参数会被忽略，不影响正常输出。
            if stream and 'stream_options' not in kwargs:
                kwargs['stream_options'] = {'include_usage': True}

            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=stream,
                **kwargs  # 可扩展参数：temperature, max_tokens等
            )
            return response
        except Exception as e:
            error_msg = str(e)
            if "API key" in error_msg:
                error_msg = "API密钥无效或未正确配置"
            elif "Rate limit" in error_msg:
                error_msg = "请求频率超限，请稍后重试"
            elif "Connection" in error_msg:
                error_msg = "连接服务器失败，请检查网络"
            return {"error": error_msg}

    def stream_response(self, response):
        """流式响应处理"""
        if isinstance(response, dict) and "error" in response:
            yield f"data: {json.dumps({'content': f'错误: {response['error']}', 'error': True})}\n\n"
            yield "data: [DONE]\n\n"
            return
            
        try:
            for chunk in response:
                # usage 只在最后一个 chunk 出现（此时 choices 通常为空）
                usage = getattr(chunk, 'usage', None)
                if usage:
                    yield "data: " + json.dumps({
                        'usage': {
                            'prompt_tokens': getattr(usage, 'prompt_tokens', 0),
                            'completion_tokens': getattr(usage, 'completion_tokens', 0),
                            'total_tokens': getattr(usage, 'total_tokens', 0),
                        }
                    }) + "\n\n"

                if chunk.choices:
                    content = chunk.choices[0].delta.content or ""
                    yield f"data: {json.dumps({'content': content})}\n\n"
            yield "data: [DONE]\n\n" 
        except Exception as e:
            yield f"data: {json.dumps({'content': f'流式输出错误: {str(e)}', 'error': True})}\n\n"
            yield "data: [DONE]\n\n"

    def format_response(self, response):
        """非流式响应处理"""
        if isinstance(response, dict) and "error" in response:
            return response
        try:
            return response.choices[0].message.content
        except Exception as e:
            return {"error": f"格式化响应失败: {str(e)}"}
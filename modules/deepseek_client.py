from openai import OpenAI
from flask import Response, stream_with_context
import json
import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

class DeepSeekClient:
    def __init__(self, model="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B", base_url="https://api.siliconflow.cn/v1"):
        # 只从环境变量获取API密钥
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未提供，请在.env文件中设置DEEPSEEK_API_KEY环境变量")
            
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)
        self.model = model
        self.messages = [{"role": "system", "content": "You are a helpful assistant."}]
    
    def add_message(self, role, content):
        """添加对话历史"""
        self.messages.append({"role": role, "content": content
        })
    
    def generate_response(self, stream=False, **kwargs):
        """生成响应（支持流式/非流式）"""
        try:
            # 验证API密钥
            if not self.api_key:
                raise ValueError("DeepSeek API密钥未配置")

            # 验证消息历史
            if not self.messages:
                raise ValueError("对话历史为空")

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
        for chunk in response:
            if chunk.choices:
                content = chunk.choices[0].delta.content or ""
                yield f"data: {json.dumps({'content': content})}\n\n"
        yield "data: [DONE]\n\n"

    def format_response(self, response):
        """非流式响应处理"""
        if isinstance(response, dict) and "error" in response:
            return response
        return response.choices[0].message.content
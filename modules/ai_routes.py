from flask import Blueprint, request, jsonify, Response, stream_with_context
import os
from dotenv import load_dotenv
from .deepseek_client import DeepSeekClient
import logging

# 加载.env文件中的环境变量
load_dotenv()

ai_bp = Blueprint('ai', __name__)

# 从环境变量获取API密钥检查
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    logging.error("DeepSeek API密钥未配置，请在.env文件中设置DEEPSEEK_API_KEY环境变量")

# 创建DeepSeekClient实例
try:
    client = DeepSeekClient()
    logging.info("DeepSeek客户端初始化成功")
except ValueError as e:
    logging.error(f"DeepSeek客户端初始化失败: {str(e)}")
    client = None

@ai_bp.route('/chat', methods=['POST'])
def chat():
    """
    AI对话接口
    功能：接收用户消息，调用DeepSeek API生成回复
    请求方法：POST
    参数：
        - message: 用户消息
        - stream: 是否使用流式输出 (布尔值，默认False)
    返回：
        - 流式模式：SSE格式的流式响应
        - 非流式模式：JSON格式的完整响应
    """
    # 检查客户端是否正确初始化
    if client is None:
        return jsonify({"error": "AI服务未正确配置，请检查API密钥"}), 500
        
    try:
        data = request.json
        if not data:
            return jsonify({"error": "无效的请求数据"}), 400
            
        user_input = data.get('message')
        if not user_input or not isinstance(user_input, str):
            return jsonify({"error": "消息不能为空"}), 400
            
        stream_mode = data.get('stream', False)
        
        # 获取可选参数
        params = {}
        for param in ['temperature', 'max_tokens', 'top_p', 'frequency_penalty', 'presence_penalty']:
            if param in data:
                params[param] = data[param]
        
        # 添加用户消息到对话历史
        client.add_message("user", user_input)
        
        # 生成响应
        logging.info(f"处理用户消息，流式模式: {stream_mode}")
        response = client.generate_response(stream=stream_mode, **params)
        
        # 错误处理
        if isinstance(response, dict) and "error" in response:
            logging.error(f"AI响应生成失败: {response['error']}")
            return jsonify({"error": response["error"]}), 500
        
        # 流式输出
        if stream_mode:
            def generate():
                for data_chunk in client.stream_response(response):
                    yield data_chunk
                    
            return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
        # 非流式输出
        assistant_response = client.format_response(response)
        client.add_message("assistant", assistant_response)
        logging.info("AI响应生成成功")
        return jsonify({"response": assistant_response})
        
    except Exception as e:
        logging.error(f"处理AI对话请求失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@ai_bp.route('/reset', methods=['POST'])
def reset_conversation():
    """
    重置对话历史接口
    功能：清空当前对话历史，开始新对话
    请求方法：POST
    返回：
        - 成功：重置成功的消息
        - 失败：错误信息
    """
    try:
        if client is None:
            return jsonify({"error": "AI服务未正确配置，请检查API密钥"}), 500
            
        # 重新初始化消息历史
        client.messages = [{"role": "system", "content": "You are a helpful assistant."}]
        logging.info("对话历史已重置")
        
        return jsonify({
            "status": "success",
            "message": "对话历史已重置"
        })
    except Exception as e:
        logging.error(f"重置对话历史失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
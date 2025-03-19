from flask import Blueprint, request, jsonify, Response, stream_with_context
import os
from dotenv import load_dotenv
from .deepseek_client import DeepSeekClient
from .local_model_client import LocalModelClient
import logging
from werkzeug.exceptions import BadRequest
import json
# 加载.env文件中的环境变量
load_dotenv()

ai_bp = Blueprint('ai', __name__)

# 从环境变量获取API密钥检查
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    logging.error("DeepSeek API密钥未配置，请在.env文件中设置DEEPSEEK_API_KEY环境变量")

# 创建AI客户端实例字典
ai_clients = {}

# 初始化DeepSeek在线客户端
try:
    ai_clients['deepseek_api'] = DeepSeekClient()
    logging.info("DeepSeek API客户端初始化成功")
except ValueError as e:
    logging.error(f"DeepSeek API客户端初始化失败: {str(e)}")
    ai_clients['deepseek_api'] = None

# 初始化本地模型客户端
base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 检查本地DeepSeek模型
deepseek_model_path = os.getenv("DEEPSEEK_LOCAL_MODEL_PATH", os.path.join(base_path, "ai_module", "DeepSeek-R1-Distill-Qwen-1.5B"))
if os.path.exists(deepseek_model_path):
    try:
        ai_clients['deepseek'] = LocalModelClient(model_type="deepseek", model_path=deepseek_model_path)
        logging.info(f"本地DeepSeek模型初始化成功: {deepseek_model_path}")
    except Exception as e:
        logging.error(f"本地DeepSeek模型初始化失败: {str(e)}")
        ai_clients['deepseek'] = None
else:
    logging.error(f"本地DeepSeek模型路径不存在: {deepseek_model_path}")
    ai_clients['deepseek'] = None

# 检查本地Qwen模型
qwen_model_path = os.getenv("QWEN_LOCAL_MODEL_PATH", os.path.join(base_path, "ai_module", "Qwen1.5-0.5B-Chat"))
if os.path.exists(qwen_model_path):
    try:
        ai_clients['qwen'] = LocalModelClient(model_type="qwen", model_path=qwen_model_path)
        logging.info(f"本地Qwen模型初始化成功: {qwen_model_path}")
    except Exception as e:
        logging.error(f"本地Qwen模型初始化失败: {str(e)}")
        ai_clients['qwen'] = None
else:
    logging.error(f"本地Qwen模型路径不存在: {qwen_model_path}")
    ai_clients['qwen'] = None

# 检查网络连接状态，决定默认模型
import socket

def check_internet_connection():
    try:
        # 尝试连接到一个常用的网站，超时设为1秒
        socket.create_connection(("www.baidu.com", 443), timeout=1)
        return True
    except (socket.timeout, socket.error):
        return False

# 根据网络状态和可用模型设置默认模型
if check_internet_connection() and ai_clients['deepseek_api'] is not None:
    default_model = 'deepseek_api'
    logging.info("网络连接正常，默认使用DeepSeek API模型")
elif ai_clients['deepseek'] is not None:
    default_model = 'deepseek'
    logging.info("使用本地DeepSeek模型作为默认模型")
elif ai_clients['qwen'] is not None:
    default_model = 'qwen'
    logging.info("使用本地Qwen模型作为默认模型")
else:
    # 如果所有模型都不可用，则提供明确的错误信息
    logging.error("所有AI模型都未正确配置，无法提供AI对话服务")
    default_model = None

@ai_bp.route('/models', methods=['GET'])
def get_available_models():
    """
    获取可用模型列表接口
    功能：返回当前可用的所有AI模型
    请求方法：GET
    返回：
        - 可用模型列表及其状态
    """
    available_models = {}
    
    for model_name, client in ai_clients.items():
        available_models[model_name] = {
            "available": client is not None,
            "default": model_name == default_model
        }
    
    return jsonify({
        "models": available_models,
        "default_model": default_model
    })

@ai_bp.route('/chat', methods=['POST'])
def chat():
    """
    AI对话接口
    功能：接收用户消息，调用AI模型生成回复
    请求方法：POST
    参数：
        - message: 用户消息
        - stream: 是否使用流式输出 (布尔值，默认False)
        - model: 使用的模型 (字符串，可选值: 'deepseek_api', 'deepseek', 'qwen'，默认为'deepseek_api')
    返回：
        - 流式模式：SSE格式的流式响应
        - 非流式模式：JSON格式的完整响应
    """
    try:
        # 检查请求数据是否为JSON格式
        if not request.is_json:
            return jsonify({"error": "无效的请求数据"}), 400
            
        try:
            data = request.get_json()
        except BadRequest:
            return jsonify({"error": "无效的请求数据"}), 400
            
        if not data:
            return jsonify({"error": "无效的请求数据"}), 400
        
        # 获取请求的模型名称，始终尊重用户的选择
        model_name = data.get('model', default_model)
        
        # 检查模型是否存在
        if model_name not in ai_clients:
            return jsonify({"error": f"不支持的模型: {model_name}"}), 400
        
        # 获取对应的客户端
        client = ai_clients[model_name]
        
        # 检查客户端是否正确初始化
        if client is None:
            return jsonify({"error": f"{model_name}模型服务未正确配置"}), 500
            
        user_input = data.get('message')
        if not user_input or not isinstance(user_input, str):
            return jsonify({"error": "消息不能为空"}), 400
            
        stream_mode = data.get('stream', False)
        
        # 获取可选参数
        params = {}
        for param in ['temperature', 'max_tokens', 'top_p', 'frequency_penalty', 'presence_penalty', 'repetition_penalty']:
            if param in data:
                params[param] = data[param]
        
        # 添加用户消息到对话历史
        client.add_message("user", user_input)
        
        # 生成响应
        logging.info(f"处理用户消息，使用模型: {model_name}，流式模式: {stream_mode}")
        response = client.generate_response(stream=stream_mode, **params)
        
        # 错误处理
        if isinstance(response, dict) and "error" in response:
            logging.error(f"AI响应生成失败: {response['error']}")
            return jsonify({"error": response["error"]}), 500
        
        # 流式输出
        if stream_mode:
            def generate():
                try:
                    for data_chunk in client.stream_response(response):
                        yield data_chunk
                except Exception as e:
                    logging.error(f"流式响应处理失败: {str(e)}")
                    yield f"data: {json.dumps({'content': f'流式输出错误: {str(e)}', 'error': True})}\n\n"
                    yield "data: [DONE]\n\n"
                    
            return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
        # 非流式输出
        try:
            assistant_response = client.format_response(response)
            client.add_message("assistant", assistant_response)
            logging.info("AI响应生成成功")
            return jsonify({"response": assistant_response})
        except Exception as e:
            logging.error(f"格式化AI响应失败: {str(e)}")
            return jsonify({"error": f"处理AI响应失败: {str(e)}"}), 500
        
    except Exception as e:
        logging.error(f"处理AI对话请求失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@ai_bp.route('/reset', methods=['POST'])
def reset_conversation():
    """
    重置对话历史接口
    功能：清空当前对话历史，开始新对话
    请求方法：POST
    参数：
        - model: 要重置的模型 (字符串，可选值: 'deepseek_api', 'deepseek', 'qwen'，默认为'deepseek_api')
    返回：
        - 成功：重置成功的消息
        - 失败：错误信息
    """
    try:
        # 检查请求数据是否为JSON格式
        if request.is_json:
            data = request.get_json()
            # 始终尊重用户的模型选择
            model_name = data.get('model', default_model)
        else:
            model_name = default_model
            
        # 检查模型是否存在
        if model_name not in ai_clients:
            return jsonify({"error": f"不支持的模型: {model_name}"}), 400
            
        # 获取对应的客户端
        client = ai_clients[model_name]
            
        if client is None:
            return jsonify({"error": f"{model_name}模型服务未正确配置"}), 500
            
        # 重新初始化消息历史
        if hasattr(client, 'messages'):
            # DeepSeekClient使用messages属性
            client.messages = [{
                "role": "system", 
                "content": "You are a helpful assistant."
            }]
        else:
            # LocalModelClient使用clear_history方法
            client.clear_history()
            
        logging.info(f"{model_name}模型对话历史已重置")
        
        return jsonify({
            "status": "success",
            "message": f"{model_name}模型对话历史已重置"
        })
    except Exception as e:
        logging.error(f"重置对话历史失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@ai_bp.route('/analyze', methods=['POST'])
def analyze_file():
    """
    文件分析接口
    功能：接收用户上传的文件内容和指令，调用AI模型进行分析
    请求方法：POST
    参数：
        - content: 用户指令/问题
        - file_content: 文件内容（文本）
        - model: 使用的模型 (字符串，可选值: 'deepseek_api', 'deepseek', 'qwen'，默认为'deepseek_api')
        - stream: 是否使用流式输出 (布尔值，默认True)
    返回：
        - 流式模式：SSE格式的流式响应
        - 非流式模式：JSON格式的完整响应
    """
    try:
        # 检查请求数据是否为JSON格式
        if not request.is_json:
            return jsonify({"error": "无效的请求数据"}), 400
            
        try:
            data = request.get_json()
        except BadRequest:
            return jsonify({"error": "无效的请求数据"}), 400
            
        if not data:
            return jsonify({"error": "无效的请求数据"}), 400
        
        # 获取请求的模型名称，始终尊重用户的选择
        model_name = data.get('model', default_model)
        
        # 检查模型是否存在
        if model_name not in ai_clients:
            return jsonify({"error": f"不支持的模型: {model_name}"}), 400
        
        # 获取对应的客户端
        client = ai_clients[model_name]
        
        # 检查客户端是否正确初始化
        if client is None:
            return jsonify({"error": f"{model_name}模型服务未正确配置"}), 500
            
        # 获取用户指令和文件内容
        user_instruction = data.get('content', '')
        file_content = data.get('file_content', '')
        
        if not file_content:
            return jsonify({"error": "文件内容为空"}), 400
            
        # 构建完整的提示信息
        if user_instruction:
            prompt = f"以下是文件内容：\n\n{file_content}\n\n用户指令：{user_instruction}"
        else:
            prompt = f"以下是文件内容，请分析并提供摘要：\n\n{file_content}"
            
        # 默认使用流式输出
        stream_mode = data.get('stream', True)
        
        # 获取可选参数
        params = {}
        for param in ['temperature', 'max_tokens', 'top_p', 'frequency_penalty', 'presence_penalty', 'repetition_penalty']:
            if param in data:
                params[param] = data[param]
        
        # 添加用户消息到对话历史
        client.add_message("user", prompt)
        
        # 生成响应
        logging.info(f"处理文件分析请求，使用模型: {model_name}，流式模式: {stream_mode}")
        response = client.generate_response(stream=stream_mode, **params)
        
        # 错误处理
        if isinstance(response, dict) and "error" in response:
            logging.error(f"AI响应生成失败: {response['error']}")
            return jsonify({"error": response["error"]}), 500
        
        # 流式输出
        if stream_mode:
            def generate():
                try:
                    for data_chunk in client.stream_response(response):
                        yield data_chunk
                except Exception as e:
                    logging.error(f"流式响应处理失败: {str(e)}")
                    yield f"data: {json.dumps({'content': f'流式输出错误: {str(e)}', 'error': True})}\n\n"
                    yield "data: [DONE]\n\n"
                    
            return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
        # 非流式输出
        try:
            assistant_response = client.format_response(response)
            client.add_message("assistant", assistant_response)
            logging.info("AI文件分析响应生成成功")
            return jsonify({"response": assistant_response})
        except Exception as e:
            logging.error(f"格式化AI响应失败: {str(e)}")
            return jsonify({"error": f"处理AI响应失败: {str(e)}"}), 500
        
    except Exception as e:
        logging.error(f"处理文件分析请求失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

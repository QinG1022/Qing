from flask import Blueprint, request, jsonify, Response, stream_with_context, session
import os
from dotenv import load_dotenv
from .deepseek_client import DeepSeekClient
from .local_model_client import LocalModelClient
import logging
from werkzeug.exceptions import BadRequest
import json
import warnings
from flask_login import current_user
from ..database import add_chat_message, get_user_chat_history, clear_user_chat_history
import uuid
from datetime import datetime

# 设置更高的日志级别，抑制不必要的日志
logging.getLogger('accelerate').setLevel(logging.ERROR)  # 将accelerate的日志级别设为ERROR
logging.getLogger('transformers').setLevel(logging.ERROR)  # 同时抑制transformers的日志
logging.getLogger('modules.ai_chat').setLevel(logging.WARNING)  # 将ai_chat的日志级别设为WARNING

# 抑制特定的警告信息
warnings.filterwarnings("ignore", message="Sliding Window Attention is enabled")
warnings.filterwarnings("ignore", message="Some parameters are on the meta device")
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
        - conversation_id: 对话ID (字符串，可选，用于区分不同对话)
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
            # 尝试使用其他可用的模型作为回退
            for backup_name, backup_client in ai_clients.items():
                if backup_client is not None:
                    client = backup_client
                    model_name = backup_name
                    logging.warning(f"模型 {model_name} 不可用，回退到 {backup_name}")
                    break
            
            # 如果没有可用的模型，返回错误
            if client is None:
                return jsonify({"error": f"所有AI模型都未正确配置"}), 500
            
        user_input = data.get('message')
        if not user_input or not isinstance(user_input, str):
            return jsonify({"error": "消息不能为空"}), 400
            
        stream_mode = data.get('stream', False)
        
        # 获取或生成对话ID
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        # 获取可选参数
        params = {}
        for param in ['temperature', 'max_tokens', 'top_p', 'frequency_penalty', 'presence_penalty', 'repetition_penalty']:
            if param in data:
                params[param] = data[param]
        
        # 添加用户消息到对话历史
        client.add_message("user", user_input)
        
        # 如果用户已登录，保存消息到数据库
        if current_user.is_authenticated:
            add_chat_message("user", user_input, model_name, conversation_id, current_user.id)
        
        # 生成响应
        logging.info(f"处理用户消息，使用模型: {model_name}，流式模式: {stream_mode}")
        response = client.generate_response(stream=stream_mode, **params)
        
        # 错误处理
        if isinstance(response, dict) and "error" in response:
            logging.error(f"AI响应生成失败: {response['error']}")
            # 尝试使用简单响应替代
            backup_response = {"response": f"抱歉，AI生成回复时遇到问题: {response['error']}。请重试或联系管理员。", "conversation_id": conversation_id}
            return jsonify(backup_response), 200
        
        # 流式输出
        if stream_mode:
            def generate():
                try:
                    full_response = ""
                    # 先发送会话ID，方便前端保存
                    yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"
                    
                    for data_chunk in client.stream_response(response):
                        yield data_chunk
                        
                        # 尝试提取内容以收集完整响应
                        try:
                            chunk_data = data_chunk.strip()
                            if chunk_data.startswith("data: ") and not chunk_data.endswith("[DONE]"):
                                json_str = chunk_data[5:].strip()
                                if json_str:
                                    parsed = json.loads(json_str)
                                    if "content" in parsed:
                                        full_response += parsed["content"]
                        except Exception as e:
                            logging.warning(f"解析流式响应块失败: {str(e)}")
                            pass
                        
                    # 完成后，如果用户已登录，保存助手回复到数据库
                    if current_user.is_authenticated and full_response:
                        add_chat_message("assistant", full_response, model_name, conversation_id, current_user.id)
                        
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logging.error(f"流式响应处理失败: {str(e)}")
                    # 发送错误信息，但确保它能被前端正确处理
                    yield f"data: {json.dumps({'content': f'流式输出错误: {str(e)}', 'error': True})}\n\n"
                    yield "data: [DONE]\n\n"
                    
            return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
        # 非流式输出
        try:
            assistant_response = client.format_response(response)
            client.add_message("assistant", assistant_response)
            
            # 如果用户已登录，保存助手回复到数据库
            if current_user.is_authenticated:
                add_chat_message("assistant", assistant_response, model_name, conversation_id, current_user.id)
                
            logging.info("AI响应生成成功")
            return jsonify({
                "response": assistant_response,
                "conversation_id": conversation_id
            })
        except Exception as e:
            logging.error(f"格式化AI响应失败: {str(e)}")
            # 尝试返回简单的错误响应，而不是HTTP错误
            return jsonify({
                "response": f"抱歉，处理AI响应时遇到问题: {str(e)}。请重试或联系管理员。",
                "conversation_id": conversation_id,
                "error": str(e)
            })
        
    except Exception as e:
        logging.error(f"处理AI对话请求失败: {str(e)}", exc_info=True)
        # 尝试返回简单的错误响应，而不是HTTP错误
        return jsonify({
            "response": f"抱歉，处理您的请求时遇到问题: {str(e)}。请重试或联系管理员。",
            "error": str(e)
        })

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
        # 默认使用默认模型
        model_name = default_model
        
        # 安全地尝试解析JSON请求体
        if request.is_json and request.data:
            try:
                data = request.get_json(silent=True) or {}
                if 'model' in data:
                    model_name = data.get('model')
            except Exception as e:
                logging.warning(f"JSON解析失败: {str(e)}")
                # 继续处理，使用默认值
            
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
            if data is None:
                return jsonify({"error": "无效的请求数据"}), 400
        except BadRequest as e:
            logging.error(f"无效的JSON数据: {str(e)}")
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
            # 尝试使用其他可用的模型作为回退
            for backup_name, backup_client in ai_clients.items():
                if backup_client is not None:
                    client = backup_client
                    model_name = backup_name
                    logging.warning(f"模型 {model_name} 不可用，回退到 {backup_name}")
                    break
            
            # 如果没有可用的模型，返回错误
            if client is None:
                return jsonify({"error": f"所有AI模型都未正确配置"}), 500
            
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
        
        # 获取或生成对话ID
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        # 获取可选参数
        params = {}
        for param in ['temperature', 'max_tokens', 'top_p', 'frequency_penalty', 'presence_penalty', 'repetition_penalty']:
            if param in data:
                params[param] = data[param]
        
        # 添加用户消息到对话历史
        client.add_message("user", prompt)
        
        # 如果用户已登录，保存消息到数据库
        if current_user.is_authenticated:
            add_chat_message("user", prompt, model_name, conversation_id, current_user.id)
        
        # 生成响应
        logging.info(f"处理文件分析请求，使用模型: {model_name}，流式模式: {stream_mode}")
        response = client.generate_response(stream=stream_mode, **params)
        
        # 错误处理
        if isinstance(response, dict) and "error" in response:
            logging.error(f"AI响应生成失败: {response['error']}")
            # 尝试使用简单响应替代
            backup_response = {"response": f"抱歉，AI分析文件时遇到问题: {response['error']}。请重试或联系管理员。", "conversation_id": conversation_id}
            return jsonify(backup_response), 200
        
        # 流式输出
        if stream_mode:
            def generate():
                try:
                    full_response = ""
                    # 先发送会话ID，方便前端保存
                    yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"
                    
                    for data_chunk in client.stream_response(response):
                        yield data_chunk
                        
                        # 尝试提取内容以收集完整响应
                        try:
                            chunk_data = data_chunk.strip()
                            if chunk_data.startswith("data: ") and not chunk_data.endswith("[DONE]"):
                                json_str = chunk_data[5:].strip()
                                if json_str:
                                    parsed = json.loads(json_str)
                                    if "content" in parsed:
                                        full_response += parsed["content"]
                        except Exception as e:
                            logging.warning(f"解析流式响应块失败: {str(e)}")
                            pass
                        
                    # 完成后，如果用户已登录，保存助手回复到数据库
                    if current_user.is_authenticated and full_response:
                        add_chat_message("assistant", full_response, model_name, conversation_id, current_user.id)
                        
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logging.error(f"流式响应处理失败: {str(e)}")
                    # 发送错误信息，但确保它能被前端正确处理
                    yield f"data: {json.dumps({'content': f'流式输出错误: {str(e)}', 'error': True})}\n\n"
                    yield "data: [DONE]\n\n"
                    
            return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
        # 非流式输出
        try:
            assistant_response = client.format_response(response)
            client.add_message("assistant", assistant_response)
            
            # 如果用户已登录，保存助手回复到数据库
            if current_user.is_authenticated:
                add_chat_message("assistant", assistant_response, model_name, conversation_id, current_user.id)
                
            logging.info("AI文件分析响应生成成功")
            return jsonify({
                "response": assistant_response,
                "conversation_id": conversation_id
            })
        except Exception as e:
            logging.error(f"格式化AI响应失败: {str(e)}")
            # 尝试返回简单的错误响应，而不是HTTP错误
            return jsonify({
                "response": f"抱歉，处理AI响应时遇到问题: {str(e)}。请重试或联系管理员。",
                "conversation_id": conversation_id,
                "error": str(e)
            })
        
    except Exception as e:
        logging.error(f"处理文件分析请求失败: {str(e)}", exc_info=True)
        # 尝试返回简单的错误响应，而不是HTTP错误
        return jsonify({
            "response": f"抱歉，处理您的请求时遇到问题: {str(e)}。请重试或联系管理员。",
            "error": str(e)
        })

@ai_bp.route('/history', methods=['GET'])
def get_chat_history():
    """
    获取对话历史记录接口
    功能：获取当前用户的对话历史记录
    请求方法：GET
    参数：
        - conversation_id: 对话ID (字符串，可选，用于获取指定对话的历史记录)
    返回：
        - 对话历史记录列表
    """
    try:
        # 检查用户是否已登录
        if not current_user.is_authenticated:
            return jsonify({"error": "未登录用户无法获取对话历史"}), 401
            
        # 获取请求参数
        conversation_id = request.args.get('conversation_id')
        
        # 获取用户的对话历史记录
        history = get_user_chat_history(current_user.id, conversation_id)
        
        return jsonify({
            "history": history,
            "conversation_id": conversation_id or "all"
        })
    except Exception as e:
        logging.error(f"获取对话历史记录失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@ai_bp.route('/history/clear', methods=['POST'])
def clear_chat_history():
    """
    清空对话历史记录接口
    功能：清空当前用户的对话历史记录
    请求方法：POST
    参数：
        - conversation_id: 对话ID (字符串，可选，用于清空指定对话的历史记录)
    返回：
        - 成功：清空成功的消息
        - 失败：错误信息
    """
    try:
        # 检查用户是否已登录
        if not current_user.is_authenticated:
            return jsonify({"error": "未登录用户无法清空对话历史"}), 401
            
        # 获取请求参数
        conversation_id = None
        
        # 安全地尝试解析JSON请求体
        if request.is_json and request.data:
            try:
                data = request.get_json(silent=True) or {}
                conversation_id = data.get('conversation_id')
            except Exception as e:
                logging.warning(f"JSON解析失败: {str(e)}")
                # 继续处理，使用默认值None
            
        # 清空用户的对话历史记录
        success = clear_user_chat_history(current_user.id, conversation_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "对话历史记录已清空"
            })
        else:
            return jsonify({"error": "清空对话历史记录失败"}), 500
    except Exception as e:
        logging.error(f"清空对话历史记录失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

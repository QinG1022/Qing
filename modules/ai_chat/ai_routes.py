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
from ..database import add_chat_message, get_user_chat_history, clear_user_chat_history, get_user_conversations
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
# 测试时跳过模型加载
if os.getenv("SKIP_MODEL_LOADING") != "True":
    # 初始化DeepSeek在线客户端
    try:
        ai_clients['deepseek_api'] = DeepSeekClient()
        logging.warning("DeepSeek API客户端初始化成功")
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
        - session_id: 会话ID (字符串，可选，用于区分不同浏览器会话)
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
            return jsonify({"error": "无效的 JSON 数据"}), 400
        
        # 获取会话ID，用于区分不同浏览器会话
        session_id = data.get('session_id')
        
        # 如果会话ID变化，可能是浏览器刷新或重新访问
        current_session_id = session.get('chat_session_id')
        if session_id and current_session_id != session_id:
            # 会话ID变化，记录新会话ID
            session['chat_session_id'] = session_id
            # 重置所有模型的对话上下文
            for model_key, model_client in ai_clients.items():
                if model_client is not None:
                    try:
                        if hasattr(model_client, 'clear_history'):
                            model_client.clear_history()
                        elif hasattr(model_client, 'messages'):
                            model_client.messages = [{"role": "system", "content": "You are a helpful assistant."}]
                    except Exception as e:
                        logging.warning(f"重置{model_key}模型会话失败: {str(e)}")
            
            logging.info(f"检测到新会话ID: {session_id}，已重置所有模型会话")
        
        # 获取模型名称，如果未指定，则使用默认模型
        model_name = data.get('model', default_model)
        if model_name not in ai_clients:
            return jsonify({"error": f"不支持的模型: {model_name}"}), 400
        
        # 获取对应的客户端
        client = ai_clients.get(model_name)
        if client is None:
            logging.warning(f"请求的模型 '{model_name}' 未正确初始化或不可用。")
            # 可以尝试回退到默认模型或其他可用模型
            if default_model and ai_clients.get(default_model):
                 model_name = default_model
                 client = ai_clients[default_model]
                 logging.warning(f"回退到默认模型: {model_name}")
            else:
                 return jsonify({"error": f"模型 '{model_name}' 不可用且无备选模型。"}), 500
            
        user_input = data.get('message')
        if not user_input or not isinstance(user_input, str) or user_input.strip() == "":
            return jsonify({"error": "消息不能为空"}), 400
        user_input = user_input.strip() # 清理空格  

        stream_mode = data.get('stream', False)
        
        # 获取或生成对话ID
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        # 获取可选参数
        params = {}
        for param_key, client_key in [
            ('temperature', 'temperature'),
            ('max_tokens', 'max_tokens'), # generate_response 会内部转为 max_new_tokens
            ('top_p', 'top_p'),
            ('frequency_penalty', 'frequency_penalty'), # DeepSeek 支持
            ('presence_penalty', 'presence_penalty'),   # DeepSeek 支持
            ('repetition_penalty', 'repetition_penalty') # LocalModelClient 支持
        ]:
            if param_key in data:
                params[client_key] = data[param_key]
        
        # 添加用户消息到对话历史
        client.add_message("user", user_input)
        
        # 如果用户已登录，保存消息到数据库
        if current_user.is_authenticated:
            add_chat_message("user", user_input, model_name, conversation_id, current_user.id)
        
        # 生成响应
        logging.info(f"调用模型 '{model_name}' (会话: {conversation_id}) 生成响应，流式: {stream_mode}")
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
                    full_response_content = ""
                    stream_interrupted = False
                    conversation_id_sent = False
                    # 先发送会话ID，方便前端保存
                    if not conversation_id_sent:
                        yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"
                        conversation_id_sent = True
                    
                    try:
                        for data_chunk in client.stream_response(response):
                            yield data_chunk
                            
                            # 尝试提取内容以收集完整响应
                            try:
                                chunk_data = data_chunk.strip()
                                if chunk_data.startswith("data: ") and not chunk_data.endswith("[DONE]"):
                                    json_str = chunk_data[5:].strip()
                                    if json_str:
                                        parsed = json.loads(json_str)
                                        if not conversation_id_sent and parsed.get('conversation_id'):
                                            current_conversation_id = parsed['conversation_id']
                                            conversation_id_sent = True
                                            continue
                                        if "content" in parsed and not parsed.get('error'):
                                            full_response_content += parsed["content"]
                            except json.JSONDecodeError:
                                pass # 忽略无法解析的行（如 [DONE]）
                            except Exception as parse_err:
                                logging.warning(f"解析流式响应块时出错: {parse_err}")
                    except GeneratorExit:
                        # 客户端断开连接，捕获GeneratorExit异常
                        logging.info(f"客户端中断了流式响应连接 (会话: {conversation_id})，停止生成")
                        stream_interrupted = True
                        # 这里不再生成更多内容，也不需要抛出异常
                        return
                        
                    # 流结束后，提取完整内容
                    final_response = full_response_content.strip()
                    logging.info(f"模型 '{model_name}' 流式响应完成。完整内容长度: {len(final_response)}")

                    # 只有在流未被中断且有实际响应内容时，才将助手回复添加到AI客户端历史和数据库
                    if not stream_interrupted and final_response:
                        # 1. 添加到AI客户端的内部历史
                        client.add_message("assistant", final_response)
                        logging.debug(f"已将成功生成的助手响应添加到模型 '{model_name}' 的内部历史 (会话: {conversation_id})")

                        # 2. 如果用户已登录，保存助手回复到数据库
                        if current_user.is_authenticated:
                            add_chat_message("assistant", final_response, model_name, conversation_id, current_user.id)
                            logging.debug(f"已将助手响应保存到数据库 (会话: {conversation_id})")
                    elif stream_interrupted:
                        logging.info(f"流式响应被中断，未添加助手消息到历史或数据库 (会话: {conversation_id})")
                    else:
                        logging.info(f"流式响应为空，未添加助手消息到历史或数据库 (会话: {conversation_id})")
                        
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logging.error(f"流式响应处理失败 (会话: {conversation_id}): {str(e)}", exc_info=True)
                    # 发送错误信息，但确保它能被前端正确处理
                    yield f"data: {json.dumps({'content': f'流式输出错误: {str(e)}', 'error': True})}\n\n"
                    yield "data: [DONE]\n\n"
                    
            return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
        else:
            # 非流式输出
            assistant_response = ""
            is_error = False
            
           # 检查非流式响应的类型和内容
            if isinstance(response, dict) and "error" in response:
                # 情况1：generate_response 直接返回错误字典 (接口调用层错误)
                error_msg = response['error']
                logging.error(f"模型接口 '{model_name}' 返回错误字典: {error_msg}")
                assistant_response = f"抱歉，AI服务暂时遇到问题 ({error_msg})，请稍后再试。"
                is_error = True

            elif isinstance(response, str) and (response.startswith("模型生成失败:") or response.startswith("生成错误:")):
                # 情况2：模型生成过程中内部出错，返回了错误描述字符串
                error_msg = response
                logging.error(f"模型 '{model_name}' 生成时返回错误字符串: {error_msg}")
                assistant_response = "抱歉，AI在生成回复时遇到内部错误，请重试或联系管理员。"
                is_error = True

            elif isinstance(response, str):
                # 情况3：成功获取到模型回复字符串
                assistant_response = response.strip()
                if not assistant_response: # 检查是否为空响应
                     logging.warning(f"模型 '{model_name}' 返回了空响应字符串。")
                     # 可以视为空响应为一种特殊情况，但不一定是错误
                     assistant_response = "[AI未提供响应]" # 或者保持为空
                     # is_error = False # 通常不视为错误
                else:
                     logging.info(f"模型 '{model_name}' 非流式响应生成成功。长度: {len(assistant_response)}")

            else:
                # 情况4：未知的响应类型
                logging.error(f"收到来自模型 '{model_name}' 的未知非流式响应类型: {type(response)}")
                assistant_response = "抱歉，处理AI响应时遇到未知格式问题。"
                is_error = True
                # 可以考虑将这个未知响应信息添加到 client history
                if client and hasattr(client, 'add_message') and \
                   (not client.conversation_history or client.conversation_history[-1]['role'] != 'assistant'):
                    client.add_message("assistant", f"[错误: 未知响应类型 {type(response)}]")


            #仅在非错误且有内容时保存助手回复到数据库 
            should_save_to_db = current_user.is_authenticated and not is_error and assistant_response and assistant_response != "[AI未提供响应]"
            if should_save_to_db:
                 try:
                     add_chat_message("assistant", assistant_response, model_name, conversation_id, current_user.id)
                 except Exception as db_err:
                     logging.error(f"保存助手非流式聊天记录到数据库失败: {db_err}", exc_info=True)

            # 返回 JSON 响应给前端
            response_data = {
                "response": assistant_response,
                "conversation_id": conversation_id
            }
            if is_error:
                response_data["error_occurred"] = True # 加个标志给前端

            return jsonify(response_data)

    except Exception as e:
        logging.error(f"处理 /ai/chat 请求时发生意外错误: {str(e)}", exc_info=True)
        # 返回统一的服务器错误响应
        return jsonify({
            "response": f"抱歉，服务器在处理您的聊天请求时遇到问题。",
            "error": str(e) # 可以考虑不在生产环境暴露具体错误细节
        }), 500

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
        
        # 确保所有模型都调用clear_history方法（如果存在）
        if hasattr(client, 'clear_history'):
            client.clear_history()
            
        # 清除会话中的对话历史
        if 'conversation_history' in session:
            session.pop('conversation_history', None)
            
        # 生成新的会话ID
        session['chat_session_id'] = str(uuid.uuid4())
            
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
        user_instruction = data.get('content', '').strip()
        file_content = data.get('file_content', '')
        
        if not file_content:
            return jsonify({"error": "文件内容为空"}), 400
            
        # 构建完整的提示信息
        if user_instruction:
            prompt = f"请根据以下文件内容和用户指令进行分析。\n\n[文件内容开始]\n{file_content}\n[文件内容结束]\n\n[用户指令]\n{user_instruction}"
        else:
            # 如果没有具体指令，可以给一个默认任务，如总结
            prompt = f"请分析并总结以下文件内容。\n\n[文件内容开始]\n{file_content}\n[文件内容结束]"
            
        # 默认使用流式输出
        stream_mode = data.get('stream', True)
        
        # 获取或生成对话ID
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        # 获取可选参数
        params = {}
        for param_key, client_key in [
            ('temperature', 'temperature'), ('max_tokens', 'max_tokens'), ('top_p', 'top_p'),
            ('frequency_penalty', 'frequency_penalty'), ('presence_penalty', 'presence_penalty'),
            ('repetition_penalty', 'repetition_penalty')
        ]:
            if param_key in data:
                params[client_key] = data[param_key]
        
        # 添加用户消息到对话历史
        client.add_message("user", prompt)
        
        # 如果用户已登录，保存消息到数据库
        if current_user.is_authenticated:
            # 保存一个代表性的记录，而不是整个文件内容
            db_log_content = f"分析文件，指令: {user_instruction}" if user_instruction else "分析文件（无具体指令）"
            db_log_content = (db_log_content[:500] + '...') if len(db_log_content) > 500 else db_log_content
            add_chat_message("user", prompt, model_name, conversation_id, current_user.id)
        
        # 生成响应
        logging.info(f"调用模型 '{model_name}' (会话: {conversation_id}) 分析文件，流式: {stream_mode}")
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
                    full_response_content = ""
                    # 先发送会话ID，方便前端保存
                    yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"
                    
                    try:
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
                                            full_response_content += parsed["content"]
                            except json.JSONDecodeError:
                                pass # 忽略无法解析的行（如 [DONE]）
                            except Exception as parse_err:
                                logging.warning(f"解析流式响应块时出错: {parse_err}")
                    except GeneratorExit:
                        # 客户端断开连接，捕获GeneratorExit异常
                        logging.info(f"客户端中断了流式分析响应连接，停止生成")
                        # 这里不再生成更多内容，也不需要抛出异常
                        return
                    
                    # 流结束后，提取完整内容    
                    final_response = full_response_content.strip()
                    logging.info(f"模型'{model_name}'流式分析响应完成。长度: {len(final_response)}")
                    
                    # 完成后，如果用户已登录，保存助手回复到数据库
                    if current_user.is_authenticated and final_response:
                        add_chat_message("assistant", final_response, model_name, conversation_id, current_user.id)
                        
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logging.error(f"流式响应处理失败: {str(e)}")
                    # 发送错误信息，但确保它能被前端正确处理
                    yield f"data: {json.dumps({'content': f'流式输出错误: {str(e)}', 'error': True})}\n\n"
                    yield "data: [DONE]\n\n"
                    
            return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
        # 非流式输出
        else:
            assistant_response = ""
            is_error = False
            if isinstance(response, dict) and "error" in response:
                error_msg = response['error']
                logging.error(f"分析模型接口 '{model_name}' 返回错误字典: {error_msg}")
                assistant_response = f"抱歉，AI在分析文件时遇到接口问题 ({error_msg})，请稍后再试。"
                is_error = True
            elif isinstance(response, str) and (response.startswith("模型生成失败:") or response.startswith("生成错误:")):
                error_msg = response
                logging.error(f"分析模型 '{model_name}' 生成时返回错误字符串: {error_msg}")
                assistant_response = "抱歉，AI在分析文件时遇到内部错误，请重试。"
                is_error = True
            elif isinstance(response, str):
                assistant_response = response.strip()
                if not assistant_response:
                    logging.warning(f"分析模型 '{model_name}' 返回了空响应。")
                    assistant_response = "[AI未提供分析结果]"
                else:
                    logging.info(f"模型 '{model_name}' 非流式分析响应生成成功。长度: {len(assistant_response)}")
            else:
                logging.error(f"收到来自分析模型 '{model_name}' 的未知非流式响应类型: {type(response)}")
                assistant_response = "抱歉，处理AI分析响应时遇到未知格式问题。"
                is_error = True
                if client and hasattr(client, 'add_message') and \
                   (not client.conversation_history or client.conversation_history[-1]['role'] != 'assistant'):
                     client.add_message("assistant", f"[错误: 未知分析响应类型 {type(response)}]")


            should_save_to_db = current_user.is_authenticated and not is_error and assistant_response and assistant_response != "[AI未提供分析结果]"
            if should_save_to_db:
                 try:
                     add_chat_message("assistant", assistant_response, model_name, conversation_id, current_user.id)
                 except Exception as db_err:
                     logging.error(f"保存助手非流式分析记录到数据库失败: {db_err}", exc_info=True)

            response_data = {
                "response": assistant_response,
                "conversation_id": conversation_id
            }
            if is_error:
                response_data["error_occurred"] = True

            return jsonify(response_data)

    except Exception as e:
        logging.error(f"处理 /ai/analyze 请求时发生意外错误: {str(e)}", exc_info=True)
        return jsonify({
            "response": f"抱歉，服务器在处理文件分析请求时遇到问题。",
            "error": str(e)
        }), 500

@ai_bp.route('/conversations', methods=['GET'])
def get_conversations():
    """
    获取用户对话列表接口
    功能：获取当前用户的所有对话列表
    请求方法：GET
    返回：
        - 对话列表，包含每个对话的ID、开始时间和消息数量
    """
    try:
        # 检查用户是否已登录
        if not current_user.is_authenticated:
            return jsonify({"error": "未登录用户无法获取对话列表"}), 401
            
        # 获取用户的对话列表
        conversations = get_user_conversations(current_user.id)
        
        return jsonify({
            "conversations": conversations
        })
    except Exception as e:
        logging.error(f"获取对话列表失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

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
            "conversation_id": conversation_id
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

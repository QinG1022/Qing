import torch
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread
from typing import Generator, List, Dict, Literal, Optional
import re
import json # 引入json用于stream_response

# 配置日志记录器
# 您可以在 app.py 中统一配置日志，这里只是一个示例
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class LocalModelClient:
    """支持DeepSeek-R1和Qwen1.5双模型的本地对话客户端（优化版）"""

    def __init__(
        self,
        model_type: Literal["deepseek", "qwen"],
        model_path: str,
        device: Optional[str] = None
        ):
        """
        初始化本地模型客户端

        :param model_type: 模型类型 'deepseek' 或 'qwen'
        :param model_path: 模型文件所在的本地路径
        :param device: 指定运行设备 ('cuda:0', 'cpu', etc.)，默认自动检测
        """
        self.logger = logging.getLogger(f"{__name__}.{model_type}") # 为不同模型类型使用不同logger名
        self.model_type = model_type

        # 自动检测设备或使用指定设备
        if device:
            self.device = device
        elif torch.cuda.is_available():
            self.device = "cuda:0"
            try:
                # 尝试打印显卡信息
                props = torch.cuda.get_device_properties(0)
                self.logger.info(f"检测到 CUDA 设备: {props.name}")
                self.logger.info(f"可用显存: {props.total_memory / 1024**3:.2f} GB")
            except Exception as e:
                 self.logger.warning(f"获取CUDA设备信息时出错: {e}")
        else:
            self.device = "cpu"

        self.logger.info(f"模型 '{model_type}' 将在设备 '{self.device.upper()}' 上加载。")

        # 初始化对话历史 (只使用这一个列表)
        self.conversation_history: List[Dict[str, str]] = []
        self.clear_history() # 初始化时就清空并设置系统提示

        # 加载模型和分词器
        try:
            self._load_model(model_path)
            self.logger.info(f"模型 '{model_path}' 加载成功。")
        except Exception as e:
            self.logger.error(f"模型加载失败: {str(e)}", exc_info=True)
            # 抛出运行时错误，以便上层应用可以捕获并处理
            raise RuntimeError(f"模型 '{model_path}' 初始化失败: {str(e)}")

    def _load_model(self, model_path: str):
        """加载指定路径的模型和分词器"""
        self.logger.info(f"正在从 '{model_path}' 加载分词器...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True,
            use_fast=True # 尽可能使用快速分词器以提高效率
        )
        self.logger.info("分词器加载完成。")

        # 特殊处理：Qwen 模型通常需要设置 pad_token
        if self.model_type == "qwen" and self.tokenizer.pad_token is None:
            # 如果没有 pad_token，通常将其设置为 eos_token
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.logger.info("为 Qwen 模型设置 pad_token 为 eos_token。")

        self.logger.info(f"正在从 '{model_path}' 加载模型到 {self.device}...")
        # 根据设备选择合适的数据类型以优化性能和内存使用
        dtype = torch.float16 if "cuda" in self.device else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            trust_remote_code=True,
            torch_dtype=dtype,
            # 自动将模型分片加载到可用设备（GPU/CPU），对多卡或显存不足场景友好
            device_map="auto",
        ).eval() # 将模型设置为评估模式，关闭 dropout 等训练相关层
        self.logger.info("模型加载并设置为评估模式完成。")

    def _format_prompt(self) -> str:
        """使用分词器的聊天模板格式化整个对话历史，生成模型输入"""
        if not self.conversation_history:
            # 确保历史记录不为空，至少包含系统消息
            self.logger.warning("对话历史为空，将重新初始化。")
            self.clear_history()

        # 优先使用 Hugging Face Transformers 推荐的 apply_chat_template 方法
        if hasattr(self.tokenizer, 'apply_chat_template'):
            try:
                # tokenize=False 表示返回格式化后的字符串
                # add_generation_prompt=True 告诉模板在末尾添加提示模型开始生成的标记 (如 '<|im_start|>assistant\n')
                formatted_prompt = self.tokenizer.apply_chat_template(
                    self.conversation_history,
                    tokenize=False,
                    add_generation_prompt=True
                )
                # self.logger.debug(f"使用聊天模板格式化后的Prompt:\n{formatted_prompt}") # Debug 时可以取消注释查看
                return formatted_prompt
            except Exception as e:
                # 如果应用模板失败，记录错误并尝试回退到手动格式化
                self.logger.error(f"应用聊天模板失败: {e}. 将尝试手动格式化。", exc_info=True)
        else:
             # 如果分词器没有实现聊天模板功能
             self.logger.warning("当前分词器不支持 apply_chat_template。正在使用基本的手动格式化（可能不完全准确）。")

        # 手动格式化回退逻辑 (作为备选方案，效果可能不如官方模板)
        prompt = ""
        for msg in self.conversation_history:
            # 简单的 '角色: 内容' 格式
            prompt += f"{msg['role']}: {msg['content']}\n"
        # 手动添加期望模型开始回复的提示符
        prompt += "assistant:"
        return prompt

    def add_message(self, role: str, content: str) -> None:
        """
        向对话历史中添加一条消息。

        :param role: 消息的角色 ('user', 'assistant', 'system')
        :param content: 消息的内容
        """
        # 验证角色是否有效
        if role not in ["user", "assistant", "system"]:
            self.logger.warning(f"尝试添加无效的角色 '{role}'，该消息已被忽略。")
            return
        # 避免添加空消息或只包含空格的消息
        if not content or content.strip() == "":
             self.logger.warning(f"尝试添加来自 '{role}' 的空消息，该消息已被忽略。")
             return

        # 清理内容两端的空格并创建消息字典
        message = {"role": role, "content": content.strip()}
        self.conversation_history.append(message)
        # self.logger.debug(f"消息已添加: {message}") # Debug 时可以取消注释

    def clear_history(self) -> None:
        """清空当前对话历史，并添加默认的系统提示"""
        # 设置默认的系统消息，指导模型的行为
        self.conversation_history = [
            {"role": "system", "content": "You are a helpful assistant."} # 你可以修改这里的系统提示
        ]
        self.logger.info("对话历史已重置，并添加了默认系统提示。")

    def generate_stream(
        self,
        # 注意：query 参数现在是可选的，因为推荐在调用此方法前就使用 add_message 添加用户消息
        query: Optional[str] = None,
        max_new_tokens: int = 1024, # 生成的最大新 token 数量
        temperature: float = 0.6,   # 控制生成文本的随机性，较低值更保守，较高值更多样
        top_p: float = 0.9,         # 控制核心采样的概率阈值
        repetition_penalty: float = 1.1, # 轻微惩罚重复的 token
    ) -> Generator[str, None, None]:
        """
        流式生成模型响应。逐步返回生成的文本块。

        :param query: (不推荐使用) 用户查询。优先使用 add_message 添加。
        :param max_new_tokens: 生成响应的最大长度 (token 数)。
        :param temperature: 控制采样温度。
        :param top_p: 控制核心采样 (nucleus sampling)。
        :param repetition_penalty: 重复惩罚因子。
        :yields: 生成的文本块 (字符串)。
        """
        # 处理兼容性：如果仍然传入了 query 参数
        if query:
             self.logger.warning("generate_stream 收到了 query 参数，但这已不推荐。请在调用前使用 add_message 添加用户消息。")
             self.add_message("user", query)

        try:
            # 格式化包含最新用户消息的完整对话历史
            prompt = self._format_prompt()
            # 将格式化后的文本转换为模型输入张量，并放到正确的设备上
            # padding=True 通常在批处理时需要，但这里为了稳健也加上
            inputs = self.tokenizer(prompt, return_tensors="pt", padding=True).to(self.model.device)

            # 创建文本流式处理器
            streamer = TextIteratorStreamer(
                self.tokenizer,
                skip_prompt=True,      # 不在输出中包含输入的 prompt 部分
                skip_special_tokens=True # 自动跳过模型生成的特殊 token (如 EOS, <|im_end|>)
            )

            # 配置生成参数
            generation_kwargs = dict(
                inputs.data, # 传递 input_ids 和 attention_mask 等
                streamer=streamer,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                # 仅当 temperature > 0 时启用采样，否则使用贪婪解码 (如果模型支持)
                do_sample=temperature > 0,
                # 设置 pad_token_id 为 EOS token ID 是常见做法，防止模型生成 padding token
                pad_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=repetition_penalty
            )

            # 在一个单独的线程中启动模型生成，避免阻塞主线程
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs, daemon=True)
            thread.start()

            # 收集所有生成的文本块
            full_response = ""
            # 从 streamer 中迭代获取生成的文本块
            for new_text in streamer:
                if new_text: # 确保不是空字符串
                    full_response += new_text
                    yield new_text # 实时产生文本块

            # 等待生成线程结束，确保所有内容都已处理完毕
            thread.join(timeout=10) # 设置超时以防线程卡死

            # 清理最终响应的首尾空格
            full_response = full_response.strip()

        except Exception as e:
            # 记录生成过程中发生的任何错误
            self.logger.error(f"流式生成失败: {str(e)}", exc_info=True)
            error_message = f"生成错误: {str(e)}"
            yield error_message # 向调用者（如 Flask 路由）传递错误信息

    def generate(
        self,
        query: Optional[str] = None, # 同样，query 参数不推荐在这里使用
        **kwargs
    ) -> str:
        """
        非流式生成模型响应。一次性返回完整的响应字符串。

        :param query: (不推荐使用) 用户查询。优先使用 add_message 添加。
        :param kwargs: 其他传递给 generate_stream 的参数 (max_new_tokens, temperature 等)。
        :return: 完整的模型响应字符串，或包含错误信息的字符串。
        """
        # 处理兼容性
        if query:
             self.logger.warning("generate 收到了 query 参数，但这已不推荐。请在调用前使用 add_message 添加用户消息。")
             self.add_message("user", query) # 兼容旧调用方式

        try:
            full_response = ""
            # 调用流式生成器并收集所有产生的文本块
            # 不再需要传入 query，因为它应该已经在 history 中了
            for chunk in self.generate_stream(query=None, **kwargs):
                # 检查是否是错误信息块
                if chunk.startswith("生成错误:"):
                     # 如果流式生成内部出错，直接将错误信息作为结果返回
                     self.logger.error(f"非流式生成过程中检测到错误: {chunk}")
                     # 助手错误消息已在 generate_stream 中添加
                     return f"模型生成失败: {chunk[len('生成错误: '):]}" # 返回更清晰的错误描述
                full_response += chunk

            # 助手消息的添加已在 generate_stream 的末尾完成
            return full_response.strip() # 返回清理后的完整响应

        except Exception as e:
            # 捕获在调用 generate_stream 或迭代过程中可能发生的其他错误
            self.logger.error(f"非流式生成失败: {str(e)}", exc_info=True)
            error_msg = f"模型生成失败: {str(e)}"
            # 确保错误也被记录到对话历史中
            if not self.conversation_history or self.conversation_history[-1]['role'] != 'assistant':
                 self.add_message("assistant", f"[错误: {str(e)}]")
            # 返回描述错误的字符串，供上层处理
            return error_msg

    # --- 兼容 ai_routes.py 的接口方法 ---
    # 这些方法是为了尽量减少对 ai_routes.py 的修改

    def generate_response(self, stream=False, **kwargs):
        """
        兼容 ai_routes.py 的接口，用于生成响应（支持流式/非流式）。
        注意：此方法不再直接处理用户消息文本。调用者应确保在调用此方法前，
              已使用 add_message 将用户的最新消息加入对话历史。
        kwargs 可以包含 'temperature', 'max_tokens', 'top_p', 'repetition_penalty' 等。
        """
        # 提取并转换参数名，因为 ai_routes.py 可能使用 'max_tokens'
        params = {}
        if 'temperature' in kwargs:
            params['temperature'] = kwargs['temperature']
        # 将 'max_tokens' (来自 ai_routes) 映射到 'max_new_tokens' (用于 generate_stream/generate)
        if 'max_tokens' in kwargs:
            params['max_new_tokens'] = kwargs['max_tokens']
        if 'top_p' in kwargs:
            params['top_p'] = kwargs['top_p']
        if 'repetition_penalty' in kwargs:
            params['repetition_penalty'] = kwargs['repetition_penalty']

        try:
            if stream:
                # 对于流式请求，返回底层的生成器
                return self.generate_stream(**params)
            else:
                # 对于非流式请求，调用 generate 获取完整响应字符串（或错误字符串）
                return self.generate(**params)
        except Exception as e:
            # 捕获在调用 generate 或 generate_stream 时可能发生的顶层错误
            self.logger.error(f"generate_response 失败: {str(e)}", exc_info=True)
            # 返回 ai_routes.py 期望的错误格式（字典）
            return {"error": f"模型生成响应时发生内部错误: {str(e)}"}

    def stream_response(self, response_generator):
        """
        兼容 ai_routes.py 的接口，处理流式响应生成器。
        将生成器产生的文本块包装成 SSE (Server-Sent Events) 格式发送。
        """
        # 首先检查传入的是否是错误字典 (来自 generate_response 的错误)
        if isinstance(response_generator, dict) and "error" in response_generator:
            yield f"data: {json.dumps({'content': f'错误: {response_generator['error']}', 'error': True})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # 确认传入的是一个可迭代的对象（生成器）
        if not hasattr(response_generator, '__iter__') or not hasattr(response_generator, '__next__'):
             self.logger.error("stream_response 接收到的不是一个有效的生成器。")
             yield f"data: {json.dumps({'content': '内部错误：无效的响应生成器', 'error': True})}\n\n"
             yield "data: [DONE]\n\n"
             return

        try:
            # 迭代从 generate_stream 返回的生成器
            for chunk in response_generator:
                # 检查是否是 generate_stream 内部产生的错误信息
                if chunk.startswith("生成错误:"):
                    error_content = f"流式输出错误: {chunk[len('生成错误: '):]}"
                    yield f"data: {json.dumps({'content': error_content, 'error': True})}\n\n"
                    # 遇到错误后，我们通常也应该结束流
                    yield "data: [DONE]\n\n"
                    return # 提前退出生成器
                else:
                    # 将正常的文本块包装在 SSE 的 data 字段中
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

            # 正常结束后发送 [DONE] 信号
            yield "data: [DONE]\n\n"
        except Exception as e:
            # 捕获在迭代生成器或发送 SSE 时可能发生的错误
            self.logger.error(f"处理流式响应时出错: {str(e)}", exc_info=True)
            # 发送错误信息到前端
            yield f"data: {json.dumps({'content': f'流式处理内部错误: {str(e)}', 'error': True})}\n\n"
            yield "data: [DONE]\n\n" # 即使出错，也发送 DONE 信号

    def format_response(self, response):
        """
        兼容 ai_routes.py 的接口，处理非流式响应。
        在此优化版本中，非流式响应通常是字符串（正常响应或错误描述）。
        此方法主要用于保持接口一致性，实际处理逻辑不多。
        """
        # 如果已经是错误字典 (来自 generate_response)，直接返回
        if isinstance(response, dict) and "error" in response:
            return response
        # 如果是字符串 (可能是正常响应，也可能是 generate 返回的错误字符串)
        elif isinstance(response, str):
            # 可以选择在这里检查字符串是否是错误信息，并转换为字典格式
            # if response.startswith("模型生成失败:"):
            #     return {"error": response}
            # 但为了简化 ai_routes.py 的处理，我们让 ai_routes.py 自己检查字符串内容
            return response
        # 处理未预期的响应类型
        else:
             self.logger.error(f"format_response 收到意外的响应类型: {type(response)}")
             # 返回 ai_routes.py 期望的错误字典格式
             return {"error": f"内部错误：未知的响应格式 {type(response)}"}
        
        # --- 使用示例 (可选，用于本地测试) ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG) # 在测试时使用更详细的日志

    # --- DeepSeek 测试 ---
    try:
        print("\n--- DeepSeek 测试 ---")
        # 请确保将下面的路径替换为你的实际模型路径
        deepseek_path = "../ai_module/DeepSeek-R1-Distill-Qwen-1.5B" # 使用相对路径示例
        deepseek_client = LocalModelClient(model_type="deepseek", model_path=deepseek_path)

        # 第一轮对话
        print("\n用户: 你好，介绍一下自己。")
        deepseek_client.add_message("user", "你好，介绍一下自己。")
        print("助手 (流式): ", end="")
        response_stream = deepseek_client.generate_response(stream=True)
        for chunk in deepseek_client.stream_response(response_stream):
            if chunk.startswith("data: "):
                 try:
                     data = json.loads(chunk[5:])
                     if 'content' in data:
                         print(data['content'], end="", flush=True)
                 except json.JSONDecodeError:
                      pass # 忽略 [DONE] 等非 JSON 数据
        print("\n" + "-"*20)

        # 第二轮对话
        print("用户: 给我讲个关于程序员的笑话。")
        deepseek_client.add_message("user", "给我讲个关于程序员的笑话。")
        print("助手 (非流式):")
        response_full = deepseek_client.generate_response(stream=False)
        if isinstance(response_full, dict) and 'error' in response_full:
             print(f"错误: {response_full['error']}")
        else:
             print(response_full)
        print("\n" + "-"*20)

        # 查看对话历史
        print("当前对话历史:")
        print(json.dumps(deepseek_client.conversation_history, indent=2, ensure_ascii=False))

        # 重置对话
        deepseek_client.clear_history()
        print("\n对话已重置。")
        print("重置后对话历史:")
        print(json.dumps(deepseek_client.conversation_history, indent=2, ensure_ascii=False))

    except RuntimeError as e:
        print(f"DeepSeek 测试失败: {e}")
    except FileNotFoundError:
         print(f"DeepSeek 模型路径未找到: {deepseek_path}. 请检查路径。")

    # --- Qwen 测试 ---
    try:
        print("\n\n--- Qwen 测试 ---")
        # 请确保将下面的路径替换为你的实际模型路径
        qwen_path = "../ai_module/Qwen1.5-0.5B-Chat" # 使用相对路径示例
        qwen_client = LocalModelClient(model_type="qwen", model_path=qwen_path)

        print("\n用户: 推荐一部科幻电影。")
        qwen_client.add_message("user", "推荐一部科幻电影。")
        print("助手 (非流式):")
        response_full = qwen_client.generate_response(stream=False)
        if isinstance(response_full, dict) and 'error' in response_full:
             print(f"错误: {response_full['error']}")
        else:
             print(response_full)
        print("\n" + "-"*20)

        print("用户: 这部电影的主题曲是什么？")
        qwen_client.add_message("user", "这部电影的主题曲是什么？")
        print("助手 (流式): ", end="")
        response_stream = qwen_client.generate_response(stream=True)
        for chunk in qwen_client.stream_response(response_stream):
             if chunk.startswith("data: "):
                 try:
                     data = json.loads(chunk[5:])
                     if 'content' in data:
                         print(data['content'], end="", flush=True)
                 except json.JSONDecodeError:
                     pass
        print("\n" + "-"*20)

        print("当前对话历史:")
        print(json.dumps(qwen_client.conversation_history, indent=2, ensure_ascii=False))

    except RuntimeError as e:
        print(f"Qwen 测试失败: {e}")
    except FileNotFoundError:
         print(f"Qwen 模型路径未找到: {qwen_path}. 请检查路径。")
# local_model_client.py
import torch
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread
from typing import Generator, List, Dict, Literal
import re

class LocalModelClient:
    """支持DeepSeek-R1和Qwen1.5双模型的本地对话客户端"""
    
    def __init__(
        self,
        model_type: Literal["deepseek", "qwen"],
        model_path: str,
        device: str = None
        ):
        """
        初始化本地模型客户端
        
        :param model_type: 模型类型 deepseek/qwen
        :param model_path: 模型本地路径
        :param device: 指定设备 (默认自动检测)
        """
        self.logger = logging.getLogger(__name__)
        self.model_type = model_type

        
    
        self.device = device or ("cuda:0" if torch.cuda.is_available() else "cpu")
        if "cuda" in self.device and not torch.cuda.is_available():
            raise RuntimeError("请求使用CUDA但当前环境不支持GPU加速")
        # 初始化对话历史
        self.conversation_history: List[Dict] = []
        # 添加messages属性以兼容ai_routes.py
        self.messages = []

        print(f"使用的计算设备: {self.device.upper()}")
        print(f"可用显存: {torch.cuda.get_device_properties(0).total_memory/1024**3:.2f}GB")
        # 加载模型
        try:
            self._load_model(model_path)
            self.logger.info(f"{model_type}模型加载成功")
        except Exception as e:
            self.logger.error(f"模型加载失败: {str(e)}")
            raise RuntimeError(f"{model_type}模型初始化失败: {str(e)}")

    def _load_model(self, model_path: str):
        """加载指定类型的模型"""
        
    # 模型加载
        self.tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code=True
        )
        
        # Qwen需要设置pad_token
        if self.model_type == "qwen":
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            trust_remote_code=True,
            torch_dtype=torch.float16 if "cuda" in self.device else torch.float32,
            device_map="auto",
           
        ).eval()

    def _format_prompt(self, query: str = None) -> str:
        """根据模型类型生成prompt模板"""
        if query:
            # 单轮对话处理
            if self.model_type == "deepseek":
                # 检查是否是文件分析请求
                if "以下是文件内容：" in query:
                    return f"<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n<think>\n1. 分析用户提供的文件内容\n2. 理解用户的分析指令\n3. 组织分析结果...\n</think>\n"
                return f"<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n<think>\n1. 分析用户问题：{query}\n2. 确认我的角色：一个专业的AI助手\n3. 组织回答思路...\n<think>\n"
            return self.tokenizer.apply_chat_template(
                [{"role": "user", "content": query}],
                tokenize=False,
                add_generation_prompt=True
            )
        
        # 多轮对话处理
        if self.model_type == "deepseek":
            prompt = ""
            for msg in self.conversation_history:
                if msg["role"] == "system":
                    continue
                prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
            prompt += "<|im_start|>assistant\n<think>\n1. 回顾对话历史\n2. 分析上下文关联\n3. 确保回答的连贯性\n4. 准备组织回复内容\n</think>\n"
            return prompt
        
        return self.tokenizer.apply_chat_template(
            self.conversation_history,
            tokenize=False,
            add_generation_prompt=True
        )

    def add_message(self, role: str, content: str) -> None:
        """添加对话记录"""
        assert role in ["user", "assistant"], "角色必须是user或assistant"
        message = {"role": role, "content": content}
        self.conversation_history.append(message)
        # 同时更新messages属性以兼容ai_routes.py
        self.messages.append(message)
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self.conversation_history.clear()
        # 同时清空messages属性
        self.messages = [{"role": "system", "content": "You are a helpful assistant."}]

    def _clean_output(self, text: str) -> str:
        """清理模型特定标记"""
        if self.model_type == "deepseek":
            text = re.sub(
                r'<\|im_start\|>.*?(<\|im_end\|>|$)|'
                r'<\|im_end\|>\n?|<\|end▁of▁sentence\|>'
                r'<\|end_of_sentence\|>|'
                r'<\|end▁of▁sentence\|>|'
                r'<｜end▁of▁sentence｜>',
                '',
                text,
                flags=re.DOTALL
            )
            text=re.sub(r'\s+',' ',text).strip()
        print("清理后的文本:",text)
        return text

    def generate_stream(
        self,
        query: str = None,
        max_new_tokens: int = 1024,
        temperature: float = 0.5,
        top_p: float = 0.9,
        repetition_penalty: float = 1.0,
    ) -> Generator[str, None, None]:
        """流式生成响应"""
        try:
            if query:
                self.add_message("user", query)
            
            prompt = self._format_prompt()
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            
            streamer = TextIteratorStreamer(
                self.tokenizer,
                skip_prompt=True,
                timeout=60,
                skip_special_tokens=False
            )
            
            generate_kwargs = dict(
                **inputs,
                streamer=streamer,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=repetition_penalty
            )
            
            thread = Thread(target=self.model.generate, kwargs=generate_kwargs)
            thread.start()
            
            buffer = ""
            full_response = ""
            while True:
                try: 
                    new_text = next(streamer)
                    buffer += new_text
                
                # 优先处理完整标记块
                    while "<|im_end|>" in buffer:
                        end_pos = buffer.find("<|im_end|>")
                        completed = buffer[:end_pos]
                        buffer = buffer[end_pos+10:]  # 10是"<|im_end|>"长度
                
                        cleaned = self._clean_output(completed)
                        if cleaned:
                            full_response += cleaned
                            yield cleaned
                    
                    # 处理不包含结束标记的部分
                    cleaned_part = self._clean_output(buffer)
                    if cleaned_part:
                        full_response += cleaned_part
                        yield cleaned_part
                        buffer = ""

                except StopIteration:
                    break
            if buffer.strip():
                cleaned_final = self._clean_output(buffer)
                full_response += cleaned_final
                yield cleaned_final
            
            # 记录最终响应
            self.add_message("assistant", full_response)
            
        except Exception as e:
            self.logger.error(f"生成失败: {str(e)}")
            yield f"生成错误: {str(e)}"

    def generate(self, **kwargs) -> str:
        """非流式生成"""
        try:
            full_response = ""
            for chunk in self.generate_stream(**kwargs):
                full_response += chunk
            return full_response
        except Exception as e:
            self.logger.error(f"生成失败: {str(e)}")
            return {"error": f"模型生成失败: {str(e)}"}
        
    def generate_response(self, stream=False, **kwargs):
        """兼容ai_routes.py的接口，生成响应（支持流式/非流式）"""
        # 参数转换
        params = {}
        if 'temperature' in kwargs:
            params['temperature'] = kwargs['temperature']
        if 'max_tokens' in kwargs:
            params['max_new_tokens'] = kwargs['max_tokens']
        if 'top_p' in kwargs:
            params['top_p'] = kwargs['top_p']
        if 'repetition_penalty' in kwargs:
            params['repetition_penalty'] = kwargs['repetition_penalty']
            
        try:
            # 流式模式直接返回生成器
            if stream:
                return self.generate_stream(**params)
            
            # 非流式模式返回完整响应
            return self.generate(**params)
        except Exception as e:
            self.logger.error(f"生成失败: {str(e)}")
            return {"error": f"模型生成失败: {str(e)}"}
    
    def stream_response(self, response_generator):
        """兼容ai_routes.py的接口，流式响应处理"""
        import json
        
        # 处理错误响应
        if isinstance(response_generator, dict) and "error" in response_generator:
            yield f"data: {json.dumps({'content': f'错误: {response_generator['error']}', 'error': True})}\n\n"
            yield "data: [DONE]\n\n"
            return
            
        try:
            for chunk in response_generator:
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            self.logger.error(f"流式输出错误: {str(e)}")
            yield f"data: {json.dumps({'content': f'流式输出错误: {str(e)}', 'error': True})}\n\n"
            yield "data: [DONE]\n\n"
    
    def format_response(self, response):
        """兼容ai_routes.py的接口，非流式响应处理"""
        if isinstance(response, dict) and "error" in response:
            return response
        return response

# 使用示例
if __name__ == "__main__":
    # DeepSeek示例
    print("DeepSeek测试:")
    deepseek_client = LocalModelClient(
        model_type="deepseek",
        model_path="/path/to/DeepSeek-R1-Distill-Qwen-1.5B"
    )
    for chunk in deepseek_client.generate_stream(query="如何做西红柿炒鸡蛋？"):
        print(chunk, end="", flush=True)
    
    # Qwen示例
    print("\n\nQwen测试:")
    qwen_client = LocalModelClient(
        model_type="qwen",
        model_path="/path/to/Qwen1.5-0.5B-Chat"
    )
    qwen_client.add_message("user", "推荐一部科幻电影")
    qwen_client.add_message("assistant", "《星际穿越》非常经典。")
    qwen_client.add_message("user", "这部电影的主题曲是什么？")
    
    response = qwen_client.generate()
    print(response)
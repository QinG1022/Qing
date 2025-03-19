/**
 * AI对话模块
 * 版本: 1.1
 * 最后更新: 2024-03-15
 * 描述: 提供AI对话功能，包括消息发送、接收和显示
 */

document.addEventListener('DOMContentLoaded', function() {
    const chatInput = document.getElementById('chatInput');
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const chatMessages = document.getElementById('chatMessages');
    const modelSelect = document.getElementById('model-select');
    // 新增文件上传相关元素
    const chatFileInput = document.getElementById('chat-file');
    const fileInfoElement = document.getElementById('fileInfo');
    const uploadStatusElement = document.getElementById('uploadStatus');
    const triggerUploadBtn = document.getElementById('triggerUpload');
    
    let controller = null;
    let currentModel = 'deepseek';  // 默认模型，将在初始化时更新
    // 新增文件内容变量
    let currentFileContent = null;  // 存储上传文件的内容
    
    // 可用的模型信息
    let availableModels = {};
    let defaultModel = null;

    // 初始化 - 获取可用模型信息
    async function initializeModels() {
        try {
            // 显示加载提示
            appendMessage('正在初始化AI模型，请稍候...', false);
            
            const response = await fetch('/ai/models');
            if (!response.ok) {
                throw new Error(`获取模型信息失败：${response.status}`);
            }
            
            const data = await response.json();
            availableModels = data.models;
            defaultModel = data.default_model;
            
            // 清空选择框
            modelSelect.innerHTML = '';
            
            // 更新模型选择框
            for (const [modelName, modelInfo] of Object.entries(availableModels)) {
                const option = document.createElement('option');
                option.value = modelName;
                
                // 设置显示名称
                let displayName;
                switch(modelName) {
                    case 'deepseek_api':
                        displayName = 'DeepSeek API (在线)';
                        break;
                    case 'deepseek':
                        displayName = 'DeepSeek-R1-Distill-Qwen-1.5B (本地)';
                        break;
                    case 'qwen':
                        displayName = 'Qwen1.5-0.5B-Chat (本地)';
                        break;
                    default:
                        displayName = modelName;
                }
                
                option.textContent = displayName;
                
                // 设置可用状态
                if (!modelInfo.available) {
                    option.disabled = true;
                    option.textContent += ' (不可用)';
                }
                
                modelSelect.appendChild(option);
            }
            
            // 设置默认选中的模型
            if (defaultModel && availableModels[defaultModel].available) {
                modelSelect.value = defaultModel;
                currentModel = defaultModel;
            } else {
                // 如果默认模型不可用，选择第一个可用的模型
                for (const [modelName, modelInfo] of Object.entries(availableModels)) {
                    if (modelInfo.available) {
                        modelSelect.value = modelName;
                        currentModel = modelName;
                        break;
                    }
                }
            }
            
            // 清除初始化消息
            chatMessages.innerHTML = '';
            
            // 添加欢迎消息
            appendMessage('您好，我是AI助手，有什么可以帮助您的吗？', false);
            
        } catch (error) {
            console.error('初始化模型失败:', error);
            appendMessage(`初始化AI模型失败: ${error.message}`, false);
        }
    }

    // 处理发送消息
    async function handleSendMessage() {
        const message = chatInput.value.trim();
        if (!message && !currentFileContent) return;

        // 禁用输入和发送按钮
        chatInput.disabled = true;
        sendMessageBtn.disabled = true;

        // 显示用户消息
        appendMessage(message, true);
        
        try {
            // 检查网络连接状态和当前选择的模型
            if (!navigator.onLine && currentModel === 'deepseek_api') {
                throw new Error('网络连接已断开，无法使用DeepSeek API，请切换到本地模型或检查网络后重试');
            }
            
            // 创建新的AbortController
            controller = new AbortController();

            // 获取当前选择的模型
            currentModel = modelSelect.value;
            
            // 确定API端点和请求数据
            let endpoint = '/ai/chat';
            let requestData = {
                message: message,
                stream: true,
                model: currentModel
            };
            
            // 如果有文件内容，使用分析接口
            if (currentFileContent) {
                endpoint = '/ai/analyze';
                requestData = {
                    content: message,
                    file_content: currentFileContent,
                    stream: true,
                    model: currentModel
                };
                
                // 添加文件分析提示
                appendMessage(`正在分析文件内容，请稍候...`, false);
            }
            
            // 发送请求到服务器
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `服务器响应异常(${response.status})`);
            }

            // 创建新的消息div用于流式显示
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ai-message';
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            messageDiv.appendChild(contentDiv);
            chatMessages.appendChild(messageDiv);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let content = '';

            while (true) {
                const {value, done} = await reader.read();
                if (done) break;

                const text = decoder.decode(value);
                const lines = text.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(5);
                        if (data.trim() === '[DONE]') continue;

                        try {
                            const parsed = JSON.parse(data);
                            content += parsed.content;
                            contentDiv.innerHTML = content;
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        } catch (e) {
                            console.error('解析响应数据失败:', e);
                        }
                    }
                }
            }
            
            // 分析完成后清除文件内容
            if (currentFileContent) {
                currentFileContent = null;
                fileInfoElement.textContent = '';
                uploadStatusElement.classList.add('hidden');
                chatFileInput.value = '';
            }
            
        } catch (error) {
            if (error.name === 'AbortError') {
                appendMessage('消息已取消发送', false);
            } else if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                appendMessage('无法连接到服务器，请检查网络连接或稍后重试', false);
            } else {
                appendMessage('发送消息失败: ' + error.message, false);
                console.error('AI对话错误:', error);
            }
        } finally {
            // 清空输入框并重新启用
            chatInput.value = '';
            chatInput.disabled = false;
            sendMessageBtn.disabled = false;
            controller = null;
        }
    }

    // 新增：处理文件上传
    async function handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        // 验证文件类型
        if (!file.name.toLowerCase().endsWith('.txt') && !file.name.toLowerCase().endsWith('.pdf')) {
            appendMessage('仅支持TXT和PDF文件', false);
            chatFileInput.value = '';
            return;
        }
        
        try {
            // 显示文件处理中状态
            appendMessage(`正在处理文件: ${file.name}`, false);
            
            // 显示加载状态
            document.getElementById('loadingOverlay').classList.remove('hidden');
            document.getElementById('loadingText').textContent = '文件处理中...';
            
            // 处理不同类型的文件
            if (file.name.toLowerCase().endsWith('.pdf')) {
                // 使用PDF提取模块处理PDF文件
                const formData = new FormData();
                formData.append('pdfs', file);
                
                const response = await fetch('/extract-pdf', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('PDF处理失败');
                }
                
                const result = await response.json();
                const taskId = result.task_id;
                
                // 轮询任务状态
                let taskComplete = false;
                while (!taskComplete) {
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    const statusResponse = await fetch(`/tasks/${taskId}`);
                    const statusResult = await statusResponse.json();
                    
                    if (statusResult.status === 'SUCCESS') {
                        // 提取PDF文本
                        if (statusResult.result && statusResult.result.results && statusResult.result.results.length > 0) {
                            currentFileContent = statusResult.result.results[0].text;
                            taskComplete = true;
                        }
                    } else if (statusResult.status === 'FAILURE') {
                        throw new Error('PDF处理失败: ' + (statusResult.error || '未知错误'));
                    }
                }
            } else {
                // 处理TXT文件
                currentFileContent = await file.text();
            }
            
            // 隐藏加载状态
            document.getElementById('loadingOverlay').classList.add('hidden');
            
            // 更新UI显示
            fileInfoElement.textContent = `已上传: ${file.name}`;
            uploadStatusElement.classList.remove('hidden');
            appendMessage(`文件 ${file.name} 已上传，请输入分析指令...`, false);
            
        } catch (error) {
            // 隐藏加载状态
            document.getElementById('loadingOverlay').classList.add('hidden');
            
            appendMessage(`文件处理失败: ${error.message}`, false);
            console.error('文件处理错误:', error);
            chatFileInput.value = '';
        }
    }

    // 添加消息到对话框
    function appendMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
        messageDiv.innerHTML = `<div class="message-content">${content}</div>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 绑定事件监听器
    sendMessageBtn.addEventListener('click', handleSendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    
    // 新增：文件上传事件
    if (chatFileInput) {
        chatFileInput.addEventListener('change', handleFileUpload);
    }
    
    // 新增：触发文件上传按钮
    if (triggerUploadBtn) {
        triggerUploadBtn.addEventListener('click', () => {
            chatFileInput.click();
        });
    }

    // 监听模型选择变化
    modelSelect.addEventListener('change', function() {
        currentModel = this.value;
        appendMessage(`已切换到${this.options[this.selectedIndex].textContent}`, false);
    });

    // 初始化模型
    initializeModels();
});
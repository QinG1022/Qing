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
    let controller = null;
    let currentModel = 'deepseek';  // 默认模型，将在初始化时更新
    
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
                if (modelInfo.available) {
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
                    modelSelect.appendChild(option);
                }
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
            let welcomeMsg = `欢迎使用AI对话助手！当前使用的是`;
            switch(currentModel) {
                case 'deepseek_api':
                    welcomeMsg += `DeepSeek API在线模型。`;
                    break;
                case 'deepseek':
                    welcomeMsg += `DeepSeek本地模型。`;
                    break;
                case 'qwen':
                    welcomeMsg += `Qwen本地模型。`;
                    break;
                default:
                    welcomeMsg += `${currentModel}模型。`;
            }
            appendMessage(welcomeMsg, false);
            
        } catch (error) {
            console.error('初始化模型失败:', error);
            appendMessage(`初始化模型失败: ${error.message}`, false);
            
            // 离线模式下默认使用本地模型
            if (!navigator.onLine) {
                updateModelSelectForOffline();
            }
        }
    }
    
    // 离线模式下更新模型选择
    function updateModelSelectForOffline() {
        modelSelect.innerHTML = '';
        
        // 添加本地模型选项
        const deepseekOption = document.createElement('option');
        deepseekOption.value = 'deepseek';
        deepseekOption.textContent = 'DeepSeek-R1-Distill-Qwen-1.5B (本地)';
        modelSelect.appendChild(deepseekOption);
        
        const qwenOption = document.createElement('option');
        qwenOption.value = 'qwen';
        qwenOption.textContent = 'Qwen1.5-0.5B-Chat (本地)';
        modelSelect.appendChild(qwenOption);
        
        // 禁用在线API选项
        const apiOption = document.createElement('option');
        apiOption.value = 'deepseek_api';
        apiOption.textContent = 'DeepSeek API (离线状态不可用)';
        apiOption.disabled = true;
        modelSelect.appendChild(apiOption);
        
        // 默认选择本地模型
        modelSelect.value = 'deepseek';
        currentModel = 'deepseek';
    }

    // 添加消息到对话框
    function appendMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
        messageDiv.innerHTML = `<div class="message-content">${content}</div>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 处理发送消息
    async function handleSendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

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
            
            // 如果是离线状态且用户选择了本地模型，添加提示信息
            if (!navigator.onLine && (currentModel === 'deepseek' || currentModel === 'qwen')) {
                appendMessage(`当前处于离线状态，正在使用本地${currentModel}模型...`, false);
            }

            // 创建新的AbortController
            controller = new AbortController();

            // 获取当前选择的模型
            currentModel = modelSelect.value;
            
            // 发送请求到服务器
            const response = await fetch('/ai/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    stream: true,
                    model: currentModel
                }),
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
                        if (data === '[DONE]') break;

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

    // 绑定发送按钮点击事件
    if (sendMessageBtn) {
        sendMessageBtn.addEventListener('click', handleSendMessage);
    }

    // 绑定输入框回车事件
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });
    }
    
    // 绑定模型切换事件
    if (modelSelect) {
        modelSelect.addEventListener('change', async () => {
            // 获取新选择的模型
            const newModel = modelSelect.value;
            
            // 如果模型发生变化，重置对话历史
            if (newModel !== currentModel) {
                // 检查网络连接状态
                if (!navigator.onLine && newModel === 'deepseek_api') {
                    // 离线状态下不允许切换到DeepSeek API
                    alert('当前处于离线状态，无法使用DeepSeek API，请使用本地模型或等待网络恢复。');
                    // 恢复选择框为之前的模型
                    modelSelect.value = currentModel;
                    return;
                }
                
                currentModel = newModel;
                
                // 清空聊天消息显示
                chatMessages.innerHTML = '';
                
                // 调用重置API
                try {
                    const response = await fetch('/ai/reset', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            model: currentModel
                        })
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({}));
                        console.error('重置对话失败:', errorData.error || `服务器响应异常(${response.status})`);
                        appendMessage(`切换模型失败: ${errorData.error || '服务器响应异常'}`, false);
                        return;
                    }
                } catch (error) {
                    console.error('重置对话请求失败:', error);
                    appendMessage(`切换模型失败: ${error.message || '请求失败'}`, false);
                    return;
                }
                
                // 添加模型切换提示消息
                let modelDisplayName;
                switch(newModel) {
                    case 'deepseek_api':
                        modelDisplayName = 'DeepSeek API (在线)';
                        break;
                    case 'deepseek':
                        modelDisplayName = 'DeepSeek-R1-Distill-Qwen-1.5B (本地)';
                        break;
                    case 'qwen':
                        modelDisplayName = 'Qwen1.5-0.5B-Chat (本地)';
                        break;
                    default:
                        modelDisplayName = newModel;
                }
                appendMessage(`已切换到${modelDisplayName}，开始新的对话。`, false);
            }
        });
        
        // 监听网络状态变化
        window.addEventListener('online', () => {
            // 网络恢复时，重新初始化模型
            initializeModels();
        });
        
        window.addEventListener('offline', () => {
            // 网络断开时，提示用户
            if (currentModel === 'deepseek_api') {
                appendMessage('网络已断开，DeepSeek API无法正常工作。正在切换到本地模型...', false);
                // 自动切换到本地模型
                updateModelSelectForOffline();
            } else {
                appendMessage('网络已断开，当前使用的是本地模型，可以继续使用。', false);
            }
        });
        
        // 初始化模型选择
        initializeModels();
    }
});
/**
 * AI对话模块
 * 版本: 1.2
 * 最后更新: 2024-03-29
 * 描述: 提供AI对话功能，包括消息发送、接收、显示和历史记录管理
 */

document.addEventListener('DOMContentLoaded', function() {
    const chatInput = document.getElementById('userMessage');
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const chatMessages = document.getElementById('chatMessages');
    const modelSelect = document.getElementById('modelSelect');
    const resetChatBtn = document.getElementById('clearChatBtn');
    const newChatBtn = document.getElementById('newChatBtn');
    const conversationHistoryList = document.getElementById('conversationHistoryList');
    const historyListContainer = document.getElementById('historyListContainer');
    // 文件上传相关元素
    const chatFileInput = document.getElementById('docUpload');
    const fileInfoElement = document.getElementById('fileInfo');
    const uploadStatusElement = document.getElementById('uploadStatus');
    const triggerUploadBtn = document.getElementById('docUploadArea');
    // 停止生成按钮
    const stopGenerationBtn = document.getElementById('stopGenerationBtn');
    
    let controller = null;
    let currentModel = 'deepseek';  // 默认模型，将在初始化时更新
    // 文件内容变量
    let currentFileContent = null;  // 存储上传文件的内容
    let currentConversationId = null; // 当前对话ID
    let previousModel = null; // 跟踪上一次使用的模型
    let userLoggedIn = false; // 用户登录状态
    
    // 页面加载时，存储页面会话ID
    const sessionId = Date.now().toString();
    sessionStorage.setItem('chatSessionId', sessionId);
    
    // 可用的模型信息
    let availableModels = {};
    let defaultModel = null;

    // 检查用户登录状态
    async function checkLoginStatus() {
        try {
            const response = await fetch('/api/check-auth');
            const data = await response.json();
            userLoggedIn = data.authenticated;
            
            // 根据登录状态更新UI
            if (userLoggedIn) {
                conversationHistoryList.style.display = 'block';
                newChatBtn.style.display = 'block';
                // 加载对话列表
                await loadConversationList();
            } else {
                conversationHistoryList.style.display = 'none';
                newChatBtn.style.display = 'none';
            }
        } catch (error) {
            console.error('检查登录状态失败:', error);
        }
    }

    // 加载对话列表
    async function loadConversationList() {
        try {
            const response = await fetch('/ai/conversations');
            if (!response.ok) {
                throw new Error(`获取对话列表失败：${response.status}`);
            }
            
            const data = await response.json();
            const conversations = data.conversations;
            
            // 清空列表容器
            historyListContainer.innerHTML = '';
            
            if (conversations.length === 0) {
                // 显示空列表提示
                const emptyMessage = document.createElement('div');
                emptyMessage.className = 'no-history';
                emptyMessage.textContent = '暂无历史对话';
                historyListContainer.appendChild(emptyMessage);
                return;
            }
            
            // 渲染对话列表
            conversations.forEach(conv => {
                const li = document.createElement('li');
                li.setAttribute('data-conversation-id', conv.conversation_id);
                
                // 格式化时间
                const date = new Date(conv.start_time);
                const timeStr = date.toLocaleString();
                
                // 创建对话信息容器
                const infoDiv = document.createElement('div');
                infoDiv.className = 'conversation-info';
                infoDiv.innerHTML = `
                    <div>对话 ${timeStr}</div>
                    <div class="conversation-time">${timeStr}</div>
                `;
                
                // 创建消息数量标签
                const countSpan = document.createElement('span');
                countSpan.className = 'message-count';
                countSpan.textContent = conv.message_count;
                
                // 创建删除按钮
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'delete-conv-btn';
                deleteBtn.setAttribute('data-conversation-id', conv.conversation_id);
                deleteBtn.innerHTML = '<span class="material-icons">delete_outline</span>';
                
                // 添加删除按钮事件监听器
                deleteBtn.addEventListener('click', async (e) => {
                    e.stopPropagation(); // 阻止事件冒泡
                    const conversationId = e.currentTarget.getAttribute('data-conversation-id');
                    const listItem = li;
                    
                    // 使用全局确认对话框
                    window.showConfirmDialog('确定要删除这个对话吗？此操作不可恢复。', async (confirmed) => {
                        if (confirmed) {
                            await deleteConversation(conversationId, listItem);
                        }
                    });
                });
                
                // 组装列表项
                li.appendChild(infoDiv);
                li.appendChild(countSpan);
                li.appendChild(deleteBtn);
                
                // 添加点击事件加载对话历史
                li.addEventListener('click', () => {
                    loadSpecificChatHistory(conv.conversation_id);
                });
                
                // 如果是当前对话，添加active类
                if (conv.conversation_id === currentConversationId) {
                    li.classList.add('active');
                }
                
                historyListContainer.appendChild(li);
            });
        } catch (error) {
            console.error('加载对话列表失败:', error);
            showToast('加载对话列表失败: ' + error.message, 'error');
        }
    }

    async function deleteConversation(conversationId, listItemElement) {
        try {
            showLoading('正在删除对话...');
            
            const response = await fetch('/ai/history/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ conversation_id: conversationId })
            });
            
            if (!response.ok) {
                throw new Error(`删除对话失败：${response.status}`);
            }
            
            // 从界面移除列表项
            listItemElement.remove();
            
            // 检查是否删除了当前对话
            if (conversationId === currentConversationId) {
                currentConversationId = null;
                chatMessages.innerHTML = '';
                appendMessage('您好，我是AI助手，有什么可以帮助您的吗？', false, true);
            }
            
            // 检查列表是否为空
            if (historyListContainer.children.length === 0) {
                const emptyMessage = document.createElement('div');
                emptyMessage.className = 'no-history';
                emptyMessage.textContent = '暂无历史对话';
                historyListContainer.appendChild(emptyMessage);
            }
            
            showToast('对话已删除', 'success');
        } catch (error) {
            console.error('删除对话失败:', error);
            showToast('删除对话失败: ' + error.message, 'error');
        } finally {
            hideLoading();
        }
    }

    // 加载特定对话的历史记录
    async function loadSpecificChatHistory(conversationId) {
        try {
            // 更新当前对话ID
            currentConversationId = conversationId;
            
            // 更新列表项的高亮状态
            document.querySelectorAll('#historyListContainer li').forEach(li => {
                li.classList.remove('active');
                if (li.getAttribute('data-conversation-id') === conversationId) {
                    li.classList.add('active');
                }
            });
            
            // 清空聊天区域
            chatMessages.innerHTML = '';
            
            // 获取对话历史
            const response = await fetch(`/ai/history?conversation_id=${conversationId}`);
            if (!response.ok) {
                throw new Error(`获取对话历史失败：${response.status}`);
            }
            
            const data = await response.json();
            const history = data.history;
            
            if (history && history.length > 0) {
                history.forEach(msg => {
                    appendMessage(msg.content, msg.role === 'user', false);
                });
            } else {
                appendMessage('没有找到对话记录', false, true);
            }
        } catch (error) {
            console.error('加载对话历史失败:', error);
            appendMessage('加载对话历史失败: ' + error.message, false, true);
        }
    }

    // 处理新对话
    async function handleNewChat() {
        try {
            // 清空聊天区域
            chatMessages.innerHTML = '';
            
            // 重置当前对话ID
            currentConversationId = null;
            
            // 移除列表项的高亮状态
            document.querySelectorAll('#historyListContainer li').forEach(li => {
                li.classList.remove('active');
            });
            
            // 显示欢迎消息
            appendMessage('您好，我是AI助手，有什么可以帮助您的吗？', false, true);
            
            // 重置文件内容
            currentFileContent = null;
            if (uploadStatusElement) {
                uploadStatusElement.classList.add('hidden');
            }
            if (chatFileInput) {
                chatFileInput.value = '';
            }
            
            // 更新上一次使用的模型
            previousModel = currentModel;
            
        } catch (error) {
            console.error('开始新对话失败:', error);
            appendMessage('开始新对话失败: ' + error.message, false, true);
        }
    }

    // 初始化 - 获取可用模型信息和历史对话记录
    async function initializeModels() {
        try {
            // 显示加载提示
            appendMessage('正在初始化AI模型，请稍候...', false, true);
            
            // 检查登录状态
            await checkLoginStatus();
            
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
            
            // 尝试获取历史对话记录
            await loadChatHistory();
            
        } catch (error) {
            console.error('初始化模型失败:', error);
            appendMessage(`初始化AI模型失败: ${error.message}`, false, true);
        }
    }

    // 加载历史对话记录
    async function loadChatHistory() {
        try {
            const response = await fetch('/ai/history');
            
            // 如果是401未授权，说明用户未登录，显示欢迎消息即可
            if (response.status === 401) {
                appendMessage('您好，我是AI助手，有什么可以帮助您的吗？', false, true);
                return;
            }
            
            if (!response.ok) {
                throw new Error(`获取对话历史失败：${response.status}`);
            }
            
            const data = await response.json();
            const history = data.history;
            
            if (history && history.length > 0) {
                // 清空聊天区域
                chatMessages.innerHTML = '';
                
                // 记录当前会话ID
                currentConversationId = history[0].conversation_id;
                
                // 按时间顺序显示历史消息，排除重复消息
                const displayedMessages = new Set(); // 用于跟踪已显示的消息
                
                history.forEach(msg => {
                    // 使用内容+角色作为唯一标识，避免重复显示相同消息
                    const messageKey = `${msg.role}-${msg.content.substring(0, 50)}`;
                    
                    if (!displayedMessages.has(messageKey)) {
                        appendMessage(msg.content, msg.role === 'user', false);
                        displayedMessages.add(messageKey);
                    }
                });
                
                // 更新对话列表的高亮状态
                if (userLoggedIn) {
                    await loadConversationList();
                }
            } else {
                // 没有历史记录，显示欢迎消息
                appendMessage('您好，我是AI助手，有什么可以帮助您的吗？', false, true);
            }
        } catch (error) {
            console.error('加载对话历史失败:', error);
            appendMessage('您好，我是AI助手，有什么可以帮助您的吗？', false, true);
        }
    }

    // 处理发送消息
    async function handleSendMessage() {
        const message = chatInput.value.trim();
        if (!message && !currentFileContent) return;

        // 禁用输入和发送按钮
        chatInput.disabled = true;
        sendMessageBtn.disabled = true;
        
        // 显示停止按钮
        stopGenerationBtn.style.display = 'flex';

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
                stream: true,  // 默认使用流式输出
                model: currentModel
            };
            
            // 如果有会话ID，添加到请求中
            if (currentConversationId) {
                requestData.conversation_id = currentConversationId;
            }
            
            // 如果有文件内容，使用分析接口
            if (currentFileContent) {
                endpoint = '/ai/analyze';
                requestData = {
                    content: message,
                    file_content: currentFileContent,
                    stream: true,
                    model: currentModel,
                    conversation_id: currentConversationId
                };
                
                // 添加文件分析提示
                appendMessage(`正在分析文件内容，请稍候...`, false);
            }
            
            // 将当前会话ID存入会话存储
            const currentSession = sessionStorage.getItem('chatSessionId');
            requestData.session_id = currentSession;
            
            console.log('发送请求:', endpoint, requestData);
            
            // 发送请求到服务器
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });

            console.log('收到服务器响应:', response.status, response.headers.get('Content-Type'));

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `服务器响应异常(${response.status})`);
            }

            // 创建新的消息div用于显示
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ai-message';
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            messageDiv.appendChild(contentDiv);
            chatMessages.appendChild(messageDiv);
            
            // 检查内容类型，决定如何处理响应
            const contentType = response.headers.get('Content-Type') || '';
            
            // 处理流式响应 (text/event-stream)
            if (contentType.includes('text/event-stream')) {
                console.log('检测到流式响应');
                // 处理流式输出
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let content = '';
                let isFirstChunk = true; // 添加标记，确保仅处理新响应
                
                console.log('开始处理流式响应');
                
                while (true) {
                    const {value, done} = await reader.read();
                    if (done) {
                        console.log('流式响应读取完成');
                        break;
                    }
                    
                    const text = decoder.decode(value);
                    console.log('接收流数据:', text);
                    const lines = text.split('\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(5);
                            if (data.trim() === '[DONE]') continue;
                            
                            try {
                                const parsed = JSON.parse(data);
                                
                                // 检查是否包含对话ID
                                if (parsed.conversation_id) {
                                    currentConversationId = parsed.conversation_id;
                                    console.log('获取到会话ID:', currentConversationId);
                                    
                                    // 如果是新对话，刷新对话列表
                                    if (userLoggedIn) {
                                        await loadConversationList();
                                    }
                                    
                                    continue; // 继续处理下一行
                                }
                                
                                // 正常处理内容
                                if (parsed.content !== undefined) {
                                    // 重置内容 - 确保每次会话只显示新内容
                                    if (isFirstChunk) {
                                        content = parsed.content || '';
                                        isFirstChunk = false;
                                    } else {
                                        content += parsed.content || '';
                                    }
                                    
                                    // 将内容按段落分割并格式化显示
                                    const formattedContent = content
                                        .replace(/([.!?。！？])([^.!?。！？\s<])/g, function(match, p1, p2, offset, string) {
                                            let sentenceStart = offset;
                                            for (let i = offset - 1; i >= 0; i--) {
                                                if (/[.!?。！？]/.test(string[i])) {
                                                    sentenceStart = i + 1;
                                                    break;
                                                }
                                            }
                                            const sentenceLength = offset - sentenceStart;
                                            
                                            if (sentenceLength > 15) {
                                                return p1 + "<br><br>" + p2;
                                            } else {
                                                return match;
                                            }
                                        })
                                        .replace(/([:：])\s*((?<!\d)\d+\.(?!\d)\s*)/g, "$1<br><br>$2")
                                        .replace(/([.!?。！？])\s*((?<!\d)\d+\.(?!\d)\s*)/g, "$1<br><br>$2")
                                        .replace(/([,，:：；;])\s*/g, "$1 ")
                                        .replace(/\n\s*\n/g, "<br><br>")
                                        .replace(/\n/g, "<br>");
                                    
                                    contentDiv.innerHTML = formattedContent;
                                    chatMessages.scrollTop = chatMessages.scrollHeight;
                                }
                                
                                // 检查是否有错误
                                if (parsed.error) {
                                    console.error('AI响应错误:', parsed.error);
                                    appendMessage(`AI响应出错: ${parsed.error}`, false);
                                }
                            } catch (e) {
                                console.error('解析响应数据失败:', e);
                            }
                        }
                    }
                }
            } else {
                // 处理非流式响应 (application/json)
                console.log('检测到JSON响应');
                try {
                    const responseData = await response.json();
                    console.log('解析JSON响应:', responseData);
                    
                    if (responseData.conversation_id) {
                        currentConversationId = responseData.conversation_id;
                        
                        // 如果是新对话，刷新对话列表
                        if (userLoggedIn) {
                            await loadConversationList();
                        }
                    }
                    
                    if (responseData.response) {
                        // 对于非流式响应，直接显示完整回复
                        let formattedContent = responseData.response
                            // 智能段落划分：通过函数处理，根据句子长度决定是否分段
                            .replace(/([.!?。！？])([^.!?。！？\s<])/g, function(match, p1, p2, offset, string) {
                                // 获取当前句子，向前查找上一个句号等标点或字符串开头
                                let sentenceStart = offset;
                                for (let i = offset - 1; i >= 0; i--) {
                                    if (/[.!?。！？]/.test(string[i])) {
                                        sentenceStart = i + 1;
                                        break;
                                    }
                                }
                                const sentenceLength = offset - sentenceStart;
                                
                                // 只有句子长度超过15个字符才添加段落分隔
                                if (sentenceLength > 15) {
                                    return p1 + "<br><br>" + p2;
                                } else {
                                    return match; // 返回原始匹配，不添加换行
                                }
                            })
                            // 处理冒号后跟列表的情况，确保列表项正确分段，但排除小数点情况
                            .replace(/([:：])\s*((?<!\d)\d+\.(?!\d)\s*)/g, "$1<br><br>$2") // 冒号后跟列表项，排除小数点
                            .replace(/([.!?。！？])\s*((?<!\d)\d+\.(?!\d)\s*)/g, "$1<br><br>$2") // 句号等后跟列表项，排除小数点
                            .replace(/([,，:：；;])\s*/g, "$1 ")  // 在逗号、冒号、分号后添加空格
                            .replace(/\n\s*\n/g, "<br><br>")  // 连续的换行符替换为HTML换行
                            .replace(/\n/g, "<br>");  // 单个换行符替换为HTML换行
                        
                        // 确保只显示最新响应
                        contentDiv.innerHTML = formattedContent;
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                    
                    if (responseData.error) {
                        console.error('AI响应错误:', responseData.error);
                        appendMessage(`AI响应出错: ${responseData.error}`, false);
                    }
                } catch (e) {
                    console.error('解析JSON响应失败:', e);
                    appendMessage(`解析AI响应失败: ${e.message}`, false);
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
                appendMessage('已停止生成', false, true);
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
            
            // 隐藏停止按钮
            stopGenerationBtn.style.display = 'none';
            
            controller = null;
        }
    }

    // 处理文件上传
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
            document.getElementById('loadingMessage').textContent = '文件处理中...';
            
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
            
            // 确保文件上传后，之前的请求已被取消
            if (controller) {
                controller.abort();
                controller = null;
            }
            
        } catch (error) {
            // 隐藏加载状态
            document.getElementById('loadingOverlay').classList.add('hidden');
            
            appendMessage(`文件处理失败: ${error.message}`, false);
            console.error('文件处理错误:', error);
            chatFileInput.value = '';
        }
    }

    // 添加消息到对话框
    function appendMessage(content, isUser = false, isSystemMsg = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
        
        // 添加系统消息的特殊类
        if (isSystemMsg) {
            messageDiv.classList.add('system-message');
        }
        
        // 对非用户消息（AI回复）进行格式化处理
        if (!isUser) {
            // 系统消息使用简单格式化
            if (isSystemMsg) {
                // 简单格式化：只处理换行符，不对标点添加段落分隔
                content = content
                    .replace(/\n\s*\n/g, "<br>")  // 连续的换行符替换为HTML换行
                    .replace(/\n/g, "<br>");  // 单个换行符替换为HTML换行
            } else {
                // AI回复使用完整的段落格式化
                content = content
                    // 智能段落划分：通过函数处理，根据句子长度决定是否分段
                    .replace(/([.!?。！？])([^.!?。！？\s<])/g, function(match, p1, p2, offset, string) {
                        // 获取当前句子，向前查找上一个句号等标点或字符串开头
                        let sentenceStart = offset;
                        for (let i = offset - 1; i >= 0; i--) {
                            if (/[.!?。！？]/.test(string[i])) {
                                sentenceStart = i + 1;
                                break;
                            }
                        }
                        const sentenceLength = offset - sentenceStart;
                        
                        // 只有句子长度超过15个字符才添加段落分隔
                        if (sentenceLength > 15) {
                            return p1 + "<br><br>" + p2;
                        } else {
                            return match; // 返回原始匹配，不添加换行
                        }
                    })
                    // 处理冒号后跟列表的情况，确保列表项正确分段，但排除小数点情况
                    .replace(/([:：])\s*((?<!\d)\d+\.(?!\d)\s*)/g, "$1<br><br>$2") // 冒号后跟列表项，排除小数点
                    .replace(/([.!?。！？])\s*((?<!\d)\d+\.(?!\d)\s*)/g, "$1<br><br>$2") // 句号等后跟列表项，排除小数点
                    .replace(/([,，:：；;])\s*/g, "$1 ")  // 在逗号、冒号、分号后添加空格
                    .replace(/\n\s*\n/g, "<br><br>")  // 连续的换行符替换为HTML换行
                    .replace(/\n/g, "<br>");  // 单个换行符替换为HTML换行
            }
        }
        
        messageDiv.innerHTML = `<div class="message-content">${content}</div>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 处理停止生成
    function handleStopGeneration() {
        if (controller) {
            console.log('用户中止了AI响应生成');
            controller.abort();
            // 立即隐藏停止按钮
            stopGenerationBtn.style.display = 'none';
        }
    }

    // 在页面卸载前取消所有进行中的请求
    window.addEventListener('beforeunload', () => {
        if (controller) {
            controller.abort();
        }
    });

    // 绑定事件监听器
    sendMessageBtn.addEventListener('click', handleSendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    
    // 绑定停止按钮事件
    stopGenerationBtn.addEventListener('click', handleStopGeneration);
    
    // 绑定新对话按钮事件
    newChatBtn.addEventListener('click', handleNewChat);
    
    // 绑定清空对话按钮事件
    resetChatBtn.addEventListener('click', handleNewChat);
    
    // 文件上传事件
    if (chatFileInput) {
        chatFileInput.addEventListener('change', handleFileUpload);
    }
    
    // 触发文件上传按钮
    if (triggerUploadBtn) {
        triggerUploadBtn.addEventListener('click', () => {
            chatFileInput.click();
        });
    }

    // 监听模型选择变化
    modelSelect.addEventListener('change', function() {
        currentModel = this.value;
        appendMessage(`已切换到${this.options[this.selectedIndex].textContent}`, false, true);
    });

    // 初始化模型
    initializeModels();
});
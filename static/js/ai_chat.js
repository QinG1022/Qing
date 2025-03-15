/**
 * AI对话模块
 * 版本: 1.0
 * 最后更新: 2024-03-06
 * 描述: 提供AI对话功能，包括消息发送、接收和显示
 */

document.addEventListener('DOMContentLoaded', function() {
    const chatInput = document.getElementById('chatInput');
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const chatMessages = document.getElementById('chatMessages');
    let controller = null;

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
            // 检查网络连接状态
            if (!navigator.onLine) {
                throw new Error('网络连接已断开，请检查网络后重试');
            }

            // 创建新的AbortController
            controller = new AbortController();

            // 发送请求到服务器
            const response = await fetch('/ai/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    stream: true
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
});
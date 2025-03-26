/**
 * 智能文档处理系统 - 主脚本
 * 版本: 1.0
 * 最后更新: 2024-03-06
 * 描述: 提供用户交互处理、表单提交、文件预览和历史记录管理等功能
 */

document.addEventListener('DOMContentLoaded', function() {                      
    /**
     * DOM元素引用 - 获取页面中所有需要操作的元素
     */
    const contentTextarea = document.getElementById('content');                 
    const generateBtn = document.getElementById('generate-btn');                
    const loadingOverlay = document.getElementById('loadingOverlay');           
    const statusMessage = document.getElementById('statusMessage');             
    const statusSection = document.querySelector('.status-section');            
    const resultsGrid = document.getElementById('resultsGrid');                 
    const extractResults = document.querySelector('.extract-results');          
    const toast = document.getElementById('toast');                             
    const modalOverlay = document.getElementById('modalOverlay');               
    const modalMessage = document.getElementById('modalMessage');               
    const modalConfirm = document.getElementById('modalConfirm');               
    const modalCancel = document.getElementById('modalCancel');                 
    const modalClose = document.getElementById('modalClose');                   
    const historyContainer = document.getElementById('historyContainer');       
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');     
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');         
    const historyCount = document.getElementById('historyCount');               
    const imagesInput = document.getElementById('images'); 
    let ocrTextAdded = false;                       

    // 页面初始化设置
    loadingOverlay.classList.add('hidden'); 
    loadHistory(); 

    /**
     * 事件监听器设置 - 绑定各个UI元素的事件
     */
    if (refreshHistoryBtn) {
        refreshHistoryBtn.addEventListener('click', loadHistory); 
    }
    
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearHistory);    
    }

    /**
     * 标签页切换功能
     * 处理不同功能标签页之间的切换
     */
    const tabButtons = document.querySelectorAll('.tab-button'); 
    const tabPanes = document.querySelectorAll('.tab-pane'); 
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            
            // 移除所有active类
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // 添加active类到当前标签
            button.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // 添加"立即使用"按钮功能
    const featureButtons = document.querySelectorAll('.feature-btn');
    const tabContainer = document.getElementById('tabContainer');
    const backToHomeContainer = document.getElementById('backToHomeContainer');
    const backToHomeBtn = document.getElementById('backToHomeBtn');
    
    // 返回主页功能
    if (backToHomeBtn) {
        backToHomeBtn.addEventListener('click', () => {
            // 隐藏标签栏和返回按钮
            tabContainer.style.display = 'none';
            backToHomeContainer.style.display = 'none';
            
            // 显示主界面，直接激活tab0（主页）
            tabPanes.forEach(pane => pane.classList.remove('active'));
            const homeTab = document.getElementById('tab0');
            if (homeTab) homeTab.classList.add('active');
        });
    }
    
    featureButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            
            // 显示标签栏和返回按钮
            tabContainer.style.display = 'flex';
            backToHomeContainer.style.display = 'block';
            
            // 找到对应的标签按钮并激活
            const targetTabButton = document.querySelector(`.tab-button[data-tab="${tabId}"]`);
            if (targetTabButton) {
                // 移除所有active类
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabPanes.forEach(pane => pane.classList.remove('active'));
                
                // 添加active类到目标标签
                targetTabButton.classList.add('active');
                document.getElementById(tabId).classList.add('active');
            }
        });
    });

    /**
     * 显示提示消息
     * 
     * @param {string} message - 要显示的消息内容
     * @param {number} duration - 显示持续时间(毫秒)，默认3000ms
     */
    function showToast(message, duration = 3000) {
        toast.textContent = message; 
        toast.classList.remove('hidden'); 
        setTimeout(() => {
            toast.classList.add('hidden'); 
        }, duration); 
    }

    /**
     * 显示确认对话框
     * 
     * @param {string} message - 确认对话框显示的消息内容
     * @param {Function} onConfirm - 用户确认时执行的回调函数
     * @param {Function} onCancel - 用户取消时执行的回调函数
     */
    function showConfirmDialog(message, onConfirm, onCancel) {
        modalMessage.innerHTML = message.replace(/\n/g, '<br>'); 
        modalOverlay.classList.add('visible'); 
        
        const handleConfirm = () => {
            modalOverlay.classList.remove('visible'); 
            removeEventListeners(); 
            if (onConfirm) onConfirm(); 
        };
        
        const handleCancel = () => {
            modalOverlay.classList.remove('visible'); 
            removeEventListeners(); 
            if (onCancel) onCancel(); 
        };
        
        const handleClose = () => {
            modalOverlay.classList.remove('visible'); 
            removeEventListeners(); 
        };
        
        const removeEventListeners = () => {
            modalConfirm.removeEventListener('click', handleConfirm); 
            modalCancel.removeEventListener('click', handleCancel); 
            modalClose.removeEventListener('click', handleClose); 
        };
        
        modalConfirm.addEventListener('click', handleConfirm); 
        modalCancel.addEventListener('click', handleCancel); 
        modalClose.addEventListener('click', handleClose); 
    }

    /**
     * 显示加载状态
     * 
     * @param {string} message - 加载状态显示的消息
     */
    function showLoading(message = '处理中，请稍候...') {
        document.getElementById('loadingText').textContent = message; 
        loadingOverlay.classList.remove('hidden'); 
    }

    /**
     * 隐藏加载状态
     */
    function hideLoading() {
        loadingOverlay.classList.add('hidden'); 
    }

    /**
     * 设置状态消息
     * 
     * @param {string} message - 状态消息内容
     * @param {boolean} isError - 是否为错误消息，影响显示颜色
     */
    function setStatusMessage(message, isError = false) {
        statusMessage.textContent = message; 
        statusMessage.style.color = isError ? 'var(--error-color)' : 'var(--primary-color)'; 
        statusSection.classList.add('visible'); 
    }

    /**
     * 清除状态消息
     */
    function clearStatusMessage() {
        statusMessage.textContent = ''; 
        statusSection.classList.remove('visible'); 
    }

    /**
     * 轮询任务状态
     * 
     * 定期检查后端任务的执行状态，直到任务完成或失败
     * 
     * @param {string} taskId - 任务ID
     */
    function pollTaskStatus(taskId) {
        console.log('开始轮询任务状态:', taskId); 
        showLoading('任务处理中，请稍候...');       
        
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/tasks/${taskId}`); 
                const data = await response.json(); 
                console.log('任务状态:', data); 
                
                if (data.status === 'SUCCESS') {
                    clearInterval(intervalId); 
                    hideLoading(); 
                    setStatusMessage('生成成功！'); 
                    
                    if (data.result) {
                        window.location.href = `/download/${data.result}`; 
                    }
                } else if (data.status === 'FAILURE') { 
                    clearInterval(intervalId); 
                    hideLoading(); 
                    setStatusMessage(`生成失败: ${data.error || '未知错误'}`, true); 
                } else {  
                    document.getElementById('loadingText').textContent = data.message || '处理中...'; 
                }
            } catch (error) {
                console.error('轮询错误:', error);  
                clearInterval(intervalId); 
                hideLoading(); 
                setStatusMessage('状态查询失败', true); 
            }
        }, 1000);   
    }

    /**
     * 处理表单提交，生成PDF文档
     * 
     * @param {boolean} includeImages - 是否包含图片
     * @returns {Promise<void>}    
     */
    async function handleSubmit(includeImages) {
        try {
            const textContent = contentTextarea.value.trim();
            if (!textContent && (!includeImages || !imagesInput.files.length)) {
                showToast('请输入文本内容或上传图片');
                return;
            }
            
            showLoading('生成文档中...');
            const formData = new FormData();
            formData.append('content', textContent); 
            
            if (includeImages) {
                Array.from(imagesInput.files).forEach(file => {
                    formData.append('images', file); 
                });
            }
            
            const response = await fetch('/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || '请求失败');
            }

            if (data.task_id) {
                if (textContent) {
                    console.log("文本内容已提交，刷新历史记录");
                    setTimeout(loadHistory, 500); 
                }
                pollTaskStatus(data.task_id); 
            } else {
                throw new Error('未收到任务ID');
            }

        } catch (error) {
            console.error('Error:', error); 
            hideLoading(); 
            showConfirmDialog(`生成失败: ${error.message}`); 
        }
    }

    /**
     * 生成文档按钮点击事件
     * 处理不同场景下的文档生成逻辑，根据内容和OCR状态显示不同的确认对话框
     */
    if (generateBtn) {
        generateBtn.addEventListener('click', async function() {
            const content = contentTextarea.value.trim();
            const hasImages = imagesInput.files.length > 0;
            const hasOCRResults = document.querySelector('.ocr-item') !== null;
            
            if (!content && !hasImages) {
                showConfirmDialog('请至少输入文本或选择图片');
                return;
            }

            // 情况1: 只有图片，且没有文本和OCR结果，直接生成
            if (hasImages && !content && !hasOCRResults) {
                await handleSubmit(true);
                return;
            }

            // 情况2: 文本和图片都有，没有OCR结果，直接生成
            if (content && hasImages && !hasOCRResults) {
                await handleSubmit(true);
                return;
            }

            // 情况3: 有文本、OCR结果和图片，且用户点击了"添加到文本"或"全部合并到文本"按钮，显示询问对话框
            if (hasImages && content && hasOCRResults && ocrTextAdded) {
                showConfirmDialog(
                    '检测到将OCR结果放入文本区，是否将图片一起放入文档？\n\n选择"是"：将图片和文字一起生成文档\n选择"否"：仅使用文本生成文档',
                    async () => await handleSubmit(true),  // 确认回调
                    async () => await handleSubmit(false)  // 取消回调
                );
                return;
            }

            // 情况4: 有图片和OCR结果，但没有文本，显示询问对话框
            if (hasImages && hasOCRResults && !content) {
                showConfirmDialog(
                    '检测到存在OCR结果，是否将OCR结果和图片一起生成文档？\n\n选择"是"：将OCR结果和图片一起生成文档\n选择"否"：直接将图片生成文档',
                    async () => {
                        // 将OCR结果添加到文本区
                        const ocrItems = document.querySelectorAll('.ocr-item .ocr-text');
                        const texts = Array.from(ocrItems).map(item => item.textContent);
                        contentTextarea.value = texts.join('\n');
                        
                        // 直接调用情况3的处理逻辑
                        await handleSubmit(true);
                    },  // 确认回调
                    async () => await handleSubmit(true)  // 取消回调
                );
                return;
            }

            // 情况5: 有图片、文本和OCR结果，显示询问对话框
            if (hasImages && content && hasOCRResults) {
                showConfirmDialog(
                    '检测到已识别OCR结果，是否将图片一起放入文档？\n\n选择"是"：将图片和文字一起生成文档\n选择"否"：仅使用文本生成文档',
                    async () => await handleSubmit(true),  // 确认回调
                    async () => await handleSubmit(false)  // 取消回调
                );
                return;
            }

            // 情况6: 只有文本，直接生成不含图片的文档
            await handleSubmit(false);
        });
    }
    
    /**
     * 复制文本到剪贴板
     * 临时创建一个文本区域元素来实现复制功能
     * 
     * @param {string} text - 要复制到剪贴板的文本
     */
    function copyToClipboard(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed'; // 避免影响页面布局
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);  
    }

    /**
     * 加载历史记录
     * 从服务器获取并显示用户的历史操作记录
     * 
     * @returns {Promise<void>}
     */
    async function loadHistory() {
        try {
            console.log("正在获取历史记录...");
            const response = await fetch('/history');
            
            if (!response.ok) {
                throw new Error('获取历史记录失败，状态码: ' + response.status);
            }
            
            const data = await response.json();
            console.log("历史记录数据:", data);
            
            if (historyCount) {
                historyCount.textContent = `(共${data.count}/${data.max_count}条内容)`;
            }
            
            if (data.status === 'success' && historyContainer) {
                historyContainer.innerHTML = '';
                
                if (data.history && data.history.length > 0) {
                    console.log(`加载 ${data.history.length} 条历史记录`);
                    
                    data.history.forEach(item => {
                        const historyItem = document.createElement('div');
                        historyItem.className = 'history-item';
                        historyItem.dataset.id = item.id;
                        
                        let typeName = '';
                        
                        switch(item.type) {
                            case 'OCR':
                                typeName = '图片OCR识别';
                                break;
                            case 'PDF':
                                typeName = 'PDF文本提取';
                                break;
                            case 'TEXT':
                                typeName = '用户输入文本';
                                break;
                            default:
                                typeName = '未知类型';
                        }
                        
                        historyItem.innerHTML = `
                            <button class="delete-history-btn" title="删除此记录">
                                <span class="material-icons">删除</span>
                            </button>
                            <div class="history-item-header">
                                <div class="history-type">
                                    <span class="material-icons">${typeName}</span>
                                </div>
                                <div class="history-timestamp">${item.timestamp}</div>
                            </div>
                            <div class="history-source">${item.source || typeName}</div>
                            <div class="history-content">${item.content || '(无内容)'}</div>
                            <div class="history-actions">
                                <button class="copy-history-btn">
                                    <span class="material-icons">复制</span> 
                                </button>
                                <button class="insert-history-btn">
                                    <span class="material-icons">插入</span> 
                                </button>
                            </div>
                        `;
                        
                        const deleteBtn = historyItem.querySelector('.delete-history-btn');
                        deleteBtn.addEventListener('click', () => {
                            deleteHistoryRecord(item.id);
                        });
                        
                        const copyBtn = historyItem.querySelector('.copy-history-btn');
                        copyBtn.addEventListener('click', () => {
                            copyToClipboard(item.content || '(无内容)');
                            showToast('已复制到剪贴板');
                        });
                        
                        const insertBtn = historyItem.querySelector('.insert-history-btn');
                        insertBtn.addEventListener('click', () => {
                            if (contentTextarea) {
                                const currentText = contentTextarea.value;
                                if (currentText) {
                                    contentTextarea.value = currentText + '\n\n' + (item.content || '(无内容)');
                                } else {
                                    contentTextarea.value = item.content || '(无内容)';
                                }
                                showToast('文本已插入到编辑器');
                                
                                const firstTabBtn = document.querySelector('.tab-button[data-tab="tab1"]');
                                if (firstTabBtn) {
                                    firstTabBtn.click();
                                    contentTextarea.scrollIntoView({ behavior: 'smooth' });
                                    setTimeout(() => {
                                        contentTextarea.focus();
                                    }, 300);
                                }
                            }
                        });
                        
                        historyContainer.appendChild(historyItem);
                    });
                } else {
                    console.log("没有历史记录");
                    historyContainer.innerHTML = '<div class="empty-history">暂无历史记录</div>';
                }
                
                document.dispatchEvent(new Event('historyLoaded'));
            }
        } catch (error) {
            console.error('获取历史记录出错:', error);
            if (historyContainer) {
                historyContainer.innerHTML = `<div class="empty-history error">获取历史记录失败: ${error.message}</div>`;
            }
            showToast('获取历史记录失败: ' + error.message);
        }
    }
    
    /**
     * 删除单条历史记录
     * 向服务器发送删除请求并刷新历史记录显示
     * 
     * @param {string} recordId - 要删除的历史记录ID
     * @returns {Promise<void>}   
     */
    async function deleteHistoryRecord(recordId) {
        try {
            showLoading('删除中...');
            const response = await fetch(`/history/${recordId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                await loadHistory();
                showToast('历史记录已删除');
            } else {
                throw new Error(data.error || '删除失败');
            }
            
            hideLoading();
        } catch (error) {
            console.error('删除历史记录失败:', error);
            hideLoading();
            showToast('删除历史记录失败: ' + error.message);
        }
    }
    
    /**
     * 清空所有历史记录
     * 显示确认对话框并在用户确认后发送清空请求
     * 
     * @returns {Promise<void>}
     */
    async function clearHistory() {
        try {
            showConfirmDialog('确定要清空所有历史记录吗？此操作不可撤销。', async () => {
                try {
                    showLoading('清空中...');
                    const response = await fetch('/history', {
                        method: 'DELETE'
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        await loadHistory();
                        showToast('所有历史记录已清空');  
                    } else {
                        throw new Error(data.error || '清空失败');
                    }
                    
                    hideLoading();
                } catch (error) {
                    console.error('清空历史记录失败:', error);
                    hideLoading();
                    showToast('清空历史记录失败: ' + error.message);
                }
            });
        } catch (error) {
            console.error('清空历史记录错误:', error);
            showToast('操作失败: ' + error.message);
        }
    }
    
    // 导出全局函数以供其他模块使用
    window.showToast = showToast;
    window.showLoading = showLoading;
    window.hideLoading = hideLoading;
    window.setStatusMessage = setStatusMessage;
    window.clearStatusMessage = clearStatusMessage;
    window.showConfirmDialog = showConfirmDialog;
    window.copyToClipboard = copyToClipboard;
    window.loadHistory = loadHistory;
    window.pollTaskStatus = pollTaskStatus;
});
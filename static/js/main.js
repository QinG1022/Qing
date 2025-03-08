document.addEventListener('DOMContentLoaded', function() {
    // DOM元素引用
    const contentTextarea = document.getElementById('content');
    const generateBtn = document.getElementById('generate-btn');
    const imagesInput = document.getElementById('images');
    const imagePreview = document.querySelector('.image-preview');
    const processImagesBtn = document.getElementById('process-images-btn');
    const pdfInput = document.getElementById('pdf-file');
    const pdfPreview = document.querySelector('.pdf-preview');
    const extractPdfBtn = document.getElementById('extract-pdf-btn');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const statusMessage = document.getElementById('statusMessage');
    const statusSection = document.querySelector('.status-section');
    const resultsGrid = document.getElementById('resultsGrid');
    const extractResults = document.querySelector('.extract-results');
    const pdfTextContent = document.getElementById('pdf-text-content');
    const copyAllBtn = document.getElementById('copy-all-btn');
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
    let ocrTextAdded = false; // 标志用户是否点击了"添加到文本"或"全部合并到文本"按钮

    // 初始化加载状态为隐藏
    loadingOverlay.classList.add('hidden');
    
    // 初始化加载历史记录
    loadHistory();

    // 为刷新历史记录按钮添加事件监听器
    if (refreshHistoryBtn) {
        refreshHistoryBtn.addEventListener('click', loadHistory);
    }
    
    // 为清空历史记录按钮添加事件监听器
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearHistory);
    }

    // 标签页切换功能
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // 移除所有active类
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // 添加当前active类
            button.classList.add('active');
            const targetTab = button.dataset.tab;
            document.getElementById(targetTab).classList.add('active');
        });
    });

    // 显示提示消息
    function showToast(message, duration = 3000) {
        toast.textContent = message;
        toast.classList.remove('hidden');
        setTimeout(() => {
            toast.classList.add('hidden');
        }, duration);
    }

    // 显示确认对话框
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

    // 加载状态控制
    function showLoading(message = '处理中，请稍候...') {
        document.getElementById('loadingText').textContent = message;
        loadingOverlay.classList.remove('hidden');
    }

    function hideLoading() {
        loadingOverlay.classList.add('hidden');
    }

    function setStatusMessage(message, isError = false) {
        statusMessage.textContent = message;
        statusMessage.style.color = isError ? 'var(--error-color)' : 'var(--primary-color)';
        statusSection.classList.add('visible');
    }

    function clearStatusMessage() {
        statusMessage.textContent = '';
        statusSection.classList.remove('visible');
    }

    // 图片预览处理
    if (imagesInput) {
        imagesInput.addEventListener('change', function(e) {
            // 隐藏OCR结果区域
            const ocrResults = document.querySelector('.ocr-results');
            ocrResults.classList.add('hidden');
            
            // 图片预览逻辑
            imagePreview.innerHTML = '';
            if (this.files.length > 0) {
                processImagesBtn.disabled = false;
                Array.from(this.files).forEach(file => {
                    if (file.type.startsWith('image/')) {
                        const reader = new FileReader();
                        const div = document.createElement('div');
                        div.className = 'preview-item';
                        
                        reader.onload = e => {
                            div.innerHTML = `
                                <img src="${e.target.result}" alt="${file.name}">
                                <div class="file-info">
                                    <span>${file.name}</span>
                                    <span>${(file.size / 1024).toFixed(1)} KB</span>
                                </div>
                            `;
                        };
                        
                        reader.readAsDataURL(file);
                        imagePreview.appendChild(div);
                    }
                });
            } else {
                processImagesBtn.disabled = true;
            }
        });
    }

    // PDF预览处理
    if (pdfInput) {
        pdfInput.addEventListener('change', function(e) {
            pdfPreview.innerHTML = '';
            if (this.files.length > 0) {
                extractPdfBtn.disabled = false;
                const file = this.files[0];
                if (file.type === 'application/pdf') {
                    const div = document.createElement('div');
                    div.className = 'pdf-preview-item';
                    div.innerHTML = `
                        <div class="pdf-icon">
                            <span class="material-icons">PDF</span>
                        </div>
                        <div class="file-info">
                            <div>${file.name}</div>
                            <div>${(file.size / (1024*1024)).toFixed(2)} MB</div>
                        </div>
                    `;
                    pdfPreview.appendChild(div);
                }
            } else {
                extractPdfBtn.disabled = true;
            }
        });
    }

    // 轮询任务状态
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

    // 处理图片OCR任务状态
    function pollOCRStatus(taskId) {
        showLoading('识别图片文字中...');
        
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/tasks/${taskId}`);
                const data = await response.json();
                
                if (data.status === 'SUCCESS') {
                    clearInterval(intervalId);
                    hideLoading();
                    handleOCRResults(data.result.results);
                    processImagesBtn.disabled = false;
                    
                    // 处理成功后刷新历史记录
                    console.log("OCR处理完成，刷新历史记录");
                    setTimeout(loadHistory, 500);
                } else if (data.status === 'FAILURE') {
                    clearInterval(intervalId);
                    hideLoading();
                    setStatusMessage(`OCR处理失败: ${data.error || '未知错误'}`, true);
                    processImagesBtn.disabled = false;
                } else {
                    document.getElementById('loadingText').textContent = data.message || '识别中...';
                }
            } catch (error) {
                clearInterval(intervalId);
                hideLoading();
                setStatusMessage('状态查询失败', true);
                processImagesBtn.disabled = false;
            }
        }, 1000);
    }

    // 处理OCR结果
    function handleOCRResults(results) {
        const ocrResults = document.querySelector('.ocr-results');
        const ocrContent = document.getElementById('ocrContent');
        ocrContent.innerHTML = '';
        
        if (results && results.length > 0) {
            const mergeAllBtn = ocrResults.querySelector('.merge-all-btn');
            mergeAllBtn.disabled = false;
            mergeAllBtn.addEventListener('click', mergeAllText);
            
            results.forEach(result => {
                const div = document.createElement('div');
                div.className = 'ocr-item';
                div.innerHTML = `
                    <div class="ocr-text">${result.text}</div>
                    <div class="ocr-actions">
                        <button class="merge-btn">
                            <span class="material-icons"></span> 添加到文本
                        </button>
                    </div>
                `;
                
                // 添加单个合并按钮事件
                const mergeBtn = div.querySelector('.merge-btn');
                mergeBtn.addEventListener('click', function() {
                    mergeText(result.text, this);
                });
                
                ocrContent.appendChild(div);
            });
            
            // 显示OCR结果区域
            ocrResults.classList.remove('hidden');
        } else {
            setStatusMessage('未识别到任何文本', true);
        }
    }

    // 合并单个文本
    function mergeText(text, button) {
        if (!contentTextarea) return;
        
        const currentValue = contentTextarea.value;
        contentTextarea.value = currentValue + (currentValue ? '\n' : '') + text;
        
        button.disabled = true;
        button.innerHTML = '<span class="material-icons"></span> 已添加';
        ocrTextAdded = true;
    }

    // 合并所有文本
    function mergeAllText() {
        if (!contentTextarea) return;
        
        const ocrItems = document.querySelectorAll('.ocr-item:not(.merged) .ocr-text');
        const texts = Array.from(ocrItems).map(item => item.textContent);
        
        if (texts.length > 0) {
            const currentValue = contentTextarea.value;
            contentTextarea.value = currentValue + (currentValue ? '\n' : '') + texts.join('\n');
            
            // 更新按钮状态
            document.querySelectorAll('.ocr-item .merge-btn').forEach(btn => {
                btn.disabled = true;
                btn.innerHTML = '<span class="material-icons"></span> 已添加';
            });
            
            // 禁用"全部合并"按钮
            const mergeAllBtn = document.querySelector('.merge-all-btn');
            if (mergeAllBtn) {
                mergeAllBtn.disabled = true;
                mergeAllBtn.innerHTML = '<span class="material-icons"></span> 已全部添加';
            }
            
            ocrTextAdded = true;
        }
    }

    // 处理表单提交
    async function handleSubmit(includeImages) {
        try {
            // 检查文本内容是否为空
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
                // 如果有文本内容，则刷新历史记录
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

    // 处理PDF文本提取
    if (extractPdfBtn) {
        extractPdfBtn.addEventListener('click', async function() {
            if (!pdfInput.files.length) {
                showToast('请先选择一个PDF文件');
                return;
            }

            const formData = new FormData();
            formData.append('pdfs', pdfInput.files[0]);
            
            showLoading('正在处理PDF文本提取...');
            extractResults.style.display = 'none';
            
            try {
                const response = await fetch('/extract-pdf', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('服务器响应错误');
                }
                
                const result = await response.json();
                
                if (result.task_id) {
                    pollPDFExtractionStatus(result.task_id);
                } else {
                    throw new Error('未能获取任务ID');
                }
            } catch (error) {
                console.error('提交任务失败:', error);
                hideLoading();
                setStatusMessage(`提交失败: ${error.message}`, true);
            }
        });
    }

    // 处理图片按钮事件
    if (processImagesBtn) {
        processImagesBtn.addEventListener('click', async function() {
            if (!imagesInput.files.length) {
                showToast('请先选择图片');
                return;
            }

            if (!document.getElementById('enableOCR').checked) {
                showToast('请勾选"对图片进行文字识别"选项');
                return;
            }

            this.disabled = true;
            
            // 确保OCR结果区域隐藏
            const ocrResults = document.querySelector('.ocr-results');
            ocrResults.classList.add('hidden');
            
            const formData = new FormData();
            Array.from(imagesInput.files).forEach(file => {
                formData.append('images', file);
            });

            try {
                showLoading('处理图片中，识别文字...');
                const response = await fetch('/process-images', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error('处理失败');
                }
                
                const data = await response.json();
                if (data.task_id) {
                    pollOCRStatus(data.task_id);
                } else {
                    throw new Error('未能获取任务ID');
                }
            } catch (error) {
                hideLoading();
                showToast('图片处理失败: ' + error.message);
                this.disabled = false;
            }
        });
    }

    // 生成文档按钮事件
    if (generateBtn) {
        generateBtn.addEventListener('click', async function() {
            const content = contentTextarea.value.trim();
            const hasImages = imagesInput.files.length > 0;
            const hasOCRResults = document.querySelector('.ocr-item') !== null;
            
            if (!content && !hasImages) {
                showConfirmDialog('请至少输入文本或选择图片');
                return;
            }

            // 情况1: 只有图片，且没有OCR结果，直接生成
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
                    '检测到OCR结果，是否将OCR结果和图片一起生成文档？\n\n选择"是"：将OCR结果和图片一起生成文档\n选择"否"：直接将图片生成文档',
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

            // 情况5: 有图片、文本和OCR结果，直接生成
            if (hasImages && content && hasOCRResults) {
                showConfirmDialog(
                    '检测到有OCR结果，是否将图片一起放入文档？\n\n选择"是"：将图片和文字一起生成文档\n选择"否"：仅使用文本生成文档',
                    async () => await handleSubmit(true),  // 确认回调
                    async () => await handleSubmit(false)  // 取消回调
                );
                return;
            }

            // 情况6: 只有文本，直接生成不含图片的文档
            await handleSubmit(false);
        });
    }

    // 轮询PDF提取任务状态
    function pollPDFExtractionStatus(taskId) {
        showLoading('提取PDF文本中...');
        
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/tasks/${taskId}`);
                const data = await response.json();
                
                if (data.status === 'SUCCESS') {
                    clearInterval(intervalId);
                    hideLoading();
                    handlePDFResults(data.result);
                    extractPdfBtn.disabled = false;
                    
                    // 处理成功后刷新历史记录
                    console.log("PDF处理完成，刷新历史记录");
                    setTimeout(loadHistory, 500);
                } else if (data.status === 'FAILURE') {
                    clearInterval(intervalId);
                    hideLoading();
                    setStatusMessage(`PDF处理失败: ${data.error || '未知错误'}`, true);
                    extractPdfBtn.disabled = false;
                } else {
                    document.getElementById('loadingText').textContent = data.message || '提取中...';
                }
            } catch (error) {
                clearInterval(intervalId);
                hideLoading();
                setStatusMessage('状态查询失败', true);
                extractPdfBtn.disabled = false;
            }
        }, 1000);
    }

    // 处理PDF提取结果
    function handlePDFResults(result) {
        if (!result) {
            setStatusMessage('未能提取文本内容', true);
            return;
        }
        
        // 更新文件信息
        document.getElementById('pdf-file-name').textContent = `文件名: ${result.results[0].filename || '未知'}`;
        document.getElementById('pdf-page-count').textContent = `总页数: ${result.results[0].total_pages || 0}`;
        document.getElementById('pdf-word-count').textContent = `总字数: ${result.results[0].text_length || 0}`;
        
        // 更新文本内容
        pdfTextContent.innerHTML = '';
        
        if (result.results && result.results.length > 0) {
            const pdf = result.results[0];
            
            if (pdf.pages && pdf.pages.length > 0) {
                pdf.pages.forEach((page) => {
                    const pageDiv = document.createElement('div');
                    pageDiv.className = 'pdf-text-page';
                    pageDiv.innerHTML = `
                        <h4>第 ${page.page_num} 页</h4>
                        <div class="page-text">${page.text || '(无文本内容)'}</div>
                        <button class="copy-btn" data-page="${page.page_num - 1}">
                            <span class="material-icons"></span> 复制此页文本
                        </button>
                    `;
                    pdfTextContent.appendChild(pageDiv);
                });
                
                // 注册复制按钮事件
                pdfTextContent.querySelectorAll('.copy-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const pageIndex = parseInt(this.dataset.page);
                        const text = pdf.pages[pageIndex].text;
                        copyToClipboard(text);
                        showToast('已复制到剪贴板');
                    });
                });
                
                // 显示结果区域
                extractResults.style.display = 'block';
                clearStatusMessage();
            } else {
                // 如果没有分页信息，直接显示全部文本
                const pageDiv = document.createElement('div');
                pageDiv.className = 'pdf-text-page';
                pageDiv.innerHTML = `
                    <h4>文本内容</h4>
                    <div class="page-text">${pdf.text || '(无文本内容)'}</div>
                `;
                pdfTextContent.appendChild(pageDiv);
                extractResults.style.display = 'block';
                clearStatusMessage();
            }
        } else {
            setStatusMessage('PDF中未发现文本内容', true);
        }
    }
    
    // 复制所有文本功能
    if (copyAllBtn) {
        copyAllBtn.addEventListener('click', function() {
            const allText = Array.from(pdfTextContent.querySelectorAll('.page-text'))
                .map(el => el.textContent)
                .join('\n\n');
                
            copyToClipboard(allText);
            showToast('已复制全部文本到剪贴板');
        });
    }
    
    // 复制到剪贴板
    function copyToClipboard(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed'; // 避免影响页面布局
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
    }

    // 历史记录相关函数
    async function loadHistory() {
        try {
            console.log("正在获取历史记录...");
            const response = await fetch('/history');
            
            if (!response.ok) {
                throw new Error('获取历史记录失败，状态码: ' + response.status);
            }
            
            const data = await response.json();
            console.log("历史记录数据:", data);
            
            // 更新历史记录计数
            if (historyCount) {
                historyCount.textContent = `(共${data.count}/${data.max_count}条内容)`;
            }
            
            if (data.status === 'success' && historyContainer) {
                // 清空历史记录容器
                historyContainer.innerHTML = '';
                
                if (data.history && data.history.length > 0) {
                    console.log(`加载 ${data.history.length} 条历史记录`);
                    // 添加所有历史记录项
                    data.history.forEach(item => {
                        const historyItem = document.createElement('div');
                        historyItem.className = 'history-item';
                        historyItem.dataset.id = item.id;
                        
                        // 获取历史记录类型的显示名称
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
                        
                        // 创建历史记录项的内容，使用item.source来显示来源信息
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
                        
                        // 为删除按钮添加事件监听器
                        const deleteBtn = historyItem.querySelector('.delete-history-btn');
                        deleteBtn.addEventListener('click', () => {
                            deleteHistoryRecord(item.id);
                        });
                        
                        // 为复制按钮添加事件监听器
                        const copyBtn = historyItem.querySelector('.copy-history-btn');
                        copyBtn.addEventListener('click', () => {
                            copyToClipboard(item.content || '(无内容)');
                            showToast('已复制到剪贴板');
                        });
                        
                        // 为插入到编辑器按钮添加事件监听器
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
                                
                                // 切换到第一个标签页并滚动到文本区域
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
                        
                        // 添加到容器中
                        historyContainer.appendChild(historyItem);
                    });
                } else {
                    console.log("没有历史记录");
                    // 没有历史记录时显示提示
                    historyContainer.innerHTML = '<div class="empty-history">暂无历史记录</div>';
                }
                
                // 触发历史记录加载完成事件
                document.dispatchEvent(new Event('historyLoaded'));
            }
        } catch (error) {
            console.error('获取历史记录出错:', error);
            // 显示错误信息
            if (historyContainer) {
                historyContainer.innerHTML = `<div class="empty-history error">获取历史记录失败: ${error.message}</div>`;
            }
            showToast('获取历史记录失败: ' + error.message);
        }
    }
    
    // 删除单条历史记录
    async function deleteHistoryRecord(recordId) {
        try {
            showLoading('删除中...');
            const response = await fetch(`/history/${recordId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // 刷新历史记录
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
    
    // 清空全部历史记录
    async function clearHistory() {
        try {
            // 显示确认对话框
            showConfirmDialog('确定要清空所有历史记录吗？此操作不可撤销。', async () => {
                try {
                    showLoading('清空中...');
                    const response = await fetch('/history', {
                        method: 'DELETE'
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        // 刷新历史记录
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
});
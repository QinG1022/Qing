/**
 * 图片处理和OCR模块
 * 版本: 1.2
 * 最后更新: 2024-05-20
 * 描述: 提供图片上传、预览、OCR文字识别和PDF生成功能
 */

// 将关键函数挂载到window对象，使其在全局可用
window.showLoading = function(message = '处理中...') {
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingMessage = document.getElementById('loadingMessage');
    
    if (loadingMessage) {
        loadingMessage.textContent = message;
    }
    
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }
};

window.hideLoading = function() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
};

window.showToast = function(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'info';
    switch (type) {
        case 'success': icon = 'check_circle'; break;
        case 'error': icon = 'error'; break;
        case 'warning': icon = 'warning'; break;
    }
    
    toast.innerHTML = `
        <span class="material-icons">${icon}</span>
        <span class="toast-message">${message}</span>
    `;
    
    toastContainer.appendChild(toast);
    
    // 自动移除提示
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => {
            if (toastContainer.contains(toast)) {
                toastContainer.removeChild(toast);
            }
        }, 300);
    }, 3000);
};

/**
 * 执行OCR文字识别
 * 全局函数，允许main.js调用
 */
window.performOCR = function() {
    // 调用原有的processOcr函数执行OCR操作
    if (typeof window.processOcr === 'function') {
        window.processOcr();
    } else {
        console.error('OCR处理函数未定义');
        window.showToast('OCR功能初始化失败', 'error');
    }
};

/**
 * 生成PDF文档
 * 全局函数，允许main.js调用
 */
window.generatePDF = function() {
    // 获取DOM元素
    const textContent = document.getElementById('textContent');
    const imageUploadInput = document.getElementById('imageUpload');
    
    // 检查基本内容
    const content = textContent ? textContent.value.trim() : '';
    const hasImages = imageUploadInput && imageUploadInput.files.length > 0;
    
    // 基本验证
    if (!content && !hasImages) {
        window.showToast('请至少输入文本或选择图片', 'warning');
        return;
    }
    
    // 获取PDF生成模块中定义的完整功能
    const pdfOcrModule = document.querySelector('#ocrPdfFeature');
    if (pdfOcrModule && typeof generatePDF === 'function') {
        // 如果在模块作用域内找到了函数，调用它
        generatePDF();
    } else {
        console.error('PDF生成函数未找到');
        window.showToast('PDF生成功能初始化失败', 'error');
    }
};

/**
 * 处理图片OCR任务状态
 * 
 * @param {string} taskId - OCR任务ID
 * @param {number} totalFiles - 总文件数
 */
window.pollOCRStatus = function(taskId, totalFiles) {
    window.showLoading('识别图片文字中...(0%)');
    
    let pollCount = 0;
    const maxPolls = 120; // 设置最大轮询次数，防止无限轮询
    
    const intervalId = setInterval(async () => {
        try {
            pollCount++;
            if (pollCount > maxPolls) {
                clearInterval(intervalId);
                window.hideLoading();
                window.showToast('OCR处理超时，请重试', 'error');
                const ocrBtn = document.getElementById('ocrBtn');
                if (ocrBtn) ocrBtn.disabled = false;
                return;
            }
            
            const response = await fetch(`/tasks/${taskId}`);
            
            if (!response.ok) {
                throw new Error(`服务器响应错误(${response.status})`);
            }
            
            const data = await response.json();
            
            // 根据任务状态处理结果
            switch (data.status) {
                case 'SUCCESS':
                    clearInterval(intervalId);
                    window.hideLoading();
                    
                    // 验证结果数据
                    if (!data.result || !data.result.results) {
                        throw new Error('服务器返回的结果数据无效');
                    }
                    
                    window.handleOCRResults(data.result.results);
                    const ocrBtn = document.getElementById('ocrBtn');
                    if (ocrBtn) ocrBtn.disabled = false;
                    
                    // 处理成功后刷新历史记录
                    if (typeof window.loadHistory === 'function') {
                        setTimeout(window.loadHistory, 500);
                    }
                    break;
                    
                case 'FAILURE':
                    clearInterval(intervalId);
                    window.hideLoading();
                    window.showToast(`OCR处理失败: ${data.error || '未知错误'}`, 'error');
                    const ocrBtnFail = document.getElementById('ocrBtn');
                    if (ocrBtnFail) ocrBtnFail.disabled = false;
                    break;
                    
                case 'PENDING':
                case 'STARTED':
                    // 更新处理进度
                    const progress = data.progress || 0;
                    document.getElementById('loadingMessage').textContent = 
                        `识别图片文字中...(${Math.round(progress * 100)}%)`;
                    break;
                    
                default:
                    document.getElementById('loadingMessage').textContent = 
                        data.message || '识别中...';
            }
        } catch (error) {
            console.error('轮询OCR状态失败:', error);
            clearInterval(intervalId);
            window.hideLoading();
            window.showToast(`状态查询失败: ${error.message}`, 'error');
            const ocrBtnErr = document.getElementById('ocrBtn');
            if (ocrBtnErr) ocrBtnErr.disabled = false;
        }
    }, 1500); // 增加轮询间隔，减少服务器负担
};

/**
 * 处理OCR识别结果
 * 
 * @param {Array} results - OCR识别结果数组
 */
window.handleOCRResults = function(results) {
    const ocrResult = document.getElementById('ocrResult');
    const textContent = document.getElementById('textContent');
    if (!ocrResult) return;
    
    ocrResult.innerHTML = '';
    
    if (!results || !Array.isArray(results) || results.length === 0) {
        window.showToast('未识别到任何文本', 'warning');
        ocrResult.innerHTML = '<div class="empty-result">未识别到任何文本内容</div>';
        return;
    }
    
    // 过滤掉空文本结果
    const validResults = results.filter(result => 
        result && result.text && result.text.trim().length > 0);
        
    if (validResults.length === 0) {
        window.showToast('未识别到有效文本', 'warning');
        ocrResult.innerHTML = '<div class="empty-result">未识别到有效文本内容</div>';
        return;
    }
    
    // 创建全部合并按钮
    const mergeAllDiv = document.createElement('div');
    mergeAllDiv.className = 'merge-all-container';
    mergeAllDiv.innerHTML = `
        <button class="btn merge-all-btn">
            <span class="material-icons">format_textdirection_r_to_l</span>
            <span>全部合并到文本</span>
        </button>
    `;
    ocrResult.appendChild(mergeAllDiv);
    
    const mergeAllBtn = mergeAllDiv.querySelector('.merge-all-btn');
    mergeAllBtn.addEventListener('click', window.mergeAllText);
    
    // 为每个OCR结果创建展示元素
    const resultsContainer = document.createElement('div');
    resultsContainer.className = 'ocr-results-container';
    ocrResult.appendChild(resultsContainer);
    
    // 计算总文字量
    const totalChars = validResults.reduce((sum, result) => sum + (result.text?.length || 0), 0);
    
    validResults.forEach((result, index) => {
        const div = document.createElement('div');
        div.className = 'ocr-item';
        
        // 准备显示文本，处理长文本
        const displayText = result.text;
        const isLongText = displayText.length > 150;
        
        div.innerHTML = `
            <div class="ocr-item-header">
                <div class="ocr-item-source">${result.path ? `源文件: ${result.path.split('/').pop()}` : `结果 #${index + 1}`}</div>
                ${result.confidence !== undefined ? `<div class="ocr-item-confidence">置信度: ${Math.round(result.confidence)}%</div>` : ''}
            </div>
            <div class="ocr-text ${isLongText ? 'collapsible' : ''}">${displayText}</div>
            ${isLongText ? '<div class="expand-btn">展开全文</div>' : ''}
            <div class="ocr-actions">
                <button class="btn add-to-text-btn">
                    <span class="material-icons">add</span>
                    <span>添加到文本</span>
                </button>
            </div>
        `;
        
        // 添加长文本展开/折叠功能
        if (isLongText) {
            const expandBtn = div.querySelector('.expand-btn');
            const textDiv = div.querySelector('.ocr-text');
            
            expandBtn.addEventListener('click', function() {
                if (textDiv.classList.contains('expanded')) {
                    textDiv.classList.remove('expanded');
                    this.textContent = '展开全文';
                } else {
                    textDiv.classList.add('expanded');
                    this.textContent = '收起文本';
                }
            });
        }
        
        // 添加单个合并按钮事件
        const addToTextBtn = div.querySelector('.add-to-text-btn');
        addToTextBtn.addEventListener('click', function() {
            window.mergeText(result.text, this);
        });
        
        resultsContainer.appendChild(div);
    });
    
    // 显示OCR结果统计信息
    const statsDiv = document.createElement('div');
    statsDiv.className = 'ocr-stats';
    statsDiv.innerHTML = `
        <div>识别结果: ${validResults.length} 项</div>
        <div>总字数: ${totalChars} 字</div>
    `;
    ocrResult.insertBefore(statsDiv, resultsContainer);
    
    // 显示OCR结果区域
    ocrResult.style.display = 'block';
    
    // 滚动到OCR结果区域
    ocrResult.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // 显示成功提示
    window.showToast(`OCR识别完成，共 ${validResults.length} 项结果`, 'success');
};

/**
 * 合并单个OCR结果到文本区域
 * 
 * @param {string} text - 要合并的OCR文本内容
 * @param {HTMLElement} button - 触发合并的按钮元素
 */
window.mergeText = function(text, button) {
    const textContent = document.getElementById('textContent');
    if (!text || !textContent) return;
    
    const currentValue = textContent.value;
    
    // 如果文本区已有内容，则添加换行符再添加新文本
    if (currentValue) {
        textContent.value = currentValue + '\n\n' + text;
    } else {
        textContent.value = text;
    }
    
    // 设置标志，表示用户已添加OCR文本
    window.ocrTextAdded = true;
    
    // 更改按钮状态和提示
    button.disabled = true;
    button.innerHTML = '<span class="material-icons">check</span><span>已添加</span>';
    
    // 显示提示
    window.showToast('OCR文本已添加到编辑器', 'success');
    
    // 聚焦到文本编辑区
    textContent.scrollIntoView({ behavior: 'smooth' });
    setTimeout(() => {
        textContent.focus();
        // 将光标移动到文本末尾
        textContent.selectionStart = textContent.selectionEnd = textContent.value.length;
    }, 300);
};

/**
 * 合并所有OCR结果到文本区域
 */
window.mergeAllText = function() {
    const textContent = document.getElementById('textContent');
    const ocrItems = document.querySelectorAll('.ocr-item .ocr-text');
    if (!ocrItems.length || !textContent) {
        window.showToast('没有可合并的OCR结果', 'warning');
        return;
    }
    
    const texts = Array.from(ocrItems).map(item => item.textContent.trim()).filter(text => text.length > 0);
    
    if (texts.length === 0) {
        window.showToast('没有可合并的有效文本', 'warning');
        return;
    }
    
    const newText = texts.join('\n\n');
    
    const currentValue = textContent.value;
    if (currentValue) {
        textContent.value = currentValue + '\n\n' + newText;
    } else {
        textContent.value = newText;
    }
    
    // 设置标志，表示用户已添加OCR文本
    window.ocrTextAdded = true;
    
    // 禁用所有"添加"按钮
    document.querySelectorAll('.ocr-item .add-to-text-btn').forEach(btn => {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-icons">check</span><span>已添加</span>';
    });
    
    // 禁用"全部合并"按钮
    document.querySelector('.merge-all-btn').disabled = true;
    
    // 显示提示
    window.showToast(`已合并 ${texts.length} 项OCR文本到编辑器`, 'success');
    
    // 聚焦到文本编辑区
    textContent.scrollIntoView({ behavior: 'smooth' });
    setTimeout(() => {
        textContent.focus();
        // 将光标移动到文本末尾
        textContent.selectionStart = textContent.selectionEnd = textContent.value.length;
    }, 300);
};

// OCR识别处理全局函数
window.processOcr = async function() {
    const imageUploadInput = document.getElementById('imageUpload');
    const ocrBtn = document.getElementById('ocrBtn');
    
    // 检查图片是否已上传
    if (!imageUploadInput || !imageUploadInput.files.length) {
        window.showToast('请先选择图片', 'warning');
        return;
    }

    // 准备上传数据
    const formData = new FormData();
    const fileCount = imageUploadInput.files.length;
    Array.from(imageUploadInput.files).forEach((file, index) => {
        formData.append('images', file);
    });
    
    // 禁用按钮并显示加载状态
    ocrBtn.disabled = true;
    window.showLoading(`上传图片中...(0/${fileCount})`);
    
    try {
        // 发送OCR请求
        const response = await fetch('/process-images', {
            method: 'POST',
            body: formData
        });
        
        // 检查响应状态
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `服务器响应错误(${response.status})`);
        }
        
        // 解析响应数据
        const result = await response.json();
        
        // 检查任务ID
        if (result.task_id) {
            // 开始轮询任务状态
            window.pollOCRStatus(result.task_id, fileCount);
        } else {
            throw new Error('服务器未返回任务ID');
        }
    } catch (error) {
        console.error('提交OCR任务失败:', error);
        window.hideLoading();
        window.showToast(`OCR处理失败: ${error.message}`, 'error');
        ocrBtn.disabled = false;
    }
};

/**
 * 处理图片上传和预览
 * 暴露给全局使用
 */
window.handleImageUpload = function(e) {
    // 获取必要的DOM元素
    const imagePreview = document.getElementById('imagePreview');
    const ocrBtn = document.getElementById('ocrBtn');
    const ocrResult = document.getElementById('ocrResult');
    
    // 清空OCR结果区域
    if (ocrResult) {
        ocrResult.innerHTML = '';
    }
    
    // 图片预览逻辑
    if (imagePreview) {
        imagePreview.innerHTML = '';
        if (e.target.files.length > 0) {
            ocrBtn.disabled = false;
            
            // 筛选有效图片文件
            const validFiles = Array.from(e.target.files).filter(file => 
                file.type.startsWith('image/'));
            
            if (validFiles.length === 0) {
                window.showToast('没有有效的图片文件', 'warning');
                ocrBtn.disabled = true;
                return;
            }
            
            // 为每个图片创建预览元素
            validFiles.forEach(file => {
                const reader = new FileReader();
                const div = document.createElement('div');
                div.className = 'preview-item';
                
                reader.onload = e => {
                    div.innerHTML = `
                        <img src="${e.target.result}" alt="${file.name}">
                        <div class="file-info">
                            <span>${file.name.length > 20 ? file.name.substring(0, 17) + '...' : file.name}</span>
                            <span>${(file.size / 1024).toFixed(1)} KB</span>
                        </div>
                    `;
                };
                
                reader.readAsDataURL(file);
                imagePreview.appendChild(div);
            });
            
            // 如果文件数量过多，显示提示
            if (validFiles.length > 5) {
                window.showToast(`已选择${validFiles.length}张图片，处理可能需要较长时间`, 'info');
            }
        } else {
            ocrBtn.disabled = true;
        }
    }
};

document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const imageUploadInput = document.getElementById('imageUpload');
    const imagePreview = document.getElementById('imagePreview');
    const ocrBtn = document.getElementById('ocrBtn');
    const generatePdfBtn = document.getElementById('generatePdfBtn');
    const textContent = document.getElementById('textContent');
    const ocrResult = document.getElementById('ocrResult');
    const generateResult = document.getElementById('generateResult');
    const imageUploadArea = document.getElementById('imageUploadArea');
    
    // 标记OCR文本是否已添加到编辑器
    window.ocrTextAdded = false;

    /**
     * 图片上传区域拖放功能和点击上传功能
     */
    if (imageUploadArea) {
        // 拖放功能
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            imageUploadArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            imageUploadArea.addEventListener(eventName, () => {
                imageUploadArea.classList.add('highlight');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            imageUploadArea.addEventListener(eventName, () => {
                imageUploadArea.classList.remove('highlight');
            }, false);
        });

        imageUploadArea.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            // 验证文件类型
            const validFiles = Array.from(files).filter(file => 
                file.type.startsWith('image/'));
                
            if (validFiles.length === 0) {
                window.showToast('请上传有效的图片文件', 'warning');
                return;
            }
            
            imageUploadInput.files = files;
            
            // 触发change事件，以便显示预览
            const event = new Event('change');
            imageUploadInput.dispatchEvent(event);
        }

        // 添加点击上传功能
        imageUploadArea.addEventListener('click', function() {
            // 模拟点击隐藏的文件输入框
            imageUploadInput.click();
        });
    }

    /**
     * 图片预览处理
     * 当用户选择图片文件时，显示预览并启用处理按钮
     */
    if (imageUploadInput) {
        imageUploadInput.addEventListener('change', window.handleImageUpload);
    }

    /**
     * 处理图片OCR按钮点击事件
     */
    if (ocrBtn) {
        ocrBtn.addEventListener('click', window.processOcr);
    }

    /**
     * 生成PDF文档按钮点击事件
     */
    if (generatePdfBtn) {
        generatePdfBtn.addEventListener('click', function() {
            generatePDF();
        });
    }

    /**
     * 生成PDF文档的主函数
     */
    async function generatePDF() {
        const content = textContent ? textContent.value.trim() : '';
        const hasImages = imageUploadInput && imageUploadInput.files.length > 0;
        const hasOCRResults = document.querySelector('.ocr-item') !== null;
        
        // 基本验证
        if (!content && !hasImages) {
            window.showToast('请至少输入文本或选择图片', 'warning');
            return;
        }

        // 简化决策逻辑
        let includeImages = false;
        
        // 情况1: 只有图片 - 直接使用图片
        if (hasImages && !content) {
            includeImages = true;
            await handleSubmit(includeImages);
            return;
        }
        
        // 情况2: 只有文本 - 只使用文本
        if (content && !hasImages) {
            includeImages = false;
            await handleSubmit(includeImages);
            return;
        }
        
        // 情况3: 有文本和图片 - 询问用户
        showConfirmDialog(
            '检测到同时存在文本和图片，您希望如何生成文档？\n\n选择"是"：将图片和文字一起生成文档\n选择"否"：仅使用文本生成文档',
            async () => await handleSubmit(true),  // 包含图片
            async () => await handleSubmit(false)  // 不包含图片
        );
    }

    /**
     * 处理表单提交，生成PDF文档
     * 
     * @param {boolean} includeImages - 是否包含图片
     * @returns {Promise<void>}    
     */
    async function handleSubmit(includeImages) {
        try {
            const content = textContent ? textContent.value.trim() : '';
            if (!content && (!includeImages || !imageUploadInput || !imageUploadInput.files.length)) {
                window.showToast('请输入文本内容或上传图片', 'warning');
                return;
            }
            
            // 禁用生成按钮
            generatePdfBtn.disabled = true;
            
            window.showLoading('准备生成文档...');
            const formData = new FormData();
            formData.append('content', content); 
            
            // 添加图片文件（如果需要）
            if (includeImages && imageUploadInput && imageUploadInput.files.length) {
                const imageCount = imageUploadInput.files.length;
                Array.from(imageUploadInput.files).forEach((file, index) => {
                    if (file.type.startsWith('image/')) {
                        formData.append('images', file);
                    }
                });
                
                window.showLoading(`正在处理图片(0/${imageCount})...`);
            }
            
            // 发送生成请求
            const response = await fetch('/generate', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `请求失败(${response.status})`);
            }

            const data = await response.json();
            
            if (data.task_id) {
                if (content) {
                    // 文本内容已提交，刷新历史记录
                    if (typeof window.loadHistory === 'function') {
                        setTimeout(window.loadHistory, 500);
                    }
                }
                
                // 开始轮询生成状态
                pollGenerateStatus(data.task_id); 
            } else {
                throw new Error('服务器未返回任务ID');
            }

        } catch (error) {
            console.error('生成PDF文档失败:', error); 
            window.hideLoading(); 
            window.showToast(`生成失败: ${error.message}`, 'error');
            generatePdfBtn.disabled = false;
        }
    }

    /**
     * 轮询生成PDF任务状态
     * 
     * @param {string} taskId - 任务ID
     */
    function pollGenerateStatus(taskId) {
        window.showLoading('生成文档中...');
        
        let pollCount = 0;
        const maxPolls = 60; // 设置最大轮询次数
        
        const intervalId = setInterval(async () => {
            try {
                pollCount++;
                if (pollCount > maxPolls) {
                    clearInterval(intervalId);
                    window.hideLoading();
                    window.showToast('文档生成超时，请重试', 'error');
                    generatePdfBtn.disabled = false;
                    return;
                }
                
                const response = await fetch(`/tasks/${taskId}`);
                
                if (!response.ok) {
                    throw new Error(`服务器响应错误(${response.status})`);
                }
                
                const data = await response.json();
                
                // 根据任务状态处理结果
                switch (data.status) {
                    case 'SUCCESS':
                        clearInterval(intervalId);
                        window.hideLoading();
                        
                        // 处理不同的结果格式
                        // data.result可能是字符串(文件名)或对象(包含file_url)
                        handleGenerateResult(data.result);
                        generatePdfBtn.disabled = false;
                        
                        // 处理成功后刷新历史记录
                        if (typeof window.loadHistory === 'function') {
                            setTimeout(window.loadHistory, 500);
                        }
                        break;
                        
                    case 'FAILURE':
                        clearInterval(intervalId);
                        window.hideLoading();
                        window.showToast(`生成文档失败: ${data.error || '未知错误'}`, 'error');
                        generatePdfBtn.disabled = false;
                        break;
                        
                    case 'PENDING':
                    case 'STARTED':
                        // 更新处理进度
                        const progress = data.progress || 0;
                        document.getElementById('loadingMessage').textContent = 
                            `生成文档中...(${Math.round(progress * 100)}%)`;
                        break;
                        
                    default:
                        document.getElementById('loadingMessage').textContent = 
                            data.message || '生成中...';
                }
            } catch (error) {
                console.error('轮询生成状态失败:', error);
                clearInterval(intervalId);
                window.hideLoading();
                window.showToast(`状态查询失败: ${error.message}`, 'error');
                generatePdfBtn.disabled = false;
            }
        }, 1500); // 增加轮询间隔
    }

    /**
     * 处理文档生成结果
     * 
     * @param {Object|string} result - 生成结果，可能是对象或字符串
     */
    function handleGenerateResult(result) {
        // 处理不同的结果格式
        let fileUrl = '';
        let fileName = '';
        let fileType = 'pdf';
        let fileSize = '';
        
        // 情况1: result是对象且包含file_url
        if (result && typeof result === 'object' && result.file_url) {
            fileUrl = result.file_url;
            fileName = result.file_name || fileUrl.split('/').pop() || '文档';
            fileType = result.file_type || fileUrl.split('.').pop() || 'pdf';
            fileSize = result.file_size || '';
        }
        // 情况2: result是字符串(文件名)
        else if (result && typeof result === 'string') {
            fileName = result;
            fileType = result.split('.').pop() || 'pdf';
            // 构建下载URL (使用/download/路由)
            fileUrl = `/download/${result}`;
        }
        else {
            // 无效的结果
            window.showToast('文档生成结果无效', 'error');
            console.error('无效的生成结果:', result);
            return;
        }
        
        // 添加自动下载功能
        triggerAutomaticDownload(fileUrl, fileName);
        
        // 显示成功浮动通知
        showSuccessNotification(fileName, fileType, fileUrl, fileSize);
        
        // 显示成功提示
        window.showToast('文档生成成功，已开始下载', 'success');
        
        // 记录调试信息
        console.log('文档生成成功:', { 
            resultType: typeof result, 
            fileName: fileName, 
            fileUrl: fileUrl 
        });
    }
    
    /**
     * 触发自动下载
     * 
     * @param {string} fileUrl - 文件URL
     * @param {string} fileName - 文件名
     */
    function triggerAutomaticDownload(fileUrl, fileName) {
        // 创建一个不可见的链接元素
        const downloadLink = document.createElement('a');
        downloadLink.href = fileUrl;
        downloadLink.download = fileName; // 设置下载属性
        downloadLink.style.display = 'none';
        
        // 添加到文档并触发点击
        document.body.appendChild(downloadLink);
        downloadLink.click();
        
        // 短暂延迟后移除元素
        setTimeout(() => {
            document.body.removeChild(downloadLink);
        }, 100);
    }

    /**
     * 根据文件类型获取图标
     * 
     * @param {string} fileType - 文件类型
     * @returns {string} - 图标名称
     */
    function getFileTypeIcon(fileType) {
        switch(fileType.toLowerCase()) {
            case 'pdf': return 'picture_as_pdf';
            case 'doc':
            case 'docx': return 'description';
            case 'xls': 
            case 'xlsx': return 'table_chart';
            case 'ppt':
            case 'pptx': return 'slideshow';
            case 'txt': return 'text_snippet';
            case 'zip':
            case 'rar': return 'folder_zip';
            default: return 'insert_drive_file';
        }
    }

    /**
     * 显示确认对话框
     * 
     * @param {string} message - 显示的消息
     * @param {Function} confirmCallback - 确认按钮回调
     * @param {Function} cancelCallback - 取消按钮回调
     */
    function showConfirmDialog(message, confirmCallback, cancelCallback) {
        // 创建对话框元素
        const dialogOverlay = document.createElement('div');
        dialogOverlay.className = 'dialog-overlay';
        
        const dialogBox = document.createElement('div');
        dialogBox.className = 'dialog-box';
        
        dialogBox.innerHTML = `
            <div class="dialog-content">
                <p>${message}</p>
            </div>
            <div class="dialog-buttons">
                <button class="btn cancel-btn">否</button>
                <button class="btn confirm-btn primary-btn">是</button>
            </div>
        `;
        
        dialogOverlay.appendChild(dialogBox);
        document.body.appendChild(dialogOverlay);
        
        // 添加按钮事件
        const confirmBtn = dialogBox.querySelector('.confirm-btn');
        const cancelBtn = dialogBox.querySelector('.cancel-btn');
        
        confirmBtn.addEventListener('click', () => {
            document.body.removeChild(dialogOverlay);
            if (typeof confirmCallback === 'function') {
                confirmCallback();
            }
        });
        
        cancelBtn.addEventListener('click', () => {
            document.body.removeChild(dialogOverlay);
            if (typeof cancelCallback === 'function') {
                cancelCallback();
            }
        });
        
        // ESC键关闭对话框
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                document.body.removeChild(dialogOverlay);
                document.removeEventListener('keydown', handleKeyDown);
                if (typeof cancelCallback === 'function') {
                    cancelCallback();
                }
            }
        };
        
        document.addEventListener('keydown', handleKeyDown);
    }

    /**
     * 显示成功浮动通知
     * 
     * @param {string} fileName - 文件名
     * @param {string} fileType - 文件类型
     * @param {string} fileUrl - 文件URL
     * @param {string} fileSize - 文件大小
     */
    function showSuccessNotification(fileName, fileType, fileUrl, fileSize) {
        const fileIcon = getFileTypeIcon(fileType);
        
        // 移除任何已存在的通知
        const existingNotification = document.querySelector('.pdf-success-notification');
        if (existingNotification) {
            document.body.removeChild(existingNotification);
        }
        
        // 创建新的浮动通知
        const notification = document.createElement('div');
        notification.className = 'pdf-success-notification';
        notification.innerHTML = `
            <div class="notification-header">
                <span class="material-icons">check_circle</span>
                <span>文档生成成功</span>
                <button class="close-btn"><span class="material-icons">close</span></button>
            </div>
            <div class="notification-content">
                <div class="file-icon">
                    <span class="material-icons">${fileIcon}</span>
                    <span class="file-ext">${fileType.toUpperCase()}</span>
                </div>
                <div class="file-info">
                    <div class="file-name">${fileName}</div>
                    <div class="file-size">${fileSize}</div>
                    <div class="download-status">已自动开始下载</div>
                </div>
            </div>
        `;
        
        // 添加样式
        const style = document.createElement('style');
        if (!document.querySelector('#pdf-notification-style')) {
            style.id = 'pdf-notification-style';
            style.textContent = `
                .pdf-success-notification {
                    position: fixed;
                    top: 20px;
                    left: 20px;
                    width: 300px;
                    background-color: #fff;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    z-index: 9999;
                    overflow: hidden;
                    animation: slideIn 0.3s ease-out;
                }
                
                @keyframes slideIn {
                    from { transform: translateX(-100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                
                .pdf-success-notification .notification-header {
                    display: flex;
                    align-items: center;
                    padding: 12px 15px;
                    background-color: #4caf50;
                    color: white;
                }
                
                .pdf-success-notification .notification-header .material-icons {
                    margin-right: 8px;
                }
                
                .pdf-success-notification .close-btn {
                    margin-left: auto;
                    background: none;
                    border: none;
                    color: white;
                    cursor: pointer;
                }
                
                .pdf-success-notification .notification-content {
                    padding: 15px;
                    display: flex;
                    align-items: center;
                }
                
                .pdf-success-notification .file-icon {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    margin-right: 15px;
                }
                
                .pdf-success-notification .file-icon .material-icons {
                    font-size: 36px;
                    color: #f44336;
                }
                
                .pdf-success-notification .file-ext {
                    font-size: 10px;
                    font-weight: bold;
                    margin-top: 4px;
                }
                
                .pdf-success-notification .file-info {
                    flex: 1;
                }
                
                .pdf-success-notification .file-name {
                    font-weight: bold;
                    margin-bottom: 4px;
                    word-break: break-all;
                }
                
                .pdf-success-notification .file-size {
                    font-size: 12px;
                    color: #666;
                    margin-bottom: 8px;
                }
                
                .pdf-success-notification .download-status {
                    font-size: 12px;
                    color: #4caf50;
                    display: flex;
                    align-items: center;
                }
                
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(-100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(notification);
        
        // 添加关闭按钮事件
        const closeBtn = notification.querySelector('.close-btn');
        closeBtn.addEventListener('click', () => {
            document.body.removeChild(notification);
        });
        
        // 5秒后自动关闭
        setTimeout(() => {
            if (document.body.contains(notification)) {
                notification.style.animation = 'slideOut 0.3s ease-in forwards';
                notification.style.animationFillMode = 'forwards';
                
                setTimeout(() => {
                    if (document.body.contains(notification)) {
                        document.body.removeChild(notification);
                    }
                }, 300);
            }
        }, 5000);
    }
});
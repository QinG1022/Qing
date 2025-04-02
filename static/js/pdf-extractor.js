/**
 * PDF文本提取模块
 * 版本: 2.0
 * 最后更新: 2024-05-15
 * 描述: 提供PDF文件上传、预览、文本提取和结果显示功能
 */

/**
 * 提取PDF文本
 * 全局函数，允许main.js调用
 */
window.extractText = function() {
    const extractBtn = document.getElementById('extractBtn');
    
    // 检查是否有提取按钮并点击它，触发现有的处理逻辑
    if (extractBtn) {
        extractBtn.click();
    } else {
        console.error('PDF提取按钮未找到');
        if (typeof window.showToast === 'function') {
            window.showToast('PDF提取功能初始化失败', 'error');
        } else {
            alert('PDF提取功能初始化失败');
        }
    }
};

/**
 * 处理PDF文件上传
 * 全局函数，允许其他模块调用
 * 
 * @param {Event} e - 事件对象，包含已上传的文件信息
 */
window.handlePdfUpload = function(e) {
    const pdfPreview = document.getElementById('pdfPreview');
    const extractBtn = document.getElementById('extractBtn');
    const extractResults = document.getElementById('extractResult');
    
    // 清空预览区域
    if (pdfPreview) {
        pdfPreview.innerHTML = '';
    }
    
    // 禁用提取按钮，直到验证文件有效
    if (extractBtn) {
        extractBtn.disabled = true;
    }
    
    // 隐藏之前的结果
    if (extractResults) {
        extractResults.style.display = 'none';
    }
    
    // 隐藏文件信息和复制按钮（如果存在）
    const fileInfoContainer = document.getElementById('pdf-file-info');
    const copyAllBtn = document.getElementById('copy-all-btn');
    const pdfTextContent = document.getElementById('pdf-text-content');
    
    if (fileInfoContainer) fileInfoContainer.style.display = 'none';
    if (copyAllBtn) copyAllBtn.style.display = 'none';
    if (pdfTextContent) pdfTextContent.innerHTML = '';
    
    // 处理文件
    if (e.target.files.length > 0) {
        const file = e.target.files[0];
        if (file.type === 'application/pdf') {
            // 创建预览元素
            if (pdfPreview) {
                const div = document.createElement('div');
                div.className = 'pdf-preview-item';
                div.innerHTML = `
                    <div class="pdf-icon">
                        <span class="material-icons">picture_as_pdf</span>
                    </div>
                    <div class="file-info">
                        <div>${file.name}</div>
                        <div>${(file.size / (1024*1024)).toFixed(2)} MB</div>
                    </div>
                `;
                pdfPreview.appendChild(div);
                if (extractBtn) extractBtn.disabled = false;
            }
        } else {
            if (typeof window.showToast === 'function') {
                window.showToast('请选择PDF文件', 'warning');
            } else {
                alert('请选择PDF文件');
            }
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // DOM元素选择器
    const elements = {
        pdfInput: document.getElementById('pdfUpload'),
        pdfPreview: document.getElementById('pdfPreview'),
        extractBtn: document.getElementById('extractBtn'),
        extractResults: document.getElementById('extractResult'),
        pdfUploadArea: document.getElementById('pdfUploadArea')
    };
    
    // 创建UI组件
    const ui = setupUIComponents(elements);
    
    // 初始化事件监听器
    initEventListeners(elements, ui);
    
    // 初始化拖放功能
    initDragAndDrop(elements);
    
    /**
     * 设置UI组件
     * @param {Object} elements - DOM元素对象
     * @returns {Object} 创建的UI组件
     */
    function setupUIComponents(elements) {
        const ui = {};
        
        // 创建PDF文本内容显示容器
        ui.pdfTextContent = document.getElementById('pdf-text-content');
        if (!ui.pdfTextContent) {
            ui.pdfTextContent = document.createElement('div');
            ui.pdfTextContent.id = 'pdf-text-content';
            ui.pdfTextContent.className = 'pdf-text-content';
            elements.extractResults.appendChild(ui.pdfTextContent);
        }

        // 创建复制全部按钮
        ui.copyAllBtn = document.getElementById('copy-all-btn');
        if (!ui.copyAllBtn) {
            ui.copyAllBtn = document.createElement('button');
            ui.copyAllBtn.id = 'copy-all-btn';
            ui.copyAllBtn.className = 'btn primary-btn';
            ui.copyAllBtn.innerHTML = '<span class="material-icons">content_copy</span> 复制全部文本';
            ui.copyAllBtn.style.marginTop = '10px';
            ui.copyAllBtn.style.display = 'none'; // 初始隐藏
            elements.extractResults.insertBefore(ui.copyAllBtn, ui.pdfTextContent);
        }
        
        // 创建文件信息显示容器
        ui.fileInfoContainer = document.getElementById('pdf-file-info');
        if (!ui.fileInfoContainer) {
            ui.fileInfoContainer = document.createElement('div');
            ui.fileInfoContainer.id = 'pdf-file-info';
            ui.fileInfoContainer.className = 'pdf-file-info';
            ui.fileInfoContainer.innerHTML = `
                <p id="pdf-file-name">文件名: -</p>
                <p id="pdf-page-count">总页数: -</p>
                <p id="pdf-word-count">总字数: -</p>
            `;
            ui.fileInfoContainer.style.display = 'none'; // 初始隐藏
            elements.extractResults.insertBefore(ui.fileInfoContainer, ui.copyAllBtn);
        }
        
        return ui;
    }
    
    /**
     * 初始化事件监听器
     * @param {Object} elements - DOM元素对象
     * @param {Object} ui - UI组件对象
     */
    function initEventListeners(elements, ui) {
        // PDF文件选择器变更事件
        if (elements.pdfInput) {
            elements.pdfInput.addEventListener('change', (e) => handleFileSelection(e, elements, ui));
        }
        
        // 提取按钮点击事件
        if (elements.extractBtn) {
            elements.extractBtn.addEventListener('click', () => handleExtractButtonClick(elements, ui));
        }
        
        // 复制全部按钮点击事件
        if (ui.copyAllBtn) {
            ui.copyAllBtn.addEventListener('click', () => {
                const allText = Array.from(ui.pdfTextContent.querySelectorAll('.page-text'))
                    .map(el => el.textContent)
                    .join('\n\n');
                    
                copyToClipboard(allText);
                showToast('已复制全部文本到剪贴板');
            });
        }
    }
    
    /**
     * 初始化拖放功能
     * @param {Object} elements - DOM元素对象
     */
    function initDragAndDrop(elements) {
        const dropArea = elements.pdfUploadArea;
        if (!dropArea) return;
        
        // 阻止默认拖放行为
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        // 高亮拖放区域
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                dropArea.classList.add('highlight');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                dropArea.classList.remove('highlight');
            }, false);
        });
        
        // 处理文件拖放
        dropArea.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0 && files[0].type === 'application/pdf') {
                elements.pdfInput.files = files;
                // 触发change事件以更新UI
                const event = new Event('change');
                elements.pdfInput.dispatchEvent(event);
            } else {
                showToast('请上传PDF文件');
            }
        }, false);
        
        // 添加点击上传功能
        dropArea.addEventListener('click', () => {
            elements.pdfInput.click();
        }, false);
    }
    
    /**
     * 处理文件选择
     * @param {Event} e - 事件对象
     * @param {Object} elements - DOM元素对象
     * @param {Object} ui - UI组件对象
     */
    function handleFileSelection(e, elements, ui) {
        elements.pdfPreview.innerHTML = '';
        elements.extractBtn.disabled = true;
        
        // 隐藏之前的结果
        elements.extractResults.style.display = 'none';
        ui.fileInfoContainer.style.display = 'none';
        ui.copyAllBtn.style.display = 'none';
        ui.pdfTextContent.innerHTML = '';
        
        if (elements.pdfInput.files.length > 0) {
            const file = elements.pdfInput.files[0];
            if (file.type === 'application/pdf') {
                // 创建预览元素
                const div = document.createElement('div');
                div.className = 'pdf-preview-item';
                div.innerHTML = `
                    <div class="pdf-icon">
                        <span class="material-icons">picture_as_pdf</span>
                    </div>
                    <div class="file-info">
                        <div>${file.name}</div>
                        <div>${(file.size / (1024*1024)).toFixed(2)} MB</div>
                    </div>
                `;
                elements.pdfPreview.appendChild(div);
                elements.extractBtn.disabled = false;
            } else {
                showToast('请选择PDF文件');
            }
        }
    }
    
    /**
     * 处理提取按钮点击
     * @param {Object} elements - DOM元素对象
     * @param {Object} ui - UI组件对象
     */
    async function handleExtractButtonClick(elements, ui) {
        if (!elements.pdfInput.files.length) {
            showToast('请先选择一个PDF文件');
            return;
        }

        const formData = new FormData();
        formData.append('pdfs', elements.pdfInput.files[0]);
        
        // 直接操作加载元素确保显示
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            const loadingMessage = document.getElementById('loadingMessage');
            if (loadingMessage) {
                loadingMessage.textContent = '正在处理PDF文本提取...';
            }
            loadingOverlay.style.display = 'flex';
        }
        
        // 仍然调用showLoading保持兼容性
        showLoading('正在处理PDF文本提取...');
        
        elements.extractResults.style.display = 'none';
        elements.extractBtn.disabled = true;
        
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
                pollPDFExtractionStatus(result.task_id, elements, ui);
            } else {
                throw new Error('未能获取任务ID');
            }
        } catch (error) {
            console.error('提交任务失败:', error);
            // 直接隐藏加载元素
            if (loadingOverlay) {
                loadingOverlay.style.display = 'none';
            }
            hideLoading();
            setStatusMessage(`提交失败: ${error.message}`, true);
            elements.extractBtn.disabled = false;
            
            // 显示错误消息
            showToast(`提交失败: ${error.message}`);
        }
    }

    /**
     * 轮询PDF提取任务状态
     * @param {string} taskId - PDF提取任务ID
     * @param {Object} elements - DOM元素对象
     * @param {Object} ui - UI组件对象
     */
    function pollPDFExtractionStatus(taskId, elements, ui) {
        // 确保加载状态显示
        const loadingOverlay = document.getElementById('loadingOverlay');
        const loadingMessage = document.getElementById('loadingMessage');
        
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
            if (loadingMessage) {
                loadingMessage.textContent = '提取PDF文本中...';
            }
        }
        
        showLoading('提取PDF文本中...');
        console.log('开始轮询PDF提取状态，任务ID:', taskId);
        
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/tasks/${taskId}`);
                const data = await response.json();
                
                console.log('轮询状态:', data.status, data.message || '');
                
                // 更新加载消息
                if (loadingMessage && data.message) {
                    loadingMessage.textContent = data.message;
                }
                
                if (data.status === 'SUCCESS') {
                    clearInterval(intervalId);
                    
                    // 直接隐藏加载元素
                    if (loadingOverlay) {
                        loadingOverlay.style.display = 'none';
                    }
                    
                    hideLoading();
                    handlePDFResults(data.result, elements, ui);
                    elements.extractBtn.disabled = false;
                    
                    // 处理成功后刷新历史记录
                    console.log("PDF处理完成，刷新历史记录");
                    if (typeof fetchHistory === 'function') {
                        setTimeout(fetchHistory, 500);
                    }
                    
                    showToast('PDF文本提取完成');
                } else if (data.status === 'FAILURE') {
                    clearInterval(intervalId);
                    
                    // 直接隐藏加载元素
                    if (loadingOverlay) {
                        loadingOverlay.style.display = 'none';
                    }
                    
                    hideLoading();
                    setStatusMessage(`PDF处理失败: ${data.error || '未知错误'}`, true);
                    elements.extractBtn.disabled = false;
                    
                    showToast(`PDF处理失败: ${data.error || '未知错误'}`);
                } else {
                    // 更新加载消息
                    const message = data.message || '提取中...';
                    if (loadingMessage) {
                        loadingMessage.textContent = message;
                    }
                    showLoading(message);
                }
            } catch (error) {
                console.error('状态查询失败:', error);
                clearInterval(intervalId);
                
                // 直接隐藏加载元素
                if (loadingOverlay) {
                    loadingOverlay.style.display = 'none';
                }
                
                hideLoading();
                setStatusMessage('状态查询失败', true);
                elements.extractBtn.disabled = false;
                
                showToast('状态查询失败');
            }
        }, 1000);
    }

    /**
     * 处理PDF提取结果
     * @param {Object} result - PDF提取结果对象
     * @param {Object} elements - DOM元素对象
     * @param {Object} ui - UI组件对象
     */
    function handlePDFResults(result, elements, ui) {
        if (!result) {
            setStatusMessage('未能提取文本内容', true);
            return;
        }
        
        // 显示UI元素
        elements.extractResults.style.display = 'block';
        ui.fileInfoContainer.style.display = 'block';
        ui.copyAllBtn.style.display = 'block';
        
        if (result.results && result.results.length > 0) {
            const pdf = result.results[0];
            
            // 更新文件信息
            document.getElementById('pdf-file-name').textContent = `文件名: ${pdf.filename || '未知'}`;
            document.getElementById('pdf-page-count').textContent = `总页数: ${pdf.total_pages || 0}`;
            document.getElementById('pdf-word-count').textContent = `总字数: ${pdf.text_length || 0}`;
            
            // 清空之前的内容
            ui.pdfTextContent.innerHTML = '';
            
            if (pdf.pages && pdf.pages.length > 0) {
                // 有分页信息，按页显示
                pdf.pages.forEach((page) => {
                    const pageDiv = document.createElement('div');
                    pageDiv.className = 'pdf-text-page';
                    pageDiv.innerHTML = `
                        <h4>第 ${page.page_num} 页</h4>
                        <div class="page-text">${page.text || '(无文本内容)'}</div>
                        <button class="copy-btn btn btn-small" data-page="${page.page_num - 1}">
                            <span class="material-icons">content_copy</span> 复制此页文本
                        </button>
                    `;
                    ui.pdfTextContent.appendChild(pageDiv);
                });
                
                // 注册页面复制按钮事件
                ui.pdfTextContent.querySelectorAll('.copy-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const pageIndex = parseInt(this.dataset.page);
                        const text = pdf.pages[pageIndex].text;
                        copyToClipboard(text);
                        showToast('已复制到剪贴板');
                    });
                });
                
                clearStatusMessage();
            } else if (pdf.text) {
                // 没有分页信息但有文本，显示全部文本
                const pageDiv = document.createElement('div');
                pageDiv.className = 'pdf-text-page';
                pageDiv.innerHTML = `
                    <h4>文本内容</h4>
                    <div class="page-text">${pdf.text || '(无文本内容)'}</div>
                `;
                ui.pdfTextContent.appendChild(pageDiv);
                clearStatusMessage();
            } else {
                setStatusMessage('PDF中未发现文本内容', true);
            }
        } else {
            setStatusMessage('PDF中未发现文本内容', true);
        }
    }
    
    /**
     * 复制文本到剪贴板
     * @param {string} text - 要复制的文本
     */
    function copyToClipboard(text) {
        if (window.copyToClipboard) {
            window.copyToClipboard(text);
        } else {
            try {
                navigator.clipboard.writeText(text)
                    .then(() => console.log('文本已复制到剪贴板'))
                    .catch(err => {
                        console.error('无法使用Clipboard API复制: ', err);
                        fallbackCopy();
                    });
            } catch (err) {
                console.error('复制失败: ', err);
                fallbackCopy();
            }
            
            // 后备复制方法
            function fallbackCopy() {
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
            }
        }
    }
    
    // 工具函数 - 使用main.js提供的方法或提供后备实现
    
    /**
     * 显示Toast消息
     * @param {string} message - 消息内容
     */
    function showToast(message) {
        if (window.showToast) {
            window.showToast(message);
        } else {
            console.log(message);
            // 简单的后备实现
            const toast = document.createElement('div');
            toast.className = 'simple-toast';
            toast.textContent = message;
            toast.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:10px 20px;border-radius:4px;z-index:9999;';
            document.body.appendChild(toast);
            setTimeout(() => document.body.removeChild(toast), 3000);
        }
    }
    
    /**
     * 显示加载状态
     * @param {string} message - 加载提示消息
     */
    function showLoading(message) {
        if (window.showLoading) {
            window.showLoading(message);
        } else {
            console.log('Loading: ' + message);
        }
    }
    
    /**
     * 隐藏加载状态
     */
    function hideLoading() {
        if (window.hideLoading) {
            window.hideLoading();
        }
    }

    /**
     * 设置状态消息
     * @param {string} message - 状态消息
     * @param {boolean} isError - 是否为错误消息
     */
    function setStatusMessage(message, isError) {
        if (window.setStatusMessage) {
            window.setStatusMessage(message, isError);
        } else {
            console.log((isError ? 'Error: ' : 'Status: ') + message);
        }
    }
    
    /**
     * 清除状态消息
     */
    function clearStatusMessage() {
        if (window.clearStatusMessage) {
            window.clearStatusMessage();
        }
    }
});
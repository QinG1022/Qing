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
            document.body.addEventListener(eventName, preventDefaults, false); // 防止浏览器打开文件
        });
    
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
    
        // 高亮拖放区域
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                if (!dropArea.classList.contains('highlight')) {
                    dropArea.classList.add('highlight');
                }
            }, false);
        });
    
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                 dropArea.classList.remove('highlight');
            }, false);
        });
    
        // 处理文件拖放
        dropArea.addEventListener('drop', (e) => {
            dropArea.classList.remove('highlight'); // 确保移除高亮
    
            const dt = e.dataTransfer;
            const files = dt.files;
            const pdfFiles = []; // 存放有效的PDF文件
    
            if (files && files.length > 0) {
                for (let i = 0; i < files.length; i++) {
                    // 严格检查 MIME 类型
                    if (files[i].type === 'application/pdf') {
                        pdfFiles.push(files[i]);
                    } else {
                         if (typeof showToast === 'function') {
                            showToast(`文件 "${files[i].name}" 不是PDF格式，已被忽略。`, 'warning');
                         } else {
                             console.warn(`文件 "${files[i].name}" 不是PDF格式，已被忽略。`);
                         }
                    }
                }
    
                if (pdfFiles.length > 0) {
                    // 使用 DataTransfer API 创建新的 FileList (现代浏览器支持)
                    const dataTransfer = new DataTransfer();
                    pdfFiles.forEach(file => dataTransfer.items.add(file));
    
                    // 更新 input 元素的 files 属性
                    elements.pdfInput.files = dataTransfer.files;
    
                    // 手动触发 change 事件以使用更新后的 handleFileSelection 更新UI
                    const event = new Event('change', { bubbles: true });
                    elements.pdfInput.dispatchEvent(event);
    
                } else {
                     // 如果拖放的文件中没有有效的PDF
                     if (typeof showToast === 'function') {
                        showToast('请拖放有效的PDF文件。', 'error');
                     } else {
                         console.error('请拖放有效的PDF文件。');
                     }
                }
            }
        }, false);
    
        // 点击上传功能 
        dropArea.addEventListener('click', () => {
            // 确保不会因为拖放区域覆盖而无法点击
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
    if (ui.fileInfoContainer) ui.fileInfoContainer.style.display = 'none';
    if (ui.copyAllBtn) ui.copyAllBtn.style.display = 'none';
    if (ui.pdfTextContent) ui.pdfTextContent.innerHTML = '';

    let validFilesFound = false; // 标记是否找到有效PDF文件
    const files = elements.pdfInput.files; // 获取所有选中的文件

    if (files && files.length > 0) {
        // 遍历所有选中的文件
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (file.type === 'application/pdf') {
                // 为每个有效的PDF文件创建预览元素
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
                validFilesFound = true; // 找到至少一个有效文件
            } else {
                // 如果包含非PDF文件，给出提示 (需要 showToast 函数可用)
                if (typeof showToast === 'function') {
                    showToast(`文件 "${file.name}" 不是PDF格式，将被忽略。`, 'warning');
                } else {
                    console.warn(`文件 "${file.name}" 不是PDF格式，将被忽略。`);
                }
            }
        }
    }

    // 如果至少有一个有效的PDF文件被选中，则启用提取按钮
    if (validFilesFound) {
        elements.extractBtn.disabled = false;
    } else {
        // 如果没有选择文件或所有文件都无效
        if (files && files.length > 0) {
            if (typeof showToast === 'function') {
                showToast('未选择有效的PDF文件。', 'error');
            } else {
                console.error('未选择有效的PDF文件。');
            }
        }
        // 保持按钮禁用状态
    }
}
    
    /**
     * 处理提取按钮点击
     * @param {Object} elements - DOM元素对象
     * @param {Object} ui - UI组件对象
     */
    async function handleExtractButtonClick(elements, ui) {
        const files = elements.pdfInput.files; // 获取所有选定的文件
    if (!files || files.length === 0) {
        showToast('请先选择至少一个PDF文件');
        return;
    }

    const formData = new FormData();
    let pdfCount = 0;
    // 遍历所有选中的文件
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        // 确保只上传PDF文件
        if (file.type === 'application/pdf') {
            // 使用相同的键名 'pdfs' 多次 append，后端 getlist('pdfs') 会收到列表
            formData.append('pdfs', file, file.name);
            pdfCount++;
        }
    }

    // 如果过滤后没有有效的PDF文件
    if (pdfCount === 0) {
        showToast('选择的文件中没有有效的PDF文件可供上传。', 'error');
        return;
    }

    // 显示加载状态，提示正在处理的文件数量
    const loadingMessageText = `正在处理 ${pdfCount} 个PDF文件...`;
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        const loadingMessageElement = document.getElementById('loadingMessage');
        if (loadingMessageElement) {
            loadingMessageElement.textContent = loadingMessageText;
        }
        loadingOverlay.style.display = 'flex';
    }
    // 仍然调用 showLoading 保持兼容性（如果 main.js 中也控制加载）
    if (typeof showLoading === 'function') showLoading(loadingMessageText);


    elements.extractResults.style.display = 'none';
    elements.extractBtn.disabled = true;

    try {
        const response = await fetch('/extract-pdf', {
            method: 'POST',
            body: formData // formData 现在包含所有有效的PDF文件
        });

        if (!response.ok) {
            // 尝试解析错误信息
             let errorMsg = '服务器响应错误';
             try {
                 const errorData = await response.json();
                 errorMsg = errorData.error || errorMsg;
             } catch (e) {
                 // 无法解析JSON，使用通用错误
             }
            throw new Error(errorMsg);
        }

        const result = await response.json();

        if (result.task_id) {
            // 启动轮询，传入 elements 和 ui 以便后续更新
            pollPDFExtractionStatus(result.task_id, elements, ui);
        } else {
            throw new Error(result.error || '未能获取任务ID');
        }
    } catch (error) {
        console.error('提交任务失败:', error);
        // 直接隐藏加载元素
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
        // 调用 hideLoading 保持兼容性
         if (typeof hideLoading === 'function') hideLoading();
        // 显示状态消息
         if (typeof setStatusMessage === 'function') setStatusMessage(`提交失败: ${error.message}`, true);
        elements.extractBtn.disabled = false; // 重新启用按钮

        // 显示Toast提示
        if (typeof showToast === 'function') showToast(`提交失败: ${error.message}`, 'error');
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
        // 检查是否有有效的结果数据
        if (!result || !result.results || !Array.isArray(result.results) || result.results.length === 0) {
            const msg = '未能提取任何文本内容或返回结果格式无效。';
             if (typeof setStatusMessage === 'function') setStatusMessage(msg, true);
            elements.extractResults.style.display = 'block'; // 仍然显示结果区以展示消息
            if (ui.pdfTextContent) ui.pdfTextContent.innerHTML = `<p>${msg}</p>`;
            // 隐藏可能存在的旧的文件信息和复制按钮
            if (ui.fileInfoContainer) ui.fileInfoContainer.style.display = 'none';
            if (ui.copyAllBtn) ui.copyAllBtn.style.display = 'none';
            return;
        }
    
        // 显示结果区域
        elements.extractResults.style.display = 'block';
    
        // 隐藏旧的单一文件信息区域 (因为现在要为每个文件显示信息)
        if (ui.fileInfoContainer) ui.fileInfoContainer.style.display = 'none';
    
        // 显示“复制全部”按钮（如果需要）
        if (ui.copyAllBtn) ui.copyAllBtn.style.display = 'block';
    
        // 清空之前的内容
        if (ui.pdfTextContent) ui.pdfTextContent.innerHTML = '';
    
        let allExtractedText = []; // 用于“复制全部”功能
    
        // 遍历后端返回的每个PDF的处理结果
        result.results.forEach((pdfResult, index) => {
            // 为每个文件创建一个结果容器
            const fileResultDiv = document.createElement('div');
            fileResultDiv.className = 'pdf-file-result';
            // 添加一些样式区分不同的文件结果
            fileResultDiv.style.marginBottom = '25px';
            fileResultDiv.style.border = '1px solid var(--border-color)';
            fileResultDiv.style.padding = '15px';
            fileResultDiv.style.borderRadius = 'var(--border-radius)';
            fileResultDiv.style.backgroundColor = 'var(--card-bg)'; // 使用卡片背景色
    
            // 文件信息头部
            const fileHeader = document.createElement('div');
            fileHeader.className = 'pdf-result-header';
            fileHeader.style.marginBottom = '15px';
            fileHeader.style.borderBottom = '1px solid var(--border-color)';
            fileHeader.style.paddingBottom = '10px';
            fileHeader.innerHTML = `
                <h4>文件: ${pdfResult.filename || `文件 ${index + 1}`}</h4>
                <p style="font-size: 0.9em; color: var(--text-secondary);">总页数: ${pdfResult.total_pages || 0} | 总字数: ${pdfResult.text_length || 0}</p>
            `;
            fileResultDiv.appendChild(fileHeader);
    
            // 文本内容容器
            const textContentDiv = document.createElement('div');
            textContentDiv.className = 'pdf-result-text-content';
    
            // 处理错误情况
            if (pdfResult.error) {
                textContentDiv.innerHTML = `<p class="error-message" style="color: var(--error-color);">处理错误: ${pdfResult.error}</p>`;
            } else if (pdfResult.pages && pdfResult.pages.length > 0) {
                // 按页显示文本
                pdfResult.pages.forEach((page) => {
                    const pageDiv = document.createElement('div');
                    pageDiv.className = 'pdf-text-page'; // 可以复用之前的页面样式
                    pageDiv.style.marginBottom = '10px'; // 页面间距
    
                    // 使用唯一ID，结合文件索引和页码
                    const pageTextId = `file-${index}-page-text-${page.page_num}`;
    
                    pageDiv.innerHTML = `
                        <h5 style="margin-bottom: 5px;">第 ${page.page_num} 页</h5>
                        <div class="page-text" id="${pageTextId}" style="white-space: pre-wrap; word-wrap: break-word; max-height: 200px; overflow-y: auto; background-color: var(--input-bg); padding: 8px; border-radius: 4px;">${page.text || '(无文本内容)'}</div>
                        <button class="copy-btn btn btn-small" data-target="#${pageTextId}" style="margin-top: 5px;">
                            <span class="material-icons">content_copy</span> 复制此页文本
                        </button>
                    `;
                    textContentDiv.appendChild(pageDiv);
                });
                allExtractedText.push(pdfResult.text || ''); // 添加整个文件的文本到总列表
            } else if (pdfResult.text) {
                // 如果没有分页信息但有总文本
                const pageDiv = document.createElement('div');
                pageDiv.className = 'pdf-text-page';
                pageDiv.innerHTML = `
                    <h5 style="margin-bottom: 5px;">文本内容</h5>
                    <div class="page-text" style="white-space: pre-wrap; word-wrap: break-word; max-height: 300px; overflow-y: auto; background-color: var(--input-bg); padding: 8px; border-radius: 4px;">${pdfResult.text || '(无文本内容)'}</div>
                `;
                textContentDiv.appendChild(pageDiv);
                allExtractedText.push(pdfResult.text || '');
            } else {
                // 没有提取到文本且没有错误信息
                textContentDiv.innerHTML = '<p>此PDF中未发现文本内容。</p>';
            }
    
            fileResultDiv.appendChild(textContentDiv);
    
            // 将这个文件的结果块添加到主结果容器中
            if (ui.pdfTextContent) {
                ui.pdfTextContent.appendChild(fileResultDiv);
            }
        });
    
        // 更新“复制全部”按钮的逻辑 (如果保留该按钮)
        if (ui.copyAllBtn) {
            ui.copyAllBtn.onclick = () => {
                // 用清晰的分隔符连接所有文件的文本
                const combinedText = allExtractedText.join('\n\n=====\n\n');
                 if (typeof copyToClipboard === 'function') {
                    copyToClipboard(combinedText);
                     if (typeof showToast === 'function') showToast('已复制所有文件的文本到剪贴板');
                 }
            };
            // 确保按钮在有内容时可见
            ui.copyAllBtn.style.display = allExtractedText.length > 0 ? 'block' : 'none';
        }
    
        // 为所有新创建的复制按钮添加事件监听器 (使用事件委托可能更高效，但这里直接查询)
        ui.pdfTextContent.querySelectorAll('.copy-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const targetSelector = this.getAttribute('data-target');
                const textElement = document.querySelector(targetSelector);
                if (textElement && typeof copyToClipboard === 'function') {
                    copyToClipboard(textElement.textContent);
                    if (typeof showToast === 'function') showToast('已复制到剪贴板');
                }
            });
        });
    
        // 清除可能存在的全局状态消息
        if (typeof clearStatusMessage === 'function') clearStatusMessage();
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
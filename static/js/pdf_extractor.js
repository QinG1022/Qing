/**
 * PDF文本提取模块
 * 版本: 1.0
 * 最后更新: 2024-03-06
 * 描述: 提供PDF文件上传、预览、文本提取和结果显示功能
 */

document.addEventListener('DOMContentLoaded', function() {
    const pdfInput = document.getElementById('pdf-file');
    const pdfPreview = document.querySelector('.pdf-preview');
    const extractPdfBtn = document.getElementById('extract-pdf-btn');
    const extractResults = document.querySelector('.extract-results');
    const pdfTextContent = document.getElementById('pdf-text-content');
    const copyAllBtn = document.getElementById('copy-all-btn');

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

    /**
     * 处理PDF文本提取按钮点击事件
     */
    if (extractPdfBtn) {
        extractPdfBtn.addEventListener('click', async function() {
            if (!pdfInput.files.length) {
                window.showToast('请先选择一个PDF文件');
                return;
            }

            const formData = new FormData();
            formData.append('pdfs', pdfInput.files[0]);
            
            window.showLoading('正在处理PDF文本提取...');
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
                window.hideLoading();
                window.setStatusMessage(`提交失败: ${error.message}`, true);
            }
        });
    }

    /**
     * 轮询PDF提取任务状态
     * 
     * @param {string} taskId - PDF提取任务ID
     */
    function pollPDFExtractionStatus(taskId) {
        window.showLoading('提取PDF文本中...');
        
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/tasks/${taskId}`);
                const data = await response.json();
                
                if (data.status === 'SUCCESS') {
                    clearInterval(intervalId);
                    window.hideLoading();
                    handlePDFResults(data.result);
                    extractPdfBtn.disabled = false;
                    
                    // 处理成功后刷新历史记录
                    console.log("PDF处理完成，刷新历史记录");
                    setTimeout(window.loadHistory, 500);
                } else if (data.status === 'FAILURE') {
                    clearInterval(intervalId);
                    window.hideLoading();
                    window.setStatusMessage(`PDF处理失败: ${data.error || '未知错误'}`, true);
                    extractPdfBtn.disabled = false;
                } else {
                    document.getElementById('loadingText').textContent = data.message || '提取中...';
                }
            } catch (error) {
                clearInterval(intervalId);
                window.hideLoading();
                window.setStatusMessage('状态查询失败', true);
                extractPdfBtn.disabled = false;
            }
        }, 1000);
    }

    /**
     * 处理PDF提取结果
     * 
     * @param {Object} result - PDF提取结果对象
     */
    function handlePDFResults(result) {
        if (!result) {
            window.setStatusMessage('未能提取文本内容', true);
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
                            <span class="material-icons">复制此页文本</span> 
                        </button>
                    `;
                    pdfTextContent.appendChild(pageDiv);
                });
                
                // 注册复制按钮事件
                pdfTextContent.querySelectorAll('.copy-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const pageIndex = parseInt(this.dataset.page);
                        const text = pdf.pages[pageIndex].text;
                        window.copyToClipboard(text);
                        window.showToast('已复制到剪贴板');
                    });
                });
                
                // 显示结果区域
                extractResults.style.display = 'block';
                window.clearStatusMessage();
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
                window.clearStatusMessage();
            }
        } else {
            window.setStatusMessage('PDF中未发现文本内容', true);
        }
    }
    
    /**
     * 复制所有PDF提取文本功能
     */
    if (copyAllBtn) {
        copyAllBtn.addEventListener('click', function() {
            const allText = Array.from(pdfTextContent.querySelectorAll('.page-text'))
                .map(el => el.textContent)
                .join('\n\n');
                
            window.copyToClipboard(allText);
            window.showToast('已复制全部文本到剪贴板');
        });
    }
});
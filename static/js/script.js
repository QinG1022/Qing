// 改进的异步处理逻辑
async function handleSubmit(event) {
    event.preventDefault();
    const loading = document.getElementById('loading');
    loading.style.display = 'block';

    try {
        const formData = new FormData();
        formData.append('textContent', document.getElementById('textContent').value);
        
        imageFiles.forEach(file => {
            formData.append('imageUpload', file);
        });

        const response = await fetch('/generate-pdf', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error(await response.text());
        
        const { task_id } = await response.json();
        pollTaskStatus(task_id);
        
    } catch (error) {
        showError(error.message || '请求失败');
        loading.style.display = 'none';
    }
}

// 增强型状态轮询
async function pollTaskStatus(task_id) {
    try {
        const response = await fetch(`/tasks/${task_id}`);
        const data = await response.json();
        
        switch(data.state) {
            case 'SUCCESS':
                downloadPDF(data.result);
                break;
            case 'FAILURE':
                showError(data.status || '生成失败');
                break;
            default:
                setTimeout(() => pollTaskStatus(task_id), 1000);
        }
    } catch (error) {
        showError('状态查询失败');
    }
}

function downloadPDF(pdfData) {
    const blob = new Blob([pdfData], { type: 'application/pdf' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `document_${Date.now()}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
}
// 前端代码需添加请求监听
document.addEventListener('DOMContentLoaded', function() {
    const mainForm = document.getElementById('documentForm');
    const content = document.getElementById('content');
    const imagesInput = document.getElementById('images');
    const preview = document.getElementById('preview');
    const loading = document.getElementById('loading');
    const status = document.getElementById('status');

    if (!mainForm) {
        console.error('表单元素未找到');
        return;
    }

    // 图片预览处理
    if (imagesInput) {
        imagesInput.addEventListener('change', function(e) {
            preview.innerHTML = '';
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
                    preview.appendChild(div);
                }
            });
        });
    }

    function pollTaskStatus(taskId) {
        console.log('开始轮询任务状态:', taskId);
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/tasks/${taskId}`);
                const data = await response.json();
                console.log('任务状态:', data);

                if (data.status === 'SUCCESS') {
                    clearInterval(interval);
                    status.textContent = '生成成功！';
                    loading.style.display = 'none';
                    
                    // 下载文件
                    if (data.result) {
                        window.location.href = `/download/${data.result}`;
                    }
                    
                } else if (data.status === 'FAILURE') {
                    clearInterval(interval);
                    status.textContent = '生成失败: ' + (data.error || '未知错误');
                    loading.style.display = 'none';
                    
                } else {
                    status.textContent = data.message || '处理中...';
                }
                
            } catch (error) {
                console.error('轮询错误:', error);
                clearInterval(interval);
                status.textContent = '状态查询失败';
                loading.style.display = 'none';
            }
        }, 1000);
    }

    // 处理图片按钮点击事件
    document.getElementById('processImagesBtn').addEventListener('click', async function() {
        if (!document.getElementById('enableOCR').checked) return;
        
        const files = document.getElementById('images').files;
        if (files.length === 0) {
            showMessage('请先选择图片');
            return;
        }

        this.disabled = true;
        document.getElementById('loading').classList.remove('hidden');
        
        try {
            const formData = new FormData();
            Array.from(files).forEach(file => {
                formData.append('images', file);
            });

            const response = await fetch('/process-images', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('处理失败');
            
            const data = await response.json();
            if (data.task_id) {
                pollOCRStatus(data.task_id);
            }
            
        } catch (error) {
            showMessage('图片处理失败: ' + error.message);
            this.disabled = false;
            document.getElementById('loading').classList.add('hidden');
        }
    });

    // OCR结果处理
    function handleOCRResults(results) {
        const ocrResults = document.getElementById('ocrResults');
        ocrResults.innerHTML = '';
        
        const resultHeader = document.createElement('div');
        resultHeader.className = 'ocr-header';
        resultHeader.innerHTML = `
            <h3>识别结果</h3>
            <button onclick="mergeAllText()" class="merge-all-btn">
                全部合并到文本
            </button>
        `;
        ocrResults.appendChild(resultHeader);
        
        results.forEach(result => {
            const div = document.createElement('div');
            div.className = 'ocr-item';
            div.innerHTML = `
                <div class="ocr-text">${result.text}</div>
                <div class="ocr-actions">
                    <button onclick="mergeText(this)" data-text="${result.text}" class="btn secondary">
                        添加到文本
                    </button>
                </div>
            `;
            ocrResults.appendChild(div);
        });
    }

    // 合并单个文本
    window.mergeText = function(button) {
        const text = button.dataset.text;
        const content = document.getElementById('content');
        const currentValue = content.value;
        content.value = currentValue + (currentValue ? '\n' : '') + text;
        button.disabled = true;
        button.textContent = '已添加';
    };

    // 合并所有文本
    window.mergeAllText = function() {
        const content = document.getElementById('content');
        const ocrItems = document.querySelectorAll('.ocr-item:not(.merged) .ocr-text');
        const texts = Array.from(ocrItems).map(item => item.textContent);
        
        if (texts.length > 0) {
            const currentValue = content.value;
            content.value = currentValue + (currentValue ? '\n' : '') + texts.join('\n');
            
            // 更新按钮状态
            document.querySelectorAll('.ocr-item button').forEach(btn => {
                btn.disabled = true;
                btn.textContent = '已添加';
            });
            
            // 禁用"全部合并"按钮
            const mergeAllBtn = document.querySelector('.merge-all-btn');
            if (mergeAllBtn) {
                mergeAllBtn.disabled = true;
                mergeAllBtn.textContent = '已全部添加';
            }
        }
    }

    function pollOCRStatus(taskId) {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/tasks/${taskId}`);
                const data = await response.json();
                
                if (data.status === 'SUCCESS') {
                    clearInterval(interval);
                    handleOCRResults(data.result.results);
                    document.getElementById('loading').classList.add('hidden');
                    document.getElementById('processImagesBtn').disabled = false;
                } else if (data.status === 'FAILURE') {
                    clearInterval(interval);
                    showMessage('OCR处理失败: ' + (data.error || '未知错误'));
                    document.getElementById('loading').classList.add('hidden');
                    document.getElementById('processImagesBtn').disabled = false;
                }
            } catch (error) {
                clearInterval(interval);
                showMessage('状态查询失败');
                document.getElementById('loading').classList.add('hidden');
                document.getElementById('processImagesBtn').disabled = false;
            }
        }, 1000);
    }

    // 添加自动合并功能
    function enableAutoMerge() {
        const autoMerge = document.getElementById('autoMerge');
        const ocrResults = document.getElementById('ocrResults');
        
        if (autoMerge.checked) {
            const textArea = document.getElementById('content');
            // 监听OCR结果变化
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.addedNodes.length) {
                        const newText = Array.from(mutation.addedNodes)
                            .filter(node => node.classList && node.classList.contains('ocr-item'))
                            .map(node => node.querySelector('.ocr-text').textContent)
                            .join('\n');
                        
                        if (newText) {
                            textArea.value += (textArea.value ? '\n' : '') + newText;
                        }
                    }
                });
            });

            observer.observe(ocrResults, { childList: true });
        }
    }

    function showLoading() {
        const statusSection = document.querySelector('.status-section');
        statusSection.classList.add('visible');
    }

    function hideLoading() {
        const statusSection = document.querySelector('.status-section');
        statusSection.classList.remove('visible');
    }

    // 修改轮询任务状态函数
    function pollTaskStatus(taskId) {
        console.log('开始轮询任务状态:', taskId);
        showLoading();  // 显示加载状态
        
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/tasks/${taskId}`);
                const data = await response.json();
                console.log('任务状态:', data);

                if (data.status === 'SUCCESS') {
                    clearInterval(interval);
                    hideLoading();  // 隐藏加载状态
                    status.textContent = '生成成功！';
                    
                    if (data.result) {
                        window.location.href = `/download/${data.result}`;
                    }
                    
                } else if (data.status === 'FAILURE') {
                    clearInterval(interval);
                    hideLoading();  // 隐藏加载状态
                    status.textContent = '生成失败: ' + (data.error || '未知错误');
                    
                } else {
                    document.getElementById('loadingText').textContent = data.message || '处理中...';
                }
                
            } catch (error) {
                console.error('轮询错误:', error);
                clearInterval(interval);
                hideLoading();  // 隐藏加载状态
                status.textContent = '状态查询失败';
            }
        }, 1000);
    }

    // 表单提交处理

    // 添加自定义对话框函数
    function showConfirmDialog(message, onConfirm, onCancel) {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        
        const dialog = document.createElement('div');
        dialog.className = 'modal-dialog';
        
        dialog.innerHTML = `
            <div class="modal-content">
                <button class="modal-close" id="closeBtn">&times;</button>
                <div class="modal-message">${message.replace(/\n/g, '<br>')}</div>
                <div class="modal-buttons">
                    <button class="modal-btn primary" id="confirmBtn">是</button>
                    <button class="modal-btn secondary" id="cancelBtn">否</button>
                </div>
            </div>
        `;
        
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        
        requestAnimationFrame(() => {
            overlay.style.display = 'flex';
        });
        
        const confirmBtn = dialog.querySelector('#confirmBtn');
        const cancelBtn = dialog.querySelector('#cancelBtn');
        const closeBtn = dialog.querySelector('#closeBtn');
        
        // 清理函数
        const cleanup = () => {
            overlay.remove();
        };
        
        // 取消处理函数
        const handleCancel = () => {
            cleanup();
            // 只在明确点击"取消"按钮时才执行onCancel回调
            if (cancelBtn === event.target) {
                onCancel && onCancel();
            }
        };
        
        confirmBtn.onclick = () => {
            cleanup();
            onConfirm && onConfirm();
        };
        
        cancelBtn.onclick = handleCancel;
        
        // 关闭按钮只清理对话框，不执行任何回调
        closeBtn.onclick = cleanup;
    }

     // 处理表单提交
     async function handleSubmit(includeImages) {
        try {
            showLoading();
            const formData = new FormData();
            formData.append('content', document.getElementById('content').value.trim());
            
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
                pollTaskStatus(data.task_id);
            } else {
                throw new Error('未收到任务ID');
            }

        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            showConfirmDialog('生成失败: ' + error.message);
        }
    }
    // 删除所有旧的表单提交监听器，只保留这一个
    mainForm.removeEventListener('submit', null);
    mainForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const content = document.getElementById('content').value.trim();
        const hasImages = imagesInput.files.length > 0;
        const hasOCRResults = document.querySelector('.ocr-item') !== null;
        
        if (!content && !hasImages) {
            showConfirmDialog('请至少输入文本或选择图片');
            return;
        }

        // 情况1: 如果只有图片，且没有OCR结果，直接生成
        if (hasImages && !content && !hasOCRResults) {
            await handleSubmit(true);
            return;
        }

        //情况2：文本和图片都有，没有OCR结果，直接生成
        if (content && hasImages && !hasOCRResults) {
            await handleSubmit(true);
            return;
        }
        // 情况3: 如果有文本、OCR结果和图片，显示询问对话框
        if (hasImages && content && hasOCRResults) {
            showConfirmDialog(
                '检测到将ocr结果放入文本区，是否将图片一起放入文档？\n\n选择"是"：将图片和文字一起生成文档\n选择"否"：仅使用文本生成文档',
                async () => await handleSubmit(true),  // 确认回调
                async () => await handleSubmit(false)  // 取消回调
            );
            return;
        }

        // 情况4: 如果有图片和OCR结果，但没有文本，显示询问对话框
        if (hasImages && hasOCRResults && !content) {
            showConfirmDialog(
                '检测到OCR结果，是否将OCR结果和图片一起生成文档？\n\n选择"是"：将OCR结果和图片一起生成文档\n选择"否"：直接将图片生成文档',
                async () => {
                    // 将OCR结果添加到文本区
                    const ocrItems = document.querySelectorAll('.ocr-item .ocr-text');
                    const texts = Array.from(ocrItems).map(item => item.textContent);
                    document.getElementById('content').value = texts.join('\n');
                    
                    // 直接调用情况3的处理逻辑
                    await handleSubmit(true);
                },  // 确认回调
                async () => await handleSubmit(true)  // 取消回调
            );
            return;
        }
        // 情况5: 只有文本，直接生成不含图片的文档
        await handleSubmit(false);
    });
});



/**
 * 图片处理和OCR模块
 * 版本: 1.0
 * 最后更新: 2024-03-06
 * 描述: 提供图片上传、预览、OCR文字识别和结果显示功能
 */

document.addEventListener('DOMContentLoaded', function() {
    const imagesInput = document.getElementById('images');
    const imagePreview = document.querySelector('.image-preview');
    const processImagesBtn = document.getElementById('process-images-btn');
    const contentTextarea = document.getElementById('content');
    let ocrTextAdded = false;

    /**
     * 图片预览处理
     * 当用户选择图片文件时，显示预览并启用处理按钮
     */
    if (imagesInput) {
        imagesInput.addEventListener('change', function(e) {
            // 隐藏OCR结果区域
            const ocrResults = document.querySelector('.ocr-results');
            ocrResults.classList.add('hidden');
            
            // 图片预览逻辑
            imagePreview.innerHTML = '';
            if (this.files.length > 0) {
                processImagesBtn.disabled = false;
                
                // 为每个图片创建预览元素
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

    /**
     * 处理图片OCR任务状态
     * 
     * @param {string} taskId - OCR任务ID
     */
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

    /**
     * 处理OCR识别结果
     * 
     * @param {Array} results - OCR识别结果数组
     */
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
                            <span class="material-icons">添加到文本</span>    
                        </button>
                    </div>
                `;
                
                const mergeBtn = div.querySelector('.merge-btn');
                mergeBtn.addEventListener('click', function() {
                    mergeText(result.text, this);
                });
                
                ocrContent.appendChild(div);
            });
            
            ocrResults.classList.remove('hidden');
        } else {
            setStatusMessage('未识别到任何文本', true);
            // 确保在没有识别结果时保持结果区域隐藏
            ocrResults.classList.add('hidden');
        }
    }

    /**
     * 合并单个OCR结果到文本区域
     * 
     * @param {string} text - 要合并的OCR文本内容
     * @param {HTMLElement} button - 触发合并的按钮元素
     */
    function mergeText(text, button) {
        if (text && contentTextarea) {
            const currentValue = contentTextarea.value;
            
            if (currentValue) {
                contentTextarea.value = currentValue + "\n\n" + text;
            } else {
                contentTextarea.value = text;
            }
            
            button.disabled = true;
            button.textContent = '已添加';
            button.style.backgroundColor = '#ccc';
            
            ocrTextAdded = true;
            showToast('内容已添加到文本区');
        }
    }

    /**
     * 合并所有OCR结果到文本区域
     */
    function mergeAllText() {
        const ocrItems = document.querySelectorAll('.ocr-item .ocr-text');
        if (ocrItems.length > 0 && contentTextarea) {
            let allText = '';
            ocrItems.forEach(item => {
                if (item.textContent) {
                    allText += item.textContent + "\n\n";
                }
            });
            
            if (allText) {
                const currentValue = contentTextarea.value;
                if (currentValue) {
                    contentTextarea.value = currentValue + "\n\n" + allText.trim();
                } else {
                    contentTextarea.value = allText.trim();
                }
                
                document.querySelectorAll('.merge-btn').forEach(btn => {
                    btn.disabled = true;
                    btn.textContent = '已添加';
                    btn.style.backgroundColor = '#ccc';
                });
                
                const mergeAllBtn = document.querySelector('.merge-all-btn');
                if (mergeAllBtn) {
                    mergeAllBtn.disabled = true;
                    mergeAllBtn.textContent = '已合并全部';
                    mergeAllBtn.style.backgroundColor = '#ccc';
                }
                
                ocrTextAdded = true;
                showToast('所有内容已添加到文本区');
            }
        }
    }

    /**
     * 处理图片按钮点击事件
     */
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
});
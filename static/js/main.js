/**
 * 智能文档处理系统 - 主脚本
 * 版本: 1.0
 * 最后更新: 2024-03-06
 * 描述: 提供用户交互处理、表单提交、文件预览和历史记录管理等功能
 */

document.addEventListener('DOMContentLoaded', function() {                      // 页面加载完成后执行  
    /**
     * DOM元素引用 - 获取页面中所有需要操作的元素
     */
    const chatInput = document.getElementById('chatInput');
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const chatMessages = document.getElementById('chatMessages');
    const contentTextarea = document.getElementById('content');                 // 获取内容文本区域
    const generateBtn = document.getElementById('generate-btn');                // 获取生成按钮
    const imagesInput = document.getElementById('images');                      // 获取图片输入框
    const imagePreview = document.querySelector('.image-preview');              // 获取图片预览区域
    const processImagesBtn = document.getElementById('process-images-btn');     // 获取处理图片按钮
    const pdfInput = document.getElementById('pdf-file');                       // 获取PDF文件输入框
    const pdfPreview = document.querySelector('.pdf-preview');                  // 获取PDF预览区域
    const extractPdfBtn = document.getElementById('extract-pdf-btn');           // 获取提取PDF按钮
    const loadingOverlay = document.getElementById('loadingOverlay');           // 获取加载状态覆盖层
    const statusMessage = document.getElementById('statusMessage');             // 获取状态消息
    const statusSection = document.querySelector('.status-section');            // 获取状态区域
    const resultsGrid = document.getElementById('resultsGrid');                 // 获取结果网格
    const extractResults = document.querySelector('.extract-results');          // 获取提取结果
    const pdfTextContent = document.getElementById('pdf-text-content');         // 获取PDF文本内容
    const copyAllBtn = document.getElementById('copy-all-btn');                 // 获取复制全部按钮
    const toast = document.getElementById('toast');                             // 获取提示消息
    const modalOverlay = document.getElementById('modalOverlay');               // 获取模态覆盖层
    const modalMessage = document.getElementById('modalMessage');               // 获取模态消息
    const modalConfirm = document.getElementById('modalConfirm');               // 获取模态确认按钮
    const modalCancel = document.getElementById('modalCancel');                 // 获取模态取消按钮
    const modalClose = document.getElementById('modalClose');                   // 获取模态关闭按钮
    const historyContainer = document.getElementById('historyContainer');       // 获取历史记录容器
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');     // 获取刷新历史记录按钮
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');         // 获取清空历史记录按钮
    const historyCount = document.getElementById('historyCount');               // 获取历史记录计数
    let ocrTextAdded = false;                       // 标志用户是否点击了"添加到文本"或"全部合并到文本"按钮

    // 页面初始化设置
    loadingOverlay.classList.add('hidden'); // 初始化加载状态为隐藏
    loadHistory(); // 初始化加载历史记录

    /**
     * 事件监听器设置 - 绑定各个UI元素的事件
     */
    // 为刷新历史记录按钮添加事件监听器
    if (refreshHistoryBtn) {
        refreshHistoryBtn.addEventListener('click', loadHistory); // 点击刷新历史记录按钮时，加载历史记录
    }
    
    // 为清空历史记录按钮添加事件监听器
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearHistory); // 点击清空历史记录按钮时，清空历史记录    
    }

    /**
     * 标签页切换功能
     * 处理不同功能标签页之间的切换
     */
    const tabButtons = document.querySelectorAll('.tab-button'); // 获取所有标签页按钮
    const tabPanes = document.querySelectorAll('.tab-pane'); // 获取所有标签页内容
    // 为每个标签页按钮添加事件监听器          
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // 移除所有active类
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active')); 
            
            // 添加当前active类
            button.classList.add('active'); // 添加当前标签页按钮的active类 
            const targetTab = button.dataset.tab; // 获取当前标签页按钮的data-tab属性值
            document.getElementById(targetTab).classList.add('active'); // 添加当前标签页内容的active类
        });
    });

    /**
     * 显示提示消息
     * 
     * @param {string} message - 要显示的消息内容
     * @param {number} duration - 显示持续时间(毫秒)，默认3000ms
     */
    // 显示提示消息函数
    function showToast(message, duration = 3000) {//显示提示消息    
        toast.textContent = message; // 设置提示消息内容
        toast.classList.remove('hidden'); // 移除隐藏类
        setTimeout(() => {
            toast.classList.add('hidden'); // 添加隐藏类
        }, duration); // 设置显示持续时间
    }

    /**
     * 显示确认对话框
     * 
     * @param {string} message - 确认对话框显示的消息内容
     * @param {Function} onConfirm - 用户确认时执行的回调函数
     * @param {Function} onCancel - 用户取消时执行的回调函数
     */
    function showConfirmDialog(message, onConfirm, onCancel) {//显示确认对话框
        modalMessage.innerHTML = message.replace(/\n/g, '<br>'); // 将消息内容中的换行符替换为HTML换行符
        modalOverlay.classList.add('visible'); // 添加可见类
        
        // 确认按钮处理函数
        const handleConfirm = () => {
            modalOverlay.classList.remove('visible'); // 移除可见类
            removeEventListeners(); // 移除事件监听器
            if (onConfirm) onConfirm(); // 执行确认回调函数
        };
        
        // 取消按钮处理函数
        const handleCancel = () => {
            modalOverlay.classList.remove('visible'); // 移除可见类
            removeEventListeners(); // 移除事件监听器
            if (onCancel) onCancel(); // 执行取消回调函数
        };
        
        // 关闭按钮处理函数
        const handleClose = () => {
            modalOverlay.classList.remove('visible'); // 移除可见类
            removeEventListeners(); // 移除事件监听器
        };
        
        // 清理事件监听器，防止重复绑定
        const removeEventListeners = () => {
            modalConfirm.removeEventListener('click', handleConfirm); // 移除确认按钮的事件监听器
            modalCancel.removeEventListener('click', handleCancel); // 移除取消按钮的事件监听器
            modalClose.removeEventListener('click', handleClose); // 移除关闭按钮的事件监听器
        };
        
        // 绑定事件监听器
        modalConfirm.addEventListener('click', handleConfirm); // 添加确认按钮的事件监听器
        modalCancel.addEventListener('click', handleCancel); // 添加取消按钮的事件监听器
        modalClose.addEventListener('click', handleClose); // 添加关闭按钮的事件监听器
    }

    /**
     * 显示加载状态
     * 
     * @param {string} message - 加载状态显示的消息
     */
    function showLoading(message = '处理中，请稍候...') {//显示加载状态
        document.getElementById('loadingText').textContent = message; // 设置加载状态消息
        loadingOverlay.classList.remove('hidden'); // 移除隐藏类
    }

    /**
     * 隐藏加载状态
     */
    function hideLoading() {//隐藏加载状态
        loadingOverlay.classList.add('hidden'); // 添加隐藏类
    }

    /**
     * 设置状态消息
     * 
     * @param {string} message - 状态消息内容
     * @param {boolean} isError - 是否为错误消息，影响显示颜色
     */
    function setStatusMessage(message, isError = false) {//设置状态消息
        statusMessage.textContent = message; // 设置状态消息内容
        statusMessage.style.color = isError ? 'var(--error-color)' : 'var(--primary-color)'; // 设置状态消息颜色
        statusSection.classList.add('visible'); // 添加可见类
    }

    /**
     * 清除状态消息
     */
    function clearStatusMessage() {//清除状态消息
        statusMessage.textContent = ''; // 设置状态消息内容为空
        statusSection.classList.remove('visible'); // 移除可见类
    }

    // 图片处理和OCR相关功能已移至 image_processor.js

    // PDF文本提取相关功能已移至 pdf_extractor.js

    /**
     * 轮询任务状态
     * 
     * 定期检查后端任务的执行状态，直到任务完成或失败
     * 
     * @param {string} taskId - 任务ID
     */
    function pollTaskStatus(taskId) {//轮询任务状态 
        console.log('开始轮询任务状态:', taskId); // 打印任务ID
        showLoading('任务处理中，请稍候...'); // 显示加载状态       
        // 设置轮询间隔
        const intervalId = setInterval(async () => {
            try {
                // 发送请求获取任务状态     
                const response = await fetch(`/tasks/${taskId}`); 
                const data = await response.json(); // 解析响应数据
                console.log('任务状态:', data); // 打印任务状态
                // 根据任务状态执行不同的操作
                if (data.status === 'SUCCESS') {
                    clearInterval(intervalId); // 停止轮询
                    hideLoading(); // 隐藏加载状态
                    setStatusMessage('生成成功！'); // 设置状态消息
                    // 如果任务结果存在，则重定向到下载页面 
                    if (data.result) {
                        window.location.href = `/download/${data.result}`; // 重定向到下载页面
                    }
                } else if (data.status === 'FAILURE') { // 如果任务失败
                    clearInterval(intervalId); // 停止轮询
                    hideLoading(); // 隐藏加载状态
                    setStatusMessage(`生成失败: ${data.error || '未知错误'}`, true); // 设置错误状态消息
                } else { // 如果任务状态为其他  
                    document.getElementById('loadingText').textContent = data.message || '处理中...'; // 设置加载状态消息
                }
            } catch (error) {//处理错误     
                console.error('轮询错误:', error); // 打印轮询错误  
                clearInterval(intervalId); // 停止轮询
                hideLoading(); // 隐藏加载状态
                setStatusMessage('状态查询失败', true); // 设置错误状态消息
            }
        }, 1000); // 设置轮询间隔为1秒  
    }

    /**
     * 处理图片OCR任务状态
     * 
     * 定期检查OCR任务的执行状态，完成后显示识别结果
     * 
     * @param {string} taskId - OCR任务ID
     */
    function pollOCRStatus(taskId) {
        showLoading('识别图片文字中...'); // 显示加载状态
        // 设置轮询间隔 
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/tasks/${taskId}`);//发送请求获取任务状态 
                const data = await response.json(); // 解析响应数据
                // 根据任务状态执行不同的操作   
                if (data.status === 'SUCCESS') {
                    clearInterval(intervalId); // 停止轮询  
                    hideLoading(); // 隐藏加载状态
                    handleOCRResults(data.result.results); // 处理OCR结果
                    processImagesBtn.disabled = false; // 启用处理图片按钮
                    
                    // 处理成功后刷新历史记录
                    console.log("OCR处理完成，刷新历史记录");
                    setTimeout(loadHistory, 500); // 刷新历史记录
                } else if (data.status === 'FAILURE') { // 如果任务失败
                    clearInterval(intervalId); // 停止轮询
                    hideLoading(); // 隐藏加载状态
                    setStatusMessage(`OCR处理失败: ${data.error || '未知错误'}`, true); // 设置错误状态消息
                    processImagesBtn.disabled = false; // 启用处理图片按钮  
                } else { // 如果任务状态为其他  
                    document.getElementById('loadingText').textContent = data.message || '识别中...'; // 设置加载状态消息
                }
            } catch (error) {//处理错误 
                clearInterval(intervalId); // 停止轮询
                hideLoading(); // 隐藏加载状态
                setStatusMessage('状态查询失败', true); // 设置错误状态消息
                processImagesBtn.disabled = false; // 启用处理图片按钮
            }
        }, 1000); // 设置轮询间隔为1秒
    }

    /**
     * 处理OCR识别结果
     * 
     * 将OCR识别结果显示在界面上，并添加合并到文本区域的功能
     * 
     * @param {Array} results - OCR识别结果数组
     */
    function handleOCRResults(results) {//处理OCR识别结果   
        const ocrResults = document.querySelector('.ocr-results'); // 获取OCR结果区域
        const ocrContent = document.getElementById('ocrContent'); // 获取OCR内容区域
        ocrContent.innerHTML = ''; // 清空OCR内容区域
        // 如果OCR结果存在，则启用"合并全部"按钮    
        if (results && results.length > 0) {
            const mergeAllBtn = ocrResults.querySelector('.merge-all-btn'); // 获取合并全部按钮
                mergeAllBtn.disabled = false; // 启用合并全部按钮
            mergeAllBtn.addEventListener('click', mergeAllText); // 添加合并全部按钮事件
            
            // 为每个OCR结果创建展示元素
            results.forEach(result => {
                const div = document.createElement('div'); // 创建展示元素
                div.className = 'ocr-item'; // 设置展示元素的类名   
                div.innerHTML = `
                    <div class="ocr-text">${result.text}</div>
                    <div class="ocr-actions">
                        <button class="merge-btn">
                            <span class="material-icons">添加到文本</span>    
                        </button>
                    </div>
                `;
                
                // 添加单个合并按钮事件
                const mergeBtn = div.querySelector('.merge-btn'); // 获取合并按钮
                mergeBtn.addEventListener('click', function() {
                    mergeText(result.text, this); // 添加单个合并按钮事件
                });
                
                ocrContent.appendChild(div); // 将展示元素添加到OCR内容区域
            });
            
            // 显示OCR结果区域
            ocrResults.classList.remove('hidden'); // 移除隐藏类
        } else {//如果OCR结果不存在
            setStatusMessage('未识别到任何文本', true); // 设置错误状态消息
        }
    }

    /**
     * 合并单个OCR结果到文本区域
     * 
     * @param {string} text - 要合并的OCR文本内容
     * @param {HTMLElement} button - 触发合并的按钮元素
     */
    function mergeText(text, button) {//合并单个OCR结果到文本区域
        if (text && contentTextarea) {//如果OCR文本存在且文本区存在 
            const currentValue = contentTextarea.value; // 获取文本区当前内容
            
            // 如果文本区已有内容，则添加换行符再添加新文本
            if (currentValue) {
                contentTextarea.value = currentValue + "\n\n" + text; // 添加换行符再添加新文本
            } else {
                contentTextarea.value = text; // 添加新文本
            }
            
            // 禁用按钮并修改其外观
            button.disabled = true; // 禁用按钮
            button.textContent = '已添加'; // 修改按钮文本
            button.style.backgroundColor = '#ccc'; // 修改按钮样式
            
            ocrTextAdded = true; // 设置标志
            showToast('内容已添加到文本区'); // 显示提示消息    
        }
    }

    /**
     * 合并所有OCR结果到文本区域
     * 将所有OCR识别的文本结果合并到文本输入区
     */
    function mergeAllText() {
        const ocrItems = document.querySelectorAll('.ocr-item .ocr-text'); // 获取所有OCR结果文本
        if (ocrItems.length > 0 && contentTextarea) {//如果OCR结果文本存在且文本区存在  
            let allText = ''; // 初始化合并文本
            ocrItems.forEach(item => {//遍历OCR结果文本 
                if (item.textContent) {//如果OCR结果文本存在
                    allText += item.textContent + "\n\n"; // 追加OCR结果文本
                }
            });
            
            // 追加或设置文本内容
            if (allText) {
                const currentValue = contentTextarea.value; // 获取文本区当前内容
                if (currentValue) {//如果文本区已有内容，则添加换行符再添加新文本   
                    contentTextarea.value = currentValue + "\n\n" + allText.trim(); // 追加OCR结果文本
                } else {//如果文本区没有内容，则直接设置文本区内容  
                    contentTextarea.value = allText.trim(); // 设置文本区内容
                }
                
                // 禁用所有添加按钮
                document.querySelectorAll('.merge-btn').forEach(btn => {
                    btn.disabled = true; // 禁用添加按钮
                    btn.textContent = '已添加'; // 修改按钮文本
                    btn.style.backgroundColor = '#ccc'; // 修改按钮样式
                });
                
                // 禁用合并全部按钮
                const mergeAllBtn = document.querySelector('.merge-all-btn');//获取合并全部按钮
                if (mergeAllBtn) {//如果合并全部按钮存在    
                    mergeAllBtn.disabled = true; // 禁用合并全部按钮
                    mergeAllBtn.textContent = '已合并全部'; // 修改按钮文本
                    mergeAllBtn.style.backgroundColor = '#ccc'; // 修改按钮样式
                }
                
                ocrTextAdded = true; // 设置标志
                showToast('所有内容已添加到文本区'); // 显示提示消息    
            }
        }
    }

    /**
     * 处理表单提交，生成PDF文档
     * 
     * @param {boolean} includeImages - 是否包含图片
     * @returns {Promise<void>}//返回一个Promise对象    
     */
    async function handleSubmit(includeImages) {//处理表单提交，生成PDF文档
        try {//处理表单提交，生成PDF文档    
            // 检查文本内容是否为空
            const textContent = contentTextarea.value.trim();//获取文本区内容
            if (!textContent && (!includeImages || !imagesInput.files.length)) {//如果文本区没有内容，且没有图片
                showToast('请输入文本内容或上传图片');//显示提示消息
                return;
            }
            
            showLoading('生成文档中...');//显示加载状态
            const formData = new FormData();//创建FormData对象
            formData.append('content', textContent); // 添加文本内容到FormData对象
            
            if (includeImages) {//如果包含图片
                Array.from(imagesInput.files).forEach(file => {//遍历图片文件
                    formData.append('images', file); // 添加图片文件到FormData对象
                });
            }
            
            const response = await fetch('/generate', {//发送生成请求
                method: 'POST',//发送POST请求
                body: formData//发送FormData对象
            });

            const data = await response.json();//解析响应数据
            if (!response.ok) {//如果请求失败
                throw new Error(data.error || '请求失败');//抛出错误
            }

            if (data.task_id) {//如果有任务ID
                // 如果有文本内容，则刷新历史记录
                if (textContent) {
                    console.log("文本内容已提交，刷新历史记录");//打印日志
                    setTimeout(loadHistory, 500); // 刷新历史记录
                }
                pollTaskStatus(data.task_id); // 轮询任务状态
            } else {//如果没有任务ID    
                throw new Error('未收到任务ID');//抛出错误
            }

        } catch (error) {//处理错误 
            console.error('Error:', error); // 打印错误 
            hideLoading(); // 隐藏加载状态
            showConfirmDialog(`生成失败: ${error.message}`); // 显示确认对话框
        }
    }

    /**
     * 处理PDF文本提取按钮点击事件
     * 上传PDF文件并发送到服务器进行文本提取
     */
    if (extractPdfBtn) {//如果提取PDF按钮存在       
        extractPdfBtn.addEventListener('click', async function() {//为提取PDF按钮绑定事件
            if (!pdfInput.files.length) {//如果PDF输入区没有文件
                showToast('请先选择一个PDF文件');//显示提示消息
                return;
            }

            const formData = new FormData();//创建FormData对象
            formData.append('pdfs', pdfInput.files[0]); // 添加PDF文件到FormData对象
            
            showLoading('正在处理PDF文本提取...');//显示加载状态
            extractResults.style.display = 'none';//隐藏提取结果区域
            
            try {//处理提取PDF文本请求
                const response = await fetch('/extract-pdf', {//发送提取请求
                    method: 'POST',//发送POST请求
                    body: formData//发送FormData对象
                });
                
                if (!response.ok) {//如果请求失败
                    throw new Error('服务器响应错误');//抛出错误
                }
                
                const result = await response.json();//解析响应数据
                
                if (result.task_id) {//如果有任务ID
                    pollPDFExtractionStatus(result.task_id); // 轮询任务状态
                } else {//如果没有任务ID
                    throw new Error('未能获取任务ID');//抛出错误
                }
            } catch (error) {//处理错误
                    console.error('提交任务失败:', error); // 打印错误
                hideLoading(); // 隐藏加载状态
                setStatusMessage(`提交失败: ${error.message}`, true); // 设置错误状态消息
            }
        });
    }

    /**
     * 处理图片按钮点击事件
     * 为处理图片按钮绑定事件，上传图片并进行OCR处理
     */
    if (processImagesBtn) {//如果处理图片按钮存在
        processImagesBtn.addEventListener('click', async function() {//为处理图片按钮绑定事件
            if (!imagesInput.files.length) {//如果图片输入区没有文件
                showToast('请先选择图片');//显示提示消息
                return;
            }

            if (!document.getElementById('enableOCR').checked) {//如果未勾选"对图片进行文字识别"选项
                showToast('请勾选"对图片进行文字识别"选项');//显示提示消息
                return;
            }

            this.disabled = true; // 禁用按钮
            
            // 确保OCR结果区域隐藏
            const ocrResults = document.querySelector('.ocr-results');//获取OCR结果区域
            ocrResults.classList.add('hidden');//隐藏OCR结果区域
            
            const formData = new FormData();//创建FormData对象
            Array.from(imagesInput.files).forEach(file => {//遍历图片文件
                formData.append('images', file); // 添加图片文件到FormData对象
            });

            try {//处理图片请求
                showLoading('处理图片中，识别文字...');//显示加载状态
                const response = await fetch('/process-images', {//发送处理请求
                    method: 'POST',//发送POST请求
                    body: formData//发送FormData对象
                });

                if (!response.ok) {//如果请求失败
                    throw new Error('处理失败');//抛出错误
                }
                
                const data = await response.json();//解析响应数据
                if (data.task_id) {//如果有任务ID
                    pollOCRStatus(data.task_id); // 轮询任务状态
                } else {//如果没有任务ID
                    throw new Error('未能获取任务ID');//抛出错误
                }
            } catch (error) {//处理错误
                hideLoading(); // 隐藏加载状态
                showToast('图片处理失败: ' + error.message); // 显示错误消息
                this.disabled = false; // 启用按钮
            }
        });
    }

    /**
     * 生成文档按钮点击事件
     * 处理不同场景下的文档生成逻辑，根据内容和OCR状态显示不同的确认对话框
     */
    if (generateBtn) {//如果生成按钮存在
        generateBtn.addEventListener('click', async function() {//为生成按钮绑定事件
            const content = contentTextarea.value.trim();//获取文本区内容
            const hasImages = imagesInput.files.length > 0;//是否有图片
            const hasOCRResults = document.querySelector('.ocr-item') !== null;//是否有OCR结果
            
            if (!content && !hasImages) {//如果文本区没有内容，且没有图片
                showConfirmDialog('请至少输入文本或选择图片');//显示确认对话框
                return;
            }

            // 情况1: 只有图片，且没有文本和OCR结果，直接生成
            if (hasImages && !content && !hasOCRResults) {//如果只有图片，且没有文本和OCR结果，直接生成
                await handleSubmit(true);//处理生成请求
                return;
            }

            // 情况2: 文本和图片都有，没有OCR结果，直接生成
            if (content && hasImages && !hasOCRResults) {
                await handleSubmit(true);//处理生成请求
                return;
            }

            // 情况3: 有文本、OCR结果和图片，且用户点击了"添加到文本"或"全部合并到文本"按钮，显示询问对话框
            if (hasImages && content && hasOCRResults && ocrTextAdded) {
                showConfirmDialog(//显示确认对话框      
                    '检测到将OCR结果放入文本区，是否将图片一起放入文档？\n\n选择"是"：将图片和文字一起生成文档\n选择"否"：仅使用文本生成文档',
                    async () => await handleSubmit(true),  // 确认回调
                    async () => await handleSubmit(false)  // 取消回调
                );
                return;
            }

            // 情况4: 有图片和OCR结果，但没有文本，显示询问对话框
            if (hasImages && hasOCRResults && !content) {
                showConfirmDialog(//显示确认对话框  
                    '检测到存在OCR结果，是否将OCR结果和图片一起生成文档？\n\n选择"是"：将OCR结果和图片一起生成文档\n选择"否"：直接将图片生成文档',
                    async () => {
                        // 将OCR结果添加到文本区
                        const ocrItems = document.querySelectorAll('.ocr-item .ocr-text');//获取OCR结果文本
                        const texts = Array.from(ocrItems).map(item => item.textContent);//获取OCR结果文本
                        contentTextarea.value = texts.join('\n');//将OCR结果文本添加到文本区
                        
                        // 直接调用情况3的处理逻辑
                        await handleSubmit(true);
                    },  // 确认回调
                    async () => await handleSubmit(true)  // 取消回调
                );
                return;
            }

            // 情况5: 有图片、文本和OCR结果，显示询问对话框
            if (hasImages && content && hasOCRResults) {
                showConfirmDialog(//显示确认对话框  
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
     * 轮询PDF提取任务状态
     * 定期检查PDF文本提取任务的执行状态，完成后显示提取结果
     * 
     * @param {string} taskId - PDF提取任务ID
     */
    function pollPDFExtractionStatus(taskId) {//轮询PDF提取任务状态
        showLoading('提取PDF文本中...');//显示加载状态
        
        const intervalId = setInterval(async () => {//设置定时器    
            try {//处理PDF提取请求
                const response = await fetch(`/tasks/${taskId}`);//发送提取请求
                const data = await response.json();//解析响应数据
                
                if (data.status === 'SUCCESS') {//如果提取成功
                    clearInterval(intervalId);//清除定时器
                    hideLoading();//隐藏加载状态
                    handlePDFResults(data.result);//处理提取结果
                    extractPdfBtn.disabled = false;//启用提取按钮
                    
                    // 处理成功后刷新历史记录
                    console.log("PDF处理完成，刷新历史记录");
                    setTimeout(loadHistory, 500);
                } else if (data.status === 'FAILURE') {//如果提取失败
                    clearInterval(intervalId);//清除定时器
                    hideLoading();//隐藏加载状态
                    setStatusMessage(`PDF处理失败: ${data.error || '未知错误'}`, true);//设置错误状态消息
                    extractPdfBtn.disabled = false;//启用提取按钮   
                } else {//如果提取中
                    document.getElementById('loadingText').textContent = data.message || '提取中...';//设置加载状态消息
                }
            } catch (error) {//处理错误
                clearInterval(intervalId);//清除定时器
                hideLoading();//隐藏加载状态
                setStatusMessage('状态查询失败', true);//设置错误状态消息
                extractPdfBtn.disabled = false;//启用提取按钮
            }
        }, 1000);//设置定时器间隔时间
    }

    /**
     * 处理PDF提取结果
     * 解析并显示PDF提取的文本内容，支持分页显示和复制功能
     * 
     * @param {Object} result - PDF提取结果对象
     */
    function handlePDFResults(result) {//处理PDF提取结果
        if (!result) {//如果提取结果为空
            setStatusMessage('未能提取文本内容', true);//设置错误状态消息
            return;//返回
        }
        
        // 更新文件信息
        document.getElementById('pdf-file-name').textContent = `文件名: ${result.results[0].filename || '未知'}`;//设置文件名
        document.getElementById('pdf-page-count').textContent = `总页数: ${result.results[0].total_pages || 0}`;//设置总页数
        document.getElementById('pdf-word-count').textContent = `总字数: ${result.results[0].text_length || 0}`;//设置总字数
        
        // 更新文本内容
        pdfTextContent.innerHTML = '';//清空文本内容
        
        if (result.results && result.results.length > 0) {//如果提取结果不为空
            const pdf = result.results[0];//获取提取结果
            
            if (pdf.pages && pdf.pages.length > 0) {//如果提取结果有页面
                pdf.pages.forEach((page) => {//遍历页面
                    const pageDiv = document.createElement('div');//创建页面元素
                    pageDiv.className = 'pdf-text-page';//设置页面样式
                    pageDiv.innerHTML = `
                        <h4>第 ${page.page_num} 页</h4>
                        <div class="page-text">${page.text || '(无文本内容)'}</div>
                        <button class="copy-btn" data-page="${page.page_num - 1}">
                            <span class="material-icons">复制此页文本</span> 
                        </button>
                    `;
                    pdfTextContent.appendChild(pageDiv);//添加页面元素
                });
                
                // 注册复制按钮事件
                pdfTextContent.querySelectorAll('.copy-btn').forEach(btn => {//遍历复制按钮
                    btn.addEventListener('click', function() {//为复制按钮绑定事件
                        const pageIndex = parseInt(this.dataset.page);//获取页面索引
                        const text = pdf.pages[pageIndex].text;//获取页面文本
                        copyToClipboard(text);//复制文本
                        showToast('已复制到剪贴板');//显示提示消息
                    });
                });
                
                // 显示结果区域
                extractResults.style.display = 'block';//显示结果区域
                clearStatusMessage();//清除状态消息 
            } else {//如果没有分页信息
                // 如果没有分页信息，直接显示全部文本
                const pageDiv = document.createElement('div');//创建页面元素
                pageDiv.className = 'pdf-text-page';//设置页面样式
                pageDiv.innerHTML = `
                    <h4>文本内容</h4>
                    <div class="page-text">${pdf.text || '(无文本内容)'}</div>
                `;
                pdfTextContent.appendChild(pageDiv);//添加页面元素
                extractResults.style.display = 'block';//显示结果区域
                clearStatusMessage();//清除状态消息
            }
        } else {//如果没有文本内容
            setStatusMessage('PDF中未发现文本内容', true);//设置错误状态消息
        }
    }
    
    /**
     * 复制所有PDF提取文本功能
     * 将所有页面的文本内容合并并复制到剪贴板
     */
    if (copyAllBtn) {//如果复制全部按钮存在
        copyAllBtn.addEventListener('click', function() {//为复制全部按钮绑定事件
            const allText = Array.from(pdfTextContent.querySelectorAll('.page-text'))//获取所有页面文本
                .join('\n\n');//合并文本
                
            copyToClipboard(allText);//复制文本
            showToast('已复制全部文本到剪贴板');//显示提示消息  
        });
    }
    
    /**
     * 复制文本到剪贴板
     * 临时创建一个文本区域元素来实现复制功能
     * 
     * @param {string} text - 要复制到剪贴板的文本
     */
    function copyToClipboard(text) {//复制文本到剪贴板
        const textarea = document.createElement('textarea');//创建文本区域元素
        textarea.value = text;//设置文本区域内容
        textarea.style.position = 'fixed'; // 避免影响页面布局
        document.body.appendChild(textarea);//添加到文档中
        textarea.select();//选中文本
        document.execCommand('copy');//执行复制命令
        document.body.removeChild(textarea);//删除文本区域元素  
    }

    /**
     * 加载历史记录
     * 从服务器获取并显示用户的历史操作记录
     * 
     * @returns {Promise<void>}
     */
    async function loadHistory() {//加载历史记录
        try {//处理加载历史记录请求
            console.log("正在获取历史记录...");//打印日志
            const response = await fetch('/history');//发送获取历史记录请求
            
            if (!response.ok) {//如果请求失败
                throw new Error('获取历史记录失败，状态码: ' + response.status);//抛出错误
            }
            
            const data = await response.json();//解析响应数据
            console.log("历史记录数据:", data);//打印日志
            
            // 更新历史记录计数
            if (historyCount) {//如果历史记录计数存在
                historyCount.textContent = `(共${data.count}/${data.max_count}条内容)`;//设置历史记录计数
            }
            
            if (data.status === 'success' && historyContainer) {//如果请求成功且历史记录容器存在
                // 清空历史记录容器
                historyContainer.innerHTML = '';
                
                if (data.history && data.history.length > 0) {//如果历史记录不为空
                    console.log(`加载 ${data.history.length} 条历史记录`);
                    // 添加所有历史记录项
                    data.history.forEach(item => {//遍历历史记录
                        const historyItem = document.createElement('div');//创建历史记录项
                        historyItem.className = 'history-item';//设置历史记录项样式
                        historyItem.dataset.id = item.id;//设置历史记录项ID
                        
                        // 获取历史记录类型的显示名称
                        let typeName = '';//设置历史记录类型名称
                        
                        switch(item.type) {//根据历史记录类型设置显示名称   
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
                        const deleteBtn = historyItem.querySelector('.delete-history-btn');//获取删除按钮   
                        deleteBtn.addEventListener('click', () => {//为删除按钮绑定事件
                            deleteHistoryRecord(item.id);//删除历史记录
                        });
                        
                        // 为复制按钮添加事件监听器
                        const copyBtn = historyItem.querySelector('.copy-history-btn');//获取复制按钮
                        copyBtn.addEventListener('click', () => {//为复制按钮绑定事件
                            copyToClipboard(item.content || '(无内容)');//复制文本
                            showToast('已复制到剪贴板');//显示提示消息
                        });
                        
                        // 为插入到编辑器按钮添加事件监听器
                        const insertBtn = historyItem.querySelector('.insert-history-btn');//获取插入按钮
                        insertBtn.addEventListener('click', () => {//为插入按钮绑定事件
                            if (contentTextarea) {//如果文本区域存在
                                    const currentText = contentTextarea.value;//获取当前文本
                                if (currentText) {//如果当前文本存在
                                    contentTextarea.value = currentText + '\n\n' + (item.content || '(无内容)');//插入文本
                                } else {//如果当前文本不存在
                                    contentTextarea.value = item.content || '(无内容)';//插入文本
                                }
                                showToast('文本已插入到编辑器');//显示提示消息
                                
                                // 切换到第一个标签页并滚动到文本区域
                                const firstTabBtn = document.querySelector('.tab-button[data-tab="tab1"]');//获取第一个标签页   
                                if (firstTabBtn) {//如果第一个标签页存在
                                    firstTabBtn.click();//点击第一个标签页
                                    contentTextarea.scrollIntoView({ behavior: 'smooth' });//滚动到文本区域
                                    setTimeout(() => {
                                        contentTextarea.focus();//聚焦文本区域  
                                    }, 300);//设置定时器
                                }
                            }
                        });
                        
                        // 添加到容器中
                        historyContainer.appendChild(historyItem);//添加到历史记录容器中
                    });
                } else {//如果没有历史记录
                    console.log("没有历史记录");//打印日志
                    // 没有历史记录时显示提示
                    historyContainer.innerHTML = '<div class="empty-history">暂无历史记录</div>';//设置历史记录容器内容
                }
                
                // 触发历史记录加载完成事件
                document.dispatchEvent(new Event('historyLoaded'));//触发历史记录加载完成事件
            }
        } catch (error) {
            console.error('获取历史记录出错:', error);//打印错误信息
            // 显示错误信息
            if (historyContainer) {//如果历史记录容器存在
                historyContainer.innerHTML = `<div class="empty-history error">获取历史记录失败: ${error.message}</div>`;//设置历史记录容器内容
            }
            showToast('获取历史记录失败: ' + error.message);//显示错误信息
        }
    }
    
    /**
     * 删除单条历史记录
     * 向服务器发送删除请求并刷新历史记录显示
     * 
     * @param {string} recordId - 要删除的历史记录ID
     * @returns {Promise<void>}//返回Promise对象    
     */
    async function deleteHistoryRecord(recordId) {//删除单条历史记录
        try {//处理删除历史记录请求
            showLoading('删除中...');//显示加载状态
            const response = await fetch(`/history/${recordId}`, {//发送删除请求
                method: 'DELETE'//发送DELETE请求
            });
            
            const data = await response.json();//解析响应数据
            
            if (response.ok) {//如果请求成功
                await loadHistory();//刷新历史记录
                showToast('历史记录已删除');//显示提示消息
            } else {//如果请求失败
                throw new Error(data.error || '删除失败');//抛出错误
            }
            
            hideLoading();//隐藏加载状态
        } catch (error) {//处理错误
            console.error('删除历史记录失败:', error);//打印错误信息
            hideLoading();//隐藏加载状态
            showToast('删除历史记录失败: ' + error.message);//显示错误信息
        }
    }
    
    /**
     * 清空所有历史记录
     * 显示确认对话框并在用户确认后发送清空请求
     * 
     * @returns {Promise<void>}
     */
    async function clearHistory() {//清空所有历史记录
        try {//处理清空历史记录请求 
            // 显示确认对话框
            showConfirmDialog('确定要清空所有历史记录吗？此操作不可撤销。', async () => {
                try {//处理清空历史记录请求 
                    showLoading('清空中...');//显示加载状态
                    const response = await fetch('/history', {//发送清空请求
                        method: 'DELETE'//发送DELETE请求
                    });
                    
                    const data = await response.json();//解析响应数据
                    
                    if (response.ok) {//如果请求成功
                        await loadHistory();//刷新历史记录
                        showToast('所有历史记录已清空');//显示提示消息  
                    } else {//如果请求失败
                        throw new Error(data.error || '清空失败');//抛出错误
                    }
                    
                    hideLoading();//隐藏加载状态
                } catch (error) {//处理错误
                    console.error('清空历史记录失败:', error);//打印错误信息
                    hideLoading();//隐藏加载状态
                    showToast('清空历史记录失败: ' + error.message);//显示错误信息
                }
            });
        } catch (error) {//处理错误 
            console.error('清空历史记录错误:', error);//打印错误信息
            showToast('操作失败: ' + error.message);//显示错误信息
        }
    }

    // AI对话相关功能已移至 ai_chat.js
});
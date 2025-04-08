/**
 * 智能文档处理系统 - 主脚本
 * 版本: 1.0
 * 描述: 处理主页面逻辑和用户交互
 */

// DOM 加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否应该显示欢迎页面
    checkShowWelcome();
    
    // 全局变量
    const state = {
        theme: localStorage.getItem('theme') || 'light',
        authenticated: false,
        username: '',
        userId: null,
        uploadedImages: [],
        uploadedPdfs: [],
        activeFeature: null,
        currentTask: null,
        historyItems: [],
        maxHistoryItems: 10 // 默认最大历史记录数
    };
    
    // 初始化主题
    initTheme();
    
    // 检查用户登录状态
    checkAuthentication();
    
    // 获取历史记录
    fetchHistory();
    
    // 检查是否是登录成功跳转
    checkLoginSuccess();
    
    // 初始化卡片动画
    initCardAnimations();
    
    // 事件监听器
    addEventListeners();
    
    /**
     * 检查是否应该显示欢迎页
     */
    function checkShowWelcome() {
        // 检查是否是直接访问主页的（不是从欢迎页跳转过来的）
        const current = window.location.pathname;
        const referrer = document.referrer;
        const urlParams = new URLSearchParams(window.location.search);
        const skipWelcome = urlParams.get('skip_welcome');
        
        // 如果当前是主页，且不是从欢迎页或其他内部页面跳转来的，且没有跳过欢迎页参数
        if (current === '/' && !referrer.includes('/welcome') && !skipWelcome && !sessionStorage.getItem('skipWelcome')) {
            // 第一次访问，跳转到欢迎页
            window.location.href = '/welcome';
        }
        
        // 如果是从欢迎页跳转来的，则记录状态防止刷新页面再次跳转
        if (referrer.includes('/welcome')) {
            sessionStorage.setItem('skipWelcome', 'true');
        }
    }
    
    /**
     * 初始化主题设置
     */
    function initTheme() {
        const theme = localStorage.getItem('theme') || 'light';
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            document.getElementById('themeToggle').querySelector('.material-icons').textContent = 'light_mode';
        } else {
            document.documentElement.removeAttribute('data-theme');
            document.getElementById('themeToggle').querySelector('.material-icons').textContent = 'dark_mode';
        }
    }
    
    /**
     * 检查是否是登录成功跳转
     */
    function checkLoginSuccess() {
        const urlParams = new URLSearchParams(window.location.search);
        const loginSuccess = urlParams.get('login_success');
        
        if (loginSuccess === 'true') {
            // 登录成功跳转，显示欢迎消息
            showToast('欢迎回来！', 'success');
            
            // 移除URL参数
            const newUrl = window.location.pathname;
            window.history.replaceState({}, document.title, newUrl);
        }
    }
    
    /**
     * 检查用户登录状态
     */
    function checkAuthentication() {
        fetch('/api/check-auth')
            .then(response => response.json())
            .then(data => {
                if (data.authenticated) {
                    state.authenticated = true;
                    state.username = data.user.username;
                    state.userId = data.user.id;
                    
                    // 更新UI
                    document.getElementById('loginBtn').style.display = 'none';
                    
                    // 获取或创建用户信息区域
                    const userInfo = document.getElementById('userInfo');
                    userInfo.style.display = 'flex';
                    
                    // 显示用户名
                    let usernameElement = document.getElementById('username');
                    if (!usernameElement) {
                        usernameElement = document.createElement('span');
                        usernameElement.id = 'username';
                        userInfo.appendChild(usernameElement);
                    }
                    usernameElement.textContent = state.username;
                    
                    // 创建用户头像元素（如果不存在）
                    let userAvatar = document.getElementById('userAvatar');
                    if (!userAvatar) {
                        userAvatar = document.createElement('div');
                        userAvatar.id = 'userAvatar';
                        userAvatar.className = 'user-avatar';
                        userAvatar.innerHTML = '<span class="material-icons">account_circle</span>';
                        userInfo.appendChild(userAvatar);
                    }
                    
                    // 初始化用户菜单
                    initUserMenu();
                } else {
                    state.authenticated = false;
                }
            })
            .catch(error => {
                console.error('身份验证检查失败:', error);
                showToast('检查登录状态时出错', 'error');
            });
    }
    
    /**
     * 获取历史记录
     */
    function fetchHistory() {
        fetch('/history')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // 保存最大记录数
                    if (data.max_count) {
                        state.maxHistoryItems = data.max_count;
                    }
                    
                    if (data.history && data.history.length > 0) {
                        state.historyItems = data.history;
                        renderHistory();
                    } else {
                        state.historyItems = [];
                        document.getElementById('historyContainer').innerHTML = 
                            '<p class="empty-history">暂无历史记录</p>';
                        // 更新历史记录计数器为0
                        document.getElementById('historyCounter').textContent = `(0/${state.maxHistoryItems})`;
                    }
                } else {
                    state.historyItems = [];
                    document.getElementById('historyContainer').innerHTML = 
                        '<p class="empty-history">暂无历史记录</p>';
                    // 更新历史记录计数器为0
                    document.getElementById('historyCounter').textContent = `(0/${state.maxHistoryItems})`;
                }
            })
            .catch(error => {
                console.error('获取历史记录失败:', error);
                showToast('获取历史记录失败', 'error');
                // 出错时也要更新计数器为0
                document.getElementById('historyCounter').textContent = `(0/${state.maxHistoryItems})`;
            });
    }
    
    /**
     * 渲染历史记录
     */
    function renderHistory() {
        const container = document.getElementById('historyContainer');
        const counter = document.getElementById('historyCounter');
        
        // 更新历史记录计数器
        counter.textContent = `(${state.historyItems.length}/${state.maxHistoryItems})`;
        
        if (state.historyItems.length === 0) {
            container.innerHTML = '<p class="empty-history">暂无历史记录</p>';
            return;
        }
        
        let html = '';
        state.historyItems.forEach(item => {
            const timestamp = item.timestamp;
            const content = item.content.length > 100 
                ? item.content.substring(0, 100) + '...' 
                : item.content;
            const typeIcon = getTypeIcon(item.type);
            // 格式化内容，去除多余的空白
            const formattedContent = content.replace(/\n\s*\n/g, '\n').trim();
            
            html += `
                <div class="history-item" data-id="${item.id}">
                    <div class="history-item-header">
                        <span class="material-icons">${typeIcon}</span>
                        <span class="history-item-source">${item.source || '用户输入'}</span>
                        <span class="history-item-time">${timestamp}</span>
                        <button class="delete-history-btn" data-id="${item.id}">
                            <span class="material-icons">close</span>
                        </button>
                    </div>
                    <div class="history-item-content">${formattedContent}</div>
                </div>
            `;
        });
        
        container.innerHTML = html;
        
        // 添加删除事件监听器
        document.querySelectorAll('.delete-history-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const id = this.getAttribute('data-id');
                deleteHistoryItem(id);
            });
        });
        
        // 添加点击历史记录项事件
        document.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                const historyItem = state.historyItems.find(h => h.id === id);
                if (historyItem) {
                    if (historyItem.type === 'TEXT' || historyItem.type === 'OCR' || historyItem.type === 'PDF') {
                        openFeature('ocr-pdf');
                        document.getElementById('textContent').value = historyItem.content;
                    }
                }
            });
        });
    }
    
    /**
     * 获取历史记录项类型对应的图标
     */
    function getTypeIcon(type) {
        switch(type) {
            case 'TEXT': return 'text_fields';
            case 'OCR': return 'image_search';
            case 'PDF': return 'picture_as_pdf';
            case 'AI_CHAT': return 'chat';
            default: return 'history';
        }
    }
    
    /**
     * 删除历史记录项
     */
    function deleteHistoryItem(id) {
        fetch(`/history/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // 从状态中移除
                state.historyItems = state.historyItems.filter(item => item.id !== id);
                
                // 从DOM中移除
                const item = document.querySelector(`.history-item[data-id="${id}"]`);
                if (item) {
                    item.remove();
                }
                
                // 如果没有记录，显示空状态
                if (state.historyItems.length === 0) {
                    document.getElementById('historyContainer').innerHTML = 
                        '<p class="empty-history">暂无历史记录</p>';
                }
                
                // 更新计数器
                document.getElementById('historyCounter').textContent = `(${state.historyItems.length}/${state.maxHistoryItems})`;
                
                showToast('已删除历史记录', 'success');
            } else {
                showToast(data.error || '删除失败', 'error');
            }
        })
        .catch(error => {
            console.error('删除历史记录失败:', error);
            showToast('删除历史记录失败', 'error');
        });
    }
    
    /**
     * 清空历史记录
     */
    function clearHistory() {
        fetch('/history', {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                state.historyItems = [];
                document.getElementById('historyContainer').innerHTML = 
                    '<p class="empty-history">暂无历史记录</p>';
                
                // 更新计数器为0
                document.getElementById('historyCounter').textContent = `(0/${state.maxHistoryItems})`;
                
                showToast('已清空历史记录', 'success');
            } else {
                showToast(data.error || '清空失败', 'error');
            }
        })
        .catch(error => {
            console.error('清空历史记录失败:', error);
            showToast('清空历史记录失败', 'error');
        });
    }
    
    /**
     * 确认清空历史记录
     */
    function confirmClearHistory() {
        if (confirm('确定要清空所有历史记录吗？此操作不可恢复。')) {
            clearHistory();
        }
    }
    
    /**
     * 添加事件监听器
     */
    function addEventListeners() {
        // 登录按钮点击事件
        document.getElementById('loginBtn').addEventListener('click', function() {
            const theme = localStorage.getItem('theme') || 'light';
            window.location.href = `/login?theme=${theme}`;
        });
        
        // 主题切换按钮点击事件
        document.getElementById('themeToggle').addEventListener('click', toggleTheme);
        
        // 功能卡片点击事件
        document.querySelectorAll('.card').forEach(card => {
            card.addEventListener('click', function() {
                const feature = this.getAttribute('data-feature');
                openFeature(feature);
            });
        });
        
        // 返回按钮点击事件
        document.querySelectorAll('.back-btn').forEach(btn => {
            btn.addEventListener('click', closeFeature);
        });
        
        // 历史记录相关按钮事件
        document.getElementById('refreshHistoryBtn').addEventListener('click', fetchHistory);
        document.getElementById('clearHistoryBtn').addEventListener('click', confirmClearHistory);
        
        // OCR相关事件
        const imageUpload = document.getElementById('imageUpload');
        if (imageUpload) {
            imageUpload.addEventListener('change', handleImageUpload);
            
            // 拖放事件
            const imageUploadArea = document.getElementById('imageUploadArea');
            if (imageUploadArea) {
                imageUploadArea.addEventListener('dragover', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.classList.add('drag-over');
                });
                
                imageUploadArea.addEventListener('dragleave', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.classList.remove('drag-over');
                });
                
                imageUploadArea.addEventListener('drop', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.classList.remove('drag-over');
                    
                    const files = e.dataTransfer.files;
                    if (files.length > 0) {
                        imageUpload.files = files;
                        handleImageUpload({target: imageUpload});
                    }
                });
            }
        }
        
        // OCR按钮点击事件
        const ocrBtn = document.getElementById('ocrBtn');
        if (ocrBtn) {
            ocrBtn.addEventListener('click', performOCR);
        }
        
        // 生成PDF按钮点击事件
        const generatePdfBtn = document.getElementById('generatePdfBtn');
        if (generatePdfBtn) {
            generatePdfBtn.addEventListener('click', generatePDF);
        }
        
        // PDF上传事件
        const pdfUpload = document.getElementById('pdfUpload');
        if (pdfUpload) {
            pdfUpload.addEventListener('change', handlePdfUpload);
            
            // PDF拖放事件
            const pdfUploadArea = document.getElementById('pdfUploadArea');
            if (pdfUploadArea) {
                pdfUploadArea.addEventListener('dragover', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.classList.add('drag-over');
                });
                
                pdfUploadArea.addEventListener('dragleave', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.classList.remove('drag-over');
                });
                
                pdfUploadArea.addEventListener('drop', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.classList.remove('drag-over');
                    
                    const files = e.dataTransfer.files;
                    if (files.length > 0 && files[0].type === 'application/pdf') {
                        pdfUpload.files = files;
                        handlePdfUpload({target: pdfUpload});
                    } else {
                        showToast('请上传PDF文件', 'error');
                    }
                });
            }
        }
        
        // 提取文本按钮点击事件
        const extractBtn = document.getElementById('extractBtn');
        if (extractBtn) {
            extractBtn.addEventListener('click', extractText);
        }
        
        // 模态框关闭按钮
        document.querySelector('.modal .close').addEventListener('click', closeModal);
        
        // 标签切换
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const tabName = this.getAttribute('data-tab');
                switchTab(tabName);
            });
        });
        
        // 登录表单
        document.getElementById('loginForm').addEventListener('submit', handleLogin);
        
        // 注册表单
        document.getElementById('registerForm').addEventListener('submit', handleRegister);
        
        // 文档上传区域
        if (typeof initDocUpload === 'function') {
            initDocUpload();
        }
        
        // AI聊天功能
        if (typeof initAiChat === 'function') {
            initAiChat();
        }
    }
    
    /**
     * 初始化卡片动画
     */
    function initCardAnimations() {
        // 为每张卡片设置动画延迟
        document.querySelectorAll('.card').forEach((card, index) => {
            card.style.setProperty('--card-index', index);
            
            // 鼠标移动效果
            card.addEventListener('mousemove', function(e) {
                const rect = this.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                this.style.setProperty('--x', x + 'px');
                this.style.setProperty('--y', y + 'px');
            });
        });
        
        // 设置标签随机颜色
        document.querySelectorAll('.tag').forEach(tag => {
            // 生成随机颜色，但基于主色调变化
            const hue = Math.floor(Math.random() * 60) + 160; // 160-220色相范围（绿色-青色）
            const saturation = Math.floor(Math.random() * 30) + 70; // 70-100%饱和度
            const lightness = Math.floor(Math.random() * 20) + 30; // 30-50%亮度
            
            tag.style.backgroundColor = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
        });
    }
    
    /**
     * 切换主题模式
     */
    function toggleTheme() {
        const theme = localStorage.getItem('theme') || 'light';
        
        if (theme === 'light') {
            localStorage.setItem('theme', 'dark');
            document.documentElement.setAttribute('data-theme', 'dark');
            document.getElementById('themeToggle').querySelector('.material-icons').textContent = 'light_mode';
        } else {
            localStorage.setItem('theme', 'light');
            document.documentElement.removeAttribute('data-theme');
            document.getElementById('themeToggle').querySelector('.material-icons').textContent = 'dark_mode';
        }
    }
    
    /**
     * 显示登录模态框
     */
    function showLoginModal() {
        const modal = document.getElementById('authModal');
        modal.classList.add('show');
        // 确保模态框应用当前主题
        const theme = localStorage.getItem('theme') || 'light';
        if (theme === 'dark') {
            modal.setAttribute('data-theme', 'dark');
        } else {
            modal.removeAttribute('data-theme');
        }
    }
    
    /**
     * 关闭模态框
     */
    function closeModal() {
        const modal = document.getElementById('authModal');
        modal.classList.remove('show');
        // 不移除data-theme属性，保持主题一致性
    }
    
    /**
     * 切换标签页
     */
    function switchTab(tabName) {
        // 移除所有标签按钮的active类
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // 隐藏所有标签内容
        document.querySelectorAll('.tab-content').forEach(content => {
            content.style.display = 'none';
        });
        
        // 添加active类到当前标签按钮
        document.querySelector(`.tab-btn[data-tab="${tabName}"]`).classList.add('active');
        
        // 显示当前标签内容
        document.getElementById(`${tabName}Tab`).style.display = 'block';
    }
    
    /**
     * 处理登录表单提交
     */
    function handleLogin(e) {
        e.preventDefault();
        
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        const remember = document.getElementById('rememberMe').checked;
        
        if (!username || !password) {
            showToast('请输入用户名和密码', 'error');
            return;
        }
        
        showLoading('正在登录...');
        
        fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                password,
                remember
            })
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            
            if (data.success) {
                state.authenticated = true;
                state.username = data.user.username;
                state.userId = data.user.id;
                
                // 更新UI
                document.getElementById('loginBtn').style.display = 'none';
                document.getElementById('userInfo').style.display = 'flex';
                document.getElementById('username').textContent = state.username;
                
                // 关闭模态框
                closeModal();
                
                // 重新获取历史记录
                fetchHistory();
                
                showToast('登录成功', 'success');
            } else {
                showToast(data.message || '登录失败', 'error');
            }
        })
        .catch(error => {
            hideLoading();
            console.error('登录请求失败:', error);
            showToast('登录请求失败', 'error');
        });
    }
    
    /**
     * 处理注册表单提交
     */
    function handleRegister(e) {
        e.preventDefault();
        
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        // 表单验证
        if (!username || !email || !password || !confirmPassword) {
            showToast('请填写所有必填字段', 'error');
            return;
        }
        
        if (username.length < 4 || username.length > 20) {
            showToast('用户名长度必须在4-20个字符之间', 'error');
            return;
        }
        
        if (password.length < 8) {
            showToast('密码长度必须至少为8个字符', 'error');
            return;
        }
        
        if (password !== confirmPassword) {
            showToast('两次输入的密码不一致', 'error');
            return;
        }
        
        // 邮箱格式验证
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(email)) {
            showToast('请输入有效的邮箱地址', 'error');
            return;
        }
        
        showLoading('正在注册...');
        
        fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                email,
                password
            })
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            
            if (data.success) {
                showToast('注册成功，请登录', 'success');
                
                // 切换到登录标签
                switchTab('login');
                
                // 清空注册表单
                document.getElementById('registerForm').reset();
            } else {
                showToast(data.message || '注册失败', 'error');
            }
        })
        .catch(error => {
            hideLoading();
            console.error('注册请求失败:', error);
            showToast('注册请求失败', 'error');
        });
    }
        
    /**
     * 处理退出登录
     */
    function logout() {
        fetch('/api/logout', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                state.authenticated = false;
                state.username = '';
                state.userId = null;
                
                // 更新UI
                document.getElementById('loginBtn').style.display = 'block';
                document.getElementById('userInfo').style.display = 'none';
                
                // 隐藏用户菜单
                const userMenu = document.getElementById('userMenu');
                if (userMenu) {
                    userMenu.style.display = 'none';
                }
                
                // 重新获取历史记录
                fetchHistory();
                
                showToast('已成功登出', 'success');
            } else {
                showToast('登出失败', 'error');
            }
        })
        .catch(error => {
            console.error('登出请求失败:', error);
            showToast('登出请求失败', 'error');
        });
    }
    
    /**
     * 显示提示消息
     */
    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const id = 'toast-' + Date.now();
        
        let icon = 'info';
        if (type === 'success') icon = 'check_circle';
        if (type === 'error') icon = 'error';
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.id = id;
        toast.innerHTML = `
            <span class="material-icons">${icon}</span>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        // 3秒后自动移除
        setTimeout(() => {
            const toastElement = document.getElementById(id);
            if (toastElement) {
                toastElement.remove();
            }
        }, 3000);
    }
    
    /**
     * 显示加载中遮罩
     */
    function showLoading(message = '处理中，请稍候...') {
        const loadingOverlay = document.getElementById('loadingOverlay');
        document.getElementById('loadingMessage').textContent = message;
        loadingOverlay.classList.add('show');
    }
    
    /**
     * 隐藏加载中遮罩
     */
    function hideLoading() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        loadingOverlay.classList.remove('show');
    }
    
    /**
     * 打开功能界面
     */
    function openFeature(feature) {
        state.activeFeature = feature;
        
        // 显示功能容器
        const featureContainer = document.getElementById('featureContainer');
        featureContainer.style.display = 'block';
        
        // 隐藏所有功能内容
        document.querySelectorAll('.feature-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // 显示对应功能内容
        let featureId;
        switch (feature) {
            case 'ocr-pdf':
                featureId = 'ocrPdfFeature';
                break;
            case 'pdf-extract':
                featureId = 'pdfExtractFeature';
                break;
            case 'ai-chat':
                featureId = 'aiChatFeature';
                break;
        }
        
        if (featureId) {
            document.getElementById(featureId).classList.add('active');
        }
    }
    
    /**
     * 关闭功能界面
     */
    function closeFeature() {
        state.activeFeature = null;
        
        // 隐藏功能容器
        const featureContainer = document.getElementById('featureContainer');
        featureContainer.style.display = 'none';
        
        // 隐藏所有功能内容
        document.querySelectorAll('.feature-content').forEach(content => {
            content.classList.remove('active');
        });
    }
    
    /**
     * 用户菜单功能
     * 初始化用户头像点击事件及菜单显示
     */
    function initUserMenu() {
        // 确保已添加用户头像和用户菜单元素
        const userInfo = document.getElementById('userInfo');
        let userAvatar = document.getElementById('userAvatar');
        let userMenu = document.getElementById('userMenu');
        
        // 如果用户菜单不存在，动态创建
        if (!userMenu) {
            userMenu = document.createElement('div');
            userMenu.id = 'userMenu';
            userMenu.className = 'user-menu';
            userMenu.style.display = 'none';
            userMenu.innerHTML = `
                <div class="user-menu-header">
                    <span class="material-icons">account_circle</span>
                    <span id="menuUsername">${state.username}</span>
                </div>
                <div class="user-menu-items">
                    <div class="menu-item" id="viewProfileBtn">
                        <span class="material-icons">person</span>
                        <span>用户信息</span>
                    </div>
                    <div class="menu-item" id="logoutMenuBtn">
                        <span class="material-icons">logout</span>
                        <span>退出登录</span>
                    </div>
                </div>
            `;
            document.body.appendChild(userMenu);
        }
        
        // 添加用户头像点击事件
        userAvatar.addEventListener('click', function(e) {
            e.stopPropagation();
            
            // 获取头像位置，将菜单定位在头像下方
            const rect = userAvatar.getBoundingClientRect();
            userMenu.style.top = (rect.bottom + 5) + 'px';
            // 调整菜单右侧对齐位置为头像右侧
            userMenu.style.right = (window.innerWidth - rect.right) + 'px';
            
            // 切换菜单显示状态
            userMenu.style.display = userMenu.style.display === 'none' ? 'block' : 'none';
            
            // 更新菜单中的用户名
            document.getElementById('menuUsername').textContent = state.username;
        });
        
        // 点击页面其他区域关闭菜单
        document.addEventListener('click', function() {
            if (userMenu) {
                userMenu.style.display = 'none';
            }
        });
        
        // 防止菜单点击事件冒泡
        userMenu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
        
        // 绑定用户信息按钮点击事件
        document.getElementById('viewProfileBtn').addEventListener('click', function() {
            showUserProfile();
        });
        
        // 绑定退出登录按钮点击事件
        document.getElementById('logoutMenuBtn').addEventListener('click', function() {
            logout();
        });
    }
    
    /**
     * 显示用户资料信息
     */
    function showUserProfile() {
        // 显示加载状态
        showLoading('加载用户信息...');
        
        // 获取用户资料
        fetch('/api/user-profile')
            .then(response => response.json())
            .then(data => {
                hideLoading();
                
                if (data.success) {
                    // 创建用户资料弹窗
                    const profileModal = document.createElement('div');
                    profileModal.className = 'modal';
                    profileModal.id = 'profileModal';
                    
                    // 格式化时间
                    const registerTime = data.user.register_time || '未知';

                    
                    // 用户资料弹窗内容
                    profileModal.innerHTML = `
                        <div class="modal-content profile-modal">
                            <button class="close-modal-top"><span class="material-icons">close</span></button>
                            <div class="modal-header">
                                <h2>用户信息</h2>
                            </div>
                            <div class="modal-body">
                                <div class="profile-avatar">
                                    <span class="material-icons">account_circle</span>
                                </div>
                                <div class="profile-info">
                                    <div class="info-item">
                                        <span class="info-label">用户名：</span>
                                        <span class="info-value">${data.user.username}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="info-label">邮箱：</span>
                                        <span class="info-value">${data.user.email}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="info-label">注册时间：</span>
                                        <span class="info-value">${registerTime}</span>
                                    </div>

                                </div>
                            </div>
                        </div>
                    `;
                    
                    document.body.appendChild(profileModal);
                    
                    // 显示模态框
                    setTimeout(() => {
                        profileModal.classList.add('show');
                    }, 10);
                    
                    // 添加关闭按钮事件
                    profileModal.querySelector('.close-modal-top').addEventListener('click', function() {
                        profileModal.classList.remove('show');
                        setTimeout(() => {
                            document.body.removeChild(profileModal);
                        }, 300);
                    });
                    
                    // 点击弹窗外部区域关闭
                    profileModal.addEventListener('click', function(e) {
                        if (e.target === profileModal) {
                            profileModal.classList.remove('show');
                            setTimeout(() => {
                                document.body.removeChild(profileModal);
                            }, 300);
                        }
                    });
                } else {
                    showToast(data.message || '获取用户信息失败', 'error');
                }
            })
            .catch(error => {
                hideLoading();
                console.error('获取用户资料失败:', error);
                showToast('获取用户资料失败，请稍后再试', 'error');
            });
    }
}); 
/**
 * 登录与注册页面脚本
 * 版本: 1.0
 * 描述: 处理用户登录和注册功能
 */

// DOM 加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化主题
    initTheme();
    
    // 初始化标签切换
    initTabs();
    
    // 添加表单提交事件
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('registerForm').addEventListener('submit', handleRegister);
});

/**
 * 初始化主题设置
 */
function initTheme() {
    // 先尝试从URL参数中获取主题设置
    const urlParams = new URLSearchParams(window.location.search);
    const themeParam = urlParams.get('theme');
    
    // 如果URL参数中有主题设置，则使用它并保存到localStorage
    if (themeParam) {
        localStorage.setItem('theme', themeParam);
    }
    
    // 从localStorage中获取主题设置
    const theme = localStorage.getItem('theme') || 'light';
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
}

/**
 * 初始化标签切换功能
 */
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // 移除所有标签按钮的活动状态
            tabButtons.forEach(btn => btn.classList.remove('active'));
            
            // 添加当前按钮的活动状态
            this.classList.add('active');
            
            // 获取目标标签
            const targetTab = this.getAttribute('data-tab');
            
            // 隐藏所有标签内容
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.style.display = 'none';
            });
            
            // 显示目标标签内容
            if (targetTab === 'login') {
                document.getElementById('loginTab').style.display = 'block';
            } else {
                document.getElementById('registerTab').style.display = 'block';
            }
        });
    });
}

/**
 * 处理登录表单提交
 * @param {Event} e - 表单提交事件
 */
function handleLogin(e) {
    e.preventDefault();
    
    // 获取表单数据
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    const rememberMe = document.getElementById('rememberMe').checked;
    
    // 验证表单数据
    if (!username || !password) {
        showToast('用户名和密码不能为空', 'error');
        return;
    }
    
    // 显示加载状态
    showLoading('登录中，请稍候...');
    
    // 发送登录请求
    fetch('/api/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username,
            password,
            remember: rememberMe
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        
        if (data.success) {
            showToast('登录成功，正在跳转...', 'success');
            
            // 延迟跳转到主页
            setTimeout(() => {
                window.location.href = '/?login_success=true';
            }, 1000);
        } else {
            showToast(data.message || '登录失败，请检查用户名和密码', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('登录请求失败:', error);
        showToast('登录请求失败，请稍后再试', 'error');
    });
}

/**
 * 处理注册表单提交
 * @param {Event} e - 表单提交事件
 */
function handleRegister(e) {
    e.preventDefault();
    
    // 获取表单数据
    const username = document.getElementById('registerUsername').value.trim();
    const email = document.getElementById('registerEmail').value.trim();
    const password = document.getElementById('registerPassword').value.trim();
    const confirmPassword = document.getElementById('confirmPassword').value.trim();
    
    // 验证表单数据
    if (!username || !email || !password || !confirmPassword) {
        showToast('所有字段都必须填写', 'error');
        return;
    }
    
    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showToast('请输入有效的电子邮箱地址', 'error');
        return;
    }
    
    // 验证密码一致性
    if (password !== confirmPassword) {
        showToast('两次输入的密码不一致', 'error');
        return;
    }
    
    // 验证密码强度
    if (password.length < 6) {
        showToast('密码长度至少为6个字符', 'error');
        return;
    }
    
    // 显示加载状态
    showLoading('注册中，请稍候...');
    
    // 发送注册请求
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
            document.querySelector('.tab-btn[data-tab="login"]').click();
            
            // 自动填充用户名
            document.getElementById('loginUsername').value = username;
        } else {
            showToast(data.message || '注册失败，请稍后再试', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('注册请求失败:', error);
        showToast('注册请求失败，请稍后再试', 'error');
    });
}

/**
 * 显示提示消息
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型 (success, error, info)
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // 显示提示
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // 3秒后隐藏
    setTimeout(() => {
        toast.classList.remove('show');
        
        // 动画结束后移除元素
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 3000);
}

/**
 * 显示加载遮罩
 * @param {string} message - 加载提示消息
 */
function showLoading(message = '处理中，请稍候...') {
    document.getElementById('loadingMessage').textContent = message;
    document.getElementById('loadingOverlay').classList.add('active');
}

/**
 * 隐藏加载遮罩
 */
function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
} 
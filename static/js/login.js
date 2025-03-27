document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const loginBtn = document.getElementById('loginBtn');
    const loginModalOverlay = document.getElementById('loginModalOverlay');
    const loginModalClose = document.getElementById('loginModalClose');
    const loginCancel = document.getElementById('loginCancel');
    const loginForm = document.getElementById('loginForm');
    const registerLink = document.getElementById('registerLink');
    const forgotPasswordLink = document.getElementById('forgotPasswordLink');
      // 注册相关元素
    const registerModalOverlay = document.getElementById('registerModalOverlay');
    const registerModalClose = document.getElementById('registerModalClose');
    const registerCancel = document.getElementById('registerCancel');
    const registerForm = document.getElementById('registerForm');
    const backToLoginLink = document.getElementById('backToLoginLink');

    // 用户是否已登录的标志
    let isUserLoggedIn = false;
    let currentUser = null;

    // 创建用户菜单元素
    const userMenu = document.createElement('div');
    userMenu.className = 'user-menu';
    userMenu.style.display = 'none';
    userMenu.innerHTML = `
        <div class="user-menu-header">
            <span class="material-icons">account_circle</span>
            <span class="user-name">用户名</span>
        </div>
        <div class="user-menu-item" id="viewProfileBtn">
            <span class="material-icons">person</span>
            <span>个人信息</span>
        </div>
        <div class="user-menu-item" id="logoutBtn">
            <span class="material-icons">logout</span>
            <span>退出登录</span>
        </div>
    `;
    document.body.appendChild(userMenu);

    // 打开登录模态框或用户菜单
    loginBtn.addEventListener('click', function(e) {
        e.stopPropagation(); // 阻止事件冒泡
        
        // 先检查服务器端登录状态，再决定显示登录窗口还是用户菜单
        fetch('/api/check-auth', {
            method: 'GET',
            credentials: 'include'
        })
        .then(response => response.json())
        .then(data => {
            if (data.authenticated) {
                // 服务器确认用户已登录，显示用户菜单
                if (!isUserLoggedIn) {
                    // 更新本地状态
                    isUserLoggedIn = true;
                    currentUser = data.user;
                    loginBtn.innerHTML = `<span class="material-icons">person</span><span>${data.user.username}</span>`;
                    userMenu.querySelector('.user-name').textContent = data.user.username;
                    localStorage.setItem('user', JSON.stringify(data.user));
                }
                
                // 显示用户菜单
                const btnRect = loginBtn.getBoundingClientRect();
                userMenu.style.position = 'absolute';
                userMenu.style.top = (btnRect.bottom + window.scrollY) + 'px';
                userMenu.style.right = (window.innerWidth - btnRect.right) + 'px';
                userMenu.style.display = 'block';
            } else {
                // 服务器认为用户未登录，显示登录对话框
                if (isUserLoggedIn) {
                    // 清除本地状态
                    isUserLoggedIn = false;
                    currentUser = null;
                    localStorage.removeItem('user');
                    loginBtn.innerHTML = `<span class="material-icons">person</span><span>登录</span>`;
                }
                
                // 显示登录对话框
                loginModalOverlay.style.display = 'flex';
            }
        })
        .catch(error => {
            console.error('验证登录状态失败:', error);
            // 出错时，假设未登录
            loginModalOverlay.style.display = 'flex';
        });
    });

    // 点击页面其他区域关闭用户菜单
    document.addEventListener('click', function(e) {
        if (userMenu.style.display === 'block' && !userMenu.contains(e.target) && e.target !== loginBtn) {
            userMenu.style.display = 'none';
        }
    });

    // 用户菜单项点击事件
    document.getElementById('viewProfileBtn').addEventListener('click', function() {
        userMenu.style.display = 'none';
        // 显示用户资料，可以根据需要实现
        showToast('用户资料功能开发中...');
    });

    document.getElementById('logoutBtn').addEventListener('click', function() {
        userMenu.style.display = 'none';
        // 登出操作
        logout();
    });

    // 登出函数
    function logout() {
        // 显示加载状态
        document.getElementById('loadingOverlay').classList.remove('hidden');
        document.getElementById('loadingText').textContent = '退出登录中...';
        
        fetch('/api/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            // 隐藏加载状态
            document.getElementById('loadingOverlay').classList.add('hidden');
            if (data.success) {
                isUserLoggedIn = false;
                currentUser = null;
                localStorage.removeItem('user');
                // 恢复登录按钮状态
                loginBtn.innerHTML = `<span class="material-icons">person</span><span>登录</span>`;
                showToast('已成功退出登录');
            } else {
                showToast('退出登录失败: ' + data.message);
            }
        })
        .catch(error => {
            // 隐藏加载状态
            document.getElementById('loadingOverlay').classList.add('hidden');
            showToast('退出登录请求错误');
            console.error('退出登录错误:', error);
        });
    }

    // 关闭登录模态框
    function closeLoginModal() {
        loginModalOverlay.style.display = 'none';
        loginForm.reset(); // 重置表单
    }

    loginModalClose.addEventListener('click', closeLoginModal);
    loginCancel.addEventListener('click', closeLoginModal);

    // 点击模态框外部关闭
    loginModalOverlay.addEventListener('click', function(e) {
        if (e.target === loginModalOverlay) {
            closeLoginModal();
        }
    });

    // 表单提交
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        // 显示加载状态
        document.getElementById('loadingOverlay').classList.remove('hidden');
        document.getElementById('loadingText').textContent = '登录中...';
        // 模拟登录请求
        fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        })
        .then(response => response.json())
        .then(data => {
            // 隐藏加载状态
            document.getElementById('loadingOverlay').classList.add('hidden');
            if (data.success) {
                // 登录成功
                showToast('登录成功');
                closeLoginModal();
                // 更新登录状态
                isUserLoggedIn = true;
                currentUser = data.user;
                // 将用户信息存储到localStorage
                localStorage.setItem('user', JSON.stringify(data.user || {username: username}));
                // 更新UI显示已登录状态
                loginBtn.innerHTML = `<span class="material-icons">person</span><span>${username}</span>`;
                // 更新用户菜单中的用户名
                userMenu.querySelector('.user-name').textContent = username;
            } else {
                // 登录失败
                showToast('登录失败：' + data.message);
            }
        })
        .catch(error => {
             // 隐藏加载状态
            document.getElementById('loadingOverlay').classList.add('hidden');
            showToast('登录请求出错');
            console.error('登录错误:', error);
        });
    });

    // 显示提示消息
    function showToast(message) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.classList.remove('hidden');
        
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 3000);
    }

    // 注册链接和忘记密码链接的点击事件

    forgotPasswordLink.addEventListener('click', function(e) {
        e.preventDefault();
        // the login page
        alert('忘记密码功能开发中...');
    });

    // 打开注册模态框
    registerLink.addEventListener('click', function(e) {
        e.preventDefault();
        loginModalOverlay.style.display = 'none';
        registerModalOverlay.style.display = 'flex';
    });

    // 关闭注册模态框
    function closeRegisterModal() {
        registerModalOverlay.style.display = 'none';
        registerForm.reset();
    }

    registerModalClose.addEventListener('click', closeRegisterModal);
    registerCancel.addEventListener('click', closeRegisterModal);

    // 返回登录界面
    backToLoginLink.addEventListener('click', function(e) {
        e.preventDefault();
        registerModalOverlay.style.display = 'none';
        loginModalOverlay.style.display = 'flex';
    });

    // 点击模态框外部关闭
    registerModalOverlay.addEventListener('click', function(e) {
        if (e.target === registerModalOverlay) {
            closeRegisterModal();
        }
    });

    // 表单验证
    const registerUsername = document.getElementById('registerUsername');
    const registerEmail = document.getElementById('registerEmail');
    const registerPassword = document.getElementById('registerPassword');
    const confirmPassword = document.getElementById('confirmPassword');

    function validatePassword() {
        const password = registerPassword.value;
        const confirm = confirmPassword.value;
        
        if (password !== confirm) {
            confirmPassword.setCustomValidity('密码不匹配');
        } else {
            confirmPassword.setCustomValidity('');
        }
    }

    registerPassword.addEventListener('change', validatePassword);
    confirmPassword.addEventListener('keyup', validatePassword);

    // 注册表单提交
    registerForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // 表单验证
        if (!registerForm.checkValidity()) {
            // 显示验证信息
            Array.from(registerForm.elements).forEach(input => {
                if (input.nodeName === 'INPUT' && !input.validity.valid) {
                    input.classList.add('invalid');
                }
            });
            return;
        }

        const formData = {
            username: registerUsername.value,
            email: registerEmail.value,
            password: registerPassword.value
        };

        // 显示加载状态
    document.getElementById('loadingOverlay').classList.remove('hidden');
    document.getElementById('loadingText').textContent = '注册中...';


        // 发送注册请求
        fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            // 隐藏加载状态
            document.getElementById('loadingOverlay').classList.add('hidden');
            if (data.success) {
                showToast('注册成功！请登录');
                closeRegisterModal();
                loginModalOverlay.style.display = 'flex';
            } else {
                showToast('注册失败：' + data.message);
            }
        })
        .catch(error => {
            // 隐藏加载状态
            document.getElementById('loadingOverlay').classList.add('hidden');
            showToast('注册请求出错');
            console.error('注册错误:', error);
        });
    });

    // 实时用户名验证
    registerUsername.addEventListener('input', function() {
        if (this.value.length < 4 || this.value.length > 20) {
            this.setCustomValidity('用户名长度必须在4-20个字符之间');
        } else {
            this.setCustomValidity('');
        }
    });

    // 实时密码验证
    registerPassword.addEventListener('input', function() {
        const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/;
        if (!passwordRegex.test(this.value)) {
            this.setCustomValidity('密码必须至少8位，包含字母和数字');
        } else {
            this.setCustomValidity('');
        }
    });
    // 检查登录状态
    checkLoginStatus();
});
// 检查登录状态
function checkLoginStatus() {
    // 显示微小的加载状态
    loginBtn.innerHTML = `<span class="material-icons">hourglass_empty</span><span>加载中</span>`;
    
    // 总是先从服务器端验证登录状态
    fetch('/api/check-auth', {
        method: 'GET',
        credentials: 'include',
        // 避免缓存影响
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.authenticated) {
            // 服务器确认用户已登录
            isUserLoggedIn = true;
            currentUser = data.user;
            // 更新UI
            loginBtn.innerHTML = `<span class="material-icons">person</span><span>${data.user.username}</span>`;
            userMenu.querySelector('.user-name').textContent = data.user.username;
            // 更新本地存储
            localStorage.setItem('user', JSON.stringify(data.user));
            console.log('用户已登录:', data.user.username);
        } else {
            // 服务器认为用户未登录
            isUserLoggedIn = false;
            currentUser = null;
            localStorage.removeItem('user');
            loginBtn.innerHTML = `<span class="material-icons">person</span><span>登录</span>`;
            console.log('用户未登录');
        }
    })
    .catch(error => {
        console.error('验证登录状态失败:', error);
        // 出错时，检查本地存储
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
            try {
                const user = JSON.parse(storedUser);
                // 暂时以本地存储为准，但在下次点击时会再次检查
                isUserLoggedIn = true;
                currentUser = user;
                loginBtn.innerHTML = `<span class="material-icons">person</span><span>${user.username}</span>`;
            } catch (e) {
                console.error('解析用户数据失败:', e);
                localStorage.removeItem('user');
                loginBtn.innerHTML = `<span class="material-icons">person</span><span>登录</span>`;
            }
        } else {
            loginBtn.innerHTML = `<span class="material-icons">person</span><span>登录</span>`;
        }
    });
}
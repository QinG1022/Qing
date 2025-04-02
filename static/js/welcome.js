/**
 * 智能文档处理系统 - 欢迎页脚本
 * 版本: 1.0
 * 描述: 处理欢迎页面动画和交互
 */

// DOM 加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化主题
    initTheme();
    
    // 初始化背景粒子
    initParticles();
    
    // 添加进入系统按钮事件
    document.getElementById('enterSystemBtn').addEventListener('click', function() {
        // 添加淡出动画
        const welcomeCard = document.querySelector('.welcome-card');
        welcomeCard.style.animation = 'fadeOut 0.5s forwards';
        
        // 在动画结束后跳转
        setTimeout(() => {
            // 设置会话标记，防止从主页跳回欢迎页
            sessionStorage.setItem('skipWelcome', 'true');
            window.location.href = '/?skip_welcome=true';
        }, 500);
    });
    
    // 添加主题切换按钮事件
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    
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
     * 初始化背景粒子
     */
    function initParticles() {
        const particles = document.getElementById('particles');
        const particleCount = 15;
        
        for (let i = 0; i < particleCount; i++) {
            createParticle(particles, i);
        }
        
        // 每隔一段时间重新创建一个粒子，保持动态效果
        setInterval(() => {
            // 移除一个旧粒子
            if (particles.children.length > 0) {
                particles.removeChild(particles.children[0]);
            }
            
            // 创建一个新粒子
            createParticle(particles, particleCount);
        }, 3000);
    }
    
    /**
     * 创建单个粒子
     */
    function createParticle(container, index) {
        const size = Math.random() * 50 + 20;
        const left = Math.random() * 100;
        const delay = Math.random() * 10;
        const duration = Math.random() * 10 + 10;
        const opacity = Math.random() * 0.3 + 0.1;
        
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;
        particle.style.left = `${left}%`;
        particle.style.top = `${Math.random() * 100}%`;
        particle.style.animationDelay = `${delay}s`;
        particle.style.animationDuration = `${duration}s`;
        particle.style.opacity = opacity;
        
        // 随机颜色变化
        if (Math.random() > 0.7) {
            particle.style.background = 'var(--secondary-color)';
        }
        
        container.appendChild(particle);
    }
    
    /**
     * 添加动态打字效果到标题
     */
    function typeWriter(element, text, speed = 100) {
        let i = 0;
        element.textContent = '';
        
        function type() {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(type, speed);
            }
        }
        
        type();
    }
    
    // 为标题添加打字效果
    const headerTitle = document.querySelector('.welcome-header h1');
    if (headerTitle) {
        const originalText = headerTitle.textContent;
        typeWriter(headerTitle, originalText, 80);
    }
    
    // 添加特性项目的动画
    const featureItems = document.querySelectorAll('.feature-item');
    featureItems.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateY(20px)';
        item.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        item.style.transitionDelay = `${0.3 + index * 0.1}s`;
        
        // 延迟显示
        setTimeout(() => {
            item.style.opacity = '1';
            item.style.transform = 'translateY(0)';
        }, 100);
    });
}); 
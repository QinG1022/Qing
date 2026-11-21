/* ==========================================================================
   入口页逻辑：主题、快捷入口、把内容交接给对话页
   ========================================================================== */
(function () {
    'use strict';

    var $ = function (id) { return document.getElementById(id); };

    var QUICK = [
        ['picture_as_pdf', '33,150,243', '总结一份 PDF', '选择文件后自动提取并总结', '/?intent=file&q=' + encodeURIComponent('请阅读这份 PDF 并总结要点')],
        ['image_search', '33,191,115', '识别图片文字', '选择图片后自动识别', '/?intent=image&q=' + encodeURIComponent('请识别这张图片里的文字')],
        ['description', '245,158,11', '文本转 PDF', '输入内容后生成文档', 'text'],
        ['manage_search', '139,92,246', '分析长文档', '选择文件后逐段检索', '/?intent=file&q=' + encodeURIComponent('请阅读这份文档并分析重点')]
    ];

function initBackdrop() {
        var decor = document.getElementById('bgDecor');
        var canvas = document.getElementById('bgCanvas');
        if (!decor || !canvas) return;

        var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        var mx = 0, my = 0, px = -9999, py = -9999, raf = 0;

        window.addEventListener('pointermove', function (e) {
            if (e.pointerType && e.pointerType !== 'mouse') return;
            mx = e.clientX; my = e.clientY; px = e.clientX; py = e.clientY;

            if (raf) return;
            raf = requestAnimationFrame(function () {
                raf = 0;
                decor.style.setProperty('--mx', mx.toFixed(0) + 'px');
                decor.style.setProperty('--my', my.toFixed(0) + 'px');
                decor.style.setProperty('--nx', ((mx / window.innerWidth) * 2 - 1).toFixed(3));
                decor.style.setProperty('--ny', ((my / window.innerHeight) * 2 - 1).toFixed(3));
            });
        });

        if (reduce) { canvas.style.display = 'none'; return; }

        var ctx = canvas.getContext('2d');
        var W = 0, H = 0, dots = [];

        function isDark() { return document.documentElement.hasAttribute('data-theme'); }
        function dotColor() { return isDark() ? '107, 147, 255' : '33, 150, 243'; }

        function resize() {
            var dpr = Math.min(window.devicePixelRatio || 1, 2);
            W = canvas.clientWidth; H = canvas.clientHeight;
            canvas.width = Math.floor(W * dpr);
            canvas.height = Math.floor(H * dpr);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

            var count = Math.max(24, Math.min(56, Math.round((W * H) / 32000)));
            dots = [];
            for (var i = 0; i < count; i++) {
                dots.push({
                    x: Math.random() * W,
                    y: Math.random() * H,
                    vx: (Math.random() - 0.5) * 0.26,
                    vy: (Math.random() - 0.5) * 0.26,
                    r: 1 + Math.random() * 1.5
                });
            }
        }

        var LINK = 130, MOUSE = 190;

        function frame() {
            ctx.clearRect(0, 0, W, H);
            var rgb = dotColor();

            for (var i = 0; i < dots.length; i++) {
                var p = dots[i];
                p.x += p.vx; p.y += p.vy;
                if (p.x < 0 || p.x > W) p.vx *= -1;
                if (p.y < 0 || p.y > H) p.vy *= -1;

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(' + rgb + ', .55)';
                ctx.fill();
            }

            for (var a = 0; a < dots.length; a++) {
                for (var b = a + 1; b < dots.length; b++) {
                    var dx = dots[a].x - dots[b].x, dy = dots[a].y - dots[b].y;
                    var d2 = dx * dx + dy * dy;
                    if (d2 > LINK * LINK) continue;
                    var alpha = (1 - Math.sqrt(d2) / LINK) * 0.15;
                    ctx.strokeStyle = 'rgba(' + rgb + ',' + alpha.toFixed(3) + ')';
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(dots[a].x, dots[a].y);
                    ctx.lineTo(dots[b].x, dots[b].y);
                    ctx.stroke();
                }
            }

            if (px > -1000) {
                for (var c = 0; c < dots.length; c++) {
                    var ex = dots[c].x - px, ey = dots[c].y - py;
                    var d = Math.sqrt(ex * ex + ey * ey);
                    if (d > MOUSE) continue;
                    var al = (1 - d / MOUSE) * 0.5;
                    ctx.strokeStyle = 'rgba(' + rgb + ',' + al.toFixed(3) + ')';
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(dots[c].x, dots[c].y);
                    ctx.lineTo(px, py);
                    ctx.stroke();
                }
            }

            requestAnimationFrame(frame);
        }

        resize();
        window.addEventListener('resize', resize);
        requestAnimationFrame(frame);
    }

    function icon(name) {
        return '<span class="material-icons">' + name + '</span>';
    }

    function applyTheme(dark) {
        if (dark) document.documentElement.setAttribute('data-theme', 'dark');
        else document.documentElement.removeAttribute('data-theme');
        $('themeBtn').innerHTML = icon(dark ? 'light_mode' : 'dark_mode');
    }

    function autoGrow() {
        var ta = $('input');
        ta.style.height = 'auto';
        ta.style.height = Math.min(190, ta.scrollHeight) + 'px';
    }

    function updateSend() {
        $('sendBtn').disabled = $('input').value.trim() === '';
    }

    function go(url) {
        window.location.href = url;
    }

    function init() {
        initBackdrop();
        var saved = null;
        try { saved = localStorage.getItem('qing-theme'); } catch (e) { /* 忽略 */ }
        applyTheme(saved === 'dark');

        $('themeBtn').addEventListener('click', function () {
            var dark = !document.documentElement.hasAttribute('data-theme');
            applyTheme(dark);
            try { localStorage.setItem('qing-theme', dark ? 'dark' : 'light'); } catch (e) { /* 忽略 */ }
        });

        var grid = $('quickGrid');
        QUICK.forEach(function (it) {
            var card = document.createElement('div');
            card.className = 'quick-card';
            card.style.setProperty('--tone', it[1]);
            card.innerHTML =
                '<span class="q-icon">' + icon(it[0]) + '</span>' +
                '<span class="q-body"><strong>' + it[2] + '</strong><span>' + it[3] + '</span></span>';
            card.addEventListener('mouseenter', function () {
                var decor = document.getElementById('bgDecor');
                if (decor) decor.style.setProperty('--glow', it[1]);
            });
            card.addEventListener('mouseleave', function () {
                var decor = document.getElementById('bgDecor');
                if (decor) decor.style.setProperty('--glow', '33, 150, 243');
            });
            card.addEventListener('click', function () {
                if (it[4] === 'text') {
                    $('input').value = '把下面这段内容做成 PDF：\n\n';
                    autoGrow();
                    updateSend();
                    $('input').focus();
                    return;
                }
                go(it[4]);
            });
            grid.appendChild(card);
        });

        var input = $('input');
        input.addEventListener('input', function () { autoGrow(); updateSend(); });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submit();
            }
        });

        $('sendBtn').addEventListener('click', submit);

        function submit() {
            var text = input.value.trim();
            if (!text) return;
            go('/?q=' + encodeURIComponent(text));
        }

        $('attachBtn').addEventListener('click', function () {
            go('/?intent=file');
        });

        updateSend();
        input.focus();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

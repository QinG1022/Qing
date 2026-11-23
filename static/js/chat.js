/* ==========================================================================
   Qing 聊天界面 —— 对接真实后端
   接口：/ai/conversations、/ai/history、/ai/chat（SSE）、/api/settings
   ========================================================================== */
(function () {
    'use strict';

    var $ = function (id) { return document.getElementById(id); };
    var msgBox = function () { return $('messagesInner'); };

    var state = {
        conversationId: null,
        streaming: false,
        controller: null,
        configured: false,
        settings: { provider: 'siliconflow', base_url: '', model: '', api_key_set: false },
        conversations: []
    };

    var PRESETS = {
        siliconflow: ['https://api.siliconflow.cn/v1', 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B'],
        deepseek: ['https://api.deepseek.com/v1', 'deepseek-chat'],
        custom: ['', '']
    };

    /* ---------------- 基础工具 ---------------- */
    function el(tag, cls, html) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        if (html !== undefined) n.innerHTML = html;
        return n;
    }

    function icon(name) {
        return '<span class="material-icons">' + name + '</span>';
    }

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

/* ---------------- 轻量 Markdown 渲染 ---------------- */
    /* ---------------- 轻量 Markdown 渲染 ---------------- */
    function inlineFormat(escaped) {
        return escaped
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/`([^`]+)`/g, '<code>$1</code>');
    }

    function parseRow(line) {
        var cells = line.trim();
        if (cells.charAt(0) === '|') cells = cells.slice(1);
        if (cells.charAt(cells.length - 1) === '|') cells = cells.slice(0, -1);
        return cells.split('|').map(function (c) { return c.trim(); });
    }

    /** 判断第 i 行是否是表格开头：本行有 |，下一行是 ---|--- 的分隔行 */
    function isTableStart(lines, i) {
        if (i + 1 >= lines.length) return false;
        if (lines[i].indexOf('|') === -1) return false;
        var sep = lines[i + 1].trim();
        if (sep.indexOf('|') === -1 || sep.indexOf('-') === -1) return false;
        return /^\|?[\s:|-]+\|[\s:|-]*$/.test(sep);
    }

    function renderTable(lines, start) {
        var header = parseRow(lines[start]);
        var rows = [];
        var i = start + 2;

        while (i < lines.length && lines[i].trim() !== '' && lines[i].indexOf('|') !== -1) {
            rows.push(parseRow(lines[i]));
            i++;
        }

        var html = '<div class="md-table-wrap"><table class="md-table"><thead><tr>';
        header.forEach(function (h) { html += '<th>' + inlineFormat(h) + '</th>'; });
        html += '</tr></thead><tbody>';
        rows.forEach(function (row) {
            html += '<tr>';
            header.forEach(function (_, idx) {
                html += '<td>' + inlineFormat(row[idx] || '') + '</td>';
            });
            html += '</tr>';
        });
        html += '</tbody></table></div>';
        return { html: html, next: i };
    }

    /**
     * 纯文本 → 安全 HTML：先整体转义，再只放行我们自己生成的标签。
     * 支持：**粗体**、`代码`、- 列表、### 小标题、表格、--- 分隔线
     */
    function formatMessage(text) {
        var safe = escapeHtml(text || '');
        var lines = safe.split('\n');
        var html = '';
        var inList = false;
        var i = 0;

        while (i < lines.length) {
            var line = lines[i];
            var trimmed = line.trim();

            // 表格
            if (isTableStart(lines, i)) {
                if (inList) { html += '</ul>'; inList = false; }
                var table = renderTable(lines, i);
                html += table.html;
                i = table.next;
                continue;
            }

            // 只把 - * + 当列表；“3. 平台优势”这类编号小节保留成普通段落
            var bullet = trimmed.match(/^[-*+]\s+(.*)$/);
            var item = bullet ? bullet[1] : null;

            if (item !== null) {
                if (!inList) { html += '<ul>'; inList = true; }
                html += '<li>' + inlineFormat(item) + '</li>';
                i++;
                continue;
            }

            if (inList) { html += '</ul>'; inList = false; }

            if (/^(-{3,}|\*{3,})$/.test(trimmed)) {
                html += '<hr class="md-hr">';
            } else if (trimmed === '') {
                html += '<div class="gap"></div>';
            } else if (/^#{1,6}\s/.test(trimmed)) {
                html += '<div class="md-h">' + inlineFormat(trimmed.replace(/^#{1,6}\s+/, '')) + '</div>';
            } else {
                html += '<div class="md-p">' + inlineFormat(line) + '</div>';
            }
            i++;
        }

        if (inList) html += '</ul>';
        return html;
    }

    // 只在用户本来就贴着底部时才自动跟到底。
    // 之前每来一段流式内容就强制 scrollTop，用户往上翻看历史会被立刻拽回去。
    var stickBottom = true;
    var STICK_THRESHOLD = 80;   // 距底部多少像素内算"贴底"

    function nearBottom() {
        var box = $('messages');
        if (!box) return true;
        return box.scrollHeight - box.scrollTop - box.clientHeight < STICK_THRESHOLD;
    }

    function scrollBottom(force) {
        var box = $('messages');
        if (!box) return;
        if (!force && !stickBottom) return;   // 用户在读历史，别打扰
        box.scrollTop = box.scrollHeight;
    }

    function toast(text, ok) {
        var wrap = $('toastWrap');
        while (wrap.children.length >= 3) wrap.removeChild(wrap.firstChild);
        var node = el('div', 'toast' + (ok ? ' ok' : ''),
            icon(ok ? 'check_circle' : 'info') + '<span>' + escapeHtml(text) + '</span>');
        wrap.appendChild(node);
        setTimeout(function () {
            node.style.opacity = '0';
            node.style.transition = 'opacity .3s';
            setTimeout(function () { node.remove(); }, 300);
        }, 2400);
    }

    function api(path, options) {
        return fetch(path, options).catch(function (e) {
            // fetch 抛 TypeError 说明连接没建立，和后端返回错误不是一回事
            throw new Error(e && e.message === 'Failed to fetch'
                ? '无法连接本机服务，请确认 run.bat 的窗口还开着'
                : (e && e.message) || '网络请求失败');
        }).then(function (r) {
            return r.json().catch(function () { return {}; }).then(function (data) {
                if (!r.ok) {
                    var msg = data.message || data.error || ('HTTP ' + r.status);
                    throw new Error(msg);
                }
                return data;
            });
        });
    }

    /* ---------------- 空状态 ---------------- */
    function buildEmptyState() {
        var node = el('div', 'empty-state');
        node.id = 'emptyState';
        node.innerHTML =
            '<div class="logo">' + icon('auto_awesome') + '</div>' +
            '<h1>今天想处理什么？</h1>' +
            '<p>直接提问，或拖入 PDF / 图片后发送。</p>' +
            '<div class="quick-grid"></div>';

        var grid = node.querySelector('.quick-grid');
        var items = [
            ['picture_as_pdf', '33,150,243', '总结一份 PDF', '选择文件后自动提取并总结', 'file'],
            ['image_search', '33,191,115', '识别图片文字', '选择图片后自动识别', 'image'],
            ['description', '245,158,11', '文本转 PDF', '输入内容后生成文档', 'text'],
            ['manage_search', '139,92,246', '分析长文档', '选择文件后逐段检索', 'file']
        ];

        items.forEach(function (it) {
            var card = el('div', 'quick-card',
                '<span class="q-icon">' + icon(it[0]) + '</span>' +
                '<span class="q-body"><strong>' + it[2] + '</strong><span>' + it[3] + '</span></span>');
            card.style.setProperty('--tone', it[1]);
            card.addEventListener('click', function () {
                if (it[4] === 'text') {
                    $('input').value = '把下面这段内容做成 PDF：\n\n';
                    autoGrow();
                    updateSendBtn();
                    $('input').focus();
                } else {
                    // 选文件：图片类只筛图片，其余放开
                    $('fileInput').setAttribute('accept', it[4] === 'image' ? 'image/*' : '.pdf,.txt,.md,.csv,.json,image/*');
                    $('fileInput').click();
                }
            });
            grid.appendChild(card);
        });

        return node;
    }

    function clearEmpty() {
        var e = $('emptyState');
        if (e) e.remove();
    }

    /* ---------------- 消息渲染 ---------------- */
    function initLightbox() {
        document.addEventListener('click', function (e) {
            var el2 = e.target;
            if (!el2 || el2.tagName !== 'IMG') return;
            if (el2.classList.contains('msg-thumb') || el2.classList.contains('result-thumb')) {
                openLightbox(el2.src);
            }
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeLightbox();
        });
    }

    /** 图片文件 → 预览地址；非图片返回 undefined */
    function thumbOf(file) {
        if (!file || !file.type || file.type.indexOf('image/') !== 0) return undefined;
        return trackUrl(URL.createObjectURL(file));
    }

    function openLightbox(src) {
        var box = $('lightbox');
        if (!box) {
            // 模板里没有就现场建一个，保证一定能打开
            box = document.createElement('div');
            box.id = 'lightbox';
            box.className = 'lightbox';
            var close = document.createElement('button');
            close.className = 'lightbox-close';
            close.textContent = '\u00d7';
            close.addEventListener('click', closeLightbox);
            var big = document.createElement('img');
            big.id = 'lightboxImg';
            box.appendChild(close);
            box.appendChild(big);
            box.addEventListener('click', function (e) {
                if (e.target === box) closeLightbox();
            });
            document.body.appendChild(box);
        }
        var img = document.getElementById('lightboxImg');
        if (img) img.src = src;

        // 内联样式兜底：即使 CSS 没加载也能显示
        box.style.position = 'fixed';
        box.style.inset = '0';
        box.style.zIndex = '99999';
        box.style.display = 'flex';
        box.style.alignItems = 'center';
        box.style.justifyContent = 'center';
        box.style.background = 'rgba(8, 12, 20, .86)';
        box.style.cursor = 'zoom-out';
    }

    function closeLightbox() {
        var box = document.getElementById('lightbox');
        if (!box) return;
        box.style.display = 'none';
        box.classList.remove('show');
        var img = document.getElementById('lightboxImg');
        if (img) img.removeAttribute('src');
    }

    function addUserMessage(text, files) {
        clearEmpty();
        var msg = el('div', 'msg user');
        msg.innerHTML =
            '<div class="avatar user">' + icon('person') + '</div>' +
            '<div class="bubble-wrap"></div>';
        var wrap = msg.querySelector('.bubble-wrap');

        // 附件预览：图片显示缩略图，其他类型显示文件名条
        var images = (files || []).filter(function (f) {
            return f.type && f.type.indexOf('image/') === 0;
        });
        var others = (files || []).filter(function (f) {
            return !(f.type && f.type.indexOf('image/') === 0);
        });

        if (images.length) {
            var strip = el('div', 'msg-images');
            images.slice(0, 4).forEach(function (f) {
                var img = document.createElement('img');
                img.className = 'msg-thumb';
                img.src = trackUrl(URL.createObjectURL(f));
                img.alt = f.name;
                img.title = f.name + '（点击放大）';
                strip.appendChild(img);
            });
            if (images.length > 4) {
                var more = el('span', 'msg-thumb-more', '+' + (images.length - 4));
                strip.appendChild(more);
            }
            wrap.appendChild(strip);
        }

        if (others.length) {
            var chips = el('div', 'msg-filechips');
            others.forEach(function (f) {
                var chip = el('span', 'msg-filechip', icon('description'));
                var label = document.createElement('span');
                label.textContent = f.name;   // 用 textContent，文件名不可信
                chip.appendChild(label);
                chips.appendChild(chip);
            });
            wrap.appendChild(chips);
        }

        // 只有真的有文字才加气泡：纯图片消息不该再出现「（附件 ×1）」
        if (text && String(text).trim()) {
            var bubble = el('div', 'bubble');
            bubble.textContent = text;
            wrap.appendChild(bubble);
            wrap.appendChild(buildMeta(text, false));
        }

        msgBox().appendChild(msg);
        scrollBottom();
    }

    function addAssistantShell() {
        clearEmpty();
        var msg = el('div', 'msg assistant');
        msg.innerHTML =
            '<div class="avatar">' + icon('smart_toy') + '</div>' +
            '<div class="bubble-wrap"><div class="bubble"></div></div>';
        msgBox().appendChild(msg);
        scrollBottom();
        return msg;
    }

    /** 消息下方的小操作：复制 / 重新生成 */
    function buildMeta(text, canRegenerate) {
        var meta = el('div', 'msg-meta');
        var copy = el('button', '', icon('content_copy') + '<span>复制</span>');
        copy.addEventListener('click', function () {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(text || '').then(function () {
                    toast('已复制', true);
                }).catch(function () { /* 忽略 */ });
            }
        });
        meta.appendChild(copy);

        if (canRegenerate) {
            var retry = el('button', '', icon('refresh') + '<span>重新生成</span>');
            retry.addEventListener('click', regenerate);
            meta.appendChild(retry);
        }
        return meta;
    }

    var lastUserText = '';
    var lastExtracted = '';

    var lastUsage = null;
    state.switching = false;          // 本轮请求的 token 用量
    var sessionTokens = { prompt: 0, completion: 0 };   // 本次会话累计

    function fmtNum(n) {
        n = Number(n) || 0;
        if (n >= 10000) return (n / 1000).toFixed(1) + 'k';
        return String(n);
    }

    function addSessionTokens(usage) {
        sessionTokens.prompt += Number(usage.prompt_tokens) || 0;
        sessionTokens.completion += Number(usage.completion_tokens) || 0;
        var meter = $('tokenMeter');
        if (!meter) return;
        var total = sessionTokens.prompt + sessionTokens.completion;
        meter.textContent = total > 0
            ? '本会话 ↑' + fmtNum(sessionTokens.prompt) + ' ↓' + fmtNum(sessionTokens.completion)
            : '';
        meter.title = '输入 ' + sessionTokens.prompt + ' / 输出 ' + sessionTokens.completion + ' tokens';
    }
   // 最近一次提取出来的附件正文

    function regenerate() {
        if (state.streaming || !lastUserText) return;
        var msgs = msgBox().querySelectorAll('.msg');
        if (msgs.length) msgs[msgs.length - 1].remove();
        sendChat(lastUserText, '');
    }

    /* ---------------- 会话列表 ---------------- */
    function loadConversations() {
        return api('/ai/conversations').then(function (data) {
            state.conversations = (data && data.conversations) || [];
            renderConversations();
        }).catch(function () {
            state.conversations = [];
            renderConversations();
        });
    }

    function renderConversations() {
        var list = $('convList');
        list.innerHTML = '';

        if (!state.conversations.length) {
            list.appendChild(el('div', 'conv-group-title', '还没有对话'));
            return;
        }

        list.appendChild(el('div', 'conv-group-title', '最近对话'));
        state.conversations.forEach(function (conv) {
            var id = conv.conversation_id;
            var title = conv.title || id;
            var active = id === state.conversationId;
            var node = el('div', 'conv-item' + (active ? ' active' : ''),
                icon('chat_bubble_outline') + '<span class="conv-title"></span>');
            node.querySelector('.conv-title').textContent = title;
            node.title = title;

            var del = el('button', 'conv-del', icon('close'));
            del.title = '删除这个对话';
            del.addEventListener('click', function (e) {
                e.stopPropagation();
                removeConversation(id);
            });
            node.appendChild(del);

            node.addEventListener('click', function () { openConversation(id); });
            list.appendChild(node);
        });
    }

    /** 按 id 找到会话标题 */
    function titleOf(id) {
        for (var i = 0; i < state.conversations.length; i++) {
            if (state.conversations[i].conversation_id === id) {
                return state.conversations[i].title || id;
            }
        }
        return id;
    }

    function openConversation(id) {
        state.conversationId = id;
        $('convTitle').textContent = titleOf(id);
        renderConversations();
        revokeUrls();
        msgBox().innerHTML = '';

        api('/ai/history?conversation_id=' + encodeURIComponent(id)).then(function (data) {
            var history = (data && data.history) || [];
            if (!history.length) {
                msgBox().appendChild(buildEmptyState());
                return;
            }
            history.forEach(function (m) {
                if (m.role === 'user') {
                    var msg = el('div', 'msg user');
                    msg.innerHTML = '<div class="avatar user">' + icon('person') + '</div>' +
                        '<div class="bubble-wrap"><div class="bubble"></div></div>';

                    // 存档里带上了附件正文（追问时要用），显示时只取用户真正写的部分
                    var raw = m.content || '';
                    var marker = '【附件内容】';
                    var cut = raw.indexOf(marker);
                    var visible = cut >= 0 ? raw.slice(0, cut).trim() : raw;
                    var wrap = msg.querySelector('.bubble-wrap');
                    var bubble = msg.querySelector('.bubble');
                    bubble.textContent = visible || '（附件）';

                    if (cut >= 0) {
                        var tag = el('span', 'attach-tag', '含附件内容');
                        wrap.appendChild(tag);
                    }
                    msgBox().appendChild(msg);
                } else {
                    var a = el('div', 'msg assistant');
                    a.innerHTML = '<div class="avatar">' + icon('smart_toy') + '</div>' +
                        '<div class="bubble-wrap"><div class="bubble"></div></div>';
                    a.querySelector('.bubble').innerHTML = formatMessage(m.content || '');
                    msgBox().appendChild(a);
                }
            });
            scrollBottom();
        }).catch(function (e) {
            toast('读取对话失败：' + e.message);
        });
    }

    function removeConversation(id) {
        api('/ai/history/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conversation_id: id })
        }).then(function () {
            if (state.conversationId === id) {
                state.conversationId = null;
                revokeUrls();
        msgBox().innerHTML = '';
                msgBox().appendChild(buildEmptyState());
                $('convTitle').textContent = '新对话';
            }
            return loadConversations();
        }).then(function () {
            toast('已删除', true);
        }).catch(function (e) {
            toast('删除失败：' + e.message);
        });
    }

    function newChat() {
        stopStreaming();
        state.conversationId = null;
        state.pendingTitle = '新对话';
        $('convTitle').textContent = '新对话';
        revokeUrls();
        msgBox().innerHTML = '';
        msgBox().appendChild(buildEmptyState());
        renderConversations();
        $('input').focus();
    }

    /* ---------------- 附件暂存 ---------------- */
    var stagedFiles = [];
    var objectUrls = [];   // 消息里的缩略图地址，切会话时统一释放

    function trackUrl(url) { objectUrls.push(url); return url; }

    function revokeUrls() {
        objectUrls.forEach(function (u) { try { URL.revokeObjectURL(u); } catch (e) {} });
        objectUrls = [];
    }

    function humanSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }

    function renderStaged() {
        var box = $('staged');
        box.innerHTML = '';
        box.classList.toggle('has', stagedFiles.length > 0);

        stagedFiles.forEach(function (file, index) {
            var isImage = file.type && file.type.indexOf('image/') === 0;
            var node = el('div', 'staged-item');
            var thumb = el('span', 'si-thumb');
            if (isImage) {
                var img = document.createElement('img');
                img.src = URL.createObjectURL(file);
                img.alt = file.name;
                img.onload = function () { URL.revokeObjectURL(img.src); };
                thumb.appendChild(img);
            } else {
                thumb.innerHTML = icon(/\.pdf$/i.test(file.name) ? 'picture_as_pdf' : 'description');
            }
            var meta = el('span', 'si-meta',
                '<span class="si-name"></span><span class="si-size"></span>');
            meta.querySelector('.si-name').textContent = file.name;
            meta.querySelector('.si-size').textContent = humanSize(file.size);

            var x = el('button', 'si-x', icon('close'));
            x.title = '移除';
            x.addEventListener('click', function () {
                stagedFiles.splice(index, 1);
                renderStaged();
                updateSendBtn();
            });

            node.appendChild(thumb);
            node.appendChild(meta);
            node.appendChild(x);
            box.appendChild(node);
        });
        updateSendBtn();
    }

    function stageFiles(files) {
        Array.prototype.slice.call(files).forEach(function (f) { stagedFiles.push(f); });
        renderStaged();
    }

    function clearStaged() {
        stagedFiles = [];
        renderStaged();
    }

    /* ---------------- 发送（SSE 流式） ---------------- */
    function updateSendBtn() {
        var btn = $('sendBtn');
        btn.innerHTML = icon(state.streaming ? 'stop' : 'arrow_upward');
        btn.disabled = !state.streaming && $('input').value.trim() === '' && stagedFiles.length === 0;
    }

    function autoGrow() {
        var ta = $('input');
        ta.style.height = 'auto';
        ta.style.height = Math.min(190, ta.scrollHeight) + 'px';
    }

    function send() {
        if (state.streaming) { stopStreaming(); return; }

        var text = $('input').value.trim();
        if (!text && !stagedFiles.length) return;

        if (!state.configured) {
            toast('还没配置 API Key');
            openSettings();
            return;
        }

        var files = stagedFiles.slice();
        clearStaged();
        $('input').value = '';
        autoGrow();
        updateSendBtn();

        if (!files.length) {
            addUserMessage(text);
            sendChat(text, '');
            return;
        }

        lastUserText = text || '请阅读这些文件并总结要点';
        stickBottom = true;
        addUserMessage(text, files);
        processFiles(files, function (contextText) {
            if (!contextText) {
                toast('文件没能解析出内容，换个文件或直接把文字贴进来');
                return;
            }
            lastExtracted = contextText;
            if (!text) {
                // 只上传了文件、没提问：只提取，不调用模型。
                // 想总结就点结果卡片上的「让 AI 总结」，避免白白消耗 token。
                toast('已提取内容，可直接复制，或点卡片上的「让 AI 总结」', true);
                return;
            }
            sendChat(text, contextText);
        });
    }

    /* ---------------- 文件 → 任务 ---------------- */
    function processFiles(files, done) {
        var collected = [];
        var index = 0;

        function next() {
            if (index >= files.length) {
                done(collected.join('\n\n'));
                return;
            }
            var file = files[index++];
            var progress = addProgressCard(file.name);

            runFileTask(file).then(function (text) {
                progress.remove();
                addResultCard(file.name, text,
                              undefined, thumbOf(file));
                if (text) collected.push('【' + file.name + '】\n' + text);
                next();
            }).catch(function (e) {
                progress.remove();
                addResultCard(file.name, '', e.message, thumbOf(file));
                next();
            });
        }
        next();
    }

    function extractText(result) {
        if (!result || !result.results) return '';
        var out = [];
        result.results.forEach(function (r) {
            if (!r) return;
            if (r.text) { out.push(r.text); return; }
            if (r.pages) {
                r.pages.forEach(function (p) { if (p && p.text) out.push(p.text); });
            }
        });
        return out.join('\n');
    }

    /** 把文件变成纯文本：txt 本地读、pdf 走提取、图片走 OCR */
    function runFileTask(file) {
        var name = (file.name || '').toLowerCase();

        // 纯文本类：直接本地读，不用上传也就不用 OCR
        var isText = /\.(txt|md|markdown|csv|json|log|py|js|css|html)$/.test(name)
            || (file.type && file.type.indexOf('text/') === 0);
        if (isText) {
            return file.text().then(function (t) {
                if (!t || !t.trim()) throw new Error('文件是空的');
                return t;
            });
        }

        var isPdf = /\.pdf$/.test(name) || file.type === 'application/pdf';
        var isImage = file.type && file.type.indexOf('image/') === 0;

        if (!isPdf && !isImage) {
            return Promise.reject(new Error('暂不支持这种文件类型（可试 txt / pdf / 图片）'));
        }

        var fd = new FormData();
        fd.append(isPdf ? 'pdfs' : 'images', file, file.name);

        return fetch(isPdf ? '/extract-pdf' : '/process-images', { method: 'POST', body: fd })
            .then(function (r) {
                return r.json().catch(function () { return {}; }).then(function (d) {
                    if (!r.ok) throw new Error(d.error || d.message || ('HTTP ' + r.status));
                    return d;
                });
            })
            .then(function (d) {
                if (!d.task_id) throw new Error(d.error || d.message || '任务创建失败');
                return pollTask(d.task_id);
            })
            .then(function (result) {
                var text = extractText(result);
                if (!text) throw new Error('没有提取到文本内容');
                return text;
            });
    }

    function pollTask(taskId) {
        return new Promise(function (resolve, reject) {
            var tries = 0;
            var timer = setInterval(function () {
                tries++;
                if (tries > 120) {
                    clearInterval(timer);
                    reject(new Error('任务超时（2 分钟）'));
                    return;
                }
                fetch('/tasks/' + taskId)
                    .then(function (r) { return r.json(); })
                    .then(function (d) {
                        if (d.status === 'SUCCESS') {
                            clearInterval(timer);
                            resolve(d.result);
                        } else if (d.status === 'FAILURE') {
                            clearInterval(timer);
                            reject(new Error(d.error || '任务失败'));
                        }
                    })
                    .catch(function (e) {
                        clearInterval(timer);
                        reject(e);
                    });
            }, 1000);
        });
    }

    /** 处理中的占位卡片：先给用户一个"在动"的信号 */
    function addProgressCard(name) {
        clearEmpty();
        var msg = el('div', 'msg assistant');
        msg.innerHTML = '<div class="avatar">' + icon('hourglass_top') + '</div>' +
            '<div class="bubble-wrap"></div>';
        var wrap = msg.querySelector('.bubble-wrap');
        var card = el('div', 'progress-card',
            '<div class="progress-head">' + icon('autorenew') +
            '<span class="p-label"></span></div>' +
            '<div class="progress-bar"><i class="indeterminate"></i></div>');
        card.querySelector('.p-label').textContent = '正在处理 ' + name + ' …';
        wrap.appendChild(card);
        msgBox().appendChild(msg);
        scrollBottom();

        return {
            remove: function () { msg.remove(); }
        };
    }

    function addResultCard(name, text, error, thumbUrl) {
        clearEmpty();
        var msg = el('div', 'msg assistant');
        msg.innerHTML = '<div class="avatar">' + icon('description') + '</div>' +
            '<div class="bubble-wrap"></div>';
        var wrap = msg.querySelector('.bubble-wrap');
        var card = el('div', 'result-card');

        // 头部：小缩略图（或图标）+ 标题
        var head = el('div', 'result-head');
        if (thumbUrl) {
            var th = document.createElement('img');
            th.className = 'result-thumb-sm';
            th.src = thumbUrl;
            th.alt = name;
            th.title = '点击查看原图';
            head.appendChild(th);
        } else {
            head.appendChild(el('span', 'result-icon', icon(error ? 'error' : 'text_snippet')));
        }
        var title = el('span', 'result-title');
        title.textContent = error ? (name + ' 处理失败') : (name + ' · ' + (text || '').length + ' 字');
        head.appendChild(title);
        card.appendChild(head);

        if (error) {
            var errBody = el('div', 'result-body');
            var em = el('span', 'error-message');
            em.textContent = error;
            errBody.appendChild(em);
            card.appendChild(errBody);
        } else {
            var bodyText = text || '（没有提取到文本）';
            var body = el('div', 'result-body clamped');
            body.textContent = bodyText;
            card.appendChild(body);

            var foot = el('div', 'result-foot');

            var expand = el('button', 'chip', icon('unfold_more') + '<span>展开全文</span>');
            expand.addEventListener('click', function () {
                body.classList.toggle('clamped');
                expand.querySelector('span').textContent =
                    body.classList.contains('clamped') ? '展开全文' : '收起';
            });
            foot.appendChild(expand);

            var copy = el('button', 'chip', icon('content_copy') + '<span>复制</span>');
            copy.addEventListener('click', function () {
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(bodyText).then(function () {
                        toast('已复制全部内容', true);
                    }).catch(function () { /* 忽略 */ });
                }
            });
            foot.appendChild(copy);

            // 需要模型参与时才调用，不再是"上传即总结"
            if (text) {
                var summarize = el('button', 'chip primary', icon('auto_awesome') + '<span>让 AI 总结</span>');
                summarize.addEventListener('click', function () {
                    if (state.streaming) return;
                    sendChat('请总结这些内容的要点', '【' + name + '】\n' + text);
                });
                foot.appendChild(summarize);
            }

            card.appendChild(foot);
        }

        wrap.appendChild(card);
        msgBox().appendChild(msg);
        scrollBottom();
    }

    /* 有会话 id 才带上，避免后端把 null 当作"已指定会话" */
    function buildChatBody(text) {
        var body = { message: text, stream: true, model: 'deepseek_api' };
        if (state.conversationId) body.conversation_id = state.conversationId;
        return body;
    }

    /* ---------------- 对话请求 ---------------- */
    function sendChat(text, contextText) {
        var shell = addAssistantShell();
        var bubble = shell.querySelector('.bubble');
        var cursor = el('span', 'cursor');
        bubble.appendChild(cursor);

        var payloadText = text;
        if (contextText) {
            payloadText += '\n\n【附件内容】\n' + contextText.slice(0, 6000);
        }

        state.streaming = true;
        state.controller = new AbortController();
        $('sendBtn').innerHTML = icon('stop');
        $('sendBtn').disabled = false;

        var full = '';
        lastUsage = null;

        fetch('/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(buildChatBody(payloadText)),
            signal: state.controller.signal
        }).then(function (response) {
            if (!response.ok) {
                return response.json().catch(function () { return {}; }).then(function (d) {
                    throw new Error(d.error || ('HTTP ' + response.status));
                });
            }

            var ctype = response.headers.get('Content-Type') || '';
            if (ctype.indexOf('text/event-stream') === -1) {
                return response.json().then(function (data) {
                    if (data.error) throw new Error(data.error);
                    full = data.response || data.content || '';
                    bubble.innerHTML = formatMessage(full);
                    finish();
                });
            }

            var reader = response.body.getReader();
            var decoder = new TextDecoder();
            var buffer = '';

            function pump() {
                return reader.read().then(function (res) {
                    if (res.done) { finish(); return; }
                    buffer += decoder.decode(res.value, { stream: true });
                    var blocks = buffer.split('\n\n');
                    buffer = blocks.pop();

                    blocks.forEach(function (block) {
                        block.split('\n').forEach(function (line) {
                            if (line.indexOf('data: ') !== 0) return;
                            var raw = line.slice(6).trim();
                            if (!raw || raw === '[DONE]') return;
                            try {
                                var obj = JSON.parse(raw);
                                if (obj.conversation_id) {
                                    state.conversationId = obj.conversation_id;
                                    $('convTitle').textContent = titleOf(obj.conversation_id);
                                }
                                if (obj.usage) {
                                    lastUsage = obj.usage;
                                    addSessionTokens(obj.usage);
                                }
                                if (obj.content) {
                                    full += obj.content;
                                    bubble.innerHTML = formatMessage(full);
                                    scrollBottom();
                                }
                            } catch (e) { /* 半个 JSON，忽略 */ }
                        });
                    });
                    return pump();
                });
            }
            return pump();

        }).catch(function (e) {
            if (e.name === 'AbortError') {
                bubble.innerHTML = formatMessage(full + '\n\n（已停止生成）');
            } else {
                bubble.innerHTML = formatMessage('出错了：' + e.message);
            }
            finish();
        });

        function finish() {
            cursor.remove();
            if (full) {
                var wrap = shell.querySelector('.bubble-wrap');
                if (wrap && !wrap.querySelector('.msg-meta')) {
                    wrap.appendChild(buildMeta(full, true));
                }
                if (lastUsage && wrap) {
                    var u = el('div', 'msg-usage');
                    u.textContent = '↑ ' + fmtNum(lastUsage.prompt_tokens) +
                        ' · ↓ ' + fmtNum(lastUsage.completion_tokens) + ' tokens';
                    u.title = '本次请求消耗：输入 ' + lastUsage.prompt_tokens +
                        ' / 输出 ' + lastUsage.completion_tokens;
                    wrap.appendChild(u);
                }
            }
            state.streaming = false;
            state.controller = null;
            updateSendBtn();
            loadConversations();
        }
    }

    function stopStreaming() {
        if (state.controller) state.controller.abort();
        state.streaming = false;
        document.querySelectorAll('.cursor').forEach(function (c) { c.remove(); });
        updateSendBtn();
    }

    /* ---------------- 设置 ---------------- */
    function loadSettings() {
        return api('/api/settings').then(function (data) {
            state.configured = !!data.configured;
            state.settings = data.settings || state.settings;
            paintModelLabel();
            if (!state.configured) {
                setTimeout(function () {
                    toast('先填一个 API Key 才能开始对话');
                    openSettings();
                }, 400);
            }
        }).catch(function () { /* 忽略 */ });
    }

    function paintModelLabel() {
        var model = state.settings.model || '未配置模型';
        var shortName = model.split('/').pop();
        $('modelChipLabel').textContent = shortName;
        $('modelChip').title = model;
    }

    /* ---------------- 快速切换模型 ---------------- */
    function toggleModelMenu() {
        var menu = $('modelMenu');
        if (!menu) { openSettings(); return; }
        if (menu.classList.contains('open')) { menu.classList.remove('open'); return; }
        openModelMenu();
    }

    function openModelMenu() {
        var menu = $('modelMenu');
        var list = $('modelMenuList');
        if (!menu || !list) return;

        var models = state.models || [];
        if (!models.length) {
            list.innerHTML = '<div class="mm-empty">还没有模型列表，先拉取一次…</div>';
            menu.classList.add('open');
            fetchModelsForMenu();
            return;
        }
        renderModelMenu();
        menu.classList.add('open');
    }

    /** 菜单里只放能对话的模型（纯文本 + 识图） */
    function renderModelMenu() {
        var list = $('modelMenuList');
        // 对话只用纯文本模型；识图模型在「设置 → 图片识别」里单独选
        var items = (state.models || []).filter(function (m) {
            return m.kind === 'text' || m.id === state.settings.model;
        });
        if (!items.length) {
            list.innerHTML = '<div class="mm-empty">列表里没有可对话的纯文本模型</div>';
            return;
        }
        list.innerHTML = '';
        items.forEach(function (m) {
            var row = el('div', 'mm-item' + (m.id === state.settings.model ? ' active' : ''),
                '<span class="mm-name"></span>');
            row.title = m.id;
            row.querySelector('.mm-name').textContent = m.id;

            var cap = chatCap(m.id);
            if (cap !== null) {
                var mark = el('span', 'mm-cap' + (cap ? ' ok' : ' bad'), cap ? '\u2713' : '\u2715');
                mark.title = cap ? '已验证可以对话' : '已验证无法对话';
                row.appendChild(mark);
            }
            // 纯文本是绝大多数，没必要每行都标；只有特殊能力才显示标签
            if (m.kind && m.kind !== 'text') {
                var tag = el('span', 'model-kind kind-' + m.kind);
                tag.textContent = m.label || m.kind;
                row.appendChild(tag);
            }
            row.addEventListener('click', function () {
                switchModel(m.id);
            });
            list.appendChild(row);
        });
    }

    function fetchModelsForMenu() {
        var list = $('modelMenuList');
        api('/api/settings/models', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
            .then(function (res) {
                state.models = res.models || [];
                fillVisionModels();
                renderModelMenu();
            })
            .catch(function (e) {
                if (list) list.innerHTML = '<div class="mm-empty">拉取失败：' + escapeHtml(e.message) + '</div>';
            });
    }

    function switchModel(id) {
        if (!id) return;
        if (state.switching) return;

        var menu = $('modelMenu');
        if (menu) menu.classList.remove('open');
        state.switching = true;
        toast('正在验证 ' + id.split('/').pop() + ' …');

        // 先发一个 1 token 的请求：能用才切换，不能用就保持原状
        api('/api/settings/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: id })
        }).then(function () {
            return api('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: id })
            });
        }).then(function () {
            state.settings.model = id;
            setCap(id, 'chat', true);
            paintModelLabel();
            toast('已切换到 ' + id.split('/').pop(), true);
        }).catch(function (e) {
            setCap(id, 'chat', false);
            toast('这个模型不能用来对话，已保持原模型：' + e.message);
        }).then(function () {
            state.switching = false;
        });
    }

    /** 本地记录一次实测结果，并刷新界面标记 */
    function setCap(id, key, ok) {
        if (!state.settings.model_caps) state.settings.model_caps = {};
        var entry = state.settings.model_caps[id] || {};
        entry[key] = ok;
        state.settings.model_caps[id] = entry;
    }

    /** 该模型是否已验证过对话能力 */
    function chatCap(id) {
        var caps = (state.settings && state.settings.model_caps) || {};
        var entry = caps[id];
        if (!entry || typeof entry.chat !== 'boolean') return null;
        return entry.chat;
    }

    function openSettings() {
        $('provider').value = state.settings.provider || 'siliconflow';
        $('baseUrl').value = state.settings.base_url || '';
        $('modelName').value = state.settings.model || '';
        $('apiKey').value = '';
        $('keyHint').textContent = state.settings.api_key_set
            ? ('已配置：' + state.settings.api_key_masked + '，留空表示不修改')
            : '仅保存在本机 config.json';
        $('testStatus').textContent = '';
        $('testStatus').className = 'test-status';

        // OCR 区块
        var s = state.settings || {};
        if ($('ocrProvider')) {
            $('ocrProvider').value = s.ocr_provider || 'vision';
            $('ocrModel').value = s.ocr_model || '';
            $('ocrBaseUrl').value = s.ocr_base_url || 'https://api.deepseek.com';
            $('ocrApiKey').value = '';
            $('ocrKeyHint').textContent = s.ocr_api_key_set
                ? ('已配置：' + (s.ocr_api_key_masked || '') + '，留空表示不修改')
                : '留空则复用对话的 Key（同域名时）';
            syncOcrProvider();
        }

        $('settingsModal').classList.add('open');
    }

    /** 根据识别方式显示/隐藏 DeepSeek 专属字段 */
    function syncOcrProvider() {
        var sel = $('ocrProvider');
        if (!sel) return;
        var section = sel.closest('.settings-section');
        if (section) section.classList.toggle('deepseek', sel.value === 'deepseek');
        var hint = $('ocrHint');
        if (hint) {
            hint.textContent = {
                vision: '视觉模型直接读取图片，适合截图、表格、拍照文档',
                deepseek: 'DeepSeek 官方 OCR，按页计费（约 ¥0.0016/页），需要单独的 Key',
                tesseract: '本地引擎，需要先安装 Tesseract 与中文语言包'
            }[sel.value] || '';
        }
    }

    function closeSettings() {
        $('settingsModal').classList.remove('open');
    }

    function payload() {
        var data = {
            provider: $('provider').value,
            base_url: $('baseUrl').value.trim(),
            model: $('modelName').value.trim(),
            api_key: $('apiKey').value.trim()
        };
        // OCR 配置（旧版模板没有这些字段时跳过）
        if ($('ocrProvider')) {
            data.ocr_provider = $('ocrProvider').value;
            data.ocr_model = $('ocrModel').value.trim();
            data.ocr_base_url = $('ocrBaseUrl').value.trim();
            var ocrKey = $('ocrApiKey').value.trim();
            if (ocrKey) data.ocr_api_key = ocrKey;   // 留空表示不修改
        }
        return data;
    }

    /** 拉取列表后刷新 OCR 下拉的候选 */
    function fillVisionModels() {
        if ($('ocrModelList')) renderOcrModelList();
        if ($('modelMenu') && $('modelMenu').classList.contains('open')) renderModelMenu();
    }

    /* ---------------- OCR 模型下拉（只列可看图的模型） ---------------- */
    var ocrTyped = false;

    /** 箭头随展开状态翻转（内联 transform，不依赖 CSS） */
    function rotateArrow(open) {
        var combo = document.getElementById('ocrCombo');
        if (!combo) return;
        var arrow = combo.querySelector('.combo-arrow');
        if (!arrow) return;
        arrow.style.transform = 'translateY(-50%) rotate(' + (open ? 180 : 0) + 'deg)';
        arrow.style.color = open ? 'var(--primary-color)' : 'var(--text-muted)';
    }

    function closeOcrList() {
        var list = $('ocrModelList');
        if (list) {
            list.classList.remove('open');
            list.style.top = '';
            list.style.bottom = '';
            list.style.left = '';
            list.style.width = '';
            list.style.maxHeight = '';
        }
        var combo = $('ocrCombo');
        if (combo) combo.classList.remove('active');
        rotateArrow(false);
    }

    function renderOcrModelList() {
        var list = $('ocrModelList');
        if (!list) return;
        var keyword = ocrTyped ? ($('ocrModel').value || '').trim().toLowerCase() : '';
        // 识图（VL）和 OCR 专用模型都能处理图片
        var items = (state.models || []).filter(function (m) {
            if (m.kind !== 'vision' && m.kind !== 'ocr') return false;
            return !keyword || m.id.toLowerCase().indexOf(keyword) !== -1;
        });
        if (!items.length) {
            list.innerHTML = '<div class="combo-empty">' +
                ((state.models || []).length ? '没有可看图的模型，先点「获取列表」' : '先点「获取列表」拉取模型') +
                '</div>';
            return;
        }
        list.innerHTML = '';
        items.forEach(function (m) {
            var row = el('div', 'combo-item' + (m.id === $('ocrModel').value ? ' active' : ''),
                '<span class="model-name"></span><span class="model-kind kind-' + m.kind + '"></span>');
            row.querySelector('.model-name').textContent = m.id;
            row.querySelector('.model-kind').textContent = m.label || '';
            row.addEventListener('mousedown', function (e) {
                e.preventDefault();
                e.stopPropagation();
                $('ocrModel').value = m.id;
                ocrTyped = false;
                closeOcrList();
            });
            list.appendChild(row);
        });
    }

    /* ---------------- 主题 ---------------- */
    function applyTheme(dark) {
        if (dark) document.documentElement.setAttribute('data-theme', 'dark');
        else document.documentElement.removeAttribute('data-theme');
        $('themeBtn').innerHTML = icon(dark ? 'light_mode' : 'dark_mode');
    }


    /* ---------------- 动态背景：极光视差 + 粒子网络 + 光标高光 ---------------- */
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


    /** 从主界面带过来的参数：q=要发送的内容，intent=file|image 打开文件选择 */
    function consumeEntryParams() {
        var params = new URLSearchParams(window.location.search);
        var q = params.get('q');
        var intent = params.get('intent');
        if (!q && !intent) return false;

        if (q) {
            $('input').value = q;
            autoGrow();
            updateSendBtn();
        }
        if (intent) {
            $('fileInput').setAttribute('accept', intent === 'image' ? 'image/*' : '.pdf,.txt,.md,.csv,.json,image/*');
            setTimeout(function () { $('fileInput').click(); }, 250);
        }
        if (q && !intent) {
            setTimeout(send, 300);
        }

        // 清掉参数，避免刷新时重复发送
        try {
            window.history.replaceState({}, '', window.location.pathname);
        } catch (e) { /* 忽略 */ }
        return true;
    }

    /* ---------------- 初始化 ---------------- */
    function init() {
        var savedTheme = null;
        try { savedTheme = localStorage.getItem('qing-theme'); } catch (e) { /* 忽略 */ }
        applyTheme(savedTheme === 'dark');

        var sidebar = $('sidebar');
        function applySidebar(collapsed) {
            sidebar.classList.toggle('collapsed', collapsed);
            $('sidebarToggle').innerHTML = icon(collapsed ? 'menu' : 'menu_open');
        }
        applySidebar(true);
        $('sidebarToggle').addEventListener('click', function () {
            applySidebar(!sidebar.classList.contains('collapsed'));
        });

        $('themeBtn').addEventListener('click', function () {
            var dark = !document.documentElement.hasAttribute('data-theme');
            applyTheme(dark);
            try { localStorage.setItem('qing-theme', dark ? 'dark' : 'light'); } catch (e) { /* 忽略 */ }
        });

        $('newChatBtn').addEventListener('click', newChat);
        $('sendBtn').addEventListener('click', send);

        /* ---- 附件：点击选择 + 整页拖放 ---- */
        $('attachBtn').addEventListener('click', function () { $('fileInput').click(); });
        $('fileInput').addEventListener('change', function (e) {
            stageFiles(e.target.files);
            e.target.value = '';
        });

        /* ---- 整页拖放 ----
           注意：不能只靠 dataTransfer.types 判断。某些浏览器/来源下它不可靠，
           一旦误判就 return，dragover 没被 preventDefault，浏览器会认为
           "这里不接受放置"，松手时直接打开文件。所以：
             - dragover 一律 preventDefault（允许放置）
             - 只用一个宽容的判断决定"要不要显示遮罩" */
        var dragDepth = 0;

        function isFileDrag(e) {
            var dt = e.dataTransfer;
            if (!dt) return false;

            var types = dt.types || [];
            for (var i = 0; i < types.length; i++) {
                if (String(types[i]).toLowerCase() === 'files') return true;
            }
            var items = dt.items || [];
            for (var j = 0; j < items.length; j++) {
                if (items[j] && items[j].kind === 'file') return true;
            }
            return !!(dt.files && dt.files.length);
        }

        /* 遮罩在运行时创建：模板里可能没有（缓存），CSS 也可能没加载，
           所以用内联样式兜底，确保一定能显示 */
        function ensureVeil() {
            var veil = document.getElementById('dropVeil');
            if (veil) return veil;

            veil = document.createElement('div');
            veil.id = 'dropVeil';
            veil.setAttribute('aria-hidden', 'true');
            veil.style.position = 'fixed';
            veil.style.inset = '0';
            veil.style.zIndex = '9999';
            veil.style.display = 'none';
            veil.style.alignItems = 'center';
            veil.style.justifyContent = 'center';
            veil.style.background = 'rgba(12, 18, 30, .45)';
            veil.style.backdropFilter = 'blur(2px)';
            veil.style.pointerEvents = 'none';

            var box = document.createElement('div');
            box.style.padding = '34px 54px';
            box.style.border = '2px dashed rgba(255,255,255,.7)';
            box.style.borderRadius = '22px';
            box.style.background = 'rgba(33, 150, 243, .24)';
            box.style.color = '#fff';
            box.style.textAlign = 'center';
            box.style.boxShadow = '0 18px 44px rgba(0,0,0,.3)';
            box.innerHTML =
                '<span class="material-icons" style="font-size:38px;display:block;margin-bottom:8px;">upload_file</span>' +
                '<p style="margin:0;font-size:15px;font-weight:600;">松开即可添加文件</p>' +
                '<small style="display:block;margin-top:6px;font-size:12px;opacity:.85;">PDF / 图片 / 文本</small>';

            veil.appendChild(box);
            document.body.appendChild(veil);
            return veil;
        }

        function showVeil() {
            ensureVeil().style.display = 'flex';
            var composer = $('composer');
            if (composer) composer.classList.add('dragover');
        }

        function hideVeil() {
            var veil = document.getElementById('dropVeil');
            if (veil) veil.style.display = 'none';
            var composer = $('composer');
            if (composer) composer.classList.remove('dragover');
        }

        window.addEventListener('dragenter', function (e) {
            if (!isFileDrag(e)) return;
            e.preventDefault();
            dragDepth++;
            showVeil();
        });

        window.addEventListener('dragover', function (e) {
            // 无条件允许放置，否则浏览器会走"打开文件"的默认行为
            e.preventDefault();
            if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
            if (isFileDrag(e) && dragDepth === 0) {
                dragDepth = 1;
                showVeil();
            }
        });

        window.addEventListener('dragleave', function (e) {
            // 拖出窗口时 relatedTarget 为 null
            if (e.relatedTarget === null) {
                dragDepth = 0;
                hideVeil();
                return;
            }
            dragDepth = Math.max(0, dragDepth - 1);
            if (dragDepth === 0) hideVeil();
        });

        window.addEventListener('drop', function (e) {
            e.preventDefault();
            dragDepth = 0;
            hideVeil();
            var dropped = (e.dataTransfer && e.dataTransfer.files) || [];
            if (dropped.length) {
                stageFiles(dropped);
            }
        });

        if ($('lightboxClose')) {
            $('lightboxClose').addEventListener('click', closeLightbox);
        }
        if ($('lightbox')) {
            $('lightbox').addEventListener('click', function (e) {
                if (e.target === $('lightbox')) closeLightbox();
            });
        }
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeLightbox();
        });

        if ($('ocrProvider')) {
            $('ocrProvider').addEventListener('change', syncOcrProvider);
        }

        if ($('ocrModel')) {
            function openOcrList() {
                ocrTyped = false;
                closeModelList();
                $('ocrCombo').classList.add('active');
                rotateArrow(true);
                renderOcrModelList();

                // 弹窗底部空间不足时向上展开，否则列表会被 modal 的 overflow 裁掉
                var list = $('ocrModelList');
                var rect = $('ocrModel').getBoundingClientRect();
                // 优先向下展开，用 max-height 适配剩余空间；
                // 只有下方几乎没有空间时才向上弹，避免盖住上面的字段
                // 弹窗自身是 overflow:auto，绝对定位会被裁掉。
                // 改成 fixed 定位到输入框下方，空间不足时向上翻。
                var list = $('ocrModelList');
                var rect = $('ocrModel').getBoundingClientRect();
                var spaceBelow = window.innerHeight - rect.bottom - 16;
                var spaceAbove = rect.top - 16;
                var want = 300;

                list.style.position = 'fixed';
                list.style.left = rect.left + 'px';
                list.style.width = rect.width + 'px';

                if (spaceBelow >= Math.min(want, 200) || spaceBelow >= spaceAbove) {
                    list.classList.remove('up');
                    list.style.top = (rect.bottom + 6) + 'px';
                    list.style.bottom = 'auto';
                    list.style.maxHeight = Math.min(want, spaceBelow) + 'px';
                } else {
                    list.classList.add('up');
                    list.style.bottom = (window.innerHeight - rect.top + 6) + 'px';
                    list.style.top = 'auto';
                    list.style.maxHeight = Math.min(want, spaceAbove) + 'px';
                }
                list.classList.add('open');
            }
            $('ocrModel').addEventListener('focus', openOcrList);
            // 点箭头或输入框空白处也能展开（箭头本身 pointer-events:none，事件落在 combo 上）
            $('ocrCombo').addEventListener('click', function (e) {
                if (e.target.tagName !== 'INPUT' || e.target.value === '') {
                    openOcrList();
                }
            });
            $('ocrModel').addEventListener('input', function () {
                ocrTyped = true;
                renderOcrModelList();
                $('ocrModelList').classList.add('open');
            });
            document.addEventListener('mousedown', function (e) {
                if (!e.target.closest('#ocrCombo')) closeOcrList();
            });
        }
        if ($('modelMenuMore')) {
            $('modelMenuMore').addEventListener('click', function () {
                $('modelMenu').classList.remove('open');
                openSettings();
            });
        }
        document.addEventListener('mousedown', function (e) {
            if (!e.target.closest('#modelMenu') && !e.target.closest('#modelChip')) {
                var m = $('modelMenu');
                if (m) m.classList.remove('open');
            }
        });

        var modalCard = document.querySelector('#settingsModal .modal-card');
        if (modalCard) {
            modalCard.addEventListener('scroll', function () { closeOcrList(); });
        }
        $('settingsBtn').addEventListener('click', openSettings);
        $('modelChip').addEventListener('click', toggleModelMenu);
        $('closeSettings').addEventListener('click', closeSettings);

        $('settingsModal').addEventListener('click', function (e) {
            if (e.target === $('settingsModal')) closeSettings();
        });

        var input = $('input');
        input.addEventListener('input', function () { autoGrow(); updateSendBtn(); });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
            }
        });

        // 服务商现在是可输入的下拉：只有命中预设时才自动填地址和模型，
        // 自己填的名字不会被覆盖
        function applyProviderPreset() {
            var key = ($('provider').value || '').trim().toLowerCase();
            var preset = PRESETS[key];
            if (!preset) return;
            if (preset[0]) $('baseUrl').value = preset[0];
            if (preset[1]) $('modelName').value = preset[1];
        }
        $('provider').addEventListener('change', applyProviderPreset);
        $('provider').addEventListener('blur', applyProviderPreset);
        $('provider').addEventListener('input', function () {
            if (PRESETS[(this.value || '').trim().toLowerCase()]) applyProviderPreset();
        });

        $('testBtn').addEventListener('click', function () {
            var data = payload();
            var status = $('testStatus');
            if (!data.api_key && !state.settings.api_key_set) {
                status.textContent = '请先填写 API Key';
                status.className = 'test-status err';
                return;
            }
            status.textContent = '正在测试…';
            status.className = 'test-status busy';
            api('/api/settings/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(function (res) {
                status.textContent = res.message || '连接成功';
                status.className = 'test-status ok';
            }).catch(function (e) {
                status.textContent = e.message;
                status.className = 'test-status err';
            });
        });

        $('probeVisionBtn').addEventListener('click', function () {
            var data = payload();
            var hint = $('modelHint');
            if (!data.model) {
                hint.textContent = '请先选择模型';
                hint.className = 'hint warn';
                return;
            }
            if (!data.api_key && !state.settings.api_key_set) {
                hint.textContent = '请先填写 API Key';
                hint.className = 'hint warn';
                return;
            }
            hint.textContent = '正在探测（约 1 个 token）…';
            hint.className = 'hint';

            api('/api/settings/probe-vision', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(function (res) {
                hint.textContent = (res.supported ? '支持看图：' : '不支持看图：') + res.message;
                hint.className = 'hint ' + (res.supported ? 'ok' : 'warn');
            }).catch(function (e) {
                hint.textContent = e.message;
                hint.className = 'hint warn';
            });
        });
        $('fetchModelsBtn').addEventListener('click', function () {
            var data = payload();
            var hint = $('modelHint');
            if (!data.api_key && !state.settings.api_key_set) {
                hint.textContent = '请先填写 API Key';
                return;
            }
            hint.textContent = '正在拉取模型列表…';
            api('/api/settings/models', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(function (res) {
                state.models = res.models || [];
                fillVisionModels();
                hint.textContent = '共 ' + res.count + ' 个可用模型，点输入框选择';
                toast('拉到 ' + res.count + ' 个模型', true);
                renderModelList();
                openModelList();
            }).catch(function (e) {
                hint.textContent = e.message;
            });
        });

        /* ---- 模型下拉：自建面板，支持点击展开 + 输入过滤 ---- */
        var typedSinceOpen = false;   // 只有用户真的打字了才过滤，避免旧值把列表滤空

        var modelFilter = 'all';
        var KIND_LABELS = {
            text: '纯文本', vision: '识图', audio: '语音',
            embedding: '向量', rerank: '重排', image: '生图', video: '视频'
        };

        function renderModelList() {
            var list = $('modelList');
            var keyword = typedSinceOpen ? ($('modelName').value || '').trim().toLowerCase() : '';
            var models = state.models || [];

            if (!models.length) {
                list.innerHTML = '<div class="combo-empty">还没有拉取模型列表，先点「获取列表」</div>';
                return;
            }

            var counts = {};
            models.forEach(function (m) { counts[m.kind] = (counts[m.kind] || 0) + 1; });

            var head = '<div class="combo-filters">';
            head += filterChip('all', '全部', models.length);
            Object.keys(counts).forEach(function (kind) {
                head += filterChip(kind, KIND_LABELS[kind] || kind, counts[kind]);
            });
            head += '</div>';

            var filtered = models.filter(function (m) {
                if (modelFilter !== 'all' && m.kind !== modelFilter) return false;
                return !keyword || m.id.toLowerCase().indexOf(keyword) !== -1;
            });

            if (!filtered.length) {
                list.innerHTML = head + '<div class="combo-empty">没有匹配的模型</div>';
                bindFilterChips();
                return;
            }

            var body = '<div class="combo-scroll">';
            filtered.slice(0, 400).forEach(function (m) {
                body += '<div class="combo-item' + (m.id === state.settings.model ? ' active' : '') +
                    '" data-id="' + escapeHtml(m.id) + '">' +
                    '<span class="model-name">' + escapeHtml(m.id) + '</span>' +
                    '<span class="model-kind kind-' + m.kind + '">' +
                    escapeHtml(m.label || KIND_LABELS[m.kind] || '') + '</span>' +
                    '</div>';
            });
            body += '</div>';

            list.innerHTML = head + body;
            bindFilterChips();

            Array.prototype.forEach.call(list.querySelectorAll('.combo-item'), function (node) {
                node.addEventListener('mousedown', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    $('modelName').value = node.getAttribute('data-id');
                    typedSinceOpen = false;
                    closeModelList();
                });
            });
        }

        function filterChip(kind, label, n) {
            var active = kind === modelFilter ? ' active' : '';
            return '<button class="combo-chip' + active + '" data-kind="' + kind + '">' +
                escapeHtml(label) + ' <b>' + n + '</b></button>';
        }

        function bindFilterChips() {
            Array.prototype.forEach.call($('modelList').querySelectorAll('.combo-chip'), function (btn) {
                btn.addEventListener('mousedown', function (e) {
                    e.preventDefault();
                    // 关键：不阻止冒泡的话，节点被重建后 document 会把这次点击
                    // 当成"点在弹窗外面"，导致面板刚打开又被关掉
                    e.stopPropagation();
                    modelFilter = btn.getAttribute('data-kind');
                    renderModelList();
                    $('modelList').classList.add('open');
                });
            });
        }

        function openModelList() {
            closeOcrList();
            var combo = $('modelCombo');
            if (combo) combo.classList.add('active');
            renderModelList();
            var list = $('modelList');
            // 下方空间不足时向上展开，避免被弹窗底部裁掉
            var rect = $('modelName').getBoundingClientRect();
            var spaceBelow = window.innerHeight - rect.bottom;
            list.classList.toggle('up', spaceBelow < 320);
            list.classList.add('open');
        }

        function closeModelList() {
            $('modelList').classList.remove('open');
            var combo = $('modelCombo');
            if (combo) combo.classList.remove('active');
        }

        $('modelName').addEventListener('focus', function () {
            typedSinceOpen = false;
            openModelList();
        });
        $('modelName').addEventListener('input', function () {
            typedSinceOpen = true;
            openModelList();
        });
        $('modelName').addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeModelList();
        });
        document.addEventListener('mousedown', function (e) {
            if (!e.target.closest('#modelCombo')) closeModelList();
        });

        $('saveBtn').addEventListener('click', function () {
            var data = payload();
            if (!data.api_key && !state.settings.api_key_set) {
                toast('请先填写 API Key');
                return;
            }
            if (!data.api_key) delete data.api_key;

            api('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(function (res) {
                state.settings = res.settings || state.settings;
                state.configured = true;
                paintModelLabel();
                closeSettings();
                toast('配置已保存', true);
                loadConversations();
            }).catch(function (e) {
                toast('保存失败：' + e.message);
            });
        });


        var msgBoxEl = $('messages');
        var jumpBtn = $('jumpBottom');
        msgBoxEl.addEventListener('scroll', function () {
            stickBottom = nearBottom();
            if (jumpBtn) {
                jumpBtn.classList.toggle('show', !stickBottom && !!state.streaming);
            }
        });
        if (jumpBtn) {
            jumpBtn.addEventListener('click', function () {
                stickBottom = true;
                scrollBottom(true);
                jumpBtn.classList.remove('show');
            });
        }

        initBackdrop();
        initLightbox();
        msgBox().appendChild(buildEmptyState());
        // 等配置加载完再处理 URL 参数，否则自动发送会因为"未配置"而丢内容
        loadSettings().then(function () {
            loadConversations();
            consumeEntryParams();
        });
        updateSendBtn();
        input.focus();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

r"""启动自检：验证依赖、数据库、路由是否正常。

用法（在 cmd 里，先 set PYTHONPATH）：
    set PYTHONPATH=C:\Users\14426\Documents\deepseek-harness\default-workspace\Qing-AI\pydeps
    "C:\Users\14426\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" check.py

全部通过时最后一行是 ALL OK；有失败项会列出具体原因并以非零码退出。
"""
import io
import json
import sys
import traceback

# Windows 控制台默认 GBK，强制 UTF-8 避免中文乱码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FAILS = []
PASSES = []
SKIPPED = []


def check(name, fn):
    try:
        result = fn()
        PASSES.append((name, result))
        print(f'  [OK]   {name}  {result if result else ""}')
    except Exception as e:
        FAILS.append((name, e))
        print(f'  [FAIL] {name}  {type(e).__name__}: {e}')


def skip(name, reason):
    SKIPPED.append((name, reason))
    print(f'  [SKIP] {name}  {reason}')


def main():
    print('=' * 62)
    print(' Qing 启动自检')
    print('=' * 62)

    print('\n[1] 导入模块')
    try:
        import app as app_module
    except Exception:
        print('  [FAIL] import app')
        traceback.print_exc()
        return 1
    print('  [OK]   import app')
    client = app_module.app.test_client()

    print('\n[2] 页面路由')
    for path in ['/', '/welcome', '/legacy']:
        check(f'GET {path}', lambda p=path: _status(client, 'GET', p))
    check('渲染 chat.html', lambda: _render_chat(app_module))

    print('\n[3] 单用户相关接口')
    check('GET /api/check-auth', lambda: _json(client, 'GET', '/api/check-auth'))
    check('GET /api/user-profile', lambda: _json(client, 'GET', '/api/user-profile'))
    check('POST /api/logout', lambda: _json(client, 'POST', '/api/logout'))

    print('\n[4] 历史记录接口')
    check('GET /history', lambda: _json(client, 'GET', '/history'))

    print('\n[5] 已移除的接口（应返回 404/405）')
    for path in ['/api/login', '/api/register', '/login']:
        check(f'{path} 已移除', lambda p=path: _expect_gone(client, p))

    print('\n[6] AI 配置状态')
    check('ai_clients', lambda: _ai_state(app_module))

    print('\n[7] 配置接口')
    check('GET /setup 页面', lambda: _status(client, 'GET', '/setup'))
    check('GET /api/settings', lambda: _settings(client))
    # 注意：这里只做「非法输入应被拒绝」的测试，不能发会写入的合法请求，
    # 否则会覆盖用户已经保存好的 base_url / model
    check('POST /api/settings 拒绝非法 Base URL', lambda: _expect_400(
        client, 'POST', '/api/settings', {'base_url': 'ftp://invalid'}))

    # 已保存 Key 时，空的 api_key 会回退到已存的 Key，请求会真的打到服务商，
    # 既慢又依赖网络，所以只在「尚未配置」时验证拒绝逻辑
    if _key_is_set(client):
        skip('POST /api/settings/test 缺 Key 时拒绝', '已保存 Key，空值会回退到已存 Key')
    else:
        check('POST /api/settings/test 缺 Key 时拒绝', lambda: _expect_400(
            client, 'POST', '/api/settings/test', {'api_key': ''}))

    print('\n[8] 任务执行器（进程内，替代 Celery + Redis）')
    check('delay + 状态流转', _task_runner_selftest)
    check('未知任务返回 FAILURE', _unknown_task)

    print('\n' + '=' * 62)
    if FAILS:
        print(f' {len(PASSES)} 项通过，{len(FAILS)} 项失败')
        for name, e in FAILS:
            print(f'   - {name}: {type(e).__name__}: {e}')
        print('=' * 62)
        return 1
    extra = f'，{len(SKIPPED)} 项跳过' if SKIPPED else ''
    print(f' ALL OK（{len(PASSES)} 项{extra}）')
    print('=' * 62)
    return 0


def _status(client, method, path):
    r = client.open(path, method=method)
    if r.status_code >= 400:
        raise AssertionError(f'HTTP {r.status_code}')
    return f'{r.status_code}, {len(r.data)} bytes'


def _json(client, method, path):
    r = client.open(path, method=method)
    if r.status_code >= 400:
        raise AssertionError(f'HTTP {r.status_code}')
    data = r.get_json()
    if data is None:
        raise AssertionError('返回不是 JSON')
    text = json.dumps(data, ensure_ascii=False)
    return text[:100]


def _task_runner_selftest():
    """跑一个极小的任务，验证 delay → PROCESSING → SUCCESS 的流转。"""
    import time
    from modules.task_runner import TaskProxy, AsyncResult

    def _double(self, value):
        self.update_state(state='PROCESSING', meta={'progress': 50, 'message': '一半'})
        return value * 2

    proxy = TaskProxy(_double, 'selftest')
    submitted = proxy.delay(21)

    deadline = time.time() + 5
    while time.time() < deadline:
        state = AsyncResult(submitted.id).state
        if state == 'SUCCESS':
            result = AsyncResult(submitted.id).result
            if result != 42:
                raise AssertionError(f'结果错误: {result}')
            return 'PENDING→PROCESSING→SUCCESS，结果 42'
        if state == 'FAILURE':
            raise AssertionError(f'任务失败: {AsyncResult(submitted.id).result}')
        time.sleep(0.05)
    raise AssertionError('5 秒内没有完成')


def _unknown_task():
    from modules.task_runner import AsyncResult
    state = AsyncResult('not-exist').state
    if state != 'FAILURE':
        raise AssertionError(f'未知任务应为 FAILURE，实际 {state}')
    return 'FAILURE（不会让前端无限轮询）'


def _render_chat(app_module):
    """直接渲染 chat.html，绕开“未配置就跳 /setup”的分支。"""
    with app_module.app.test_request_context('/'):
        html = app_module.render_template('chat.html')
    for token in ['modelChip', 'settingsModal', 'chat.js']:
        if token not in html:
            raise AssertionError(f'缺少关键元素: {token}')
    return f'{len(html)} bytes，关键元素齐全'


def _settings(client):
    r = client.get('/api/settings')
    if r.status_code != 200:
        raise AssertionError(f'HTTP {r.status_code}')
    data = r.get_json() or {}
    if 'configured' not in data or 'settings' not in data:
        raise AssertionError(f'字段缺失: {list(data)}')
    return f"configured={data['configured']}, key_set={data['settings'].get('api_key_set')}"


def _key_is_set(client):
    """是否已经保存过 API Key（保存后空 Key 会回退到它）。"""
    r = client.get('/api/settings')
    data = r.get_json() or {}
    return bool((data.get('settings') or {}).get('api_key_set'))


def _expect_400(client, method, path, body):
    r = client.open(path, method=method, json=body)
    if r.status_code != 400:
        raise AssertionError(f'期望 400，实际 {r.status_code}')
    data = r.get_json() or {}
    return data.get('message', '')[:40]


def _expect_gone(client, path):
    r = client.open(path, method='POST' if path.startswith('/api') else 'GET')
    if r.status_code not in (404, 405):
        raise AssertionError(f'仍然存在（HTTP {r.status_code}）')
    return f'{r.status_code} 已移除'


def _ai_state(app_module):
    clients = getattr(app_module, 'ai_clients', None)
    if clients is None:
        # ai_clients 定义在 ai_routes 里
        from modules.ai_chat import ai_routes
        clients = ai_routes.ai_clients
    state = {k: ('已配置' if v is not None else '未配置') for k, v in clients.items()}
    return json.dumps(state, ensure_ascii=False)


if __name__ == '__main__':
    sys.exit(main())

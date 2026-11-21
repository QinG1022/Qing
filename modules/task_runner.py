"""进程内任务执行器（替代 Celery + Redis）。

为什么换：
  单用户本地应用不需要分布式任务队列。原来要跑 Redis + Celery worker + Flask
  三个进程，Windows 上 Celery 还只能 --pool=solo（等于没有并发）。

设计：
  - ThreadPoolExecutor 在自己的进程里跑任务
  - 任务状态放在内存字典里（单进程单用户够用）
  - 对外暴露与 Celery 兼容的 .delay() / AsyncResult，调用点不用改

注意：OCR 主要耗时在 pytesseract（子进程，会释放 GIL），所以线程足够；
      将来如果有重 CPU 的 Python 任务，再换 ProcessPoolExecutor。
"""
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

LOG = logging.getLogger(__name__)

_LOCK = threading.RLock()
_JOBS = {}
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix='qing-task')


class Job(object):
    """一次任务执行的状态容器。任务函数把它当作 Celery 的 self 使用。"""

    def __init__(self, name):
        self.id = uuid.uuid4().hex
        self.name = name
        self.state = 'PENDING'
        self.result = None
        self.meta = {'progress': 0, 'message': '任务等待中...'}
        self.created_at = time.time()
        self.updated_at = time.time()

    def update_state(self, state=None, meta=None):
        """兼容 Celery 的 self.update_state(state=..., meta={...})。"""
        with _LOCK:
            if state:
                self.state = state
            if meta:
                self.meta.update(meta)
            self.updated_at = time.time()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state,
            'result': _safe_result(self.result),
            'meta': dict(self.meta),
        }


def _safe_result(result):
    """结果要能 jsonify：异常转成字符串。"""
    if isinstance(result, BaseException):
        return {'error': str(result)}
    return result


class TaskProxy(object):
    """像 Celery 任务一样用：proxy.delay(a, b) 立刻返回带 .id 的对象。"""

    def __init__(self, func, name):
        self.func = func
        self.name = name

    def delay(self, *args, **kwargs):
        job = Job(self.name)
        with _LOCK:
            _JOBS[job.id] = job
        _EXECUTOR.submit(self._run, job, args, kwargs)
        LOG.info("任务已入队: %s (%s)", self.name, job.id)
        return _Submitted(job.id)

    def _run(self, job, args, kwargs):
        with _LOCK:
            job.state = 'PROCESSING'
            job.meta['message'] = '处理中...'
            job.updated_at = time.time()
        try:
            # 任务函数签名是 func(self, *args, **kwargs)，self 就是 job
            result = self.func(job, *args, **kwargs)
            with _LOCK:
                job.result = result
                job.state = 'SUCCESS'
                job.meta.update({'progress': 100, 'message': '任务完成'})
                job.updated_at = time.time()
            LOG.info("任务完成: %s (%s)", self.name, job.id)
        except Exception as e:
            LOG.error("任务失败: %s (%s): %s", self.name, job.id, e, exc_info=True)
            with _LOCK:
                job.result = e
                job.state = 'FAILURE'
                job.meta.update({'message': '任务失败'})
                job.updated_at = time.time()


class _Submitted(object):
    """delay() 的返回值，只暴露 id（Celery 的 AsyncResult 也是这么用的）。"""

    def __init__(self, task_id):
        self.id = task_id


class AsyncResult(object):
    """兼容 celery.result.AsyncResult 的最小实现。"""

    def __init__(self, task_id, app=None):
        self.id = task_id
        self.app = app

    def _job(self):
        with _LOCK:
            return _JOBS.get(self.id)

    @property
    def state(self):
        job = self._job()
        if job is None:
            # 进程重启后旧任务已不存在，明确报失败，避免前端无限轮询
            return 'FAILURE'
        return job.state

    @property
    def result(self):
        job = self._job()
        if job is None:
            return Exception('任务不存在或服务已重启，请重新提交')
        return job.result

    @property
    def meta(self):
        job = self._job()
        return dict(job.meta) if job else {}

    def ready(self):
        return self.state in ('SUCCESS', 'FAILURE')


# app.py 里写的是 AsyncResult(task_id, app=celery)，保留一个占位对象
celery = None


def cleanup_finished(older_than_seconds=3600):
    """清理一小时前完成的任务，避免内存无限增长。"""
    deadline = time.time() - older_than_seconds
    with _LOCK:
        stale = [jid for jid, job in _JOBS.items()
                 if job.state in ('SUCCESS', 'FAILURE') and job.updated_at < deadline]
        for jid in stale:
            _JOBS.pop(jid, None)
    return len(stale)

"""
Celery配置文件
用途：配置Celery异步任务系统的各项参数
"""

# Redis 连接配置
broker_url = 'redis://localhost:6379/0'  # 消息代理
result_backend = 'redis://localhost:6379/0'  # 结果存储

# 序列化设置
task_serializer = 'json'  # 任务序列化格式
result_serializer = 'json'  # 结果序列化格式
accept_content = ['json']  # 允许的内容类型

# 时区设置
timezone = 'Asia/Shanghai'  # 使用中国时区
enable_utc = True  # 启用UTC时间

# 任务执行设置
task_track_started = True  # 跟踪任务开始状态
worker_max_tasks_per_child = 1000  # 子进程最大任务数
task_time_limit = 300  # 单个任务最大执行时间（秒）
worker_pool = 'solo'  # Windows兼容设置

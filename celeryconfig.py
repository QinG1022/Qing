"""
Celery配置文件
用途：配置Celery异步任务系统的各项参数
版本：1.2
最后更新：2024-02-28
描述：本配置文件定义了Celery任务队列的运行环境、性能参数和行为特性
"""

# Redis 连接配置
broker_url = 'redis://localhost:6379/0'  # 消息代理服务器URL，使用Redis数据库0
result_backend = 'redis://localhost:6379/0'  # 结果存储后端，与消息代理使用相同的Redis

# 序列化设置
task_serializer = 'json'  # 任务序列化格式，使用JSON格式序列化任务数据
result_serializer = 'json'  # 结果序列化格式，使用JSON格式序列化结果数据
accept_content = ['json']  # 允许的内容类型，只接受JSON格式的消息

# 时区设置
timezone = 'Asia/Shanghai'  # 使用中国标准时区
enable_utc = True  # 启用UTC时间，内部存储使用UTC，但显示时会根据timezone转换

# 任务执行设置
task_track_started = True  # 跟踪任务开始状态，可以获取任务的STARTED状态
worker_max_tasks_per_child = 1000  # 子进程最大任务数，处理1000个任务后自动重启，防止内存泄漏
task_time_limit = 300  # 单个任务最大执行时间（秒），超过300秒自动中断，防止任务卡死
worker_pool = 'solo'  # Windows兼容设置，在Windows环境下使用solo池，而不是默认的prefork

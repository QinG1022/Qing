"""
数据库模块测试
功能: 测试数据库模型和操作函数的正确性
版本: 1.0
最后更新: 2025-04-01
描述: 包含对数据库模型、关系和操作函数的单元测试
"""
import os
import sys
import pytest
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.database import db, User, History, ChatHistory, init_db
from modules.database import add_history_record, get_user_history, delete_history_record, clear_user_history
from modules.database import add_chat_message, get_user_chat_history, clear_user_chat_history

@pytest.fixture
def app_context():
    """
    创建应用上下文和测试数据库
    
    功能:
        提供一个配置为测试模式的Flask应用上下文，使用内存SQLite数据库
        
    返回:
        Flask应用上下文对象
    """
    from flask import Flask
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化数据库
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def test_user(app_context):
    """
    创建测试用户
    
    功能:
        在测试数据库中创建一个用户记录
        
    返回:
        User: 创建的用户对象
    """
    user = User(
        username='test_user',
        email='test@example.com',
        password='hashed_password',
        created_at=datetime.now()
    )
    db.session.add(user)
    db.session.commit()
    return user

def test_create_user(app_context):
    """
    测试用户创建
    
    测试目标:
        验证User模型能正确创建用户记录
        
    验证内容:
        - 用户被成功添加到数据库
        - 用户ID自动生成
        - 用户属性值正确
    """
    # 创建新用户
    user = User(
        username='new_user',
        email='new@example.com',
        password='password_hash',
        created_at=datetime.now()
    )
    db.session.add(user)
    db.session.commit()
    
    # 从数据库查询用户
    saved_user = User.query.filter_by(username='new_user').first()
    
    # 验证用户创建是否成功
    assert saved_user is not None
    assert saved_user.id is not None
    assert saved_user.username == 'new_user'
    assert saved_user.email == 'new@example.com'
    assert saved_user.password == 'password_hash'
    assert isinstance(saved_user.created_at, datetime)

def test_user_history_relationship(app_context, test_user):
    """
    测试用户与历史记录的关系
    
    测试目标:
        验证User模型和History模型之间的一对多关系
        
    验证内容:
        - 用户可以关联多条历史记录
        - 历史记录可以通过user_id找到所属用户
        - 删除用户时，关联的历史记录也被删除
    """
    # 创建历史记录
    history1 = History(
        id='hist_001',
        type='TEXT',
        content='测试内容1',
        source='测试来源1',
        timestamp=datetime.now(),
        user_id=test_user.id
    )
    
    history2 = History(
        id='hist_002',
        type='OCR',
        content='测试内容2',
        source='测试来源2',
        timestamp=datetime.now(),
        user_id=test_user.id
    )
    
    db.session.add_all([history1, history2])
    db.session.commit()
    
    # 测试用户的历史记录关系
    user = User.query.get(test_user.id)
    assert len(user.histories) == 2
    assert user.histories[0].id in ['hist_001', 'hist_002']
    assert user.histories[1].id in ['hist_001', 'hist_002']
    
    # 测试通过历史记录找到用户
    hist = History.query.get('hist_001')
    assert hist.user.id == test_user.id
    assert hist.user.username == 'test_user'
    
    # 测试级联删除
    db.session.delete(user)
    db.session.commit()
    
    # 验证历史记录也被删除
    assert History.query.get('hist_001') is None
    assert History.query.get('hist_002') is None

def test_add_history_record(app_context, test_user):
    """
    测试添加历史记录函数
    
    测试目标:
        验证add_history_record函数能正确添加历史记录
        
    验证内容:
        - 历史记录成功添加到数据库
        - 历史记录与用户正确关联
    """
    # 调用添加历史记录函数
    success = add_history_record(
        record_id='test_record',
        record_type='TEXT',
        content='测试添加历史记录',
        source='测试来源',
        user_id=test_user.id
    )
    
    # 验证添加结果
    assert success is True
    
    # 从数据库查询历史记录
    record = History.query.get('test_record')
    assert record is not None
    assert record.type == 'TEXT'
    assert record.content == '测试添加历史记录'
    assert record.user_id == test_user.id

def test_get_user_history(app_context, test_user):
    """
    测试获取用户历史记录函数
    
    测试目标:
        验证get_user_history函数能正确获取用户的历史记录
        
    验证内容:
        - 能获取正确数量的历史记录
        - 历史记录按时间戳倒序排列
        - 能限制返回记录数量
    """
    # 添加多条历史记录，时间递增
    for i in range(5):
        history = History(
            id=f'hist_{i}',
            type='TEXT',
            content=f'测试内容{i}',
            source=f'测试来源{i}',
            timestamp=datetime.now(),
            user_id=test_user.id
        )
        db.session.add(history)
        # 确保时间戳有差异
        import time
        time.sleep(0.01)
    
    db.session.commit()
    
    # 测试获取全部历史记录
    all_records = get_user_history(test_user.id)
    assert len(all_records) == 5
    
    # 测试限制记录数量
    limited_records = get_user_history(test_user.id, limit=3)
    assert len(limited_records) == 3
    
    # 测试按时间戳倒序排列（最新的在前面）
    assert limited_records[0]['id'] == 'hist_4'
    assert limited_records[1]['id'] == 'hist_3'
    assert limited_records[2]['id'] == 'hist_2'

def test_delete_history_record(app_context, test_user):
    """
    测试删除历史记录函数
    
    测试目标:
        验证delete_history_record函数能正确删除单条历史记录
        
    验证内容:
        - 成功删除指定ID的历史记录
        - 其他历史记录不受影响
        - 删除不存在的记录返回False
    """
    # 添加测试记录
    history1 = History(
        id='to_delete',
        type='TEXT',
        content='将被删除的记录',
        source='测试来源',
        timestamp=datetime.now(),
        user_id=test_user.id
    )
    
    history2 = History(
        id='to_keep',
        type='TEXT',
        content='将被保留的记录',
        source='测试来源',
        timestamp=datetime.now(),
        user_id=test_user.id
    )
    
    db.session.add_all([history1, history2])
    db.session.commit()
    
    # 测试删除记录
    result = delete_history_record('to_delete')
    assert result is True
    
    # 验证删除结果
    assert History.query.get('to_delete') is None
    assert History.query.get('to_keep') is not None
    
    # 测试删除不存在的记录
    result = delete_history_record('non_existent')
    assert result is False

def test_clear_user_history(app_context, test_user):
    """
    测试清空用户历史记录函数
    
    测试目标:
        验证clear_user_history函数能正确清空指定用户的所有历史记录
        
    验证内容:
        - 用户的所有历史记录被删除
        - 其他用户的历史记录不受影响
    """
    # 创建另一个测试用户
    other_user = User(
        username='other_user',
        email='other@example.com',
        password='hashed_password',
        created_at=datetime.now()
    )
    db.session.add(other_user)
    db.session.commit()
    
    # 为两个用户各添加历史记录
    for i in range(3):
        # 第一个用户的历史记录
        history1 = History(
            id=f'user1_hist_{i}',
            type='TEXT',
            content=f'用户1的记录{i}',
            source='测试来源',
            timestamp=datetime.now(),
            user_id=test_user.id
        )
        
        # 第二个用户的历史记录
        history2 = History(
            id=f'user2_hist_{i}',
            type='TEXT',
            content=f'用户2的记录{i}',
            source='测试来源',
            timestamp=datetime.now(),
            user_id=other_user.id
        )
        
        db.session.add_all([history1, history2])
    
    db.session.commit()
    
    # 清空第一个用户的历史记录
    result = clear_user_history(test_user.id)
    assert result is True
    
    # 验证第一个用户的历史记录已被清空
    user1_records = History.query.filter_by(user_id=test_user.id).all()
    assert len(user1_records) == 0
    
    # 验证第二个用户的历史记录不受影响
    user2_records = History.query.filter_by(user_id=other_user.id).all()
    assert len(user2_records) == 3

def test_chat_history_functions(app_context, test_user):
    """
    测试聊天历史记录功能
    
    测试目标:
        验证聊天历史记录相关函数的正确性
        
    验证内容:
        - 添加聊天消息
        - 获取聊天历史
        - 按对话ID筛选
        - 清空聊天历史
    """
    # 测试添加聊天消息
    conv_id = 'test_conversation'
    
    # 添加两条用户消息和两条AI回复
    add_chat_message('user', '你好', 'deepseek', conv_id, test_user.id)
    add_chat_message('assistant', '你好，有什么可以帮助你的？', 'deepseek', conv_id, test_user.id)
    add_chat_message('user', '介绍一下Python', 'deepseek', conv_id, test_user.id)
    add_chat_message('assistant', 'Python是一种高级编程语言...', 'deepseek', conv_id, test_user.id)
    
    # 测试获取聊天历史
    messages = get_user_chat_history(test_user.id)
    assert len(messages) == 4
    
    # 验证聊天消息内容
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == '你好'
    assert messages[1]['role'] == 'assistant'
    assert messages[1]['content'] == '你好，有什么可以帮助你的？'
    
    # 添加另一个对话的消息
    another_conv_id = 'another_conversation'
    add_chat_message('user', '另一个对话', 'qwen', another_conv_id, test_user.id)
    
    # 测试按对话ID筛选
    filtered_messages = get_user_chat_history(test_user.id, conversation_id=conv_id)
    assert len(filtered_messages) == 4
    
    filtered_messages = get_user_chat_history(test_user.id, conversation_id=another_conv_id)
    assert len(filtered_messages) == 1
    assert filtered_messages[0]['content'] == '另一个对话'
    
    # 测试清空特定对话的历史
    result = clear_user_chat_history(test_user.id, conversation_id=conv_id)
    assert result is True
    
    # 验证特定对话的消息已被清空
    messages = get_user_chat_history(test_user.id, conversation_id=conv_id)
    assert len(messages) == 0
    
    # 验证其他对话的消息不受影响
    messages = get_user_chat_history(test_user.id, conversation_id=another_conv_id)
    assert len(messages) == 1
    
    # 测试清空所有聊天历史
    result = clear_user_chat_history(test_user.id)
    assert result is True
    
    # 验证所有聊天消息已被清空
    messages = get_user_chat_history(test_user.id)
    assert len(messages) == 0
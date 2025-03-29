"""
数据库管理模块
功能: 提供SQLite数据库连接和模型定义
版本: 1.0
最后更新: 2025-03-27
"""

import os
import logging
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from pathlib import Path

# 配置日志系统
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建SQLAlchemy实例
db = SQLAlchemy()

class User(db.Model, UserMixin):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # 建立与历史记录的一对多关系
    histories = db.relationship('History', backref='user', lazy=True, cascade="all, delete-orphan")
    # 建立与聊天历史的一对多关系
    chat_histories = db.relationship('ChatHistory', backref='user', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.username}>"

class History(db.Model):
    """历史记录模型"""
    __tablename__ = 'histories'
    
    id = db.Column(db.String(50), primary_key=True)
    type = db.Column(db.String(10), nullable=False)  # 类型：TEXT, PDF, IMAGE等
    content = db.Column(db.Text, nullable=True)      # 文本内容
    source = db.Column(db.String(255), nullable=True) # 来源描述
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    # 外键关联到用户
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def __repr__(self):
        return f"<History {self.id} ({self.type})>"
    
    def to_dict(self):
        """将历史记录转换为字典格式用于JSON响应"""
        return {
            'id': self.id,
            'type': self.type,
            'content': self.content,
            'source': self.source,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': self.user_id
        }

class ChatHistory(db.Model):
    """AI对话历史记录模型"""
    __tablename__ = 'chat_histories'
    
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10), nullable=False)  # 角色：user或assistant
    content = db.Column(db.Text, nullable=False)     # 消息内容
    timestamp = db.Column(db.DateTime, default=datetime.now)
    model = db.Column(db.String(20), nullable=True)  # 使用的AI模型
    conversation_id = db.Column(db.String(50), nullable=False)  # 对话ID，用于分组同一次对话的消息
    
    # 外键关联到用户
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __repr__(self):
        return f"<ChatHistory {self.id} ({self.role})>"
    
    def to_dict(self):
        """将聊天记录转换为字典格式用于JSON响应"""
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'model': self.model,
            'conversation_id': self.conversation_id,
            'user_id': self.user_id
        }

def init_db(app):
    """初始化数据库"""
    try:
        # 使用绝对路径
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        data_dir = os.path.join(base_dir, 'data')
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        # 数据库文件完整路径
        db_file = os.path.join(data_dir, 'app.db')
        
        # 使用绝对路径配置数据库
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        logger.info(f"数据库路径: {db_file}")
        
        # 初始化数据库与应用
        db.init_app(app)
        
        # 在应用上下文中创建表
        with app.app_context():
            db.create_all()
            logger.info("数据库初始化成功")
        return True
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        return False


def get_user_history(user_id, limit=10):
    """获取指定用户的历史记录"""
    try:
        histories = History.query.filter_by(user_id=user_id).order_by(History.timestamp.desc()).limit(limit).all()
        return [history.to_dict() for history in histories]
    except Exception as e:
        logger.error(f"获取用户历史记录失败: {str(e)}")
        return []

def add_history_record(record_id, record_type, content, source, user_id=None):
    """添加新的历史记录"""
    try:
        new_history = History(
            id=record_id,
            type=record_type,
            content=content,
            source=source,
            user_id=user_id
        )
        db.session.add(new_history)
        db.session.commit()
        logger.info(f"添加历史记录成功，ID: {record_id}, 类型: {record_type}")
        return True
    except Exception as e:
        logger.error(f"添加历史记录失败: {str(e)}")
        db.session.rollback()
        return False

def delete_history_record(record_id):
    """删除指定的历史记录"""
    try:
        history = History.query.get(record_id)
        if history:
            db.session.delete(history)
            db.session.commit()
            logger.info(f"删除历史记录成功，ID: {record_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"删除历史记录失败: {str(e)}")
        db.session.rollback()
        return False

def clear_user_history(user_id):
    """清空用户的所有历史记录"""
    try:
        History.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        logger.info(f"清空用户历史记录成功，用户ID: {user_id}")
        return True
    except Exception as e:
        logger.error(f"清空用户历史记录失败: {str(e)}")
        db.session.rollback()
        return False

# 添加聊天历史相关函数
def get_user_chat_history(user_id, conversation_id=None, limit=100):
    """获取指定用户的对话历史记录"""
    try:
        query = ChatHistory.query.filter_by(user_id=user_id)
        if conversation_id:
            query = query.filter_by(conversation_id=conversation_id)
        
        chat_histories = query.order_by(ChatHistory.timestamp.asc()).limit(limit).all()
        return [chat.to_dict() for chat in chat_histories]
    except Exception as e:
        logger.error(f"获取用户对话历史记录失败: {str(e)}")
        return []

def add_chat_message(role, content, model, conversation_id, user_id):
    """添加新的对话消息记录"""
    try:
        new_chat = ChatHistory(
            role=role,
            content=content,
            model=model,
            conversation_id=conversation_id,
            user_id=user_id
        )
        db.session.add(new_chat)
        db.session.commit()
        logger.info(f"添加对话消息成功，用户ID: {user_id}, 角色: {role}")
        return True
    except Exception as e:
        logger.error(f"添加对话消息失败: {str(e)}")
        db.session.rollback()
        return False

def clear_user_chat_history(user_id, conversation_id=None):
    """清空用户的对话历史记录"""
    try:
        query = ChatHistory.query.filter_by(user_id=user_id)
        if conversation_id:
            query = query.filter_by(conversation_id=conversation_id)
        
        query.delete()
        db.session.commit()
        logger.info(f"清空用户对话历史记录成功，用户ID: {user_id}")
        return True
    except Exception as e:
        logger.error(f"清空用户对话历史记录失败: {str(e)}")
        db.session.rollback()
        return False 
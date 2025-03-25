"""
用户管理模块
功能: 处理用户注册、登录和管理
版本: 1.0
最后更新: 2024-06-10
"""
import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime

# 配置日志系统
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserManager:
    """用户管理类，处理用户注册和登录"""
    
    # 用户数据文件路径
    USER_DATA_DIR = Path("data")
    USER_DATA_FILE = USER_DATA_DIR / "users.json"
    
    @classmethod
    def initialize(cls):
        """初始化用户数据存储"""
        try:
            # 确保数据目录存在
            cls.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            # 创建用户数据文件（如果不存在）
            if not cls.USER_DATA_FILE.exists():
                with open(cls.USER_DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump({"users": []}, f)
                logger.info(f"用户数据文件已创建: {cls.USER_DATA_FILE}")
                
            return True
        except Exception as e:
            logger.error(f"初始化用户数据存储失败: {str(e)}")
            return False
    
    @classmethod
    def hash_password(cls, password):
        """使用SHA-256哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @classmethod
    def username_exists(cls, username):
        """检查用户名是否已存在"""
        users = cls.load_users()
        return any(user["username"].lower() == username.lower() for user in users)
    
    @classmethod
    def email_exists(cls, email):
        """检查邮箱是否已存在"""
        users = cls.load_users()
        return any(user["email"].lower() == email.lower() for user in users)
    
    @classmethod
    def load_users(cls):
        """从文件加载用户数据"""
        try:
            with open(cls.USER_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("users", [])
        except Exception as e:
            logger.error(f"加载用户数据失败: {str(e)}")
            return []
    
    @classmethod
    def save_users(cls, users):
        """保存用户数据到文件"""
        try:
            with open(cls.USER_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump({"users": users}, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存用户数据失败: {str(e)}")
            return False
    
    @classmethod
    def register_user(cls, username, email, password):
        """注册新用户"""
        try:
            # 验证用户名和邮箱是否已存在
            if cls.username_exists(username):
                return {"success": False, "message": "用户名已存在"}
            
            if cls.email_exists(email):
                return {"success": False, "message": "邮箱已被使用"}
            
            # 创建新用户
            users = cls.load_users()
            new_user = {
                "id": len(users) + 1,
                "username": username,
                "email": email,
                "password": cls.hash_password(password),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_login": None
            }
            
            # 添加到用户列表并保存
            users.append(new_user)
            if cls.save_users(users):
                logger.info(f"用户注册成功: {username}")
                return {"success": True, "message": "注册成功"}
            else:
                return {"success": False, "message": "系统错误，请稍后再试"}
        
        except Exception as e:
            logger.error(f"用户注册失败: {str(e)}")
            return {"success": False, "message": f"注册失败: {str(e)}"}
    
    @classmethod
    def authenticate_user(cls, username, password):
        """验证用户登录"""
        try:
            users = cls.load_users()
            
            # 查找匹配的用户
            for user in users:
                if user["username"] == username and user["password"] == cls.hash_password(password):
                    # 更新最后登录时间
                    user["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cls.save_users(users)
                    
                    return {
                        "success": True, 
                        "message": "登录成功",
                        "user": {
                            "id": user["id"],
                            "username": user["username"],
                            "email": user["email"]
                        }
                    }
            
            return {"success": False, "message": "用户名或密码错误"}
            
        except Exception as e:
            logger.error(f"用户验证失败: {str(e)}")
            return {"success": False, "message": f"登录失败: {str(e)}"}
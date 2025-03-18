import pytest
from unittest.mock import Mock, patch
from flask import Flask
from modules.ai_chat.ai_routes import ai_bp
from modules.ai_chat.deepseek_client import DeepSeekClient
import json

# 创建测试应用
app = Flask(__name__)
app.register_blueprint(ai_bp)
app.config['TESTING'] = True

@pytest.fixture
def client():
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture
def mock_deepseek():
    """模拟 DeepSeek 客户端"""
    with patch('modules.ai_chat.ai_routes.client') as mock:
        # 设置基本的mock属性
        mock.messages = [{"role": "system", "content": "You are a helpful assistant."}]
        mock.add_message = Mock()
        mock.generate_response = Mock()
        mock.format_response = Mock(return_value="这是一个测试回复")
        yield mock

@pytest.fixture
def mock_local_model():
    """模拟本地模型客户端"""
    with patch('modules.ai_chat.ai_routes.local_client') as mock:
        mock.messages = [{"role": "system", "content": "You are a helpful assistant."}]
        mock.add_message = Mock()
        mock.generate_response = Mock()
        mock.format_response = Mock(return_value="这是本地模型测试回复")
        yield mock

class TestChatEndpoint:
    """聊天端点测试类"""
    
    def test_chat_endpoint_success(self, client, mock_deepseek):
        """测试正常聊天请求"""
        # 模拟DeepSeek响应
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="这是一个测试回复"))]
        mock_deepseek.generate_response.return_value = mock_response
        
        # 发送测试请求
        response = client.post('/chat', 
                             json={'message': '你好', 'stream': False})
        
        # 验证响应
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data
        assert data['response'] == "这是一个测试回复"
        mock_deepseek.add_message.assert_called_once()
        mock_deepseek.generate_response.assert_called_once()

    def test_chat_endpoint_empty_message(self, client):
        """测试空消息请求"""
        response = client.post('/chat', 
                             json={'message': '', 'stream': False})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == "消息不能为空"

    def test_chat_endpoint_invalid_json(self, client):
        """测试无效的JSON数据"""
        response = client.post('/chat', 
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == "无效的请求数据"

    def test_chat_endpoint_stream_mode(self, client, mock_deepseek):
        """测试流式响应模式"""
        # 模拟流式响应
        mock_stream = [
            Mock(choices=[Mock(delta=Mock(content="这是"))]),
            Mock(choices=[Mock(delta=Mock(content="测试"))]),
            Mock(choices=[Mock(delta=Mock(content="回复"))])
        ]
        mock_deepseek.generate_response.return_value = mock_stream
        
        # 发送流式请求
        response = client.post('/chat', 
                             json={'message': '你好', 'stream': True})
        
        assert response.status_code == 200
        assert response.mimetype == 'text/event-stream'

    def test_chat_endpoint_api_error(self, client, mock_deepseek):
        """测试API错误处理"""
        # 模拟API错误
        mock_deepseek.generate_response.return_value = {"error": "API密钥无效"}
        
        response = client.post('/chat', 
                             json={'message': '你好', 'stream': False})
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == "API密钥无效"

class TestLocalModelEndpoint:
    """本地模型端点测试类"""
    
    def test_local_chat_success(self, client, mock_local_model):
        """测试本地模型正常聊天"""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="这是本地模型测试回复"))]
        mock_local_model.generate_response.return_value = mock_response
        
        response = client.post('/local_chat', 
                             json={'message': '你好', 'stream': False})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data
        assert data['response'] == "这是本地模型测试回复"
        mock_local_model.add_message.assert_called_once()
        mock_local_model.generate_response.assert_called_once()

    def test_local_chat_model_not_loaded(self, client):
        """测试本地模型未加载情况"""
        with patch('modules.ai_chat.ai_routes.local_client', None):
            response = client.post('/local_chat', 
                                 json={'message': '你好', 'stream': False})
            
            assert response.status_code == 503
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == "本地模型未加载"

class TestModelManagement:
    """模型管理测试类"""
    
    def test_switch_model_success(self, client):
        """测试切换模型成功"""
        response = client.post('/switch_model', 
                             json={'model_type': 'deepseek'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == "success"
        assert data['message'] == "模型切换成功"

    def test_switch_model_invalid_type(self, client):
        """测试切换无效的模型类型"""
        response = client.post('/switch_model', 
                             json={'model_type': 'invalid_model'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == "不支持的模型类型"

    def test_reset_conversation(self, client, mock_deepseek):
        """测试重置对话历史"""
        response = client.post('/reset')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == "success"
        assert data['message'] == "对话历史已重置"
        
        # 验证消息历史是否被重置
        assert len(mock_deepseek.messages) == 1
        assert mock_deepseek.messages[0]['role'] == "system"

class TestErrorHandling:
    """错误处理测试类"""
    
    def test_handle_connection_error(self, client, mock_deepseek):
        """测试连接错误处理"""
        mock_deepseek.generate_response.side_effect = ConnectionError("连接失败")
        
        response = client.post('/chat', 
                             json={'message': '你好', 'stream': False})
        
        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == "服务暂时不可用，请稍后重试"

    def test_handle_timeout_error(self, client, mock_deepseek):
        """测试超时错误处理"""
        mock_deepseek.generate_response.side_effect = TimeoutError("请求超时")
        
        response = client.post('/chat', 
                             json={'message': '你好', 'stream': False})
        
        assert response.status_code == 504
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == "请求超时，请重试" 
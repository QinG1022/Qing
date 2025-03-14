import pytest
from unittest.mock import Mock, patch
from flask import Flask
from modules.ai_routes import ai_bp
from modules.deepseek_client import DeepSeekClient
import json

# 创建测试应用
app = Flask(__name__)
app.register_blueprint(ai_bp)
app.config['TESTING'] = True

@pytest.fixture
def client():
    return app.test_client()

@pytest.fixture
def mock_deepseek():
    with patch('modules.ai_routes.client') as mock:
        # 设置基本的mock属性
        mock.messages = [{"role": "system", "content": "You are a helpful assistant."}]
        mock.add_message = Mock()
        mock.generate_response = Mock()
        mock.format_response = Mock(return_value="这是一个测试回复")
        yield mock

def test_chat_endpoint_success(client, mock_deepseek):
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

def test_chat_endpoint_empty_message(client):
    # 测试空消息
    response = client.post('/chat', 
                         json={'message': '', 'stream': False})
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == "消息不能为空"

def test_chat_endpoint_invalid_json(client):
    # 测试无效的JSON数据
    response = client.post('/chat', 
                         data='invalid json',
                         content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == "无效的请求数据"

def test_chat_endpoint_stream_mode(client, mock_deepseek):
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

def test_reset_conversation(client, mock_deepseek):
    # 测试重置对话
    response = client.post('/reset')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == "success"
    assert data['message'] == "对话历史已重置"
    
    # 验证消息历史是否被重置
    assert len(mock_deepseek.messages) == 1
    assert mock_deepseek.messages[0]['role'] == "system"

def test_chat_endpoint_api_error(client, mock_deepseek):
    # 模拟API错误
    mock_deepseek.generate_response.return_value = {"error": "API密钥无效"}
    
    response = client.post('/chat', 
                         json={'message': '你好', 'stream': False})
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == "API密钥无效" 
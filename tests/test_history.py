import pytest
import os
import sys
import json
from pathlib import Path
import logging
from flask import session
import shutil

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, history_records

@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    app.config['PDF_FOLDER'] = Path("test_pdfs")
    app.config['UPLOAD_FOLDER'] = Path("test_uploads")
    
    # 确保测试目录存在
    for folder in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER']]:
        folder.mkdir(parents=True, exist_ok=True)
    
    # 清空历史记录，确保测试环境干净
    history_records.clear()
    
    with app.test_client() as client:
        yield client
        
        # 清理测试文件
        for folder in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER']]:
            if folder.exists():
                for file in folder.glob('*'):
                    if file.is_file():
                        file.unlink()

def test_empty_history(client):
    """测试空历史记录"""
    # 确保历史记录为空
    history_records.clear()
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证结果
    assert response.status_code == 200
    assert data['status'] == 'success'
    assert data['count'] == 0
    assert len(data['history']) == 0
    assert data['max_count'] == app.config['MAX_HISTORY_ITEMS']

def test_add_history_record(client):
    """测试添加历史记录项"""
    # 清空历史记录
    history_records.clear()
    
    # 添加测试记录
    test_record = {
        'id': 'test_id_1',
        'type': 'TEXT',
        'content': '测试内容',
        'timestamp': '2023-03-08 10:00:00',
        'source': '测试来源'
    }
    history_records.appendleft(test_record)
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证结果
    assert response.status_code == 200
    assert data['status'] == 'success'
    assert data['count'] == 1
    assert len(data['history']) == 1
    assert data['history'][0]['id'] == 'test_id_1'
    assert data['history'][0]['content'] == '测试内容'

def test_delete_history_record(client):
    """测试删除单条历史记录"""
    # 清空历史记录
    history_records.clear()
    
    # 添加测试记录
    test_records = [
        {
            'id': 'test_id_1',
            'type': 'TEXT',
            'content': '测试内容1',
            'timestamp': '2023-03-08 10:00:00',
            'source': '测试来源1'
        },
        {
            'id': 'test_id_2',
            'type': 'OCR',
            'content': '测试内容2',
            'timestamp': '2023-03-08 11:00:00',
            'source': '测试来源2'
        }
    ]
    
    for record in test_records:
        history_records.appendleft(record)
    
    # 删除第一条记录
    response = client.delete('/history/test_id_1')
    data = json.loads(response.data)
    
    # 验证删除成功
    assert response.status_code == 200
    assert data['status'] == 'success'
    assert data['count'] == 1
    
    # 获取历史记录再次验证
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 确认只剩下一条记录，且是test_id_2
    assert data['count'] == 1
    assert data['history'][0]['id'] == 'test_id_2'

def test_delete_nonexistent_record(client):
    """测试删除不存在的历史记录"""
    # 清空历史记录
    history_records.clear()
    
    # 添加一条测试记录
    test_record = {
        'id': 'test_id_1',
        'type': 'TEXT',
        'content': '测试内容',
        'timestamp': '2023-03-08 10:00:00',
        'source': '测试来源'
    }
    history_records.appendleft(test_record)
    
    # 尝试删除不存在的记录
    response = client.delete('/history/nonexistent_id')
    data = json.loads(response.data)
    
    # 验证返回404错误
    assert response.status_code == 404
    assert 'error' in data
    
    # 确认历史记录没有变化
    response = client.get('/history')
    data = json.loads(response.data)
    assert data['count'] == 1
    assert data['history'][0]['id'] == 'test_id_1'

def test_clear_history(client):
    """测试清空所有历史记录"""
    # 清空历史记录
    history_records.clear()
    
    # 添加多条测试记录
    for i in range(3):
        test_record = {
            'id': f'test_id_{i}',
            'type': 'TEXT',
            'content': f'测试内容{i}',
            'timestamp': f'2023-03-08 {10+i}:00:00',
            'source': f'测试来源{i}'
        }
        history_records.appendleft(test_record)
    
    # 验证有3条记录
    response = client.get('/history')
    data = json.loads(response.data)
    assert data['count'] == 3
    
    # 清空所有记录
    response = client.delete('/history')
    data = json.loads(response.data)
    
    # 验证清空成功
    assert response.status_code == 200
    assert data['status'] == 'success'
    
    # 获取历史记录再次验证
    response = client.get('/history')
    data = json.loads(response.data)
    assert data['count'] == 0
    assert len(data['history']) == 0

def test_history_limit(client):
    """测试历史记录数量限制"""
    # 清空历史记录
    history_records.clear()
    
    # 添加超过限制数量的记录
    max_items = app.config['MAX_HISTORY_ITEMS']
    for i in range(max_items + 2):  # 添加比限制多2条的记录
        test_record = {
            'id': f'test_id_{i}',
            'type': 'TEXT',
            'content': f'测试内容{i}',
            'timestamp': f'2023-03-08 {10+i}:00:00',
            'source': f'测试来源{i}'
        }
        history_records.appendleft(test_record)
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证记录数量不超过限制
    assert data['count'] == max_items
    assert len(data['history']) == max_items
    
    # 验证最新的记录在前面（最后添加的在最前面）
    assert data['history'][0]['id'] == f'test_id_{max_items + 1}'
    assert data['history'][1]['id'] == f'test_id_{max_items}'

def test_history_record_format(client):
    """测试历史记录格式正确性"""
    # 清空历史记录
    history_records.clear()
    
    # 添加不同类型的测试记录
    test_records = [
        {
            'id': 'text_123',
            'type': 'TEXT',
            'content': '用户输入的文本内容',
            'timestamp': '2023-03-08 10:00:00',
            'source': '用户输入：测试文本'
        },
        {
            'id': 'ocr_456',
            'type': 'OCR',
            'content': 'OCR识别的文本内容',
            'timestamp': '2023-03-08 11:00:00',
            'source': '图片识别'
        },
        {
            'id': 'pdf_789',
            'type': 'PDF',
            'content': 'PDF提取的文本内容',
            'timestamp': '2023-03-08 12:00:00',
            'source': 'PDF提取：测试.pdf'
        }
    ]
    
    for record in test_records:
        history_records.appendleft(record)
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证各种类型的记录格式正确
    assert data['count'] == 3
    
    # 检查TEXT类型记录
    text_record = next(r for r in data['history'] if r['type'] == 'TEXT')
    assert 'id' in text_record
    assert 'content' in text_record
    assert 'timestamp' in text_record
    assert 'source' in text_record
    assert text_record['type'] == 'TEXT'
    
    # 检查OCR类型记录
    ocr_record = next(r for r in data['history'] if r['type'] == 'OCR')
    assert ocr_record['type'] == 'OCR'
    assert '图片识别' in ocr_record['source']
    
    # 检查PDF类型记录
    pdf_record = next(r for r in data['history'] if r['type'] == 'PDF')
    assert pdf_record['type'] == 'PDF'
    assert 'PDF提取' in pdf_record['source'] 
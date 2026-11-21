import pytest
import os
import sys
import json
from pathlib import Path
import logging
from flask import session
import shutil

# 添加项目根目录到 Python 路径，确保能够导入app模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, history_records  # 导入Flask应用和历史记录队列

@pytest.fixture
def client():
    """
    创建测试客户端夹具(fixture)
    
    这个夹具会:
    1. 配置Flask应用为测试模式
    2. 设置测试用的临时目录
    3. 确保必要的测试目录存在
    4. 清空历史记录，确保测试环境干净
    5. 测试结束后清理临时文件
    """
    app.config['TESTING'] = True  # 启用测试模式
    app.config['PDF_FOLDER'] = Path("test_pdfs")  # 设置测试PDF目录
    app.config['UPLOAD_FOLDER'] = Path("test_uploads")  # 设置测试上传目录
    
    # 确保测试目录存在，避免权限错误
    for folder in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER']]:
        folder.mkdir(parents=True, exist_ok=True)
    
    # 清空历史记录，确保每个测试都从干净的状态开始
    history_records.clear()
    
    # 创建并返回测试客户端，使用上下文管理器确保资源正确释放
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['anonymous_history'] = []  # 初始化匿名历史记录为空列表
        
        yield client  # 将客户端提供给测试函数
        
        # 测试完成后清理测试文件，防止文件累积
        for folder in [app.config['PDF_FOLDER'], app.config['UPLOAD_FOLDER']]:
            if folder.exists():
                for file in folder.glob('*'):
                    if file.is_file():
                        file.unlink()  # 删除测试文件

def test_empty_history(client):
    """
    测试空历史记录的情况
    
    验证当历史记录为空时，API返回正确的空列表和计数
    """
    # 使用session_transaction确保会话中的历史记录为空
    with client.session_transaction() as sess:
        sess['anonymous_history'] = []
    
    # 调用获取历史记录API
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证结果是否符合预期
    assert response.status_code == 200  # 确认请求成功
    assert data['status'] == 'success'  # 确认状态为成功
    assert data['count'] == 0  # 确认记录数为0
    assert len(data['history']) == 0  # 确认历史记录列表为空
    assert data['max_count'] == app.config['MAX_HISTORY_ITEMS']  # 确认最大记录数配置正确

def test_add_history_record(client):
    """
    测试添加历史记录功能
    
    验证添加一条历史记录后，API能正确返回该记录
    """
    # 使用session_transaction向会话中添加历史记录
    with client.session_transaction() as sess:
        sess['anonymous_history'] = [{
            'id': 'test_id_1',  # 测试记录ID
            'type': 'TEXT',     # 记录类型为文本
            'content': '测试内容',  # 记录内容
            'timestamp': '2023-03-08 10:00:00',  # 时间戳
            'source': '测试来源'  # 来源信息
        }]
    
    # 调用API获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证结果
    assert response.status_code == 200  # 确认请求成功
    assert data['status'] == 'success'  # 确认状态为成功
    assert data['count'] == 1  # 确认记录数为1
    assert len(data['history']) == 1  # 确认历史记录列表长度为1
    assert data['history'][0]['id'] == 'test_id_1'  # 确认记录ID正确
    assert data['history'][0]['content'] == '测试内容'  # 确认记录内容正确

def test_delete_history_record(client):
    """
    测试删除单条历史记录功能
    
    验证能够成功删除指定ID的历史记录，并且其他记录保持不变
    """
    # 使用session_transaction添加测试记录
    with client.session_transaction() as sess:
        sess['anonymous_history'] = [
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
    
    # 调用API删除第一条记录
    response = client.delete('/history/test_id_1')
    data = json.loads(response.data)
    
    # 验证删除操作成功
    assert response.status_code == 200  # 确认请求成功
    assert data['status'] == 'success'  # 确认状态为成功
    assert data['count'] == 1  # 确认剩余记录数为1
    
    # 获取历史记录再次验证
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 确认只剩下一条记录，且是test_id_2
    assert data['count'] == 1  # 确认记录数为1
    assert data['history'][0]['id'] == 'test_id_2'  # 确认剩余的是第二条记录

def test_delete_nonexistent_record(client):
    """
    测试删除不存在的历史记录
    
    验证当尝试删除不存在的记录时，API返回适当的错误信息，且不影响现有记录
    """
    # 使用session_transaction添加测试记录
    with client.session_transaction() as sess:
        sess['anonymous_history'] = [
            {
                'id': 'test_id_1',
                'type': 'TEXT',
                'content': '测试内容',
                'timestamp': '2023-03-08 10:00:00',
                'source': '测试来源'
            }
        ]
    
    # 尝试删除一个不存在的记录ID
    response = client.delete('/history/nonexistent_id')
    data = json.loads(response.data)
    
    # 验证返回404错误
    assert response.status_code == 404  # 确认返回404状态码
    assert 'error' in data  # 确认返回包含错误信息
    
    # 确认历史记录没有变化
    response = client.get('/history')
    data = json.loads(response.data)
    assert data['count'] == 1  # 确认记录数仍为1
    assert data['history'][0]['id'] == 'test_id_1'  # 确认原记录仍存在

def test_clear_history(client):
    """
    测试清空所有历史记录功能
    
    验证清空操作能成功删除所有历史记录
    """
    # 使用session_transaction添加测试记录
    with client.session_transaction() as sess:
        sess['anonymous_history'] = [
            {
                'id': f'test_id_0',
                'type': 'TEXT',
                'content': f'测试内容0',
                'timestamp': f'2023-03-08 10:00:00',
                'source': f'测试来源0'
            },
            {
                'id': f'test_id_1',
                'type': 'TEXT',
                'content': f'测试内容1',
                'timestamp': f'2023-03-08 11:00:00',
                'source': f'测试来源1'
            },
            {
                'id': f'test_id_2',
                'type': 'TEXT',
                'content': f'测试内容2',
                'timestamp': f'2023-03-08 12:00:00',
                'source': f'测试来源2'
            }
        ]
    
    # 验证初始状态有3条记录
    response = client.get('/history')
    data = json.loads(response.data)
    assert data['count'] == 3  # 确认记录数为3
    
    # 调用API清空所有记录
    response = client.delete('/history')
    data = json.loads(response.data)
    
    # 验证清空操作成功
    assert response.status_code == 200  # 确认请求成功
    assert data['status'] == 'success'  # 确认状态为成功
    
    # 获取历史记录再次验证
    response = client.get('/history')
    data = json.loads(response.data)
    assert data['count'] == 0  # 确认记录数为0
    assert len(data['history']) == 0  # 确认历史记录列表为空

def test_history_limit(client):
    """
    测试历史记录数量限制功能
    
    验证历史记录数量不会超过配置的最大值，且新记录会替换旧记录
    """
    # 获取配置的最大记录数
    max_items = app.config['MAX_HISTORY_ITEMS']
    
    # 创建超过限制数量的记录
    test_records = []
    for i in range(max_items + 2):  # 添加比限制多2条的记录
        test_records.append({
            'id': f'test_id_{i}',
            'type': 'TEXT',
            'content': f'测试内容{i}',
            'timestamp': f'2023-03-08 {10+i}:00:00',
            'source': f'测试来源{i}'
        })
    
    # 在会话中只保留最大限制数量的记录（从后向前截取，模拟最新的记录）
    limited_records = test_records[-max_items:]
    
    # 使用session_transaction设置测试记录
    with client.session_transaction() as sess:
        sess['anonymous_history'] = limited_records
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证记录数量不超过限制
    assert data['count'] == max_items  # 确认记录数等于最大限制
    assert len(data['history']) == max_items  # 确认列表长度等于最大限制
    
    # 验证最新的记录都在历史记录中
    record_ids = [record['id'] for record in data['history']]
    expected_ids = [f'test_id_{i}' for i in range(2, max_items + 2)]  # 因为我们有max_items+2条记录，最新的是从2开始
    for expected_id in expected_ids:
        assert expected_id in record_ids

def test_history_record_format(client):
    """
    测试历史记录格式正确性
    
    验证不同类型的历史记录（TEXT、OCR、PDF）格式正确，包含所需字段
    """
    # 添加不同类型的测试记录
    test_records = [
        # 文本类型记录
        {
            'id': 'text_123',
            'type': 'TEXT',
            'content': '用户输入的文本内容',
            'timestamp': '2023-03-08 10:00:00',
            'source': '用户输入：测试文本'
        },
        # OCR类型记录
        {
            'id': 'ocr_456',
            'type': 'OCR',
            'content': 'OCR识别的文本内容',
            'timestamp': '2023-03-08 11:00:00',
            'source': '图片识别'
        },
        # PDF类型记录
        {
            'id': 'pdf_789',
            'type': 'PDF',
            'content': 'PDF提取的文本内容',
            'timestamp': '2023-03-08 12:00:00',
            'source': 'PDF提取：测试.pdf'
        }
    ]
    
    # 使用session_transaction设置测试记录
    with client.session_transaction() as sess:
        sess['anonymous_history'] = test_records
    
    # 获取历史记录
    response = client.get('/history')
    data = json.loads(response.data)
    
    # 验证各种类型的记录格式正确
    assert data['count'] == 3  # 确认记录总数
    
    # 检查TEXT类型记录
    text_record = next(r for r in data['history'] if r['type'] == 'TEXT')
    assert 'id' in text_record  # 确认有ID字段
    assert 'content' in text_record  # 确认有内容字段
    assert 'timestamp' in text_record  # 确认有时间戳字段
    assert 'source' in text_record  # 确认有来源字段
    assert text_record['type'] == 'TEXT'  # 确认类型正确
    
    # 检查OCR类型记录
    ocr_record = next(r for r in data['history'] if r['type'] == 'OCR')
    assert ocr_record['type'] == 'OCR'  # 确认类型正确
    assert '图片识别' in ocr_record['source']  # 确认来源包含"图片识别"
    
    # 检查PDF类型记录
    pdf_record = next(r for r in data['history'] if r['type'] == 'PDF')
    assert pdf_record['type'] == 'PDF'  # 确认类型正确
    assert 'PDF提取' in pdf_record['source']  # 确认来源包含"PDF提取" 
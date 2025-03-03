import pytest
import warnings
from pathlib import Path
import shutil
import os

@pytest.fixture(autouse=True)
def ignore_reportlab_warnings():
    """自动忽略 ReportLab 的废弃警告"""
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module="reportlab.lib.rl_safe_eval"
    )

@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """创建测试数据目录"""
    return tmp_path_factory.mktemp("test_data")

@pytest.fixture(scope="function")
def clean_test_dir(tmp_path):
    """为每个测试提供清理的测试目录"""
    yield tmp_path
    # 测试后清理
    shutil.rmtree(tmp_path, ignore_errors=True)

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 创建必要的目录
    dirs = ['uploads', 'pdfs']
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
    
    yield
    
    # 测试完成后清理
    for dir_name in dirs:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

@pytest.fixture(scope="session")
def sample_files_dir(test_data_dir):
    """提供示例文件目录"""
    files_dir = test_data_dir / "sample_files"
    files_dir.mkdir(parents=True, exist_ok=True)
    return files_dir

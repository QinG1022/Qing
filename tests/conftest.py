"""
测试配置文件
功能: 为所有测试提供共享的配置和fixtures
版本: 1.0
最后更新: 2024-03-06
描述: 包含pytest的全局配置和共享fixture，用于优化测试执行环境
"""
import pytest
import warnings

@pytest.fixture(autouse=True)    # 自动应用此fixture到所有测试  
def ignore_reportlab_warnings():
    """
    自动忽略 ReportLab 库的废弃警告
    
    功能:
        在测试执行时自动过滤ReportLab库中的DeprecationWarning警告，
        避免这些警告干扰测试结果的可读性
        
    作用范围:
        由于设置了autouse=True，此fixture会自动应用于所有测试
        
    过滤对象:
        仅过滤来自reportlab.lib.rl_safe_eval模块的DeprecationWarning
    """
    warnings.filterwarnings(        # 过滤警告  
        "ignore",                   # 忽略警告      
        category=DeprecationWarning, # 警告类型  
        module="reportlab.lib.rl_safe_eval" # 模块名称  
    )

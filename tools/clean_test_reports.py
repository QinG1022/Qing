"""
测试报告清理工具
功能: 清理pytest生成的测试报告文件
作者: [您的名字]
版本: 1.0
最后更新: 2024-03-06
描述: 自动清理项目中生成的测试报告文件和目录，避免占用过多磁盘空间
"""

import os
from pathlib import Path
import logging

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def clean_test_reports(directory=None):
    """
    清理测试报告文件和目录
    
    功能:
        扫描并删除指定目录中的测试报告文件和相关资源
    
    参数:
        directory (str/Path): 测试报告所在目录，默认为项目根目录
        
    处理流程:
        1. 确定目标目录
        2. 扫描指定模式的报告文件
        3. 删除找到的文件和目录
        4. 记录操作结果
        
    返回:
        None
    """
    try:
        # 确定目标目录
        if directory is None:
            directory = Path(__file__).parent.parent
        else:
            directory = Path(directory)
            
        if not directory.exists():
            logging.warning(f"目录不存在: {directory}")
            return
            
        count_removed = 0  # 成功删除的文件/目录计数
        count_failed = 0   # 删除失败的文件/目录计数
        
        # 定义需要清理的报告文件模式
        report_patterns = ['report.html', 'assets/*']
        
        # 遍历并清理匹配的文件和目录
        for pattern in report_patterns:
            for report_file in directory.glob(f"**/{pattern}"):
                try:
                    if report_file.is_file():
                        # 删除文件
                        report_file.unlink()
                        count_removed += 1
                        logging.info(f"已删除测试报告文件: {report_file}")
                    elif report_file.is_dir():
                        # 删除目录及其内容
                        for f in report_file.glob("*"):
                            f.unlink()
                        report_file.rmdir()
                        count_removed += 1
                        logging.info(f"已删除测试报告目录: {report_file}")
                except Exception as e:
                    count_failed += 1
                    logging.error(f"文件删除失败 {report_file}: {str(e)}")
        
        # 汇总操作结果
        logging.info(f"测试报告清理完成 - 成功: {count_removed}, 失败: {count_failed}")
        
    except Exception as e:
        logging.error(f"清理过程出错: {str(e)}")

if __name__ == '__main__':
    logging.info("开始清理测试报告文件")
    clean_test_reports() 
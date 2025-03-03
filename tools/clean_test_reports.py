"""
测试报告清理工具
功能：清理pytest生成的测试报告文件
作者：[您的名字]
版本：1.0
"""

import os
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def clean_test_reports(directory=None):
    """清理测试报告文件
    
    Args:
        directory: 测试报告所在目录，默认为项目根目录
    """
    try:
        if directory is None:
            directory = Path(__file__).parent.parent
        else:
            directory = Path(directory)
            
        if not directory.exists():
            logging.warning(f"目录不存在: {directory}")
            return
            
        count_removed = 0
        count_failed = 0
        
        # 清理HTML报告文件
        report_patterns = ['report.html', 'assets/*']
        
        for pattern in report_patterns:
            for report_file in directory.glob(f"**/{pattern}"):
                try:
                    if report_file.is_file():
                        report_file.unlink()
                        count_removed += 1
                        logging.info(f"已删除测试报告文件: {report_file}")
                    elif report_file.is_dir():
                        for f in report_file.glob("*"):
                            f.unlink()
                        report_file.rmdir()
                        count_removed += 1
                        logging.info(f"已删除测试报告目录: {report_file}")
                except Exception as e:
                    count_failed += 1
                    logging.error(f"文件删除失败 {report_file}: {str(e)}")
        
        logging.info(f"测试报告清理完成 - 成功: {count_removed}, 失败: {count_failed}")
        
    except Exception as e:
        logging.error(f"清理过程出错: {str(e)}")

if __name__ == '__main__':
    logging.info("开始清理测试报告文件")
    clean_test_reports() 
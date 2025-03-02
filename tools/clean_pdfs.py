"""
PDF文件清理工具
功能：专门清理过期的PDF文件，保留目录结构
作者：[您的名字]
版本：1.1
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def clean_pdf_files(directory, max_age_days=7):
    """清理指定目录中的过期PDF文件
    
    Args:
        directory: PDF文件目录路径
        max_age_days: PDF文件最大保留天数，默认7天
    """
    try:
        directory = Path(directory)
        if not directory.exists():
            logging.warning(f"PDF目录不存在: {directory}")
            return
        
        now = datetime.now()
        cutoff_date = now - timedelta(days=max_age_days)
        
        count_removed = 0
        count_failed = 0
        
        # 仅处理PDF文件
        for pdf_file in directory.glob('**/*.pdf'):
            try:
                # 获取文件修改时间
                mtime = datetime.fromtimestamp(pdf_file.stat().st_mtime)
                
                if mtime < cutoff_date:
                    pdf_file.unlink()
                    count_removed += 1
                    logging.info(f"已删除PDF: {pdf_file}")
            except Exception as e:
                count_failed += 1
                logging.error(f"PDF删除失败 {pdf_file}: {str(e)}")
        
        logging.info(f"PDF清理完成 - 成功: {count_removed}, 失败: {count_failed}")
        
    except Exception as e:
        logging.error(f"PDF清理过程出错: {str(e)}")

if __name__ == '__main__':
    # 获取项目根目录中的PDF目录
    project_root = Path(__file__).parent.parent
    pdf_dir = project_root / 'pdfs'
    
    logging.info(f"开始清理PDF目录: {pdf_dir}")
    clean_pdf_files(pdf_dir)

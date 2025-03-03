"""
PDF文件清理工具
功能：专门清理过期的PDF文件，保留目录结构
版本：2.0

功能特性：
    1. 支持按时间清理
    2. 支持按大小清理
    3. 支持保留重要文件
    4. 详细的日志记录
    5. 安全检查机制
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging
import shutil

class PDFCleaner:
    """PDF文件清理器"""
    
    def __init__(self, directory, **kwargs):
        """
        初始化清理器
        
        参数:
            directory: PDF文件目录
            max_age_days: 文件最大保留天数（默认7天）
            max_size_mb: 单个文件最大大小（MB）
            total_size_limit_mb: 目录总大小限制（MB）
            keep_patterns: 需要保留的文件名模式列表
        """
        self.directory = Path(directory)
        self.max_age_days = kwargs.get('max_age_days', 7)
        self.max_size_mb = kwargs.get('max_size_mb', 50)
        self.total_size_limit_mb = kwargs.get('total_size_limit_mb', 500)
        self.keep_patterns = kwargs.get('keep_patterns', ['important', 'keep'])
        
        # 配置日志
        self._setup_logging()
        
    def _setup_logging(self):
        """配置日志系统"""
        self.logger = logging.getLogger('PDFCleaner')
        self.logger.setLevel(logging.INFO)
        
        # 文件处理器
        log_file = self.directory.parent / 'logs' / 'pdf_cleaner.log'
        log_file.parent.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _should_keep_file(self, file_path):
        """判断是否应该保留文件"""
        # 检查保留模式
        for pattern in self.keep_patterns:
            if pattern in file_path.name.lower():
                return True
        return False
    
    def _get_directory_size(self):
        """获取目录总大小（MB）"""
        total_size = sum(f.stat().st_size for f in self.directory.glob('**/*.pdf') if f.is_file())
        return total_size / (1024 * 1024)
    
    def _is_safe_to_delete(self, file_path):
        """检查是否安全删除文件"""
        try:
            # 检查文件是否存在
            if not file_path.exists():
                return False
                
            # 检查文件权限
            if not os.access(file_path, os.W_OK):
                self.logger.warning(f"文件无删除权限: {file_path}")
                return False
                
            # 检查是否在正确的目录下
            if not str(file_path.absolute()).startswith(str(self.directory.absolute())):
                self.logger.error(f"文件在目标目录之外: {file_path}")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"安全检查失败: {str(e)}")
            return False
    
    def clean(self):
        """执行清理操作"""
        try:
            if not self.directory.exists():
                self.logger.error(f"PDF目录不存在: {self.directory}")
                return False
            
            self.logger.info("开始清理PDF文件...")
            self.logger.info(f"目标目录: {self.directory}")
            self.logger.info(f"配置信息:")
            self.logger.info(f"- 最大保留天数: {self.max_age_days}天")
            self.logger.info(f"- 单文件大小限制: {self.max_size_mb}MB")
            self.logger.info(f"- 总大小限制: {self.total_size_limit_mb}MB")
            
            now = datetime.now()
            cutoff_date = now - timedelta(days=self.max_age_days)
            
            stats = {
                'total': 0,
                'removed': 0,
                'failed': 0,
                'skipped': 0,
                'size_cleaned': 0
            }
            
            # 获取所有PDF文件并按修改时间排序
            pdf_files = sorted(
                self.directory.glob('**/*.pdf'),
                key=lambda x: x.stat().st_mtime
            )
            
            for pdf_file in pdf_files:
                stats['total'] += 1
                try:
                    if not self._is_safe_to_delete(pdf_file):
                        stats['skipped'] += 1
                        continue
                        
                    file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
                    mtime = datetime.fromtimestamp(pdf_file.stat().st_mtime)
                    
                    # 检查是否应该删除
                    should_delete = False
                    delete_reason = []
                    
                    # 检查文件大小
                    if file_size_mb > self.max_size_mb:
                        should_delete = True
                        delete_reason.append(f"超过大小限制({file_size_mb:.1f}MB > {self.max_size_mb}MB)")
                    
                    # 检查修改时间
                    if mtime < cutoff_date:
                        should_delete = True
                        delete_reason.append(f"超过时间限制({mtime.strftime('%Y-%m-%d')})")
                    
                    # 检查是否需要保留
                    if self._should_keep_file(pdf_file):
                        should_delete = False
                        self.logger.info(f"保留重要文件: {pdf_file.name}")
                        stats['skipped'] += 1
                        continue
                    
                    if should_delete:
                        pdf_file.unlink()
                        stats['removed'] += 1
                        stats['size_cleaned'] += file_size_mb
                        self.logger.info(f"已删除PDF: {pdf_file.name} ({', '.join(delete_reason)})")
                    else:
                        stats['skipped'] += 1
                        
                except Exception as e:
                    stats['failed'] += 1
                    self.logger.error(f"处理失败 {pdf_file}: {str(e)}")
            
            # 输出统计信息
            self.logger.info("\n清理完成统计:")
            self.logger.info(f"- 总文件数: {stats['total']}")
            self.logger.info(f"- 已删除: {stats['removed']}")
            self.logger.info(f"- 已跳过: {stats['skipped']}")
            self.logger.info(f"- 失败: {stats['failed']}")
            self.logger.info(f"- 释放空间: {stats['size_cleaned']:.1f}MB")
            
            return stats['failed'] == 0
            
        except Exception as e:
            self.logger.error(f"清理过程出错: {str(e)}")
            return False

def main():
    """主函数"""
    try:
        # 获取项目根目录中的PDF目录
        project_root = Path(__file__).parent.parent
        pdf_dir = project_root / 'pdfs'
        
        # 创建清理器实例
        cleaner = PDFCleaner(
            pdf_dir,
            max_age_days=7,
            max_size_mb=50,
            total_size_limit_mb=500,
            keep_patterns=['important', 'keep', 'final']
        )
        
        # 执行清理
        success = cleaner.clean()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n清理操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"程序执行错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()

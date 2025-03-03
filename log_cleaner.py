import os
import time
from datetime import datetime
import logging
from pathlib import Path

class LogCleaner:
    """日志清理工具
    
    功能：
    1. 自动清理指定目录下的日志文件
    2. 可以保留最近N天的日志
    3. 可以保留文件大小限制
    """
    
    def __init__(self, log_dir='.', retention_days=7, max_size_mb=10):
        self.log_dir = Path(log_dir)
        self.retention_days = retention_days
        self.max_size_mb = max_size_mb
        self.log_patterns = ['app.log', 'app_audit.log']
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('LogCleaner')
    
    def clean_logs(self):
        """清理日志文件"""
        try:
            self.logger.info(f'开始清理日志文件...')
            self.logger.info(f'日志目录: {self.log_dir}')
            
            for log_pattern in self.log_patterns:
                log_file = self.log_dir / log_pattern
                if not log_file.exists():
                    self.logger.warning(f'日志文件不存在: {log_file}')
                    continue
                
                # 检查文件大小
                size_mb = log_file.stat().st_size / (1024 * 1024)
                if size_mb > self.max_size_mb:
                    self.logger.info(f'日志文件 {log_file.name} 超过大小限制 ({size_mb:.2f}MB > {self.max_size_mb}MB)')
                    self._rotate_log(log_file)
                else:
                    self.logger.info(f'日志文件 {log_file.name} 大小正常 ({size_mb:.2f}MB)')
                    
            # 清理旧的备份文件
            self._clean_old_backups()
            
        except Exception as e:
            self.logger.error(f'清理日志时发生错误: {str(e)}')
            raise
    
    def _rotate_log(self, log_file):
        """轮转日志文件"""
        try:
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = log_file.with_suffix(f'.{timestamp}.bak')
            
            # 重命名当前日志文件为备份文件
            log_file.rename(backup_file)
            self.logger.info(f'已创建备份文件: {backup_file.name}')
            
            # 创建新的空日志文件
            log_file.touch()
            self.logger.info(f'已创建新的日志文件: {log_file.name}')
            
        except Exception as e:
            self.logger.error(f'轮转日志文件时发生错误: {str(e)}')
            raise
    
    def _clean_old_backups(self):
        """清理旧的备份文件"""
        try:
            current_time = time.time()
            retention_seconds = self.retention_days * 24 * 60 * 60
            
            for backup_file in self.log_dir.glob('*.bak'):
                file_age = current_time - backup_file.stat().st_mtime
                if file_age > retention_seconds:
                    backup_file.unlink()
                    self.logger.info(f'已删除旧的备份文件: {backup_file.name}')
                    
        except Exception as e:
            self.logger.error(f'清理旧备份文件时发生错误: {str(e)}')
            raise

def main():
    """主函数"""
    try:
        # 配置清理参数
        log_dir = '.'              # 日志文件目录
        retention_days = 7         # 保留天数
        max_size_mb = 10          # 最大文件大小(MB)
        
        # 创建清理器并执行清理
        cleaner = LogCleaner(log_dir, retention_days, max_size_mb)
        cleaner.clean_logs()
        
    except Exception as e:
        print(f'程序执行错误: {str(e)}')
    finally:
        print('\n' + '='*50)
        input('按回车键退出...')

if __name__ == '__main__':
    main() 
import sqlite3
import os
import time
from datetime import datetime

# 尝试导入终端颜色支持，如果不可用则使用空字符串替代
try:
    class Colors:
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
except:
    class Colors:
        HEADER = ''
        BLUE = ''
        CYAN = ''
        GREEN = ''
        YELLOW = ''
        RED = ''
        ENDC = ''
        BOLD = ''
        UNDERLINE = ''

def print_header(text, symbol='=', color=Colors.HEADER):
    """打印美观的标题"""
    print(f"\n{color}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{color}{symbol * len(text)}{Colors.ENDC}")

def format_table(headers, rows, min_width=10):
    """创建格式化的表格输出"""
    # 计算每列的最大宽度
    col_widths = [max(min_width, len(str(h))) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # 创建表头
    header_line = ' | '.join(f"{str(h):<{col_widths[i]}}" for i, h in enumerate(headers))
    separator = '-+-'.join('-' * w for w in col_widths)
    
    # 打印表头
    print(f"{Colors.BOLD}{header_line}{Colors.ENDC}")
    print(separator)
    
    # 打印数据行
    for row in rows:
        row_str = ' | '.join(f"{str(cell):<{col_widths[i]}}" for i, cell in enumerate(row))
        print(row_str)

# 获取数据库文件的完整路径
db_path = os.path.join(os.getcwd(), 'data', 'app.db')
print_header(f"数据库信息", color=Colors.GREEN)
print(f"{Colors.CYAN}数据库路径:{Colors.ENDC} {db_path}")

# 检查文件是否存在
if not os.path.exists(db_path):
    print(f"{Colors.RED}错误: 数据库文件不存在: {db_path}{Colors.ENDC}")
    exit(1)

# 获取文件大小和修改时间
file_size = os.path.getsize(db_path)
file_size_formatted = f"{file_size / 1024:.2f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.2f} MB"
mod_time = os.path.getmtime(db_path)
mod_time_formatted = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')

print(f"{Colors.CYAN}数据库大小:{Colors.ENDC} {file_size_formatted}")
print(f"{Colors.CYAN}最后修改:{Colors.ENDC} {mod_time_formatted}")

# 连接数据库
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # 使结果以字典形式返回
cursor = conn.cursor()

# 获取所有表名和行数
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
table_info = []

print_header("数据库统计", color=Colors.BLUE)
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    row_count = cursor.fetchone()[0]
    table_info.append((table_name, row_count))

# 打印表格统计信息
format_table(["表名", "记录数"], table_info)

# 查看每个表的结构
print_header("表结构详情", color=Colors.YELLOW)
for table in tables:
    table_name = table[0]
    
    # 获取表结构
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    
    print_header(f"表: {table_name}", symbol='-', color=Colors.CYAN)
    
    # 格式化列信息
    col_data = []
    for col in columns:
        col_name = col[1]
        col_type = col[2]
        not_null = "否" if col[3] == 0 else "是"
        default = col[4] if col[4] is not None else "无"
        primary_key = "是" if col[5] else "否"
        col_data.append((col_name, col_type, not_null, str(default), primary_key))
    
    # 打印列信息表格
    format_table(["列名", "数据类型", "必填", "默认值", "主键"], col_data)
    
    # 显示表数据预览
    if table_info[tables.index(table)][1] > 0:  # 如果表中有数据
        print_header(f"{table_name} 数据预览 (最多5条)", symbol='-', color=Colors.GREEN)
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        rows = cursor.fetchall()
        if rows:
            # 获取列名
            headers = [description[0] for description in cursor.description]
            # 准备行数据
            row_data = []
            for row in rows:
                # 截断长文本字段以便显示
                formatted_row = []
                for item in row:
                    if isinstance(item, str) and len(item) > 30:
                        formatted_row.append(f"{item[:27]}...")
                    else:
                        formatted_row.append(item)
                row_data.append(formatted_row)
            # 打印数据表格    
            format_table(headers, row_data)

print_header("查询完成", color=Colors.GREEN)
conn.close()
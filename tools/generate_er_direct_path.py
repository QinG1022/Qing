#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接路径版ER图生成工具
功能: 使用GraphViz的绝对路径生成数据库ER图
版本: 1.0
最后更新: 2024-04-03
使用方法:
    python tools/generate_er_direct_path.py [选项]
    例如: python tools/generate_er_direct_path.py -p D:/wenjian/Graphviz/bin
    椭圆上下：python tools/generate_er_direct_path.py -s colorful
    左右布局：python tools/generate_er_direct_path.py -s classic 
    所有生成的ER图和文本描述将保存在项目根目录的 `assets`文件夹中
"""

import os
import sys
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_argparse():
    """设置命令行参数解析"""
    parser = argparse.ArgumentParser(description='生成数据库ER图 (直接路径版)')
    parser.add_argument('-o', '--output', type=str, default='er_diagram_direct',
                        help='输出文件名（不含扩展名）')
    parser.add_argument('-f', '--format', type=str, choices=['png', 'pdf', 'svg'], 
                        default='png', help='输出格式（png, pdf, svg）')
    parser.add_argument('-t', '--title', type=str, default='数据库实体关系图',
                        help='图表标题')
    parser.add_argument('-p', '--graphviz_path', type=str, default='D:/wenjian/Graphviz/bin',
                        help='GraphViz bin目录的路径')
    parser.add_argument('-s', '--style', type=str, 
                        choices=['classic', 'modern', 'colorful'], 
                        default='modern', help='ER图样式 (classic, modern, colorful)')
    return parser.parse_args()

def create_dot_file(metadata, output_path, title, style='modern'):
    """创建DOT文件"""
    try:
        # 根据样式选择配置
        styles = {
            'classic': {
                'rankdir': 'LR',
                'node_shape': 'record',
                'node_style': 'filled',
                'node_fillcolor': '#F8F8F8',
                'edge_style': 'arrowhead=normal',
                'pk_color': '#000000',
                'fk_color': '#000000',
                'table_color': '#000000',
            },
            'modern': {
                'rankdir': 'TB',
                'node_shape': 'box',
                'node_style': 'filled,rounded',
                'node_fillcolor': '#E8F8F5',
                'edge_style': 'arrowhead=normal',
                'pk_color': '#D35400',
                'fk_color': '#2874A6',
                'table_color': '#17202A',
            },
            'colorful': {
                'rankdir': 'TB',
                'node_shape': 'ellipse',
                'node_style': 'filled,bold',
                'node_fillcolor': '#FEF9E7',
                'edge_style': 'arrowhead=normal, color="#3498DB"',
                'pk_color': '#8E44AD',
                'fk_color': '#2E86C1',
                'table_color': '#2C3E50',
            }
        }
        
        # 使用选择的样式
        current_style = styles.get(style, styles['modern'])
        
        # DOT文件头部
        dot_content = [
            'digraph ER {',
            f'  label="{title}\\n生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}";',
            '  fontname="Arial";',
            '  labelloc="t";',
            '  fontsize=16;',
            f'  rankdir="{current_style["rankdir"]}";',
            f'  node [shape={current_style["node_shape"]}, fontname="Arial", fontsize=10, style="{current_style["node_style"]}", fillcolor="{current_style["node_fillcolor"]}"];',
            f'  edge [fontname="Arial", fontsize=8, {current_style["edge_style"]}];',
        ]
        
        # 获取所有表
        tables = metadata.tables
        
        # 创建表节点
        for table_name, table in tables.items():
            # 创建表格的HTML标签
            node_content = [
                f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" BGCOLOR="{current_style["node_fillcolor"]}">'
            ]
            
            # 表标题行
            node_content.append(f'<TR><TD COLSPAN="2" BGCOLOR="#AED6F1" PORT="{table_name}"><FONT COLOR="{current_style["table_color"]}" FACE="Arial"><B>{table_name}</B></FONT></TD></TR>')
            
            # 表字段
            for column in table.columns:
                # 确定列类型
                col_type = "普通列"
                port_name = column.name
                bg_color = current_style["node_fillcolor"]
                font_color = "#000000"
                
                if column.primary_key:
                    col_type = "PK"
                    bg_color = "#D5F5E3"
                    font_color = current_style["pk_color"]
                elif column.foreign_keys:
                    col_type = "FK"
                    bg_color = "#D6EAF8"
                    font_color = current_style["fk_color"]
                
                node_content.append(
                    f'<TR><TD BGCOLOR="{bg_color}" PORT="{port_name}"><FONT COLOR="{font_color}">{column.name}</FONT></TD>' +
                    f'<TD BGCOLOR="{bg_color}"><FONT COLOR="{font_color}">{col_type}</FONT></TD></TR>'
                )
            
            node_content.append('</TABLE>>')
            
            # 添加节点定义
            dot_content.append(f'  "{table_name}" [label={" ".join(node_content)}];')
        
        # 创建关系边
        for table_name, table in tables.items():
            for column in table.columns:
                if column.foreign_keys:
                    for fk in column.foreign_keys:
                        ref_table = fk.column.table.name
                        ref_column = fk.column.name
                        
                        # 使用HTML端口标签创建更精确的连接
                        dot_content.append(
                            f'  "{table_name}":"(column names merged):{column.name}" -> "{ref_table}":"(column names merged):{ref_column}" [label="{column.name}→{ref_column}"];'
                        )
        
        # 结束DOT文件
        dot_content.append('}')
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(dot_content))
            
        return True
    except Exception as e:
        logger.error(f"创建DOT文件失败: {e}")
        return False
    
def run_graphviz_direct(dot_path, output_path, format_type, graphviz_path):
    """使用指定的GraphViz路径运行dot命令"""
    try:
        # 构造dot命令的完整路径
        dot_cmd = os.path.join(graphviz_path, 'dot.exe')
        
        # 确保dot命令存在
        if not os.path.exists(dot_cmd):
            logger.error(f"找不到dot命令: {dot_cmd}")
            return False
        
        # 构造完整命令
        cmd = f'"{dot_cmd}" -T{format_type} "{dot_path}" -o "{output_path}"'
        logger.info(f"执行命令: {cmd}")
        
        # 运行命令
        process = subprocess.run(
            cmd, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # 检查结果
        if process.returncode == 0:
            logger.info(f"GraphViz命令执行成功")
            return True
        else:
            logger.error(f"GraphViz命令执行失败: {process.stderr}")
            return False
    except Exception as e:
        logger.error(f"运行GraphViz命令失败: {e}")
        return False

def main():
    """主函数"""
    args = setup_argparse()
    
    try:
        # 导入数据库模型
        try:
            from modules.database import db, User, History, ChatHistory
            logger.info("成功导入数据库模型")
        except ImportError as e:
            logger.error(f"导入数据库模型失败: {e}")
            return 1
        
        # 规范化GraphViz路径
        graphviz_path = args.graphviz_path.replace('\\', '/')
        
        # 确保输出目录存在
        output_dir = Path(project_root) / 'assets'
        output_dir.mkdir(exist_ok=True)
        
        # 文件路径
        dot_file = output_dir / f"{args.output}.dot"
        output_file = output_dir / f"{args.output}.{args.format}"
        
        logger.info(f"开始生成ER图，输出到: {output_file}")
        logger.info(f"使用GraphViz路径: {graphviz_path}")
        logger.info(f"图表样式: {args.style}")
        
        # 创建DOT文件
        if not create_dot_file(db.metadata, dot_file, args.title, args.style):
            logger.error("创建DOT文件失败")
            return 1
        
        # 运行GraphViz，使用指定的路径
        if run_graphviz_direct(dot_file, output_file, args.format, graphviz_path):
            logger.info(f"ER图生成成功: {output_file}")
            return 0
        else:
            logger.error("ER图生成失败")
            return 1
        
    except Exception as e:
        logger.error(f"生成ER图时发生错误: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
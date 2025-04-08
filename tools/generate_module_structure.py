#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
后端模块结构图生成工具
功能: 生成项目后端模块结构的树状可视化图表
版本: 2.0
最后更新: 2024-04-18
变更:
- 从标准结构图改为树状层次结构图
- 添加目录节点，更清晰地展示模块层次
- 优化视觉样式，使用文件夹和文件图标

使用方法:
    python tools/generate_module_structure.py [选项]
    例如: python tools/generate_module_structure.py -p D:/wenjian/Graphviz/bin -f svg
    水平树状图：python tools/generate_module_structure.py -d LR -f png -s
    垂直彩色树状图：python tools/generate_module_structure.py -d TB -f png -s -c
    所有生成的结构图将保存在项目根目录的 `assets`文件夹中
"""

import os
import sys
import logging
import importlib
import inspect
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
    parser = argparse.ArgumentParser(description='生成后端模块结构树状图')
    parser.add_argument('-o', '--output', type=str, default='backend_structure',
                        help='输出文件名（不含扩展名）')
    parser.add_argument('-f', '--format', type=str, choices=['png', 'pdf', 'svg'], 
                        default='png', help='输出格式（png, pdf, svg）')
    parser.add_argument('-t', '--title', type=str, default='后端模块结构树状图',
                        help='图表标题')
    parser.add_argument('-p', '--graphviz_path', type=str, default='D:/wenjian/Graphviz/bin',
                        help='GraphViz bin目录的路径')
    parser.add_argument('-d', '--direction', type=str, choices=['TB', 'LR'], default='TB',
                        help='树状结构方向 (TB=自上而下, LR=从左到右)')
    parser.add_argument('-c', '--colorful', action='store_true',
                        help='使用彩色节点（默认为轻微着色）')
    parser.add_argument('-s', '--show_classes', action='store_true',
                        help='在节点中显示类名称')
    return parser.parse_args()

def scan_modules():
    """扫描项目中的模块"""
    modules_info = {}
    
    # 扫描主要模块目录
    module_dirs = {
        'modules': project_root / 'modules',
        'ai_module': project_root / 'ai_module',
    }
    
    # 特别关注的文件
    special_files = [
        project_root / 'app.py',
    ]
    
    # 添加模块信息
    modules_info['app'] = {
        'path': str(project_root / 'app.py'),
        'type': 'main_app',
        'description': 'Flask主应用程序，提供Web服务、文件处理和API接口',
        'imports': [],
        'classes': []
    }
    
    # 扫描modules目录
    for module_name, module_path in module_dirs.items():
        if module_path.exists():
            # 首先添加顶级模块目录
            if module_name not in modules_info:
                modules_info[module_name] = {
                    'path': str(module_path),
                    'type': 'directory',
                    'description': f"{module_name}模块目录",
                    'imports': [],
                    'classes': []
                }
            
            # 添加所有子目录作为中间节点
            for subdir in module_path.glob('**'):
                if subdir == module_path:
                    continue
                
                # 忽略__pycache__目录和隐藏文件夹
                if '__pycache__' in str(subdir) or any(p.startswith('.') for p in subdir.parts):
                    continue
                
                # 计算相对于项目根目录的模块路径
                rel_path = subdir.relative_to(project_root)
                module_id = str(rel_path).replace('\\', '/').replace('/', '.')
                
                # 如果这是一个目录，添加为目录节点
                if subdir.is_dir() and module_id not in modules_info:
                    modules_info[module_id] = {
                        'path': str(subdir),
                        'type': 'directory',
                        'description': f"{module_id}目录",
                        'imports': [],
                        'classes': []
                    }
            
            # 然后扫描所有Python文件
            for py_file in module_path.glob('**/*.py'):
                if py_file.name == '__init__.py':
                    continue
                    
                rel_path = py_file.relative_to(project_root)
                module_id = str(rel_path.with_suffix('')).replace('\\', '/').replace('/', '.')
                
                # 读取文件内容以提取描述和导入信息
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 获取模块描述（通常在文件顶部的docstring中）
                    description = "未提供描述"
                    docstring_start = content.find('"""')
                    if docstring_start != -1:
                        docstring_end = content.find('"""', docstring_start + 3)
                        if docstring_end != -1:
                            docstring = content[docstring_start+3:docstring_end].strip()
                            description_lines = [line for line in docstring.split('\n') if line.strip()]
                            if description_lines:
                                description = description_lines[0]
                    
                    # 提取导入信息
                    imports = []
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('import ') or line.startswith('from '):
                            # 只关注项目内部模块
                            if 'modules.' in line or 'ai_module.' in line:
                                imports.append(line)
                    
                    # 提取类信息
                    classes = []
                    for line in lines:
                        line = line.strip()
                        if line.startswith('class '):
                            class_name = line.split('class ')[1].split('(')[0].strip()
                            classes.append(class_name)
                    
                    modules_info[module_id] = {
                        'path': str(py_file),
                        'type': 'module',
                        'description': description,
                        'imports': imports,
                        'classes': classes
                    }
                except Exception as e:
                    logger.error(f"处理模块 {py_file} 时出错: {e}")
    
    # 处理特别关注的文件
    for special_file in special_files:
        if special_file.exists() and special_file.name.endswith('.py'):
            rel_path = special_file.relative_to(project_root)
            module_id = str(rel_path.with_suffix('')).replace('\\', '/').replace('/', '.')
            
            # 如果还没有处理过这个文件
            if module_id not in modules_info:
                try:
                    with open(special_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 获取模块描述
                    description = "特殊文件"
                    docstring_start = content.find('"""')
                    if docstring_start != -1:
                        docstring_end = content.find('"""', docstring_start + 3)
                        if docstring_end != -1:
                            docstring = content[docstring_start+3:docstring_end].strip()
                            description_lines = [line for line in docstring.split('\n') if line.strip()]
                            if description_lines:
                                description = description_lines[0]
                    
                    # 提取类信息
                    classes = []
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('class '):
                            class_name = line.split('class ')[1].split('(')[0].strip()
                            classes.append(class_name)
                    
                    modules_info[module_id] = {
                        'path': str(special_file),
                        'type': 'special',
                        'description': description,
                        'imports': [],
                        'classes': classes
                    }
                except Exception as e:
                    logger.error(f"处理特殊文件 {special_file} 时出错: {e}")
    
    return modules_info

def create_dot_file(modules_info, output_path, title, args):
    """创建DOT文件 - 树状结构版本"""
    try:
        # DOT文件头部
        dot_content = [
            'digraph ModuleStructure {',
            f'  label="Backend Module Structure Tree\\nGenerated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}";',
            '  fontname="Arial";',
            '  labelloc="t";',
            '  fontsize=16;',
            f'  rankdir="{args.direction}";',  # 使用命令行指定的方向
            '  nodesep=0.8;',   # 增加节点间距
            '  ranksep=1.2;',   # 增加层级间距
            '  splines=ortho;', # 使用直角连线，更清晰的树状结构
            '  node [shape=box, fontname="Arial", fontsize=10, style=filled, fillcolor="#F0F8FF", margin="0.2,0.1"];',
            '  edge [fontname="Arial", fontsize=8, arrowsize=0.7];',
        ]
        
        # 定义根节点 - 使用英文避免编码问题
        dot_content.append('  "root" [label="Project Root", fillcolor="#E6E6FA", shape=folder];')
        
        # 定义颜色方案
        if args.colorful:
            # 彩色模式
            colors = {
                'app': '#FFD700',  # 金色
                'modules': '#98FB98',  # 浅绿色
                'ai_module': '#FFA07A',  # 浅珊瑚色
                'directory': '#E6E6FA',  # 淡紫色
                'module': '#F0F8FF',  # 爱丽丝蓝
            }
        else:
            # 轻微着色模式
            colors = {
                'app': '#F5F5DC',  # 米色
                'modules': '#F0F8FF',  # 爱丽丝蓝
                'ai_module': '#F5F5F5',  # 白烟色
                'directory': '#F8F8FF',  # 幽灵白
                'module': '#FFFFFF',  # 白色
            }
        
        # 定义主要分组
        main_groups = {
            'app': {'name': 'app.py', 'color': colors['app']},
            'modules': {'name': 'modules', 'color': colors['modules']},
            'ai_module': {'name': 'ai_module', 'color': colors['ai_module']},
        }
        
        # 添加主要分组节点
        for group_id, group_info in main_groups.items():
            dot_content.append(f'  "{group_id}" [label="{group_info["name"]}", fillcolor="{group_info["color"]}", shape=folder];')
            dot_content.append(f'  "root" -> "{group_id}";')
        
        # 按照路径组织模块
        module_tree = {
            'modules': {},
            'ai_module': {},
            'app': {}
        }
        
        # 先收集所有模块
        for module_id, info in modules_info.items():
            parts = module_id.split('.')
            
            if module_id == 'app':
                continue  # 已经添加过app节点
            
            # 确定模块所属的主分组
            if module_id.startswith('modules'):
                parent = 'modules'
                group_parts = parts[1:]  # 去掉"modules"前缀
            elif module_id.startswith('ai_module'):
                parent = 'ai_module'
                group_parts = parts[1:]  # 去掉"ai_module"前缀
            else:
                continue  # 跳过其他未归类模块
                
            # 没有子部分，直接添加到父级
            if not group_parts:
                continue
                
            # 构建路径
            current = module_tree[parent]
            path = parent
            
            # 为每一级创建嵌套字典
            for i, part in enumerate(group_parts[:-1]):
                next_path = f"{path}.{part}"
                if next_path not in current:
                    current[next_path] = {}
                current = current[next_path]
                path = next_path
            
            # 添加最后一级（实际文件）
            final_path = f"{path}.{group_parts[-1]}"
            current[final_path] = {}
        
        # 递归添加节点和边
        def add_tree_nodes(tree, parent_id):
            if not tree:
                return
                
            for node_id, children in tree.items():
                node_name = node_id.split('.')[-1]
                
                # 获取节点信息（如果是实际模块）
                if node_id in modules_info:
                    info = modules_info[node_id]
                    
                    # 确定填充颜色
                    fillcolor = colors['module']
                    if info['type'] == 'directory':
                        fillcolor = colors['directory']
                    
                    label_parts = [f"{node_name}"]
                    
                    # 添加类信息（如果启用了显示类选项）
                    if args.show_classes and info['classes']:
                        label_parts.append('\\n')
                        label_parts.append('\\n'.join([f"- {cls}" for cls in info['classes']]))
                    
                    label = '{' + ''.join(label_parts) + '}'
                    
                    # 确定形状
                    shape = 'box'
                    if info['type'] == 'directory':
                        shape = 'folder'
                    
                    # 使用英文描述和工具提示，避免编码问题
                    description = f"{node_id} module"
                    
                    dot_content.append(f'  "{node_id}" [label="{label}", tooltip="{description}", shape={shape}, fillcolor="{fillcolor}"];')
                else:
                    # 这是目录节点
                    tooltip = f"{node_id} directory"
                    dot_content.append(f'  "{node_id}" [label="{node_name}", shape=folder, fillcolor="{colors["directory"]}", tooltip="{tooltip}"];')
                
                # 添加与父节点的连接
                dot_content.append(f'  "{parent_id}" -> "{node_id}";')
                
                # 递归处理子节点
                add_tree_nodes(children, node_id)
        
        # 处理根级模块分组
        for group_id in main_groups.keys():
            if group_id in module_tree:
                add_tree_nodes(module_tree[group_id], group_id)
        
        # 添加app节点
        if 'app' in modules_info:
            app_info = modules_info['app']
            label_parts = ["app"]
            
            if args.show_classes and app_info['classes']:
                label_parts.append('\\n')
                label_parts.append('\\n'.join([f"- {cls}" for cls in app_info['classes']]))
            
            label = '{' + ''.join(label_parts) + '}'
            description = "Flask main application"
            dot_content.append(f'  "app" [label="{label}", tooltip="{description}", fillcolor="{colors["app"]}"];')
        
        # 结束DOT文件
        dot_content.append('}')
        
        # 写入文件 - 使用ASCII编码
        with open(output_path, 'w', encoding='ascii') as f:
            f.write('\n'.join(dot_content))
            
        return True
    except Exception as e:
        logger.error(f"创建DOT文件失败: {e}", exc_info=True)
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
        # 规范化GraphViz路径
        graphviz_path = args.graphviz_path.replace('\\', '/')
        
        # 确保输出目录存在
        output_dir = Path(project_root) / 'assets'
        output_dir.mkdir(exist_ok=True)
        
        # 文件路径
        dot_file = output_dir / f"{args.output}.dot"
        output_file = output_dir / f"{args.output}.{args.format}"
        
        logger.info(f"开始生成后端模块结构树状图，输出到: {output_file}")
        logger.info(f"使用GraphViz路径: {graphviz_path}")
        logger.info(f"使用布局方向: {args.direction}")
        
        # 扫描模块
        logger.info("开始扫描项目模块...")
        modules_info = scan_modules()
        logger.info(f"已扫描到 {len(modules_info)} 个模块")
        
        # 创建DOT文件
        if not create_dot_file(modules_info, dot_file, args.title, args):
            logger.error("创建DOT文件失败")
            return 1
        
        # 运行GraphViz，使用指定的路径
        if run_graphviz_direct(dot_file, output_file, args.format, graphviz_path):
            logger.info(f"后端模块结构树状图生成成功: {output_file}")
            
            # 输出图像信息
            dot_file_size = dot_file.stat().st_size
            output_file_size = output_file.stat().st_size
            logger.info(f"DOT文件大小: {dot_file_size/1024:.2f} KB")
            logger.info(f"输出图像大小: {output_file_size/1024:.2f} KB")
            logger.info(f"扫描的模块数量: {len(modules_info)}")
            
            return 0
        else:
            logger.error("后端模块结构树状图生成失败")
            return 1
        
    except Exception as e:
        logger.error(f"生成后端模块结构树状图时发生错误: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
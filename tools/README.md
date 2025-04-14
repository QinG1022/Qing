# 项目工具集

本目录包含各种用于项目管理、分析和可视化的工具脚本。

## 工具列表

### 数据库检查工具 (check_db.py)

该工具用于检查和分析SQLite数据库的结构和内容，提供数据库表结构、记录数量和数据预览等信息。

**功能**:
- 显示数据库文件状态信息（大小、修改时间）
- 列出所有表及其记录数
- 展示每个表的详细结构（列名、数据类型、约束等）
- 提供每个表的数据预览（最多5条记录）

**使用方法**:
```bash
python tools/check_db.py
```

**输出**:
- 在控制台中以格式化表格形式显示数据库信息
- 支持彩色输出（终端支持ANSI颜色代码时）

**依赖**:
- Python 3.6+
- SQLite3（Python标准库）

### 测试报告清理工具 (clean_test_reports.py)

该工具用于清理pytest生成的测试报告文件和相关资源目录，避免占用过多磁盘空间。

**功能**:
- 自动扫描并删除项目中的测试报告文件
- 清理相关的assets资源目录
- 提供详细的操作日志

**使用方法**:
```bash
python tools/clean_test_reports.py
```

**注意**:
- 默认清理项目根目录下的所有测试报告
- 操作不可逆，请确保不再需要这些报告文件时再执行

**依赖**:
- Python 3.6+

### 后端模块结构图生成工具 (generate_module_structure.py)

该工具用于生成项目后端模块结构的可视化图表。

**功能**:
- 扫描项目中的Python模块
- 提取模块间的依赖关系
- 识别模块中的主要类
- 生成结构化的图表展示项目架构

**使用方法**:
```bash
python tools/generate_module_structure.py [选项]
```

**选项**:
- `-o, --output`: 输出文件名（不含扩展名），默认为`backend_structure`
- `-f, --format`: 输出格式（png、pdf、svg），默认为`png`
- `-t, --title`: 图表标题，默认为`后端模块结构图`
- `-p, --graphviz_path`: GraphViz bin目录的路径，默认为`D:/wenjian/Graphviz/bin`

**示例**:
```bash
# 使用默认设置生成图表
python tools/generate_module_structure.py

# 指定GraphViz路径并生成SVG格式图表
python tools/generate_module_structure.py -p D:/Software/Graphviz/bin -f svg

# 自定义输出文件名和标题
python tools/generate_module_structure.py -o modules_diagram -t "项目后端模块关系图"
```

**依赖**:
- Python 3.6+
- GraphViz (需要预先安装)

**输出**:
- 所有生成的图表将保存在项目根目录的`assets`文件夹中

### 数据库ER图生成工具 (generate_er_direct_path.py)

该工具用于生成数据库实体关系图，展示表之间的关系。

**使用方法**:
```bash
python tools/generate_er_direct_path.py [选项]
```

**选项**:
- `-o, --output`: 输出文件名（不含扩展名），默认为`er_diagram_direct`
- `-f, --format`: 输出格式（png、pdf、svg），默认为`png`
- `-t, --title`: 图表标题，默认为`数据库实体关系图`
- `-p, --graphviz_path`: GraphViz bin目录的路径，默认为`D:/wenjian/Graphviz/bin`

## 注意事项

1. 部分工具需要安装额外的依赖项，请确保已安装所有必要的依赖
2. 所有工具都假设从项目根目录运行
3. GraphViz是一个外部依赖，需要在系统中预先安装 
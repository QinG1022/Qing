"""
字体配置检查工具
功能: 验证系统中楷体字体的安装和配置状态
版本: 1.1
最后更新: 2024-03-06
描述: 该工具检查PDF生成所需的楷体字体文件，验证其完整性，并提供兼容性测试
"""
from pathlib import Path
import logging
from hashlib import sha256
import os
import webbrowser

def verify_font_config():
    """
    楷体字体配置验证工具
    
    功能：
        1. 验证楷体字体文件存在性和路径配置
        2. 检查字体文件大小、权限和完整性
        3. 生成浏览器兼容性测试HTML文件
        4. 提供字体配置建议和解决方案
        
    验证步骤:
        - 检查字体目录是否存在
        - 检查字体文件是否存在
        - 验证文件大小和读取权限
        - 计算文件哈希值以验证完整性
        - 生成HTML测试文件用于视觉验证
    
    返回:
        None，结果直接打印到控制台
    """
    # 字体路径配置
    font_dir = Path(__file__).parent
    font_file = "simkai.ttf"
    font_path = font_dir / font_file
    
    print("楷体字体验证报告".center(50, '='))
    print(f"字体目录: {font_dir}")
    print(f"字体文件: {font_file}\n")
    
    # 1. 目录检查
    if not font_dir.exists():
        print("× 字体目录不存在！")
        return
    
    # 2. 字体文件检查
    print("文件检查".center(40, '-'))
    if not font_path.exists():
        print(f"状态: ✘ 楷体字体文件不存在")
        return
            
    # 文件验证
    try:
        # 基本信息收集
        size_mb = font_path.stat().st_size / (1024 * 1024)
        print(f"状态: ✔ 文件存在")
        print(f"大小: {size_mb:.2f}MB")
        
        # 权限检查 - 确保文件可读
        readable = os.access(str(font_path), os.R_OK)
        print(f"可读: {'✔' if readable else '✘'}")
        
        # 计算哈希值用于完整性验证
        with open(font_path, 'rb') as f:
            digest = sha256(f.read()).hexdigest()
        print(f"指纹: {digest[:16]}...")  # 显示哈希值前16位作为指纹
        
    except Exception as e:
        print(f"验证错误: {str(e)}")

    # 3. 生成HTML测试文件用于视觉验证
    test_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>楷体字体显示测试</title>
        <style>
            @font-face {{
                font-family: 'SimKai';
                src: url('{font_path}') format('truetype');
            }}
            .test-text {{
                margin: 20px;
                font-size: 18px;
                font-family: 'SimKai', sans-serif;
            }}
            body {{
                background-color: #f8f9fa;
                color: #333;
                font-family: Arial, sans-serif;
            }}
            h3 {{
                color: #0066cc;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="test-text">
            <h3>楷体显示测试</h3>
            <p>天地玄黄 宇宙洪荒</p>
            <p>日月盈昃 辰宿列张</p>
            <p>寒来暑往 秋收冬藏</p>
            <p>闰余成岁 律吕调阳</p>
        </div>
    </body>
    </html>
    """
    
    test_file = font_dir / "font_test.html"
    try:
        test_file.write_text(test_html, encoding='utf-8')
        print(f"\n测试文件已生成: {test_file}")
        print("请在浏览器中打开测试文件检查字体显示效果")
        print(test_file)
        input("按回车键打开浏览器查看测试文件")
        webbrowser.open(test_file)

    except Exception as e:
        print(f"测试文件生成失败: {str(e)}")

    # 4. 使用建议和解决方案
    print("\n" + "使用建议".center(50, '='))
    if not font_path.exists():
        print("× 楷体字体文件不存在，请检查：")
        print("1. 确认字体文件名是否为 simkai.ttf")
        print(f"2. 确认字体文件是否位于 {font_dir}")
        print("3. 可以从系统字体目录复制楷体字体文件")
    else:
        print("√ 楷体字体文件检查通过")
        print("建议：")
        print("1. 确保程序有字体文件的读取权限")
        print("2. 如遇显示问题，可尝试重新安装字体")
        print("3. 建议定期备份字体文件")

if __name__ == "__main__":
    try:
        verify_font_config()
    except Exception as e:
        print(f"程序执行错误: {str(e)}")
    finally:
        print("\n" + "="*50)
        input("按回车键退出...")

        # 清理测试文件
        test_file = Path(__file__).parent / "font_test.html"
        if test_file.exists():
            try:
                test_file.unlink()  # 删除文件
                print("测试文件已清除。")
            except Exception as e:
                print(f"清除测试文件失败: {str(e)}")
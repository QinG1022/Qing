from pathlib import Path
import logging
from hashlib import sha256
import os

def verify_font_config():
    """楷体字体配置验证工具
    
    功能：
        1. 验证楷体字体文件存在性
        2. 检查字体文件完整性
        3. 提供浏览器兼容性测试
    """
    # 字体路径配置
    font_dir = Path(r"D:\wenjian\bishe\Fonts")
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
        # 基本信息
        size_mb = font_path.stat().st_size / (1024 * 1024)
        print(f"状态: ✔ 文件存在")
        print(f"大小: {size_mb:.2f}MB")
        
        # 权限检查
        readable = os.access(str(font_path), os.R_OK)
        print(f"可读: {'✔' if readable else '✘'}")
        
        # 计算哈希值
        with open(font_path, 'rb') as f:
            digest = sha256(f.read()).hexdigest()
        print(f"指纹: {digest[:16]}...")
        
    except Exception as e:
        print(f"验证错误: {str(e)}")

    # 3. 生成测试文件
    test_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
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
    except Exception as e:
        print(f"测试文件生成失败: {str(e)}")

    # 4. 使用建议
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

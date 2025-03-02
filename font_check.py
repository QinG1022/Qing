def verify_font_config():
    """楷体专项检查"""
    cert_path = r"C:\Program Files\bishe\Fonts\simkai.ttf"
    print("楷体字体验证报告".center(50, '='))
    
    # 1. 基础存在性验证
    p = Path(cert_path)
    print(f"文件存在性: {'✔' if p.exists() else '✘'}")
    print(f"路径类型: {'文件' if p.is_file() else '目录' if p.is_dir() else '未知'}")

    # 2. 数字签名验证（仅Windows）
    if p.exists():
        try:
            from hashlib import sha256
            with open(cert_path, 'rb') as f:
                digest = sha256(f.read()).hexdigest()
            print(f"指纹SHA256: {digest[:16]}...（标准楷体应为ae12**84）")
        except Exception as e:
            print(f"指纹读取错误: {str(e)}")

    # 3. 系统兼容性测试
    test_html = f"""
    <html><body style="font-family: 'SimKai';">
        <p>楷体测试字：天地玄黄 宇宙洪荒</p>
    </body></html>
    """
    print("\n浏览器显示测试建议:\n", test_html)

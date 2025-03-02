import os
import pytest
from modules.image_processor import process_image
from io import BytesIO
from PIL import Image

def test_process_image(tmpdir):
    # 创建一个测试图片
    img = Image.new('RGB', (1000, 1000), color = 'red')
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    save_dir = tmpdir.mkdir("images")
    
    processed_image_path = process_image(img_byte_arr, str(save_dir))
    
    assert os.path.exists(processed_image_path)
    assert processed_image_path.endswith('.jpg')

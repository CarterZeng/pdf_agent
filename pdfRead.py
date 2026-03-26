import fitz  # PyMuPDF
from paddleocr import PaddleOCR
import os

# 初始化 OCR 引擎（第一次运行会自动下载模型）
ocr = PaddleOCR(use_angle_cls=True, lang='ch')

pdf_path = r'C:\Users\leo\PycharmProjects\pdfAgent\手串鉴赏与选购指南.pdf'
doc = fitz.open(pdf_path)

for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2倍缩放提高清晰度
    img_path = f"./imgs/temp_page_{page_num}.png"
    pix.save(img_path)

    # 执行 OCR
    result = ocr.ocr(img_path, cls=True)

    # 提取文本
    for idx in range(len(result)):
        res = result[idx]
        for line in res:
            print(line[1][0])  # 打印识别出的文字

    os.remove(img_path)  # 清理临时文件


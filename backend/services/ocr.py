# import easyocr

# # Load once
# reader = easyocr.Reader(['en'])

# def read_receipt(image_path: str) -> str:
#     result = reader.readtext(image_path)
#     text_lines = []

#     for item in result:
#         # item format: (bbox, text, confidence)
#         text_lines.append(item[1])

#     return "\n".join(text_lines)
import easyocr
from services.image_preprocess import preprocess_receipt_image

reader = easyocr.Reader(['en'])

def read_receipt(image_path: str) -> str:
    processed_image = preprocess_receipt_image(image_path)

    results = reader.readtext(processed_image, detail=0, paragraph=True)

    if not results:
        return ""

    return "\n".join(results)
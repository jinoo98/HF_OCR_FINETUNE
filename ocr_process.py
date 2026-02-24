import os
import io
import json
import time
from PIL import Image as PILImage
from google.cloud import vision
from google.protobuf.json_format import MessageToDict
from dotenv import load_dotenv
import concurrent.futures
load_dotenv()

# 1. 서비스 계정 인증 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS").strip('"')

# 2. Vision API 클라이언트 생성
client = vision.ImageAnnotatorClient()

def process_ocr(image_path):
    print(f"Processing {image_path}...")
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    
    # 문서 텍스트 감지 (손글씨 및 영수증 등에 더 적합)
    response = client.document_text_detection(image=image)
    
    if response.error.message:
        raise Exception(f"{response.error.message}")
    
    full_text = ""
    if response.text_annotations:
        full_text = response.text_annotations[0].description
    
    return full_text

def process_single_image(args):
    img_path, filename = args
    time.sleep(1)
    try:
        extracted_text = process_ocr(img_path)
        data = {
            "image_info": [
                {"matched_text_index": 0, "image_url": f"./images/{filename}"}
            ],
            "text_info": [
                {"text": "OCR:", "tag": "mask"},
                {"text": extracted_text, "tag": "no_mask"}
            ]
        }
        return data
    except Exception as e:
        print(f"Error processing {img_path}: {e}")
        return None

def main():
    image_dir = "dataset/images"
    output_dir = "dataset/jsonl"

    target_images = []
    img_args_list = []

    print(f"Scanning {image_dir} for images...")

    results = []

    if os.path.exists(image_dir):
        for filename in os.listdir(image_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(image_dir, filename)
                target_images.append(img_path)
                img_args_list.append((img_path, filename))
                
    else:
        print(f"Error: Directory {image_dir} not found.")
        return

    print(f"Found {len(target_images)} images. Processing in parallel...")
    
    # 병렬 처리로 변경
    # 구글 비전 API 호출 등 I/O 바운드 작업이므로 ThreadPoolExecutor를 사용합니다.
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        for data in executor.map(process_single_image, img_args_list):
            if data is not None:
                results.append(data)

    # 결과 저장
    output_file = os.path.join(output_dir, "results.jsonl")
    with open(output_file, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"\nDone! Results saved to {output_file}")

if __name__ == "__main__":
    main()

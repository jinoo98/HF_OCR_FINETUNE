import json
import os
import time
import concurrent.futures
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

class ReceiptExtraction(BaseModel):
    store_name: str = Field(description="상호명. OCR 텍스트에 있는 그대로 정확한 부분 문자열이어야 합니다.")
    business_number: str = Field(description="사업자번호. OCR 텍스트에 있는 그대로 정확한 부분 문자열이어야 합니다.")
    date: str = Field(description="날짜. OCR 텍스트에 있는 그대로 정확한 부분 문자열이어야 합니다.")
    total_amount: str = Field(description="합계 금액. OCR 텍스트에 있는 그대로 정확한 부분 문자열이어야 합니다.")

def extract_fields(ocr_text: str) -> ReceiptExtraction:
    system_prompt = (
                        "너는 영수증에서 정확한 데이터를 추출하는 AI야. "
                        "다음 내용은 영수증 이미지 파일에서 텍스트를 추출한 결과야 여기서 정확한 값을 추출해줘"
                        "**매우 중요한 규칙**: 추출한 값은 제공된 OCR 텍스트에 존재하는 **정확한 부분 문자열(Exact Substring)**이어야 한다. "
                        "포맷을 변경하거나 텍스트에 없는 문자를 추가하지 마라. 존재하지 않는 경우 빈 문자열을 반환해라."
                        "반드시 아래의 JSON 키를 사용해서 답변해. 찾을 수 없는 정보는 null로 표시해.\n"
                        "키: store_name (상호명),business_number(사업자 번호), address (주소), date (날짜 YYYY-MM-DD 형식), "
                        "total_amount (총액, 숫자만), card_number (카드번호 마지막 4자리 또는 마스킹된 번호)"
                        "store_name (상호명)의 경우 영수증에서 영어로 표기 되어있다면 그대로 출력해"
                    )
    
    completion = client.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": ocr_text},
        ],
        response_format=ReceiptExtraction,
    )
    
    return completion.choices[0].message.parsed

def process_single_line(args):
    i, line = args
    if not line.strip():
        return None
        
    data = json.loads(line)
    
    clean_data = {
        "image_info": data.get("image_info", []),
        "text_info": data.get("text_info", [])[:2]
    }
    
    import copy
    processed_data = copy.deepcopy(clean_data)
    
    ocr_text = ""
    for info in processed_data["text_info"]:
        if info["tag"] == "no_mask":
            ocr_text = info["text"]
            break
            
    if ocr_text:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                extracted = extract_fields(ocr_text)
                
                # format Q&A
                qa_pairs = [
                    {"text": "상호명은?", "tag": "mask"},
                    {"text": extracted.store_name, "tag": "no_mask"},
                    {"text": "사업자번호는?", "tag": "mask"},
                    {"text": extracted.business_number, "tag": "no_mask"},
                    {"text": "날짜는?", "tag": "mask"},
                    {"text": extracted.date, "tag": "no_mask"},
                    {"text": "합계는?", "tag": "mask"},
                    {"text": extracted.total_amount, "tag": "no_mask"}
                ]
                
                # Append QA pairs to text_info
                processed_data["text_info"].extend(qa_pairs)
                break
            except Exception as e:
                error_msg = str(e)
                if "Rate limit" in error_msg or "429" in error_msg:
                    print(f"⚠️ [{i+1}] 한도 초과! 숨 고르기 중... (재시도 {attempt+1}/{max_retries})")
                    time.sleep(15)  # 🚀 한도 초과 시 15초 동안 넉넉히 대기 후 다시 시도
                    continue # for문 처음으로 돌아가서 다시 시도
                else:
                    print(f"❌ [{i+1}] 알 수 없는 에러: {e}")
                    return {"id": i, "clean_data": clean_data, "error": error_msg}
        else:
            # 3번 다 실패했을 경우
            return {"id": i, "clean_data": clean_data, "error": "Rate limit 에러로 3회 재시도 후 실패"}
            
    return {"id": i, "clean_data": clean_data, "processed_data": processed_data}

def main():
    input_file = "dataset/jsonl/results.jsonl"
    output_without_qa = "dataset/jsonl/results_without_QA.jsonl"
    output_with_qa = "dataset/jsonl/results_with_QA.jsonl"
    
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    data_without_qa = []
    data_with_qa = []
    
    print(f"Processing {len(lines)} lines in parallel...")
    
    args_list = [(i, line) for i, line in enumerate(lines) if line.strip()]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for result in executor.map(process_single_line, args_list):
            if result is None:
                continue
            if "error" in result:
                print(f"❌ ID {result['id']+1} failed: {result['error']}")
                # 에러가 났더라도 원본 데이터는 보존 (옵션)
                data_without_qa.append(result["clean_data"])
                data_with_qa.append(result["clean_data"]) # QA 없이 원본 유지
            else:
                data_without_qa.append(result["clean_data"])
                data_with_qa.append(result["processed_data"])

    # Save without QA
    with open(output_without_qa, "w", encoding="utf-8") as f:
        for item in data_without_qa:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    # Save with QA
    with open(output_with_qa, "w", encoding="utf-8") as f:
        for item in data_with_qa:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"Update complete!\nSaved without QA: {output_without_qa}\nSaved with QA: {output_with_qa}")

if __name__ == "__main__":
    main()

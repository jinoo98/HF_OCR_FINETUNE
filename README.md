# HuggingFace OCR Finetuning Example

이 프로젝트는 영수증과 같은 이미지 데이터에서 텍스트를 추출하고, 필요한 항목을 파싱하여 파인튜닝용 데이터를 구축하기 위한 파이프라인입니다.

## 주요 파이썬 파일 설명

- **`ocr_process.py`**: 
  - `dataset/images/` 폴더 내의 이미지들을 읽어 Google Vision API를 통해 전체 OCR 텍스트를 추출합니다. 
  - 추출된 결과를 `dataset/jsonl/results.jsonl` 파일로 저장합니다.
- **`update_jsonl.py`**: 
  - `results.jsonl` 파일을 읽어들여 OpenAI API(gpt-4o-mini)를 사용해 상호명, 사업자번호, 날짜, 합계 금액을 정확한 부분 문자열(Exact Substring)로 추출합니다.
  - QA 세트가 추가된 결과를 `dataset/jsonl/results_with_QA.jsonl`로 저장합니다. 
  - Rate limit (429) 에러 발생 시 자동으로 대기 후 재시도하는 로직이 적용되어 있습니다.
- **`split_dataset.py`**: 
  - 대량의 데이터를 수동으로 검수하기 쉽게 여러 파트로 분할(예: 827개의 데이터를 200, 200, 200, 227 단위로 분할)합니다.
  - 분할된 결과물은 `example/part1` ~ `example/part4` 디렉토리에 원본과 동일한 구조(`images/`, `jsonl/`)로 저장됩니다.
- **`simple_server.py`**: 
  - 추출 및 포맷팅이 완료된 데이터를 웹 브라우저 상에서 한눈에 보며 검증 및 수정할 수 있는 로컬 웹 뷰어를 실행합니다 (`http://localhost:8000`).

## 데이터 분할 및 뷰어 검수 워크플로우

대량의 데이터(827개 등)를 한 번에 검수하기 어려울 때 `split_dataset.py`를 사용하여 4분할 한 뒤 검수하는 과정입니다.

1. **데이터 분할**: `python split_dataset.py`를 실행하여 데이터를 `example/part1` ~ `part4`로 나눕니다.
2. **분할된 데이터 세팅**: `example/partX/` 경로에 있는 `images`와 `jsonl` 폴더를 루트 디렉토리의 `dataset/` 폴더 안으로 복사하여 덮어씁니다. (예: `example/part1` 검수 시 `part1`의 데이터로 교체)
3. **로컬 서버 실행**: `python simple_server.py` 명령어를 실행하고 브라우저에서 `http://localhost:8000`에 접속합니다.
4. **검수 및 수정**: 웹 뷰어에서 잘못 인식된 텍스트를 직접 수정하고 Confirm(저장) 버튼을 누릅니다. 저장된 내용은 즉시 `dataset/jsonl/results_with_QA.jsonl`에 반영됩니다.
5. 검수가 끝나면 다음 파트(`part2`)를 동일한 방식으로 `dataset/` 폴더에 넣고 검수를 반복합니다.

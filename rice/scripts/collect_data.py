import os
import sys
import time
import json
import requests
from datetime import datetime

def fetch_and_process_auction_data(target_date=None):
    # 1. Secret Key 환경변수(ricekey) 불러오기
    service_key = os.environ.get("ricekey")
    if not service_key:
        raise ValueError("환경변수 'ricekey'가 설정되지 않았습니다.")

    # 2. 수집 대상 날짜 결정 (인자가 전달되면 해당 날짜, 없으면 오늘 날짜)
    if not target_date:
        today_str = datetime.now().strftime("%Y-%m-%d")
    else:
        today_str = target_date
    
    # 3. API 요청 주소 및 파라미터 설정
    base_url = "https://apis.data.go.kr/B552845/katRealTime2/trades2"
    params = {
        "serviceKey": service_key,
        "cond[trd_clcln_ymd::EQ]": today_str,
        "returnType": "JSON",
        "numOfRows": 100,
        "pageNo": 1
    }

    print(f"[{today_str}] API 데이터 수집 요청 시작...")

    # 4. 요청 및 타임아웃(10초) / 소요시간(deadline_ms) 측정
    start_time = time.time()
    try:
        response = requests.get(base_url, params=params, timeout=10.0)
        end_time = time.time()
        deadline_ms = int((end_time - start_time) * 1000)

        response.raise_for_status()
        data = response.json()

        # 5. 표준 Key 규격 매핑 (status, stored_value, record_date, deadline_ms, source_url)
        result_code = data.get("header", {}).get("resultCode", str(response.status_code))
        items = data.get("body", {}).get("items", [])

        mapped_data_list = []
        for item in items:
            mapped_data_list.append({
                "status": result_code,
                "stored_value": item.get("scsbd_prc"),
                "record_date": item.get("scsbd_dt"),
                "deadline_ms": deadline_ms,
                "source_url": base_url
            })

        print(f"총 {len(mapped_data_list)}건 수집 완료 (소요시간: {deadline_ms}ms)")

    except requests.exceptions.Timeout:
        end_time = time.time()
        deadline_ms = int((end_time - start_time) * 1000)
        print(f"[실패] 10000ms(10초) 타임아웃 초과 (소요시간: {deadline_ms}ms)")
        mapped_data_list = [{
            "status": "TIMEOUT_ERROR",
            "stored_value": None,
            "record_date": today_str,
            "deadline_ms": deadline_ms,
            "source_url": base_url,
            "error": "Request timed out after 10000ms"
        }]

    except Exception as e:
        end_time = time.time()
        deadline_ms = int((end_time - start_time) * 1000)
        print(f"[실패] 에러 발생: {e}")
        mapped_data_list = [{
            "status": "ERROR",
            "stored_value": None,
            "record_date": today_str,
            "deadline_ms": deadline_ms,
            "source_url": base_url,
            "error": str(e)
        }]

    # 6. 결과 파일 저장 (`rice/data/auction_YYYY-MM-DD.json`)
    script_dir = os.path.dirname(os.path.abspath(__file__)) # rice/scripts/
    rice_dir = os.path.dirname(script_dir)                 # rice/
    data_dir = os.path.join(rice_dir, "data")              # rice/data/

    os.makedirs(data_dir, exist_ok=True)
    filename = os.path.join(data_dir, f"auction_{today_str}.json")
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(mapped_data_list, f, ensure_ascii=False, indent=2)
        
    print(f"결과 파일 저장 완료: {filename}")

if __name__ == "__main__":
    # 커맨드라인 인자로 날짜가 들어왔는지 확인 (예: python collect_data.py 2026-09-05)
    req_date = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_and_process_auction_data(req_date)

import os
import sys
import time
import json
import requests
from urllib.parse import unquote
from datetime import datetime

def fetch_and_process_auction_data(target_date=None):
    service_key = os.environ.get("ricekey")
    if not service_key:
        raise ValueError("환경변수 'ricekey'가 설정되지 않았습니다.")

    # 공공데이터포털 서비스키가 이미 URL-인코딩된 형태(%2F, %3D 등 포함)로 저장돼 있을 수 있음.
    # requests는 params로 넘긴 값을 자동으로 다시 인코딩하므로, 미리 디코딩해서
    # 이중 인코딩(예: %2F -> %252F)으로 인한 403 Forbidden을 방지한다.
    service_key = unquote(service_key)

    # 인자로 넘어온 날짜가 있으면 해당 날짜, 없으면 오늘 날짜
    if not target_date:
        today_str = datetime.now().strftime("%Y-%m-%d")
    else:
        today_str = target_date
    
    base_url = "https://apis.data.go.kr/B552845/katRealTime2/trades2"
    params = {
        "serviceKey": service_key,
        "cond[trd_clcln_ymd::EQ]": today_str,
        "returnType": "JSON",
        "numOfRows": 100,
        "pageNo": 1
    }

    print(f"[{today_str}] API 데이터 수집 요청 시작...")

    start_time = time.time()
    try:
        response = requests.get(base_url, params=params, timeout=10.0)
        end_time = time.time()
        deadline_ms = int((end_time - start_time) * 1000)

        response.raise_for_status()
        data = response.json()

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

    # 저장 경로 설정: rice/data/auction_YYYY-MM-DD.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rice_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(rice_dir, "data")

    os.makedirs(data_dir, exist_ok=True)
    filename = os.path.join(data_dir, f"auction_{today_str}.json")
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(mapped_data_list, f, ensure_ascii=False, indent=2)
        
    print(f"결과 파일 저장 완료: {filename}")

if __name__ == "__main__":
    # 커맨드라인 인자로 날짜가 넘어왔는지 체크
    req_date = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_and_process_auction_data(req_date)

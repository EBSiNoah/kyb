import os
import sys
import time
import json
import requests
from urllib.parse import unquote
from datetime import datetime

# 한국수출입은행 결과 코드(result) 의미
# 1: 성공(정상 조회)  2: DATA코드 오류  3: 인증코드 오류(유효하지 않은 키)  4: 일일제한횟수 초과
RESULT_CODE_MEANING = {
    1: "성공",
    2: "DATA코드 오류",
    3: "인증코드 오류 (authkey 확인 필요)",
    4: "일일 제한횟수 초과",
}


def fetch_and_process_exchange_data(target_date=None):
    auth_key = os.environ.get("mesokey")
    if not auth_key:
        raise ValueError("환경변수 'mesokey'가 설정되지 않았습니다.")

    # 혹시 이미 URL-인코딩된 값이 시크릿에 저장돼 있어도 안전하게 원복(대부분의 경우 영향 없음)
    auth_key = unquote(auth_key)

    # 인자로 넘어온 날짜가 있으면 해당 날짜, 없으면 오늘 날짜 (YYYY-MM-DD 형식으로 통일해서 사용/저장)
    if not target_date:
        today_str = datetime.now().strftime("%Y-%m-%d")
    else:
        # target_date에 시간 등이 섞여 들어와도 앞의 YYYY-MM-DD만 사용
        today_str = target_date.strip()[:10]

    # 수출입은행 API는 searchdate를 yyyymmdd(하이픈 없음) 형식으로 요구함
    search_date_param = today_str.replace("-", "")

    base_url = "https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON"
    params = {
        "authkey": auth_key,
        "searchdate": search_date_param,
        "data": "AP01",
    }
    # 일부 공공기관 API 게이트웨이는 브라우저가 아닌 User-Agent(예: python-requests)를
    # 봇으로 간주해 연결을 끊어버리는 경우가 있어, 브라우저처럼 보이는 값을 명시적으로 지정한다.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    print(f"[{today_str}] 환율 API 데이터 수집 요청 시작...")

    start_time = time.time()
    max_attempts = 3
    last_exception = None
    response = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=10.0)
            last_exception = None
            break
        except requests.exceptions.RequestException as e:
            last_exception = e
            print(f"[재시도 {attempt}/{max_attempts}] 요청 실패: {type(e).__name__}: {e}")
            if attempt < max_attempts:
                time.sleep(2 * attempt)  # 2초, 4초 대기 후 재시도

    end_time = time.time()
    delay_ms = int((end_time - start_time) * 1000)

    try:
        if last_exception is not None:
            # 재시도까지 모두 실패한 경우 (예: Connection aborted 등 네트워크 레벨 오류)
            raise last_exception

        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list) or len(data) == 0:
            # 휴일/주말 등으로 그날 고시 환율 자체가 없는 정상적인 빈 응답
            mapped_data_list = [{
                "status": None,
                "stored_value": None,
                "source_time": today_str,
                "delay_ms": delay_ms,
                "source_url": base_url,
                "note": "해당 날짜의 고시 환율 데이터 없음 (휴일/주말일 수 있음)"
            }]
            print(f"[{today_str}] 응답 없음 (휴일/주말 가능성)")
        else:
            first_result = data[0].get("result")
            if first_result != 1:
                # 인증키 오류(3), 일일 제한 초과(4) 등 API 레벨 오류
                meaning = RESULT_CODE_MEANING.get(first_result, "알 수 없는 오류 코드")
                mapped_data_list = [{
                    "status": first_result,
                    "stored_value": None,
                    "source_time": today_str,
                    "delay_ms": delay_ms,
                    "source_url": base_url,
                    "note": f"API 오류 (result={first_result}: {meaning})"
                }]
                print(f"[실패] API 오류 result={first_result} ({meaning})")
            else:
                # 'JPY(100)'처럼 'JPY'로 시작하는 통화만 사용
                jpy_items = [
                    item for item in data
                    if str(item.get("cur_unit", "")).startswith("JPY")
                ]

                if jpy_items:
                    mapped_data_list = []
                    for item in jpy_items:
                        mapped_data_list.append({
                            "status": item.get("result"),
                            "stored_value": item.get("ttb"),
                            "source_time": today_str,
                            "delay_ms": delay_ms,
                            "source_url": base_url
                        })
                    print(f"총 {len(mapped_data_list)}건 수집 완료 (소요시간: {delay_ms}ms)")
                else:
                    mapped_data_list = [{
                        "status": first_result,
                        "stored_value": None,
                        "source_time": today_str,
                        "delay_ms": delay_ms,
                        "source_url": base_url,
                        "note": f"응답 {len(data)}건 중 JPY 통화 데이터를 찾지 못함"
                    }]
                    print(f"[{today_str}] JPY 데이터 없음 (응답 {len(data)}건)")

    except Exception as e:
        end_time = time.time()
        delay_ms = int((end_time - start_time) * 1000)
        print(f"[실패] 에러 발생: {e}")
        mapped_data_list = [{
            "status": "ERROR",
            "stored_value": None,
            "source_time": today_str,
            "delay_ms": delay_ms,
            "source_url": base_url,
            "error": str(e)
        }]

    # 저장 경로 설정: rice/data/auction_YYYY-MM-DD.json (기존 구조/파일명 그대로 유지 → index.html 수정 불필요)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rice_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(rice_dir, "data")

    os.makedirs(data_dir, exist_ok=True)
    filename = os.path.join(data_dir, f"auction_{today_str}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(mapped_data_list, f, ensure_ascii=False, indent=2)

    print(f"결과 파일 저장 완료: {filename}")


if __name__ == "__main__":
    req_date = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_and_process_exchange_data(req_date)

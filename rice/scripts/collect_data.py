from datetime import datetime
import json
import os
import requests

# 1. 환경변수에서 ricekey 읽기
SERVICE_KEY = os.environ.get("ricekey")

if not SERVICE_KEY:
    raise ValueError(
        "ricekey가 설정되지 않았습니다. GitHub Secrets를 확인하세요."
    )


# 2. API 데이터 수집 함수
def fetch_daily_auction_data(date_str):
    url = "https://apis.data.go.kr/B552845/katRealTime2/trades2"
    params = {
        "serviceKey": SERVICE_KEY,
        "returnType": "JSON",
        "cond[trd_clcln_ymd::EQ]": date_str,  # YYYY-MM-DD
        "pageNo": "1",
        "numOfRows": "1000",  # 필요시 수량 조정
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        # 데이터 존재 여부 확인
        items = (
            data.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )
        if isinstance(items, dict):  # 단건일 경우 리스트로 정규화
            items = [items]
        return items
    except Exception as e:
        print(f"[{date_str}] API 호출 중 오류 발생: {e}")
        return []


# 3. 데이터 가공 (품목별 집계)
def process_data(items):
    summary = {}

    for item in items:
        name = item.get("corp_gds_item_nm")  # 품목명
        price_str = item.get("scsbd_prc")  # 낙찰가
        qty_str = item.get("qty")  # 수량

        if not name or not price_str:
            continue

        try:
            price = float(price_str)
            qty = float(qty_str) if qty_str else 0.0
        except ValueError:
            continue

        if name not in summary:
            summary[name] = {"prices": [], "total_qty": 0.0}

        summary[name]["prices"].append(price)
        summary[name]["total_qty"] += qty

    # 평균가/최고가/최저가 계산
    result = {}
    for name, info in summary.items():
        prices = info["prices"]
        if not prices:
            continue

        result[name] = {
            "avg_price": round(sum(prices) / len(prices)),
            "min_price": int(min(prices)),
            "max_price": int(max(prices)),
            "total_qty": round(info["total_qty"], 1),
        }

    return result


def main():
    # rice/data 디렉토리 생성
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    history_file_path = os.path.join(data_dir, "history.json")

    # 기존 history.json 로드
    history_data = {}
    if os.path.exists(history_file_path):
        try:
            with open(history_file_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        except json.JSONDecodeError:
            history_data = {}

    # 오늘 날짜 (YYYY-MM-DD)
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"[{today_str}] 경매 데이터 수집 시작...")

    raw_items = fetch_daily_auction_data(today_str)

    if raw_items:
        processed_summary = process_data(raw_items)
        history_data[today_str] = processed_summary
        print(
            f"[{today_str}] 총 {len(processed_summary)}개 품목 데이터 집계 완료."
        )
    else:
        print(
            f"[{today_str}] 수집된 데이터가 없습니다. (휴장일이거나 정산 이전일 수 있음)"
        )

    # JSON 파일 업데이트 저장
    with open(history_file_path, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

    print("data/history.json 저장 완료.")


if __name__ == "__main__":
    main()

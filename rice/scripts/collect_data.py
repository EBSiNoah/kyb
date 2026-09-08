from datetime import datetime
import json
import os
import zoneinfo
import requests

SERVICE_KEY = os.environ.get("ricekey")
KST = zoneinfo.ZoneInfo("Asia/Seoul")

DATA_DIR = "data"
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
STATUS_FILE = os.path.join(DATA_DIR, "status.json")


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_status(status, error_code, last_observed_at=None):
    current_status = load_json(
        STATUS_FILE,
        {"status": "fresh", "error_code": "none", "last_observed_at": None},
    )
    current_status["status"] = status
    current_status["error_code"] = error_code
    if last_observed_at:
        current_status["last_observed_at"] = last_observed_at
    save_json(STATUS_FILE, current_status)


def fetch_live_data():
    if not SERVICE_KEY:
        update_status("stale", "auth_error")
        return None, "auth_error"

    now_kst = datetime.now(KST)
    today_str = now_kst.strftime("%Y-%m-%d")

    url = "https://apis.data.go.kr/B552845/katRealTime2/trades2"
    params = {
        "serviceKey": SERVICE_KEY,
        "returnType": "JSON",
        "cond[trd_clcln_ymd::EQ]": today_str,
        "numOfRows": "500",
    }

    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 401:
            return None, "auth_error"
        elif res.status_code == 429:
            return None, "rate_limit"
        elif res.status_code != 200:
            return None, "offline"

        data = res.json()
        items = (
            data.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )
        if isinstance(items, dict):
            items = [items]

        # '배추' 단일 품목 추출 및 정규화
        prices = []
        for it in items:
            if it.get("corp_gds_item_nm") == "배추" and it.get("scsbd_prc"):
                try:
                    prices.append(float(it["scsbd_prc"]))
                except ValueError:
                    pass

        if not prices:
            return None, "schema_break"

        avg_price = round(sum(prices) / len(prices))
        normalized_reading = {
            "signal_id": "T04-LIVE-CABBAGE",
            "source_url": url,
            "source_observed_at": now_kst.isoformat(),
            "normalized_value": avg_price,
            "unit": "원",
            "record_date": today_str,
        }
        return normalized_reading, None

    except requests.exceptions.Timeout:
        return None, "timeout"
    except requests.exceptions.RequestException:
        return None, "offline"
    except Exception:
        return None, "schema_break"


def main():
    reading, error = fetch_live_data()

    history = load_json(HISTORY_FILE, {})

    if error:
        # 장애 시 기존 저장값 유지, status만 stale로 변경
        update_status("stale", error)
        print(f"[실패] 외부 데이터 수집 실패: {error}. 기존 데이터 보존됨.")
    else:
        # 동일 record_date 원자적 갱신 / 신규 날짜 생성
        record_date = reading["record_date"]
        history[record_date] = reading
        save_json(HISTORY_FILE, history)

        update_status("fresh", "none", reading["source_observed_at"])
        print(
            f"[성공] {record_date} 배추 시세 정규화 저장 완료: {reading['normalized_value']}원"
        )


if __name__ == "__main__":
    main()

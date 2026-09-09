from datetime import datetime
import json
import os
import zoneinfo
import requests

SERVICE_KEY = os.environ.get("ricekey")
KST = zoneinfo.ZoneInfo("Asia/Seoul")

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
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


def main():
    if not SERVICE_KEY:
        update_status("stale", "auth_error")
        print("[오류] API 서비스 키(ricekey)가 설정되지 않았습니다.")
        return

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
            update_status("stale", "auth_error")
            return
        elif res.status_code == 429:
            update_status("stale", "rate_limit")
            return
        elif res.status_code != 200:
            update_status("stale", "offline")
            return

        data = res.json()
        items = (
            data.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )
        if isinstance(items, dict):
            items = [items]

        prices = [
            float(it["scsbd_prc"])
            for it in items
            if it.get("corp_gds_item_nm") == "배추" and it.get("scsbd_prc")
        ]

        if not prices:
            update_status("stale", "schema_break")
            return

        avg_price = round(sum(prices) / len(prices))
        obs_time = now_kst.isoformat()

        # history.json 원자적 갱신
        history = load_json(HISTORY_FILE, {})
        history[today_str] = {
            "signal_id": "T04-LIVE-CABBAGE",
            "source_url": url,
            "source_observed_at": obs_time,
            "normalized_value": avg_price,
            "unit": "원",
            "record_date": today_str,
        }
        save_json(HISTORY_FILE, history)
        update_status("fresh", "none", obs_time)
        print(f"[성공] {today_str} 배추 평균 시세: {avg_price}원")

    except requests.exceptions.Timeout:
        update_status("stale", "timeout")
    except requests.exceptions.RequestException:
        update_status("stale", "offline")
    except Exception:
        update_status("stale", "schema_break")


if __name__ == "__main__":
    main()

"""네이버 검색광고 API로 연관 키워드 자동 수집

네이버 검색광고 계정 필요 (무료, 개인 가입 가능):
https://searchad.naver.com → 가입 → 도구 → API 사용 신청

발급받을 것:
- NAVER_AD_API_LICENSE (API 인증키)
- NAVER_AD_API_SECRET (비밀키)
- NAVER_AD_CUSTOMER_ID (고객 ID)
"""

import base64
import csv
import hashlib
import hmac
import time
from datetime import date
from pathlib import Path

import requests

KEYWORDS_PATH = Path(__file__).parent.parent / "keywords" / "health_keywords.csv"
API_BASE_URL = "https://api.searchad.naver.com"

# 시드 키워드: 이 키워드들의 연관 키워드를 수집
SEED_KEYWORDS = [
    "다이어트식단",
    "건강음식",
    "혈당관리",
    "중년다이어트",
    "체중감량",
    "장건강",
    "관절건강",
    "고혈압식단",
    "당뇨예방",
    "갱년기건강",
]


def _generate_signature(timestamp: str, method: str, uri: str, secret: str) -> str:
    """네이버 검색광고 API 서명 생성"""
    message = f"{timestamp}.{method}.{uri}"
    sign = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(sign.digest()).decode()


def _get_headers(api_license: str, api_secret: str, customer_id: str, method: str, uri: str) -> dict:
    """API 요청 헤더 생성"""
    timestamp = str(int(time.time() * 1000))
    signature = _generate_signature(timestamp, method, uri, api_secret)
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": api_license,
        "X-Customer": str(customer_id),
        "X-Signature": signature,
    }


def fetch_related_keywords(
    seed_keyword: str,
    api_license: str,
    api_secret: str,
    customer_id: str,
) -> list:
    """시드 키워드의 연관 키워드 + 월간 검색량 조회"""
    uri = "/keywordstool"
    method = "GET"
    headers = _get_headers(api_license, api_secret, customer_id, method, uri)

    params = {
        "hintKeywords": seed_keyword,
        "showDetail": "1",
    }

    resp = requests.get(
        f"{API_BASE_URL}{uri}",
        headers=headers,
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    keywords = []
    for item in data.get("keywordList", []):
        monthly_pc = item.get("monthlyPcQcCnt", 0)
        monthly_mobile = item.get("monthlyMobileQcCnt", 0)

        # "< 10" 같은 문자열 처리
        if isinstance(monthly_pc, str):
            monthly_pc = 5
        if isinstance(monthly_mobile, str):
            monthly_mobile = 5

        total_volume = monthly_pc + monthly_mobile

        keywords.append({
            "keyword": item["relKeyword"],
            "volume": total_volume,
            "competition": item.get("compIdx", ""),
        })

    return keywords


# 건강/다이어트와 무관한 키워드 제외
EXCLUDE_WORDS = [
    "헬스장", "필라테스", "크로스핏", "PT", "맛집", "호텔", "숙박",
    "웨딩", "예신", "신부", "결혼", "브랜드", "가격", "할인", "쿠폰",
    "배달", "배송", "정기배송", "주문", "구매", "사이트", "앱",
    "리프팅", "피부과", "성형", "시술", "스킨케어", "화장품",
    "인테리어", "부동산", "발렌타인", "초콜릿추천", "선물",
]


def filter_good_keywords(keywords: list[dict], min_volume: int = 100, max_volume: int = 50000) -> list:
    """블로그에 적합한 키워드 필터링"""
    filtered = []
    for kw in keywords:
        if min_volume <= kw["volume"] <= max_volume:
            if len(kw["keyword"].split()) >= 2 or len(kw["keyword"]) >= 5:
                # 건강과 무관한 키워드 제외
                if not any(ex in kw["keyword"] for ex in EXCLUDE_WORDS):
                    filtered.append(kw)

    filtered.sort(key=lambda x: x["volume"], reverse=True)
    return filtered


def load_existing_keywords() -> set:
    """기존 CSV에 있는 키워드 목록 로드"""
    if not KEYWORDS_PATH.exists():
        return set()

    with open(KEYWORDS_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["keyword"] for row in reader}


def append_new_keywords(new_keywords: list[dict]):
    """새 키워드를 CSV에 추가"""
    existing = load_existing_keywords()
    added = 0

    with open(KEYWORDS_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for kw in new_keywords:
            if kw["keyword"] not in existing:
                writer.writerow([kw["keyword"], "건강", "N", ""])
                existing.add(kw["keyword"])
                added += 1

    print(f"[키워드 수집] 신규 {added}개 추가 (총 {len(existing)}개)")
    return added


def collect_keywords(api_license: str, api_secret: str, customer_id: str):
    """메인: 시드 키워드별 연관 키워드 수집"""
    all_keywords = []

    for seed in SEED_KEYWORDS:
        print(f"[수집] '{seed}' 연관 키워드 조회 중...")
        try:
            related = fetch_related_keywords(seed, api_license, api_secret, customer_id)
            good = filter_good_keywords(related)
            all_keywords.extend(good)
            print(f"  → {len(good)}개 적합 키워드 발견")
        except Exception as e:
            print(f"  → 오류: {e}")
        time.sleep(1)  # rate limit 방지

    # 중복 제거
    seen = set()
    unique = []
    for kw in all_keywords:
        if kw["keyword"] not in seen:
            seen.add(kw["keyword"])
            unique.append(kw)

    added = append_new_keywords(unique)
    print(f"\n[완료] 총 {len(unique)}개 수집, {added}개 신규 추가")


if __name__ == "__main__":
    import os

    collect_keywords(
        api_license=os.environ["NAVER_AD_API_LICENSE"],
        api_secret=os.environ["NAVER_AD_API_SECRET"],
        customer_id=os.environ["NAVER_AD_CUSTOMER_ID"],
    )

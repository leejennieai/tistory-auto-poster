import csv
import random
from datetime import date
from pathlib import Path

KEYWORDS_PATH = Path(__file__).parent.parent / "keywords" / "health_keywords.csv"


def get_unused_keyword():
    """미사용 키워드 중 랜덤으로 하나 선택"""
    rows = []
    with open(KEYWORDS_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    unused = [r for r in rows if r["used"] == "N"]
    if not unused:
        raise RuntimeError("사용 가능한 키워드가 없습니다. keywords CSV를 보충하세요.")

    return random.choice(unused)


def mark_keyword_used(keyword: str):
    """키워드를 사용 완료로 표시"""
    rows = []
    with open(KEYWORDS_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        if row["keyword"] == keyword:
            row["used"] = "Y"
            row["used_date"] = str(date.today())
            break

    with open(KEYWORDS_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["keyword", "category", "used", "used_date"])
        writer.writeheader()
        writer.writerows(rows)

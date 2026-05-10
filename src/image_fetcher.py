import requests


PEXELS_BASE_URL = "https://api.pexels.com/v1/search"


def fetch_images(keyword: str, api_key: str, count: int = 3) -> list[dict]:
    """Pexels API로 키워드 관련 이미지 검색"""
    headers = {"Authorization": api_key}
    params = {
        "query": keyword,
        "per_page": count,
        "locale": "ko-KR",
    }

    resp = requests.get(PEXELS_BASE_URL, headers=headers, params=params, timeout=10)
    resp.raise_for_status()

    data = resp.json()
    images = []
    for photo in data.get("photos", []):
        original = photo["src"]["original"]
        images.append({
            "url": original + "?auto=compress&cs=tinysrgb&w=400",
            "alt": photo.get("alt", keyword),
            "photographer": photo["photographer"],
        })

    return images


def insert_images_into_content(content: str, images: list[dict], keyword: str) -> str:
    """본문 HTML에 이미지 삽입 (첫 이미지는 맨 앞 = 대표이미지)"""
    if not images:
        return content

    # 첫 번째 이미지: 본문 맨 앞 (대표이미지용)
    result = _make_img_html(images[0], keyword) + "\n" + content

    # 나머지 이미지: H2 소제목 뒤에 삽입
    if len(images) > 1:
        parts = result.split("</h2>")
        if len(parts) > 1:
            rebuilt = []
            img_idx = 1
            for i, part in enumerate(parts):
                rebuilt.append(part)
                if i < len(parts) - 1:
                    rebuilt.append("</h2>")
                    if img_idx < len(images) and i > 0:
                        rebuilt.append(_make_img_html(images[img_idx], keyword))
                        img_idx += 1
            result = "".join(rebuilt)

    return result


def _make_img_html(img: dict, keyword: str) -> str:
    """이미지 HTML 태그 생성 (400px, 중앙정렬)"""
    return (
        f'\n<div style="text-align:center;margin:20px 0;">'
        f'<img src="{img["url"]}" alt="{keyword}" '
        f'width="400" style="display:inline-block;border-radius:6px;" />'
        f'</div>\n'
    )

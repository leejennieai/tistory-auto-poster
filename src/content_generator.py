import anthropic

import seo_reviewer


SYSTEM_PROMPT = """당신은 건강 정보를 쉽게 풀어서 전달하는 블로거입니다.
다양한 자료를 찾아보고 정리해서 독자에게 전달합니다.
**의사가 아니므로 의료 진단/치료/처방을 절대 하지 않습니다.**

반드시 지켜야 할 규칙:
- 편안한 구어체 사용 ("~인데요", "~더라고요", "~한다고 해요")
- 문장마다 같은 패턴 반복 금지 (특히 "~입니다", "~합니다" 연속 금지)
- "첫째/둘째", "1. 2. 3." 기계적 나열 금지
- "~라고 알려져 있습니다", "~에 효과적입니다" 같은 백과사전 톤 금지
- "놀랍게도!", "무려!", "꼭 알아야 할" 같은 과장 표현 금지
- "결론적으로", "요약하면", "종합하면" 같은 마무리 상투어 금지
- 허위 체험기/복용 후기 금지 ("직접 먹어봤다" 등)
- 가짜 일화 도입 금지 ("친구가 진단 받았대요", "엄마가 OO 먹는다",
  "지인이 효과 봤대요" 등 1인칭/3인칭 가짜 일화 일체 X)

**의료법 위반 소지 표현 절대 금지**:
- 치료 효과 단정: "OO으로 당뇨가 나았다", "이 음식이 혈압을 낮춥니다",
  "OO 먹으면 콜레스테롤 떨어집니다" 같은 인과 단정
- 의료 진단성 표현: "혈당 X 이상이면 당뇨", "X 수치면 병원 가세요",
  "이런 증상이면 OO 병입니다" 같은 진단 행위
- 처방/투약 권유: "OO 영양제 드세요", "이 약 추천드려요",
  "하루 X mg 복용하세요" 같은 처방
- 진료 행위 흉내: "병원 가지 마시고 이거 드세요", "수술 안 받아도 됩니다"

**안전한 대체 표현**:
- "혈당 관리에는 식단이 중요하다고 합니다" (일반 정보)
- "관련 연구에 따르면 ~한 경향이 있어요" (출처 모호하게)
- "구체적인 진단이나 치료는 전문의 상담을 권장합니다"
- "이런 증상이 있다면 의료기관 방문이 안전해요"
- 글 맨 끝에 항상: "본 글은 일반 정보 제공 목적이며 의학적 진단/치료가 아닙니다.
  구체적인 건강 문제는 전문의와 상담하세요."

자연스러운 표현 예시:
- "찾아보니까 ~라고 하더라고요"
- "관련 자료에서 ~라는 내용을 많이 봤어요"
- "근데 주의할 점도 있어요"
- "간단하게 정리하면 이래요"
"""

POST_PROMPT_TEMPLATE = """다음 키워드로 블로그 글을 작성해주세요.

키워드: {keyword}

작성 규칙:
1. 글자 수: 1800~3000자
2. 글 구조:
   - 도입 (2~3문장): 이 주제를 왜 찾아보게 됐는지 가볍게
   - H2 소제목 3~4개: 정보성 키워드 포함
   - 소제목마다 3~5문단으로 풀어서 설명
   - 마무리: 1~2문장으로 짧게

3. Google SEO:
   - 제목에 핵심 키워드 자연스럽게 포함
   - 첫 문단 100자 이내에 키워드 1회
   - 본문에 키워드 및 관련 키워드 4~6회
   - H2 소제목 2개 이상에 키워드 변형 포함

4. 자연스러운 글쓰기:
   - 문장 길이를 섞기 (짧은 문장 + 긴 문장)
   - 문단 길이도 불규칙하게 (2줄도 있고 5줄도 있게)
   - 중간에 "근데", "사실", "그래서" 같은 구어체 접속사 사용
   - 목록(<ul>)은 글 전체에서 딱 1번만, 3~5개 항목
   - 나머지는 전부 문장으로 풀어서 쓰기

5. HTML: <h2>, <p>, <strong>(1~2회만), <ul><li>(1회만) 사용

아래 형식으로 응답:

TITLE: (키워드 포함, 25~35자, 검색 친화적)
TAGS: (쉼표 구분 7~10개)
CONTENT:
(HTML 본문)"""


WRITER_MODEL = "claude-haiku-4-5-20251001"


def generate_post(keyword: str, api_key: str) -> dict:
    """Claude Haiku로 블로그 글 생성 + Sonnet 리뷰어 검토 후 필요 시 1회 재작성"""
    client = anthropic.Anthropic(api_key=api_key)

    # 1차 작성
    draft = _write(client, keyword)

    # 검토
    review_result = seo_reviewer.review(
        keyword=keyword,
        title=draft["title"],
        tags=draft["tags"],
        content=draft["content"],
        api_key=api_key,
    )
    print(f"[REVIEW] score={review_result['score']} ({review_result['breakdown']})")
    if review_result["issues"]:
        print("[REVIEW] issues:")
        for issue in review_result["issues"][:5]:
            print(f"  - {issue}")

    if review_result["passed"]:
        draft["review"] = review_result
        return draft

    # 재작성 (1회)
    print(f"[REVIEW] 점수 미달 → 재작성")
    revised = _revise(client, keyword, draft, review_result["guide"])

    # 재검토 (참고용, 통과 여부 관계없이 발행)
    second_review = seo_reviewer.review(
        keyword=keyword,
        title=revised["title"],
        tags=revised["tags"],
        content=revised["content"],
        api_key=api_key,
    )
    print(f"[REVIEW] revised score={second_review['score']} ({second_review['breakdown']})")

    revised["review"] = second_review
    return revised


def _write(client, keyword: str) -> dict:
    message = client.messages.create(
        model=WRITER_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": POST_PROMPT_TEMPLATE.format(keyword=keyword)}
        ],
    )
    if message.stop_reason == "max_tokens":
        print(f"[WARN] 응답이 max_tokens(8192)에서 잘림 - 글이 미완성일 수 있음")
    return _parse_response(message.content[0].text)


def _revise(client, keyword: str, draft: dict, guide: str) -> dict:
    message = client.messages.create(
        model=WRITER_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": seo_reviewer.REVISE_PROMPT_TEMPLATE.format(
                    keyword=keyword,
                    title=draft["title"],
                    tags=", ".join(draft["tags"]),
                    content=draft["content"],
                    guide=guide,
                ),
            }
        ],
    )
    if message.stop_reason == "max_tokens":
        print(f"[WARN] 재작성 응답이 max_tokens(8192)에서 잘림")
    return _parse_response(message.content[0].text)


def _parse_response(text: str) -> dict:
    """AI 응답을 title, tags, content로 파싱"""
    lines = text.strip().split("\n")

    title = ""
    tags = []
    content_lines = []
    in_content = False

    for line in lines:
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("TAGS:"):
            tags = [t.strip() for t in line.replace("TAGS:", "").split(",")]
        elif line.startswith("CONTENT:"):
            in_content = True
        elif in_content:
            content_lines.append(line)

    content = "\n".join(content_lines).strip()
    content = _strip_code_fence(content)

    return {
        "title": title,
        "tags": tags,
        "content": content,
    }


def _strip_code_fence(content: str) -> str:
    """본문 앞뒤로 감싸진 ```html ... ``` 마크다운 펜스 제거."""
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # 첫 줄(```html 또는 ```) 제거
        lines = lines[1:]
        # 마지막 ``` 줄 제거
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped

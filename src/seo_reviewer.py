"""SEO + 콘텐츠 품질 검토자 (건강 블로그용)

Sonnet 4.6으로 6축 평가 (각 점수 합 100)
- 키워드 정합성 20
- AI 티 없음 20
- 구글 SEO 20
- 자연스러움/가독성 15
- 정보 가치 15
- 후크/유지력 10
"""

import re
import anthropic


REVIEWER_MODEL = "claude-sonnet-4-6"
SCORE_THRESHOLD = 75


AI_CLICHE_LIST = [
    "결론적으로", "요약하면", "종합하면",
    "놀랍게도", "무려", "꼭 알아야 할",
    "다음과 같은 장점", "다음과 같은 이점",
    "~라고 알려져 있습니다", "~에 효과적입니다",
    "여러분도", "오늘은 ~에 대해 알아보겠습니다",
    "이상으로", "마치며",
]

# 가짜 일화 도입 (가족/지인 진단 받았다 식)
FAKE_ANECDOTE_PHRASES = [
    "친구가 진단", "지인이 진단", "엄마가 진단", "아버지가 진단",
    "동생이 진단", "직장 동료가", "옆집 사람이",
    "친구한테 들었", "지인에게 들었", "친구가 효과",
]

# 의료법 위반 소지 표현 (건강 블로그는 의사가 아닌 정보 정리자임을 명확히)
MEDICAL_VIOLATION_PHRASES = [
    # 치료 효과 단정
    "낫는다", "낫습니다", "나았", "치료된다", "완치",
    # 진단성 표현
    "OO병입니다", "X 수치면 병원", "이런 증상이면 OO",
    # 처방 권유
    "드시면 좋습니다", "드세요", "복용하세요",
    # 진료 흉내
    "병원 안 가도", "수술 안 받아도",
]


REVIEW_SYSTEM = """당신은 한국어 블로그 글의 SEO와 가독성을 평가하는 전문 에디터입니다.
구글/네이버 검색 상위 노출과 독자 체류시간을 기준으로 냉정하게 평가합니다.
AI 양산글의 흔적 (격식체 과다, 백과사전 톤, 기계적 나열, 같은 문장 반복)을 정확히 잡아냅니다.
점수에 인색하게: 평범한 AI 글은 60점대, 잘 쓴 글은 80점대, 정말 뛰어난 글만 90점+."""


REVIEW_PROMPT = """다음 블로그 글을 평가해주세요.

**키워드**: {keyword}

**제목**: {title}

**태그**: {tags}

**본문 (HTML)**:
{content}

---

평가 기준 (6축 합 100점):

### 1. 키워드 정합성 (20점)
- 글이 키워드 의도에서 벗어나지 않음
- 첫 문단 100자 이내 키워드 1회 등장
- 본문 4~6회, H2 소제목 2개 이상에 키워드 변형 포함
- 태그가 키워드와 관련 있음
- 키워드에서 동떨어진 주제로 흐른다면 큰 감점

### 2. AI 티 없음 + 안전성 (20점)
- **의료법 위반 소지 표현 (1개라도 발견 시 즉시 -15점 + ISSUES 필수 보고)**:
  {medical_list}
  → 의사가 아니므로 치료/진단/처방 표현 절대 금지
- **가짜 일화 도입 (1개라도 발견 시 -10점)**:
  {fake_anecdote_list}
  → "친구가 진단 받았대요" 같은 가짜 1·3인칭 일화는 신뢰도 ↓ + HCU 페널티
- AI 클리셰 사용 시 항목당 -3점:
  {cliche_list}
- 모든 문단이 "~입니다/~합니다"로 끝나면 -5점
- "첫째/둘째/셋째" 또는 "1.2.3." 기계적 나열 -5점
- 같은 문장 시작 패턴 3회 이상 반복 -3점

### 3. 구글 SEO (20점)
- 제목 25~35자, 키워드 앞쪽 배치
- H2 소제목 3~4개 (정보성)
- 본문 글자수 1800~3000자 (HTML 태그 제외)
- 검색 의도 매칭 (정보형 키워드면 정보 제공, 비교형이면 비교, 하우투면 방법 제시)
- 메타 정보 (TITLE, 태그) 적절성

### 4. 자연스러움 / 가독성 (15점)
- 문단 길이 다양 (모바일 기준 한 문단 3~5줄 권장)
- 문장 길이 섞임 (짧은 + 긴)
- 구어체 자연스러움 ("근데", "사실", "그래서" 등 적절히)
- 같은 단어/표현 과반복 없음

### 5. 정보 가치 (15점)
- 구체적 사례, 수치, 비교가 있는가
- 어디서나 보일 평이한 내용만 나열하지 않는가
- 독자가 검색하며 궁금해할 질문에 답하는가
- 단순 정의/설명만 있으면 감점

### 6. 후크 / 유지력 (10점)
- 첫 문단(도입)이 독자를 끌어당기는가 (왜 끝까지 읽어야 하는지)
- 마지막에 다음 액션이나 정리감이 있는가 (단, 클리셰 결론은 감점)

---

응답 형식 (정확히 이 포맷 준수):

SCORE: (0~100 정수)
PASS: (YES 또는 NO, 75 이상이면 YES)
BREAKDOWN: 키워드정합성 X/20, AI티없음 X/20, SEO X/20, 가독성 X/15, 정보가치 X/15, 후크 X/10
ISSUES:
- (구체적 문제점 1)
- (구체적 문제점 2)
...
REVISE_GUIDE:
- (재작성 시 지킬 명확한 지침 1)
- (재작성 시 지킬 명확한 지침 2)
...
"""


REVISE_PROMPT_TEMPLATE = """이전 작성한 글을 다음 피드백에 따라 개선해주세요.

**키워드**: {keyword}

**이전 글**:
TITLE: {title}
TAGS: {tags}
CONTENT:
{content}

**검토자 피드백 (반드시 모두 반영)**:
{guide}

원래 작성 규칙(글자수, HTML 태그, 자연스러운 구어체)은 유지하면서 위 피드백을 모두 반영해주세요.

형식:
TITLE: (개선된 제목)
TAGS: (쉼표 구분 7~10개)
CONTENT:
(HTML 본문)"""


def review(keyword: str, title: str, tags: list, content: str, api_key: str) -> dict:
    """글을 평가하여 점수와 가이드 반환."""
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=REVIEWER_MODEL,
        max_tokens=2000,
        system=REVIEW_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": REVIEW_PROMPT.format(
                    keyword=keyword,
                    title=title,
                    tags=", ".join(tags) if tags else "",
                    content=content,
                    cliche_list=", ".join(f'"{c}"' for c in AI_CLICHE_LIST),
                    fake_anecdote_list=", ".join(f'"{c}"' for c in FAKE_ANECDOTE_PHRASES),
                    medical_list=", ".join(f'"{c}"' for c in MEDICAL_VIOLATION_PHRASES),
                ),
            }
        ],
    )

    return _parse_review(message.content[0].text)


def _parse_review(text: str) -> dict:
    score = 0
    passed = False
    breakdown = ""
    issues = []
    guide_lines = []
    in_issues = False
    in_guide = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("SCORE:"):
            m = re.search(r"\d+", stripped)
            score = int(m.group()) if m else 0
            in_issues = in_guide = False
        elif stripped.startswith("PASS:"):
            passed = "YES" in stripped.upper()
            in_issues = in_guide = False
        elif stripped.startswith("BREAKDOWN:"):
            breakdown = stripped.replace("BREAKDOWN:", "").strip()
            in_issues = in_guide = False
        elif stripped.startswith("ISSUES:"):
            in_issues = True
            in_guide = False
        elif stripped.startswith("REVISE_GUIDE:"):
            in_issues = False
            in_guide = True
        elif in_issues and stripped.startswith("-"):
            issues.append(stripped.lstrip("- ").strip())
        elif in_guide and stripped.startswith("-"):
            guide_lines.append(stripped.lstrip("- ").strip())

    return {
        "score": score,
        "passed": passed or score >= SCORE_THRESHOLD,
        "breakdown": breakdown,
        "issues": issues,
        "guide": "\n".join(f"- {g}" for g in guide_lines),
    }

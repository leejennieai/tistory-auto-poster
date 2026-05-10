# Tistory 자동 포스팅 시스템

Tistory 블로그에 매일 자동으로 건강/다이어트/식단 관련 글을 발행하는 자동화 시스템.

## 주요 기능

- Claude Haiku AI로 SEO 최적화 블로그 글 자동 생성
- Pexels 무료 이미지 자동 검색 및 본문 삽입
- 제목 텍스트 합성 썸네일 자동 생성
- Playwright로 Tistory 자동 발행 (카테고리, 태그 포함)
- 네이버 검색광고 API로 인기 키워드 자동 수집 (주 1회)
- GitHub Actions로 하루 3회 랜덤 시간 발행
- 발행 완료 시 이메일 알림

## 프로젝트 구조

```
tistory-auto-poster/
├── .github/workflows/
│   ├── daily-post.yml           # 매일 3회 자동 발행
│   └── weekly-keywords.yml      # 매주 키워드 수집
├── src/
│   ├── main.py                  # 메인 실행
│   ├── config.py                # 환경변수 설정
│   ├── content_generator.py     # Claude AI 글 생성
│   ├── image_fetcher.py         # Pexels 이미지 검색
│   ├── thumbnail_maker.py       # 썸네일 생성
│   ├── tistory_client.py        # Playwright Tistory 발행
│   ├── keyword_manager.py       # 키워드 CSV 관리
│   ├── keyword_collector.py     # 네이버 API 키워드 수집
│   ├── login_setup.py           # 초기 로그인 세션 생성
│   └── notifier.py              # 이메일 알림
├── keywords/
│   └── health_keywords.csv      # 키워드 목록
├── fonts/
│   └── NotoSansKR.ttf           # 썸네일용 한글 폰트
├── auth_state.json              # Tistory 로그인 세션 (자동 생성)
└── requirements.txt
```

## 초기 설정

### 1. 패키지 설치

```bash
pyenv local 3.11.9
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Tistory 로그인 세션 생성

최초 1회만 실행. 브라우저가 열리면 카카오 로그인 + 2차 인증 완료.

```bash
.venv/bin/python src/login_setup.py
```

`auth_state.json`이 생성되면 성공. 세션 만료 시 다시 실행.

### 3. 로컬 테스트

```bash
ANTHROPIC_API_KEY="your-key" \
PEXELS_API_KEY="your-key" \
TISTORY_BLOG_NAME="your-blog" \
TISTORY_CATEGORY="건강" \
SMTP_EMAIL="your@gmail.com" \
SMTP_PASSWORD="your-app-password" \
NOTIFY_EMAIL="notify@email.com" \
.venv/bin/python src/main.py
```

### 4. 키워드 수집 테스트

```bash
NAVER_AD_API_LICENSE="your-license" \
NAVER_AD_API_SECRET="your-secret" \
NAVER_AD_CUSTOMER_ID="your-id" \
.venv/bin/python src/keyword_collector.py
```

## GitHub Actions 배포

### 1. Private repo 생성 후 코드 push

중요: push 전에 소스 코드 주석의 API 키 값을 모두 삭제할 것!

### 2. GitHub Secrets 등록

Settings > Secrets and variables > Actions > New repository secret

**글 발행용:**

| Name | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | Anthropic API 키 (console.anthropic.com) |
| `PEXELS_API_KEY` | Pexels API 키 (pexels.com/api) |
| `TISTORY_BLOG_NAME` | 블로그명 (예: jennie-100) |
| `TISTORY_CATEGORY` | 카테고리명 (예: 건강) |
| `SMTP_EMAIL` | 알림 발송용 Gmail |
| `SMTP_PASSWORD` | Gmail 앱 비밀번호 (16자리) |
| `NOTIFY_EMAIL` | 알림 받을 이메일 |

**키워드 수집용:**

| Name | 설명 |
|------|------|
| `NAVER_AD_API_LICENSE` | 네이버 검색광고 API 인증키 |
| `NAVER_AD_API_SECRET` | 네이버 검색광고 비밀키 |
| `NAVER_AD_CUSTOMER_ID` | 네이버 검색광고 고객 ID |

### 3. auth_state.json을 repo에 포함

로그인 세션 파일이 repo에 있어야 Actions에서 사용 가능. 반드시 private repo로 운영.

### 4. 자동 실행 스케줄

- **글 발행**: 매일 3회 (오전 7~9시, 오후 1~3시, 오후 7~9시 KST)
- **키워드 수집**: 매주 월요일 새벽 3시 KST

수동 실행: Actions 탭 > 워크플로우 선택 > Run workflow

## API 비용

| 항목 | 월 비용 |
|------|---------|
| Claude Haiku API | ~$0.5 (하루 3글 기준) |
| Pexels API | 무료 |
| 네이버 검색광고 API | 무료 |
| GitHub Actions | 무료 (private repo 2000분/월) |

## Gmail 앱 비밀번호 발급

1. Google 계정 > 보안 > 2단계 인증 활성화
2. https://myaccount.google.com/apppasswords 접속
3. 앱 이름 입력 > 생성 > 16자리 코드 복사

## 세션 만료 시

Tistory 로그인 세션이 만료되면 Actions가 실패합니다.
로컬에서 `python src/login_setup.py` 다시 실행 후 `auth_state.json` 커밋 & push.

## 키워드 관리

- `keywords/health_keywords.csv`에서 키워드 추가/삭제 가능
- 주 1회 네이버 API로 자동 보충 (weekly-keywords.yml)
- 시드 키워드 변경: `src/keyword_collector.py`의 `SEED_KEYWORDS` 수정

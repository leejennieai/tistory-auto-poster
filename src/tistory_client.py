"""Tistory Playwright 클라이언트 - 저장된 세션으로 글쓰기 자동화

사전 준비: login_setup.py를 로컬에서 실행하여 auth_state.json 생성
"""

import random
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

AUTH_STATE_PATH = Path(__file__).parent.parent / "auth_state.json"


def _human_pause(min_ms: int = 800, max_ms: int = 2000):
    """인간 흉내 랜덤 딜레이."""
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


def _human_click(page, selector: str, wait_after: tuple = (800, 2000)):
    """hover → 짧은 대기 → 클릭 → 랜덤 대기 (자동화 패턴 완화)."""
    locator = page.locator(selector).first
    try:
        locator.hover(timeout=5000)
        _human_pause(200, 500)
    except Exception:
        pass
    locator.click(timeout=10000)
    _human_pause(*wait_after)


def publish_post(
    blog_name: str,
    title: str,
    content: str,
    tags: list[str],
    category: str = "",
    thumbnail_path: str = "",
) -> str:
    """저장된 세션으로 Tistory에 글 발행. 임시저장 빠지면 1회 재시도.

    Returns:
        발행된 글의 URL
    """
    if not AUTH_STATE_PATH.exists():
        raise RuntimeError(
            "auth_state.json이 없습니다. 먼저 login_setup.py를 실행해주세요."
        )

    with sync_playwright() as p:
        # automation 흔적 줄이는 launch args
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            storage_state=str(AUTH_STATE_PATH),
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        # webdriver 흔적 숨기기
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = context.new_page()

        try:
            # 1. 글쓰기 페이지 이동
            write_url = f"https://{blog_name}.tistory.com/manage/newpost"
            page.goto(write_url)
            page.wait_for_load_state("networkidle")
            _human_pause(1500, 3000)

            if "login" in page.url:
                browser.close()
                raise RuntimeError(
                    "세션이 만료되었습니다. login_setup.py를 다시 실행해주세요."
                )

            print("[글쓰기] 에디터 진입")

            # 2. 제목 입력 (사람처럼 타이핑)
            title_input = page.locator('[placeholder*="제목"]')
            title_input.wait_for(timeout=10000)
            title_input.click()
            _human_pause(300, 800)
            title_input.fill("")
            title_input.type(title, delay=random.randint(30, 80))
            _human_pause(500, 1200)

            # 3. TinyMCE API로 본문 삽입
            page.wait_for_function(
                "typeof tinymce !== 'undefined' && tinymce.activeEditor",
                timeout=10000,
            )
            page.evaluate(
                """(content) => {
                const editor = tinymce.activeEditor;
                editor.setContent(content);
                editor.fire('change');
                editor.fire('input');
                editor.save();
                editor.nodeChanged();
            }""",
                content,
            )
            _human_pause(1000, 2000)

            # 약간의 스크롤 (사람 흉내)
            page.mouse.wheel(0, random.randint(100, 400))
            _human_pause(500, 1000)

            # 4. 카테고리 설정
            if category:
                _human_click(page, "#category-btn", wait_after=(800, 1500))
                try:
                    _human_click(
                        page, f"[aria-label='{category}']", wait_after=(500, 1000)
                    )
                except Exception:
                    print(f"[WARN] 카테고리 '{category}' 못 찾음")

            # 5. 발행 모달 열기
            print("[발행] 발행 모달 열기...")
            _human_click(page, "#publish-layer-btn", wait_after=(1500, 2500))

            # 6. 공개 라디오 선택
            _human_click(page, "#open20", wait_after=(500, 1200))

            # 7. 대표이미지 업로드
            if thumbnail_path:
                file_input = page.locator('.box_thumb input[type="file"]')
                file_input.set_input_files(thumbnail_path)
                _human_pause(2000, 3500)
                print("[썸네일] 대표이미지 업로드 완료")

            # 8. 공개 발행 클릭 (1회 시도, URL 변화 기반 검증)
            _human_click(page, "#publish-btn", wait_after=(2000, 3500))

            # URL이 newpost에서 벗어나길 최대 15초 대기 (실제 발행 신호)
            published = _wait_url_change(page, max_wait_sec=15)

            if not published:
                # 모달이 아직 떠있거나 페이지 미반응 → 한 번 더 클릭
                print("[INFO] 발행 후 URL 미변경, 한 번 더 시도")
                try:
                    if page.locator("#publish-btn").is_visible():
                        _human_click(page, "#publish-btn", wait_after=(2000, 3500))
                        published = _wait_url_change(page, max_wait_sec=15)
                except Exception:
                    pass

            if not published:
                print("[WARN] 공개 발행 미확인 → 임시저장 가능성")
                post_url = _find_post_url(page, blog_name, title) or (
                    f"https://{blog_name}.tistory.com (임시저장 추정)"
                )
                browser.close()
                return post_url

            print("[OK] 발행 URL 변화 감지 완료")

            # 9. URL 추출
            post_url = _find_post_url(page, blog_name, title) or (
                f"https://{blog_name}.tistory.com"
            )

            # 10. 세션 갱신 저장
            context.storage_state(path=str(AUTH_STATE_PATH))

            print(f"[성공] 발행 완료 - 제목: {title}")
            print(f"[링크] {post_url}")
            return post_url
        finally:
            browser.close()


def _wait_url_change(page, max_wait_sec: int = 15) -> bool:
    """공개 발행 후 URL이 /newpost에서 벗어나는지 대기.
    Tistory가 실제 발행 처리하면 URL이 글 상세나 관리 페이지로 자동 이동.
    """
    try:
        page.wait_for_url(
            lambda url: "newpost" not in url,
            timeout=max_wait_sec * 1000,
        )
        return True
    except Exception:
        return False


def _verify_published(page, blog_name: str, title: str) -> bool:
    """관리 페이지에서 글 공개 상태 직접 확인 (참고용)."""
    try:
        page.wait_for_timeout(2000)

        current = page.url
        if "newpost" not in current and "manage" in current:
            return True

        # 관리 페이지에서 직접 확인
        page.goto(
            f"https://{blog_name}.tistory.com/manage/posts/", timeout=15000
        )
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(1500)

        # 페이지 텍스트에서 제목 + 공개 상태 확인
        is_published = page.evaluate(
            """(title) => {
            const rows = document.querySelectorAll('tr, .post-item, .post_list li');
            for (const row of rows) {
                const text = row.textContent || '';
                if (text.includes(title)) {
                    // '공개' 표시 있고 '비공개'/'임시저장' 없는 경우
                    const hasPublic = text.includes('공개') && !text.includes('비공개');
                    const isDraft = text.includes('임시저장') || text.includes('대기');
                    return hasPublic && !isDraft;
                }
            }
            return false;
        }""",
            title,
        )
        return bool(is_published)
    except Exception as e:
        print(f"[WARN] 발행 검증 중 오류: {e}")
        return False


def _find_post_url(page, blog_name: str, title: str) -> str:
    """관리 페이지에서 발행된 글 URL 찾기."""
    try:
        page.goto(
            f"https://{blog_name}.tistory.com/manage/posts/", timeout=15000
        )
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(1000)
        first_link = page.evaluate(
            """(title) => {
            const items = document.querySelectorAll(
                '.post_list .title_post, .post-item a, td a'
            );
            for (const item of items) {
                if (item.textContent.includes(title)) {
                    return item.href || '';
                }
            }
            return '';
        }""",
            title,
        )
        if first_link and "/manage/" in first_link:
            post_id = first_link.split("/")[-1]
            return f"https://{blog_name}.tistory.com/{post_id}"
        if first_link:
            return first_link
    except Exception:
        pass
    return ""

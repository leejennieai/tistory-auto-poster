"""Tistory Playwright 클라이언트 - 저장된 세션으로 글쓰기 자동화

사전 준비: login_setup.py를 로컬에서 실행하여 auth_state.json 생성
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

AUTH_STATE_PATH = Path(__file__).parent.parent / "auth_state.json"


def publish_post(
    blog_name: str,
    title: str,
    content: str,
    tags: list[str],
    category: str = "",
    thumbnail_path: str = "",
) -> str:
    """저장된 세션으로 Tistory에 글 발행

    Returns:
        발행된 글의 URL
    """
    if not AUTH_STATE_PATH.exists():
        raise RuntimeError(
            "auth_state.json이 없습니다. 먼저 login_setup.py를 실행해주세요."
        )


    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(AUTH_STATE_PATH))
        page = context.new_page()

        # 1. 글쓰기 페이지 이동
        write_url = f"https://{blog_name}.tistory.com/manage/newpost"
        page.goto(write_url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 로그인 세션 만료 체크
        if "login" in page.url:
            browser.close()
            raise RuntimeError(
                "세션이 만료되었습니다. login_setup.py를 다시 실행해주세요."
            )

        print("[글쓰기] 에디터 진입")

        # 2. 제목 입력
        title_input = page.locator('[placeholder*="제목"]')
        title_input.wait_for(timeout=10000)
        title_input.fill(title)

        # 3. TinyMCE API로 본문 HTML 삽입 + 동기화
        page.wait_for_function("typeof tinymce !== 'undefined' && tinymce.activeEditor", timeout=10000)
        page.evaluate("""(content) => {
            const editor = tinymce.activeEditor;
            editor.setContent(content);
            editor.fire('change');
            editor.fire('input');
            editor.save();
            editor.nodeChanged();
        }""", content)
        page.wait_for_timeout(500)

        # 4. 카테고리 설정
        if category:
            page.click("#category-btn")
            page.wait_for_timeout(500)
            page.locator(f"[aria-label='{category}']").click()
            page.wait_for_timeout(300)

        # 5. "완료" 버튼 → 발행 모달 열기
        print("[발행] 발행 모달 열기...")
        page.click("#publish-layer-btn")
        page.wait_for_timeout(1500)

        # 6. 발행 모달에서 "공개" 라디오 선택
        page.click("#open20")
        page.wait_for_timeout(500)

        # 7. 대표이미지 업로드
        if thumbnail_path:
            file_input = page.locator('.box_thumb input[type="file"]')
            file_input.set_input_files(thumbnail_path)
            page.wait_for_timeout(2000)
            print("[썸네일] 대표이미지 업로드 완료")

        # 9. "공개 발행" 버튼 클릭
        page.click("#publish-btn")
        page.wait_for_timeout(3000)

        # 10. 발행 후 관리 페이지에서 최신 글 URL 추출
        post_url = f"https://{blog_name}.tistory.com"
        try:
            page.goto(f"https://{blog_name}.tistory.com/manage/posts/")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            first_link = page.evaluate("""(title) => {
                const items = document.querySelectorAll('.post_list .title_post, .post-item a, td a');
                for (const item of items) {
                    if (item.textContent.includes(title)) {
                        return item.href || '';
                    }
                }
                return '';
            }""", title)
            if first_link and "/manage/" in first_link:
                # /manage/newpost/12345 → /12345 로 변환
                post_id = first_link.split("/")[-1]
                post_url = f"https://{blog_name}.tistory.com/{post_id}"
        except Exception:
            pass

        # 세션 갱신 저장 (만료 연장)
        context.storage_state(path=str(AUTH_STATE_PATH))

        print(f"[성공] 발행 완료 - 제목: {title}")
        if post_url:
            print(f"[링크] {post_url}")

        browser.close()
        return post_url

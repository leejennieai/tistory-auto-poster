"""Tistory 세션 keep-alive 스크립트

저장된 auth_state.json으로 Tistory 관리 페이지에 접속하여
세션을 갱신(만료 연장)하고 다시 저장한다.

GitHub Actions에서 하루 2~3회 실행하여 세션 만료를 방지.
"""

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

AUTH_STATE_PATH = Path(__file__).parent.parent / "auth_state.json"


def keepalive(blog_name: str) -> bool:
    if not AUTH_STATE_PATH.exists():
        print("[ERROR] auth_state.json이 없습니다.", file=sys.stderr)
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(AUTH_STATE_PATH))
        page = context.new_page()

        try:
            # 발행 코드와 동일한 URL 사용 (검증된 경로)
            page.goto(f"https://{blog_name}.tistory.com/manage/newpost", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            if "login" in page.url or "auth" in page.url:
                print(f"[FAIL] 세션 만료됨 (redirected to {page.url})", file=sys.stderr)
                return False

            context.storage_state(path=str(AUTH_STATE_PATH))
            print(f"[OK] 세션 갱신 완료 - {page.url}")
            return True
        finally:
            browser.close()


if __name__ == "__main__":
    blog = os.environ.get("TISTORY_BLOG_NAME")
    if not blog:
        print("[ERROR] TISTORY_BLOG_NAME 환경변수 필요", file=sys.stderr)
        sys.exit(1)

    ok = keepalive(blog)
    sys.exit(0 if ok else 1)

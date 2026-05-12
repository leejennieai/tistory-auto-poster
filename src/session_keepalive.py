"""Tistory 세션 keep-alive 스크립트

1. auth_state.json으로 세션 시도 → 유효하면 갱신
2. 세션 만료면 KAKAO_EMAIL/KAKAO_PASSWORD로 자동 재로그인
"""

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import auto_login

AUTH_STATE_PATH = Path(__file__).parent.parent / "auth_state.json"


def try_existing_session(blog_name: str) -> bool:
    """기존 auth_state.json으로 세션 유효성 확인 + 갱신."""
    if not AUTH_STATE_PATH.exists():
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(AUTH_STATE_PATH))
        page = context.new_page()

        try:
            page.goto(f"https://{blog_name}.tistory.com/manage/newpost", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            if "login" in page.url or "auth" in page.url:
                print(f"[INFO] 세션 만료 감지 (redirected to {page.url})", file=sys.stderr)
                return False

            context.storage_state(path=str(AUTH_STATE_PATH))
            print(f"[OK] 세션 유효, 갱신 완료 - {page.url}")
            return True
        finally:
            browser.close()


def keepalive(blog_name: str) -> bool:
    # 1차: 기존 세션 시도
    if try_existing_session(blog_name):
        return True

    # 2차: ID/비번 자동 재로그인 (자격증명 있을 때만)
    email = os.environ.get("KAKAO_EMAIL")
    password = os.environ.get("KAKAO_PASSWORD")
    if not email or not password:
        print(
            "[FAIL] 세션 만료 + 자동 재로그인 자격증명(KAKAO_EMAIL/KAKAO_PASSWORD) 없음",
            file=sys.stderr,
        )
        return False

    print("[INFO] 세션 만료 → ID/비번 자동 재로그인 시도")
    if not auto_login.login_with_credentials(email, password, headless=True):
        print("[FAIL] 자동 재로그인 실패", file=sys.stderr)
        return False

    # 3차: 재로그인 후 세션 검증
    if try_existing_session(blog_name):
        print("[OK] 자동 재로그인 + 세션 검증 통과")
        return True

    print("[FAIL] 재로그인 후에도 세션 확인 실패", file=sys.stderr)
    return False


if __name__ == "__main__":
    blog = os.environ.get("TISTORY_BLOG_NAME")
    if not blog:
        print("[ERROR] TISTORY_BLOG_NAME 환경변수 필요", file=sys.stderr)
        sys.exit(1)

    ok = keepalive(blog)
    sys.exit(0 if ok else 1)

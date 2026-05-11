"""초기 로그인 세션 생성 스크립트

최초 1회만 로컬에서 실행:
    python login_setup.py

브라우저가 열리면 카카오 로그인 + 2차 인증 직접 완료.
로그인 성공하면 세션이 auth_state.json에 저장됨.
이후 자동 포스팅 시 이 파일을 사용하여 로그인 스킵.

세션 만료 시 다시 실행하면 됨.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path

AUTH_STATE_PATH = Path(__file__).parent.parent / "auth_state.json"


def setup_login():
    with sync_playwright() as p:
        # headless=False로 실제 브라우저 열기
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Tistory 로그인 페이지로 이동
        page.goto("https://www.tistory.com/auth/login")
        print("\n========================================")
        print("브라우저에서 카카오 로그인을 완료해주세요.")
        print("2차 인증까지 모두 완료하면 됩니다.")
        print("========================================\n")

        # 로그인 완료(=tistory.com 도메인이면서 /auth/ 경로가 아님)까지 대기 (최대 5분)
        page.wait_for_url(
            lambda url: "tistory.com" in url and "/auth/" not in url,
            timeout=300000,
        )
        print("[성공] 로그인 확인됨!")

        # 세션 저장
        context.storage_state(path=str(AUTH_STATE_PATH))
        print(f"[저장] 세션 저장 완료: {AUTH_STATE_PATH}")

        browser.close()
        print("\n브라우저를 닫았습니다. 이제 자동 포스팅이 가능합니다.")


if __name__ == "__main__":
    setup_login()

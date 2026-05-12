"""Kakao ID/비밀번호로 Tistory 자동 로그인

세션 만료 시 호출되어 새 세션을 만들어 auth_state.json에 저장한다.

환경변수 필요:
- KAKAO_EMAIL: 블로그용 카카오 계정 이메일
- KAKAO_PASSWORD: 비밀번호

주의:
- 회사 계정 사용 금지 (보안 분리)
- 새 IP에서 카카오 보안 정책으로 디바이스 인증 요구 가능
- captcha 출현 시 자동화 불가 → 명확한 에러로 반환
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

AUTH_STATE_PATH = Path(__file__).parent.parent / "auth_state.json"


def is_logged_in_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not (host == "tistory.com" or host.endswith(".tistory.com")):
        return False
    return "/auth/" not in parsed.path


def login_with_credentials(email: str, password: str, headless: bool = True) -> bool:
    """Kakao ID/비밀번호로 로그인 후 auth_state.json 저장.

    Returns True on success, False on failure (captcha/디바이스 인증/잘못된 자격증명 등).
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        try:
            # 1. Tistory 로그인 페이지
            page.goto("https://www.tistory.com/auth/login", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # 2. 카카오 로그인 버튼 클릭 (여러 셀렉터 시도)
            kakao_btn_selectors = [
                'a.btn_login.link_kakao_id',
                'a[href*="kakao"]',
                'button:has-text("카카오")',
                'a:has-text("카카오")',
            ]
            clicked = False
            for sel in kakao_btn_selectors:
                try:
                    page.click(sel, timeout=3000)
                    clicked = True
                    break
                except Exception:
                    continue
            if not clicked:
                print("[ERROR] 카카오 로그인 버튼 못 찾음", file=sys.stderr)
                _save_debug(page, "no_kakao_btn")
                return False

            # 3. 카카오 로그인 페이지 로딩 대기 (accounts.kakao.com 또는 kauth.kakao.com)
            page.wait_for_url(
                lambda url: "kakao.com" in url and ("login" in url or "authorize" in url),
                timeout=15000,
            )
            page.wait_for_load_state("networkidle", timeout=15000)

            # 4. 이메일 입력 - 셀렉터 시도 + 폼 등장 대기
            email_selectors = [
                'input[name="loginKey"]',
                'input[name="email"]',
                'input[name="loginId"]',
                'input[type="email"]',
                'input#loginKey--1',
                'input#input-loginKey',
                'input[placeholder*="이메일"]',
                'input[placeholder*="아이디"]',
            ]
            filled = False
            # 폼 자체가 나타날 때까지 최대 10초 대기
            try:
                page.wait_for_selector(
                    ", ".join(email_selectors),
                    timeout=10000,
                )
            except Exception:
                pass

            for sel in email_selectors:
                try:
                    page.fill(sel, email, timeout=2000)
                    filled = True
                    break
                except Exception:
                    continue
            if not filled:
                print("[ERROR] 이메일 입력 필드 못 찾음", file=sys.stderr)
                _save_debug(page, "no_email_field")
                return False

            # 5. 비밀번호 입력
            pw_selectors = [
                'input[name="password"]',
                'input[type="password"]',
            ]
            filled = False
            for sel in pw_selectors:
                try:
                    page.fill(sel, password, timeout=3000)
                    filled = True
                    break
                except Exception:
                    continue
            if not filled:
                print("[ERROR] 비밀번호 입력 필드 못 찾음", file=sys.stderr)
                _save_debug(page, "no_password_field")
                return False

            # 6. 로그인 버튼 클릭
            submit_selectors = [
                'button.btn_g.highlight.submit',
                'button[type="submit"]',
                'button.submit',
                'button:has-text("로그인")',
            ]
            clicked = False
            for sel in submit_selectors:
                try:
                    page.click(sel, timeout=3000)
                    clicked = True
                    break
                except Exception:
                    continue
            if not clicked:
                print("[ERROR] 로그인 제출 버튼 못 찾음", file=sys.stderr)
                _save_debug(page, "no_submit_btn")
                return False

            # 7. 로그인 후 tistory.com 도메인 + /auth/ 아님 까지 대기
            try:
                page.wait_for_url(is_logged_in_url, timeout=30000)
            except PlaywrightTimeout:
                current_url = page.url
                # 카카오에 머물러 있으면 captcha/디바이스 인증 가능성
                if "kakao.com" in current_url:
                    print(
                        f"[ERROR] Kakao 추가 인증 요구 가능성 (captcha/디바이스 인증). "
                        f"URL={current_url}",
                        file=sys.stderr,
                    )
                    _save_debug(page, "kakao_extra_auth")
                else:
                    print(f"[ERROR] 로그인 후 리다이렉트 실패. URL={current_url}", file=sys.stderr)
                    _save_debug(page, "no_redirect")
                return False

            # 8. 세션 저장
            context.storage_state(path=str(AUTH_STATE_PATH))
            print(f"[OK] 자동 로그인 성공 - 세션 저장: {AUTH_STATE_PATH}")
            return True

        finally:
            browser.close()


def _save_debug(page, prefix: str):
    """디버깅용 스크린샷 + HTML 저장 (GitHub Actions 로그에서 인지 가능)."""
    try:
        debug_dir = Path(__file__).parent.parent / "debug"
        debug_dir.mkdir(exist_ok=True)
        page.screenshot(path=str(debug_dir / f"{prefix}.png"), full_page=True)
        (debug_dir / f"{prefix}.html").write_text(page.content(), encoding="utf-8")
        print(f"[DEBUG] {prefix} 화면 저장: debug/{prefix}.png", file=sys.stderr)
    except Exception as e:
        print(f"[DEBUG] 디버그 저장 실패: {e}", file=sys.stderr)


if __name__ == "__main__":
    email = os.environ.get("KAKAO_EMAIL")
    password = os.environ.get("KAKAO_PASSWORD")
    if not email or not password:
        print("[ERROR] KAKAO_EMAIL, KAKAO_PASSWORD 환경변수 필요", file=sys.stderr)
        sys.exit(1)

    headless = os.environ.get("HEADLESS", "true").lower() != "false"
    ok = login_with_credentials(email, password, headless=headless)
    sys.exit(0 if ok else 1)

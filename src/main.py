"""Tistory 자동 포스팅 메인 스크립트"""

import os
import time
import tempfile

from config import get_config
from keyword_manager import get_unused_keyword, mark_keyword_used
from content_generator import generate_post
from image_fetcher import fetch_images, insert_images_into_content
from thumbnail_maker import save_thumbnail
from tistory_client import publish_post
from notifier import send_notification


def progress_bar(step, total, label=""):
    """프로그레스 바 출력"""
    width = 30
    filled = int(width * step / total)
    bar = "█" * filled + "░" * (width - filled)
    percent = int(100 * step / total)
    print(f"\r  [{bar}] {percent}% {label}", end="", flush=True)
    if step == total:
        print()


def run():
    config = get_config()
    total_steps = 7

    for i in range(config["post_count"]):
        print(f"\n{'='*50}")
        print(f"  포스팅 {i+1}/{config['post_count']} 시작")
        print(f"{'='*50}\n")

        # 1. 키워드 선택
        progress_bar(1, total_steps, "키워드 선택 중...")
        kw_row = get_unused_keyword()
        keyword = kw_row["keyword"]
        print(f"\r  [████░░░░░░░░░░░░░░░░░░░░░░░░░░] 14% 키워드: {keyword}")

        # 2. AI로 글 생성
        progress_bar(2, total_steps, "Claude Haiku로 글 생성 중...")
        start = time.time()
        post = generate_post(keyword, config["anthropic_api_key"])
        elapsed = time.time() - start
        content_len = len(post["content"])
        print(f"\r  [████████░░░░░░░░░░░░░░░░░░░░░░] 28% 글 생성 완료 ({content_len}자, {elapsed:.1f}초)")
        print(f"     제목: {post['title']}")
        print(f"     태그: {', '.join(post['tags'][:5])}...")

        # 3. 이미지 검색
        progress_bar(3, total_steps, "이미지 검색 중...")
        images = fetch_images(keyword, config["pexels_api_key"], config["image_count"])
        print(f"\r  [████████████░░░░░░░░░░░░░░░░░░] 42% 이미지 {len(images)}장 확보")

        # 4. 썸네일 생성
        progress_bar(4, total_steps, "썸네일 생성 중...")
        thumbnail_path = None
        if images:
            thumbnail_path = os.path.join(tempfile.gettempdir(), "thumbnail.jpg")
            save_thumbnail(images[0]["url"], post["title"], thumbnail_path)
            print(f"\r  [████████████████░░░░░░░░░░░░░░] 57% 썸네일 생성 완료")
        else:
            print(f"\r  [████████████████░░░░░░░░░░░░░░] 57% 썸네일 스킵")

        # 5. 이미지 본문 삽입
        progress_bar(5, total_steps, "이미지 삽입 중...")
        content_with_images = insert_images_into_content(
            post["content"], images, keyword
        )
        print(f"\r  [████████████████████░░░░░░░░░░] 71% 이미지 삽입 완료")

        # 6. Tistory 발행
        progress_bar(6, total_steps, "Tistory 발행 중...")
        post_url = publish_post(
            blog_name=config["tistory_blog_name"],
            title=post["title"],
            content=content_with_images,
            tags=post["tags"],
            category=config["tistory_category"],
            thumbnail_path=thumbnail_path,
        )
        print(f"\r  [████████████████████████░░░░░░] 85% Tistory 발행 완료!")

        # 7. 알림 + 마무리
        progress_bar(7, total_steps, "마무리 중...")
        if config.get("smtp_email"):
            send_notification(
                smtp_email=config["smtp_email"],
                smtp_password=config["smtp_password"],
                to_email=config["notify_email"],
                title=post["title"],
                post_url=post_url,
            )
            print(f"\r  [██████████████████████████████] 100% 이메일 알림 발송!")
        else:
            print(f"\r  [██████████████████████████████] 100% 완료!")

        mark_keyword_used(keyword)

        # 임시 파일 정리
        if thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)

        print(f"\n  '{keyword}' 포스팅 성공!")
        print(f"     글 링크: {post_url}")
        print()


if __name__ == "__main__":
    run()

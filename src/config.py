import os


def get_config():
    return {
        "anthropic_api_key": os.environ["ANTHROPIC_API_KEY"],
        "pexels_api_key": os.environ["PEXELS_API_KEY"],
        "tistory_blog_name": os.environ["TISTORY_BLOG_NAME"],
        "tistory_category": os.environ.get("TISTORY_CATEGORY", ""),
        "post_count": int(os.environ.get("POST_COUNT", "1")),
        "min_length": 1500,
        "max_length": 2500,
        "image_count": 3,
        # 이메일 알림 설정
        "smtp_email": os.environ.get("SMTP_EMAIL", ""),
        "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
        "notify_email": os.environ.get("NOTIFY_EMAIL", ""),
    }

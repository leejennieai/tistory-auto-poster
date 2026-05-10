"""Pexels 이미지 위에 제목 텍스트를 합성하여 썸네일 생성"""

import io
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_PATH = Path(__file__).parent.parent / "fonts" / "NotoSansKR.ttf"
THUMBNAIL_WIDTH = 800
THUMBNAIL_HEIGHT = 420


def create_thumbnail(image_url: str, title: str) -> bytes:
    """Pexels 이미지 + 제목 텍스트 합성 썸네일 생성

    Returns:
        썸네일 이미지 bytes (JPEG)
    """
    # 1. 배경 이미지 다운로드 & 리사이즈
    resp = requests.get(image_url, timeout=10)
    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
    img = _crop_center(img, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT)

    # 2. 이미지 약간 블러 (텍스트 가독성 향상)
    img = img.filter(ImageFilter.GaussianBlur(radius=2))

    # 3. 반투명 오버레이
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    draw_overlay.rectangle(
        [(0, 0), img.size],
        fill=(0, 0, 0, 120),  # 검정 반투명
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    # 4. 텍스트 그리기
    draw = ImageDraw.Draw(img)

    # 제목 줄바꿈 처리
    title_lines = _wrap_title(title, max_chars=14)
    font_size = 48 if len(title_lines) <= 2 else 40
    font = ImageFont.truetype(str(FONT_PATH), font_size)

    # 텍스트 위치 계산 (중앙 정렬)
    line_height = font_size + 12
    total_text_height = line_height * len(title_lines)
    y_start = (THUMBNAIL_HEIGHT - total_text_height) // 2

    for i, line in enumerate(title_lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (THUMBNAIL_WIDTH - text_width) // 2
        y = y_start + i * line_height

        # 텍스트 그림자
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0, 200), font=font)
        # 텍스트 본체
        draw.text((x, y), line, fill=(255, 255, 255, 255), font=font)

    # 5. JPEG로 변환
    img_rgb = img.convert("RGB")
    buffer = io.BytesIO()
    img_rgb.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def save_thumbnail(image_url: str, title: str, output_path: str) -> str:
    """썸네일 생성 후 파일로 저장"""
    thumb_bytes = create_thumbnail(image_url, title)
    with open(output_path, "wb") as f:
        f.write(thumb_bytes)
    return output_path


def _crop_center(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """이미지를 중앙 기준으로 크롭 & 리사이즈"""
    # 비율 맞춰서 리사이즈
    ratio = max(target_w / img.width, target_h / img.height)
    new_w = int(img.width * ratio)
    new_h = int(img.height * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # 중앙 크롭
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _wrap_title(title: str, max_chars: int = 14) -> list:
    """제목을 적절히 줄바꿈 (최대 3줄)"""
    if len(title) <= max_chars:
        return [title]

    lines = textwrap.wrap(title, width=max_chars)
    return lines[:3]  # 최대 3줄

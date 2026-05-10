"""하루 1~3개 글을 랜덤 시간에 발행하는 스케줄러

매일 오전 6시(KST)에 실행되어:
1. 오늘 발행할 글 개수를 1~3개 랜덤 선택
2. 각 글의 발행 시간을 오전 7시~오후 10시 사이에서 랜덤 선택
3. 시간순 정렬 후, 해당 시간까지 대기 → 발행 → 다음 시간 대기 → 발행
"""

import os
import random
import time
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

# 발행 시간 범위 (KST 기준)
START_HOUR = 7   # 오전 7시부터
END_HOUR = 22    # 오후 10시까지
MAX_POSTS = 3    # 최대 3개


def get_random_schedule():
    """오늘 발행할 개수와 시간을 랜덤 생성"""
    post_count = random.randint(1, MAX_POSTS)

    now_kst = datetime.now(KST)
    today = now_kst.date()

    # 랜덤 발행 시간 생성
    times = []
    for _ in range(post_count):
        hour = random.randint(START_HOUR, END_HOUR - 1)
        minute = random.randint(0, 59)
        post_time = datetime(today.year, today.month, today.day, hour, minute, tzinfo=KST)

        # 이미 지난 시간이면 20분 후로 조정
        if post_time <= now_kst:
            post_time = now_kst + timedelta(minutes=20)

        times.append(post_time)

    times.sort()
    return times


def send_schedule_email(schedule):
    """오늘의 발행 계획을 이메일로 발송"""
    smtp_email = os.environ.get("SMTP_EMAIL", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    notify_email = os.environ.get("NOTIFY_EMAIL", "")

    if not all([smtp_email, smtp_password, notify_email]):
        return

    from notifier import send_raw_email

    today = datetime.now(KST).strftime("%Y-%m-%d")
    time_list = "\n".join([f"  #{i+1} {t.strftime('%H:%M')} KST" for i, t in enumerate(schedule)])

    subject = f"[Tistory] {today} 발행 계획 ({len(schedule)}개)"
    body = f"""오늘의 자동 발행 계획입니다.

날짜: {today}
발행 개수: {len(schedule)}개

발행 예정 시간:
{time_list}

각 시간에 자동으로 글이 발행됩니다.
"""

    send_raw_email(smtp_email, smtp_password, notify_email, subject, body)
    print("[알림] 발행 계획 이메일 발송 완료")


def wait_until(target_time):
    """지정 시간까지 대기"""
    now = datetime.now(KST)
    delta = (target_time - now).total_seconds()

    if delta <= 0:
        return

    hours = int(delta // 3600)
    minutes = int((delta % 3600) // 60)
    print(f"  다음 발행까지 {hours}시간 {minutes}분 대기...")
    print(f"  발행 예정: {target_time.strftime('%H:%M')} KST")
    time.sleep(delta)


def main():
    immediate = os.environ.get("IMMEDIATE", "false").lower() == "true"

    if immediate:
        print("\n[즉시 발행 모드]\n")
        os.environ["POST_COUNT"] = "1"
        from main import run
        run()
        return

    schedule = get_random_schedule()

    print(f"\n{'='*50}")
    print(f"  오늘의 발행 계획")
    print(f"{'='*50}")
    print(f"  날짜: {datetime.now(KST).strftime('%Y-%m-%d')}")
    print(f"  발행 개수: {len(schedule)}개")
    for i, t in enumerate(schedule):
        print(f"  #{i+1} 예정 시간: {t.strftime('%H:%M')} KST")
    print(f"{'='*50}\n")

    # 발행 계획 이메일 발송
    send_schedule_email(schedule)

    # main.py의 run()을 글 1개씩 호출
    os.environ["POST_COUNT"] = "1"
    from main import run

    for i, post_time in enumerate(schedule):
        print(f"\n--- [{i+1}/{len(schedule)}] ---")
        wait_until(post_time)

        print(f"  {datetime.now(KST).strftime('%H:%M')} KST 발행 시작!")
        try:
            run()
        except Exception as e:
            print(f"  발행 실패: {e}")
            continue

    print(f"\n{'='*50}")
    print(f"  오늘 발행 완료! ({len(schedule)}개)")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

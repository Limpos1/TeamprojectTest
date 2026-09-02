# -*- coding: utf-8 -*-
"""
파싱된 목차(postprocess_toc_result 결과)와 사용자의 학습 기간·요일별 가용 시간을 받아
날짜별 학습 플랜을 생성한다.
- 페이지 수는 챕터의 estimatedPageCount(실측 또는 평균 추정치)를 그대로 쓴다.
- "하루 가용 시간에 비례해서 전체 분량을 나눈다"는 단순한 방식이다.
  (읽는 속도를 따로 입력받지 않고, 시간이 2배인 날은 분량도 2배로 배정)
- 페이지는 소수점이 아니라 정수 단위로 배정한다. 그날그날 반올림하면 오차가
  누적되므로, "누적 목표 페이지"의 차이로 하루치를 계산해 전체 합이 항상
  총 페이지 수와 정확히 일치하게 한다.
"""
from __future__ import annotations

import datetime

WEEKDAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]  # date.weekday(): 월=0 ... 일=6


def parse_hhmm(hhmm: str) -> int:
    """"1:30" 같은 "시:분" 문자열을 분 단위 정수로 변환한다."""
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def _get_leaf_items(parsed: dict) -> list[dict]:
    """
    스케줄링 대상 leaf 항목만 순서대로 모은다.
    - CONTENT로 분류된 항목만 대상으로 한다 (부록/머리말 등은 제외).
    - postprocess.py의 add_estimated_page_counts와 같은 규칙: 소단원이 실제
      페이지를 갖고 있으면 소단원을, 아니면 챕터 자신을 리프로 쓴다.
    - estimatedPageCount가 없는(=평균조차 못 낸) 항목은 스케줄링에서 제외한다.
    - startPage가 실제로 있으면(needsFallback=False) 그 값을 같이 들고 있어서,
      나중에 "오늘은 55~66p" 처럼 실제 페이지 범위를 보여줄 수 있게 한다.
      startPage를 모르는 항목은 페이지 수만 알려주고 범위는 표시하지 않는다.
    """
    leaves = []
    for chapter in parsed.get("chapters", []):
        if chapter.get("contentType") != "CONTENT":
            continue
        subunits = chapter.get("subunits", [])
        subunits_have_pages = any(sub.get("startPage") is not None for sub in subunits)
        if subunits and subunits_have_pages:
            for sub in subunits:
                if sub.get("estimatedPageCount"):
                    leaves.append({
                        "title": sub["title"],
                        "subject": chapter.get("subject"),
                        "pageCount": int(round(sub["estimatedPageCount"])),
                        "startPage": sub.get("startPage") if not sub.get("needsFallback") else None,
                    })
        else:
            if chapter.get("estimatedPageCount"):
                leaves.append({
                    "title": chapter["title"],
                    "subject": chapter.get("subject"),
                    "pageCount": int(round(chapter["estimatedPageCount"])),
                    "startPage": chapter.get("startPage") if not chapter.get("needsFallback") else None,
                })
    return leaves


def _study_days(
    start_date: datetime.date,
    target_date: datetime.date,
    excluded_dates: list[datetime.date] | None,
) -> list[datetime.date]:
    excluded = set(excluded_dates or [])
    days = []
    d = start_date
    while d <= target_date:
        if d not in excluded:
            days.append(d)
        d += datetime.timedelta(days=1)
    return days


def _daily_page_budgets(total_pages: int, day_minutes: list[int], total_minutes: int) -> list[int]:
    """
    하루하루 배정할 페이지 수(정수)를 "누적 목표치의 차이"로 계산한다.
    예: 총 100페이지를 5일에 걸쳐 나눌 때, 그날그날 20.0, 20.0, ... 처럼 딱 떨어지지
    않고 소수점이 있으면(예: 32페이지를 4일에), 매일 그냥 반올림하면 합이 총
    페이지 수랑 안 맞을 수 있다. 대신 "1일차까지 누적 목표", "2일차까지 누적
    목표"... 를 각각 반올림하고 그 차이를 그날 배정량으로 쓰면, 마지막 날 누적
    목표는 항상 total_pages와 정확히 같아서 전체 합이 어긋나지 않는다.
    """
    budgets = []
    cum_minutes = 0
    prev_target = 0
    for minutes in day_minutes:
        cum_minutes += minutes
        target = round(total_pages * cum_minutes / total_minutes) if total_minutes > 0 else 0
        budgets.append(target - prev_target)
        prev_target = target
    return budgets


def generate_study_plan(
    parsed_toc: dict,
    start_date: datetime.date,
    target_date: datetime.date,
    weekday_minutes: dict[str, int],
    excluded_dates: list[datetime.date] | None = None,
) -> dict:
    """
    parsed_toc: postprocess_toc_result()의 반환값
    start_date, target_date: 학습 시작일/목표일 (둘 다 포함하는 범위)
    weekday_minutes: {"월": 60, ..., "토": 180, "일": 180} 형태의 요일별 가용 시간(분).
    excluded_dates: 학습이 불가능한 날짜 목록

    반환값:
    {
        "days": [{"date": "2026-08-25", "minutes": 60,
                   "items": [{"title": ..., "pagesToday": 8, "totalPages": 32,
                              "pageRange": "55~62p", "status": "시작"}]}],
        "totalPages": ...,
        "totalMinutes": ...,
        "warnings": [...],
    }
    """
    leaves = _get_leaf_items(parsed_toc)
    total_pages = sum(l["pageCount"] for l in leaves)

    days = _study_days(start_date, target_date, excluded_dates)
    day_minutes = [weekday_minutes.get(WEEKDAY_NAMES[d.weekday()], 0) for d in days]
    total_minutes = sum(day_minutes)

    warnings = []
    if not leaves:
        warnings.append("스케줄링할 수 있는 챕터가 없습니다 (CONTENT 항목이 없거나 페이지 정보가 없음).")
    if total_minutes <= 0:
        warnings.append("학습 가능한 시간이 0분입니다. 요일별 가용 시간이나 학습 기간을 확인해주세요.")
    if not leaves or total_minutes <= 0:
        return {"days": [], "totalPages": total_pages, "totalMinutes": total_minutes, "warnings": warnings}

    day_page_budgets = _daily_page_budgets(total_pages, day_minutes, total_minutes)

    leaf_idx = 0
    leaf_remaining = leaves[0]["pageCount"]
    leaf_consumed = 0

    day_plans = []
    for d, minutes, budget in zip(days, day_minutes, day_page_budgets):
        items = []
        pages_left_today = budget

        while pages_left_today > 0 and leaf_idx < len(leaves):
            current = leaves[leaf_idx]
            take = min(pages_left_today, leaf_remaining)
            if take <= 0:
                break

            starts_today = leaf_consumed == 0
            if current["startPage"] is not None:
                range_start = current["startPage"] + leaf_consumed
                range_end = range_start + take - 1
                page_range = f"{range_start}~{range_end}p"
            else:
                page_range = None

            leaf_consumed += take
            leaf_remaining -= take
            finishes_today = leaf_remaining <= 0

            status = (
                "완료" if starts_today and finishes_today else
                "시작" if starts_today else
                "마무리" if finishes_today else
                "진행중"
            )
            items.append({
                "title": current["title"],
                "pagesToday": take,
                "totalPages": current["pageCount"],
                "pageRange": page_range,
                "status": status,
            })

            pages_left_today -= take
            if finishes_today:
                leaf_idx += 1
                leaf_consumed = 0
                if leaf_idx < len(leaves):
                    leaf_remaining = leaves[leaf_idx]["pageCount"]

        day_plans.append({"date": d.isoformat(), "minutes": minutes, "items": items})

    if leaf_idx < len(leaves):
        warnings.append(f"학습 가능 시간이 부족해 {len(leaves) - leaf_idx}개 챕터가 목표일까지 배정되지 못했습니다.")

    return {
        "days": day_plans,
        "totalPages": total_pages,
        "totalMinutes": total_minutes,
        "warnings": warnings,
    }
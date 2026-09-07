# -*- coding: utf-8 -*-
"""
React 프론트엔드와 연결하기 위한 FastAPI 서버.
- 로컬 개발용. `uvicorn server:app --reload`로 실행한다.
- 목차 파싱(사진 여러 장/PDF)과 학습 플랜 생성을 각각 엔드포인트로 노출한다.
"""
import base64
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api_call import parse_toc_from_images, parse_toc_from_text
from pdf_extract import extract_toc_text
from schedule import generate_plan_from_leaves, generate_study_plan
from checklist_sync import (
    compute_remaining_leaves,
    fetch_plan_from_firestore,
    fetch_plan_meta,
    fetch_raw_items_from_firestore,
    member_id_for_user,
    move_item_in_firestore,
    push_plan_to_firestore,
    save_plan_meta,
    study_plan_id_for_user,
)

app = FastAPI(title="Planit TOC Parser")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 팀원의 "할일 체크리스트" 백엔드(Planit-Web-Checklist-main)와 공유하는 Firestore
# 서비스 계정 키 경로. 플랜 저장/조회/이동을 전부 여기(Firestore)에 직접 한다 -
# 더 이상 메모리(PLANS_STORE)에 따로 들고 있지 않는다.
CHECKLIST_FIREBASE_CREDENTIALS = os.environ.get(
    "CHECKLIST_FIREBASE_CREDENTIALS", "firebase-service-account.json"
)


def _require_firestore_credentials() -> None:
    if not os.path.exists(CHECKLIST_FIREBASE_CREDENTIALS):
        raise HTTPException(
            status_code=503,
            detail=(
                f"{CHECKLIST_FIREBASE_CREDENTIALS} 파일이 없어서 플랜 저장소(Firestore)에 "
                "연결할 수 없습니다. 팀원에게 받은 서비스 계정 키 파일을 이 서버 루트에 넣어주세요."
            ),
        )


@app.post("/parse-toc/image")
async def parse_toc_image(
    files: list[UploadFile] = File(...),
    total_pages: int | None = Form(None),
):
    """
    목차 사진을 한 장 이상 업로드하면 구조화된 챕터 JSON을 반환한다.
    목차가 여러 장으로 나뉘어 촬영된 경우, 여러 파일을 같은 요청에 함께 보내면
    하나로 이어 붙여 파싱한다.
    """
    images = []
    for f in files:
        image_bytes = await f.read()
        images.append({
            "data": base64.b64encode(image_bytes).decode(),
            "media_type": f.content_type or "image/jpeg",
        })

    try:
        result = parse_toc_from_images(images, total_pages=total_pages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


@app.post("/parse-toc/pdf")
async def parse_toc_pdf(
    file: UploadFile = File(...),
    total_pages: int | None = Form(None),
):
    """목차가 포함된 PDF를 업로드하면 구조화된 챕터 JSON을 반환한다."""
    pdf_bytes = await file.read()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        toc_text = extract_toc_text(tmp_path)
        result = parse_toc_from_text(toc_text, total_pages=total_pages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return result


class GeneratePlanRequest(BaseModel):
    """
    parsedToc: postprocess_toc_result() 형태의 결과. 사용자가 과목 선택 화면에서
               체크 해제한 챕터는 프론트에서 이미 제외하고 보내는 것을 전제로 한다.
    startDate/targetDate: 학습 시작일/목표일 (둘 다 포함).
    weekdayMinutes: {"월": 120, ..., "토": 0, "일": 0} 형태의 요일별 가용 시간(분).
                    프론트에서 평일/주말 범위를 분으로 환산해 7일치로 채워서 보낸다.
    checkedDates: 캘린더에서 사용자가 체크한(=학습 가능한) 날짜 목록. 이 목록에
                  없는, 시작일~목표일 범위 안의 날짜는 전부 제외일로 처리한다.
    userId: 로그인 파트에서 내려주는 사용자 식별자. 있으면 생성된 플랜을 저장해서
            메인페이지가 나중에 /plans/{user_id}로 다시 조회할 수 있게 한다.
    """
    parsedToc: dict
    startDate: date
    targetDate: date
    weekdayMinutes: dict[str, int]
    checkedDates: list[date]
    userId: str | None = None


@app.post("/generate-plan")
async def generate_plan(req: GeneratePlanRequest):
    """
    선택된 챕터 + 기간/시간 설정을 받아 날짜별 학습 플랜을 생성하고, userId가 있으면
    Firestore "study_plan_items" 컬렉션에 바로 저장한다 (팀원의 체크리스트 백엔드가
    읽는 곳과 같은 컬렉션 - 별도 동기화 스크립트를 돌릴 필요 없이 여기서 바로 반영됨).
    """
    all_days = []
    d = req.startDate
    while d <= req.targetDate:
        all_days.append(d)
        d += timedelta(days=1)

    checked_set = set(req.checkedDates)
    excluded_dates = [d for d in all_days if d not in checked_set]

    try:
        result = generate_study_plan(
            req.parsedToc,
            start_date=req.startDate,
            target_date=req.targetDate,
            weekday_minutes=req.weekdayMinutes,
            excluded_dates=excluded_dates,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if req.userId:
        _require_firestore_credentials()
        study_plan_id = study_plan_id_for_user(req.userId)
        try:
            push_plan_to_firestore(
                result,
                member_id=member_id_for_user(req.userId),
                study_plan_id=study_plan_id,
                credentials_path=CHECKLIST_FIREBASE_CREDENTIALS,
            )
            # "계획 다시 생성하기"(남은 분량만 재배분)가 나중에 목차를 다시 안 받고도
            # 동작하려면, 지금 쓴 원본 목차와 배분 결과를 같이 저장해둬야 한다.
            save_plan_meta(
                study_plan_id=study_plan_id,
                parsed_toc=req.parsedToc,
                target_date=req.targetDate.isoformat(),
                weekday_minutes=req.weekdayMinutes,
                generated_days=result["days"],
                credentials_path=CHECKLIST_FIREBASE_CREDENTIALS,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"플랜 저장 실패: {e}")

    return result


class ReplanRequest(BaseModel):
    """
    "계획 다시 생성하기" 요청. 목차를 다시 올릴 필요 없이, 이미 저장해둔
    원본 목차(study_plans/{studyPlanId})에서 완료된 만큼을 빼고 남은 분량만 오늘부터
    다시 배분한다.

    targetDate: 생략하면 처음 생성할 때 정했던 목표일을 그대로 쓴다. 목표일이 이미
                지났으면(오늘보다 과거) 새 목표일을 반드시 넣어야 한다.
    checkedDates: 생략하면 오늘~목표일 사이 모든 날짜를 학습 가능일로 본다. 지정하면
                  그 목록에 없는 날짜는 제외일로 처리한다(기존 /generate-plan과 동일).
    """
    targetDate: date | None = None
    checkedDates: list[date] | None = None


@app.post("/plans/{user_id}/replan")
async def replan(user_id: str, req: ReplanRequest):
    """
    메인페이지의 "계획 다시 생성하기" 버튼이 호출하는 엔드포인트. 완료 표시해둔
    항목/기록은 그대로 두고(과거 날짜 항목은 안 건드림), 오늘 이후로 아직 안 끝난
    단원의 남은 페이지만 다시 날짜별로 배분해서 study_plan_items를 갱신한다.
    """
    _require_firestore_credentials()
    study_plan_id = study_plan_id_for_user(user_id)

    try:
        meta = fetch_plan_meta(study_plan_id, credentials_path=CHECKLIST_FIREBASE_CREDENTIALS)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기존 플랜 정보 조회 실패: {e}")

    if meta is None:
        raise HTTPException(
            status_code=404,
            detail="재생성할 기존 플랜이 없습니다. 목차 업로드부터 다시 진행해주세요.",
        )

    today = date.today()
    target_date = req.targetDate or date.fromisoformat(meta["targetDate"])
    if target_date < today:
        raise HTTPException(
            status_code=400,
            detail="기존 목표일이 이미 지났습니다. 새 목표일(targetDate)을 함께 보내주세요.",
        )

    all_days = []
    d = today
    while d <= target_date:
        all_days.append(d)
        d += timedelta(days=1)
    checked_set = set(req.checkedDates) if req.checkedDates else set(all_days)
    excluded_dates = [d for d in all_days if d not in checked_set]

    try:
        raw_items = fetch_raw_items_from_firestore(study_plan_id, credentials_path=CHECKLIST_FIREBASE_CREDENTIALS)
        remaining_leaves = compute_remaining_leaves(meta["parsedToc"], meta["generatedDays"], raw_items)
        result = generate_plan_from_leaves(
            remaining_leaves,
            start_date=today,
            target_date=target_date,
            weekday_minutes=meta["weekdayMinutes"],
            excluded_dates=excluded_dates,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재배분 계산 실패: {e}")

    try:
        # 오늘 이전(이미 지나간) 항목은 그대로 두고, 오늘 이후 항목만 지우고 새로 쓴다.
        push_plan_to_firestore(
            result,
            member_id=member_id_for_user(user_id),
            study_plan_id=study_plan_id,
            credentials_path=CHECKLIST_FIREBASE_CREDENTIALS,
            clear_from_date=today.isoformat(),
        )
        # generatedDays는 이번 재배분 결과로 통째로 덮어쓰지 않고, 오늘 이전(이미
        # 지나간) 날짜분은 예전 기록을 그대로 이어붙인다 - 안 그러면 "재생성을 두 번
        # 연속으로 했을 때, 1차 재생성 이전에 이미 다 끝낸 단원의 완료 기록이 사라져서
        # 그 단원이 남은 분량으로 되살아나는" 문제가 생긴다 (compute_remaining_leaves가
        # 단원별 완료 페이지를 generatedDays에서 찾아서 계산하기 때문).
        old_days = meta.get("generatedDays", [])
        today_str = today.isoformat()
        kept_past_days = [d for d in old_days if d["date"] < today_str]
        save_plan_meta(
            study_plan_id=study_plan_id,
            parsed_toc=meta["parsedToc"],
            target_date=target_date.isoformat(),
            weekday_minutes=meta["weekdayMinutes"],
            generated_days=kept_past_days + result["days"],
            credentials_path=CHECKLIST_FIREBASE_CREDENTIALS,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재생성된 플랜 저장 실패: {e}")

    plan = fetch_plan_from_firestore(study_plan_id, credentials_path=CHECKLIST_FIREBASE_CREDENTIALS)
    plan["memberId"] = member_id_for_user(user_id)
    return plan


@app.get("/plans/{user_id}")
async def get_plan(user_id: str):
    """
    메인페이지 캘린더가 Firestore에서 사용자의 학습 플랜을 조회할 때 쓰는 엔드포인트.
    오늘 할 일(체크리스트)은 이 응답에서 오늘 날짜에 해당하는 항목만 프론트에서
    걸러서 보여준다 - 별도로 팀원 API를 호출할 필요가 없다. memberId는 진도율
    체크(PATCH .../progress)를 프론트가 팀원 API로 직접 호출할 때 필요해서 같이 내려준다.
    """
    _require_firestore_credentials()
    try:
        plan = fetch_plan_from_firestore(
            study_plan_id_for_user(user_id),
            credentials_path=CHECKLIST_FIREBASE_CREDENTIALS,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"플랜 조회 실패: {e}")

    if not plan["days"]:
        raise HTTPException(status_code=404, detail="저장된 플랜이 없습니다.")

    plan["memberId"] = member_id_for_user(user_id)
    return plan


class MoveItemRequest(BaseModel):
    itemId: str
    toDate: str


@app.post("/plans/{user_id}/move-item")
async def move_item(user_id: str, req: MoveItemRequest):
    """메인 달력에서 항목을 다른 날짜로 드래그해서 옮겼을 때 호출된다."""
    _require_firestore_credentials()
    try:
        move_item_in_firestore(req.itemId, req.toDate, credentials_path=CHECKLIST_FIREBASE_CREDENTIALS)
        plan = fetch_plan_from_firestore(
            study_plan_id_for_user(user_id),
            credentials_path=CHECKLIST_FIREBASE_CREDENTIALS,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"항목 이동 실패: {e}")

    plan["memberId"] = member_id_for_user(user_id)
    return plan


@app.get("/health")
async def health():
    """React 쪽에서 서버가 켜져있는지 확인할 때 쓸 수 있는 간단한 상태 체크용."""
    return {"status": "ok"}
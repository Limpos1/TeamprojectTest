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
from schedule import generate_study_plan
from checklist_sync import (
    fetch_plan_from_firestore,
    member_id_for_user,
    move_item_in_firestore,
    push_plan_to_firestore,
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
        try:
            push_plan_to_firestore(
                result,
                member_id=member_id_for_user(req.userId),
                study_plan_id=study_plan_id_for_user(req.userId),
                credentials_path=CHECKLIST_FIREBASE_CREDENTIALS,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"플랜 저장 실패: {e}")

    return result


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
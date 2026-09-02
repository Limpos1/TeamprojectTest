# -*- coding: utf-8 -*-
"""
파이썬 플랜 생성 파이프라인과 팀원의 "할일 체크리스트" 백엔드
(Planit-Web-Checklist-main, Spring + Firestore) 사이의 연결부.

역할이 이렇게 나뉜다:
- 쓰기(플랜 생성, 항목 날짜 이동): 파이썬이 Firestore "study_plan_items" 컬렉션에 직접 쓴다.
- 읽기(캘린더 조회): 파이썬이 Firestore에서 읽어서 메인페이지 캘린더가 쓰는 형태로 재구성한다.
- 진도율 체크만: 프론트엔드가 파이썬을 거치지 않고 팀원의 자바 API
  (PATCH /api/study-plan-items/{id}/progress)를 직접 호출한다. 이미 팀원 쪽에
  검증 로직(허용값 확인, 본인 소유 확인)이 테스트까지 돼 있어서 중복 구현하지 않는다.

Firestore 문서 스키마는 팀원 쪽 StudyPlanItemRepository.toMap()과 정확히 맞춰야 한다:
    memberId (String), studyPlanId (String), planDate ("yyyy-MM-dd" String),
    subject (String), content (String), sortOrder (int), progressRate (int),
    completedAt (Timestamp|null), startTime (String|null), endTime (String|null),
    durationMinutes (int|null), createdAt/updatedAt (Timestamp)

주의:
- memberId는 로그인 백엔드(Planit-Web-Auth-Plan-Quiz)가 세션에 저장하는 Firebase Auth
  uid(문자열)를 그대로 쓴다. 체크리스트 백엔드의 memberId 필드도 원래 Long이었던 걸
  String으로 맞춰뒀다. 로그인 전 임시 테스트 때는 그냥 "guest" 같은 문자열을 userId로
  넘기면 되고, 로그인 붙으면 프론트가 실제 uid를 userId로 넘기기만 하면 된다(이 파일
  쪽은 바꿀 게 없음).
- 우리 플랜은 하루 단위 분량만 있고 항목별 시작/끝 시각이 없어서 startTime/endTime은
  항상 None이다. 대신 durationMinutes를 그날 전체 시간(day["minutes"])을 항목별
  pagesToday 비율로 나눠서 근사치로 채운다.
- Firestore 실제 읽기/쓰기가 필요한 함수들은 firebase-service-account.json 키 파일이
  로컬에 있어야 실행할 수 있다. 순수 변환 로직(build_study_plan_items,
  group_items_by_date)은 Firestore 없이도 그 자체로 테스트할 수 있게 분리해뒀다.
"""
from __future__ import annotations

PYTHON_API_BASE = "http://localhost:8000"


def member_id_for_user(user_id: str) -> str:
    """
    체크리스트 Firestore 문서의 memberId(String)로 쓸 값. 로그인 붙은 뒤에는 이게
    Firebase Auth uid 그 자체여야 하므로, 지금은 그냥 user_id를 그대로 돌려준다
    (예전엔 Long 타입에 맞추려고 숫자로 해시했었는데, 체크리스트 쪽 스키마를
    String으로 바꿔서 더 이상 그럴 필요가 없다).
    """
    return user_id


def study_plan_id_for_user(user_id: str) -> str:
    return f"plan-{user_id}"


def _get_firestore_client(credentials_path: str):
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ---------------------------------------------------------------------------
# 쓰기: 플랜 생성 -> Firestore
# ---------------------------------------------------------------------------

def build_study_plan_items(
    plan: dict,
    member_id: str,
    study_plan_id: str,
) -> list[dict]:
    """
    generate_study_plan()의 반환값을 Firestore "study_plan_items" 문서 목록으로 변환한다.
    Firestore에 쓰기 전 단계까지만 하는 순수 함수라서, 실제 DB 연결 없이도
    "매핑이 팀원 쪽 스키마와 맞는지"를 바로 확인해볼 수 있다.
    """
    docs = []
    for day in plan.get("days", []):
        plan_date = day["date"]
        day_minutes = day.get("minutes", 0)
        day_total_pages = sum(item.get("pagesToday", 0) for item in day.get("items", []))

        for sort_order, item in enumerate(day.get("items", [])):
            pages_today = item.get("pagesToday", 0)
            if day_total_pages > 0:
                duration_minutes = round(day_minutes * pages_today / day_total_pages)
            else:
                duration_minutes = None

            content = item["title"]
            if item.get("pageRange"):
                content = f'{content} ({item["pageRange"]})'

            docs.append({
                "memberId": member_id,
                "studyPlanId": study_plan_id,
                "planDate": plan_date,
                "subject": item.get("subject"),
                "content": content,
                "sortOrder": sort_order,
                "progressRate": item.get("progress", 0),
                "completedAt": None,
                "startTime": None,
                "endTime": None,
                "durationMinutes": duration_minutes,
                # createdAt/updatedAt은 push_plan_to_firestore()에서 SERVER_TIMESTAMP로 채운다.
            })
    return docs


def push_plan_to_firestore(
    plan: dict,
    member_id: str,
    study_plan_id: str,
    credentials_path: str = "firebase-service-account.json",
    clear_existing: bool = True,
) -> int:
    """
    build_study_plan_items()로 변환한 문서들을 실제 Firestore "study_plan_items"
    컬렉션에 써준다. clear_existing=True면, 같은 study_plan_id로 이미 들어가 있는
    예전 항목들을 먼저 지우고 새로 쓴다 ("계획 다시 생성하기"로 재생성했을 때 중복 방지).
    반환값: 실제로 써진 문서 개수.
    """
    from firebase_admin import firestore

    db = _get_firestore_client(credentials_path)
    collection = db.collection("study_plan_items")

    if clear_existing:
        existing = collection.where("studyPlanId", "==", study_plan_id).stream()
        for doc in existing:
            doc.reference.delete()

    docs = build_study_plan_items(plan, member_id, study_plan_id)
    for doc in docs:
        doc["createdAt"] = firestore.SERVER_TIMESTAMP
        doc["updatedAt"] = firestore.SERVER_TIMESTAMP
        collection.add(doc)

    return len(docs)


# ---------------------------------------------------------------------------
# 읽기: Firestore -> 메인페이지 캘린더가 쓰는 {"days": [...]}
# ---------------------------------------------------------------------------

def group_items_by_date(raw_items: list[dict]) -> dict:
    """
    Firestore 문서(딕셔너리로 이미 변환된 것)들을 날짜별로 묶어서 메인페이지 캘린더가
    기대하는 {"days": [{"date":.., "minutes":.., "items":[...]}]} 형태로 재구성한다.
    Firestore 연결 없이도 테스트할 수 있게 순수 함수로 분리했다.

    raw_items 각 원소는 {"id", "planDate", "subject", "content", "durationMinutes",
    "progressRate", "sortOrder"} 형태를 기대한다 (Firestore 문서 dict + doc.id).
    """
    by_date: dict[str, list[dict]] = {}
    for raw in raw_items:
        item = {
            "id": raw["id"],
            "subject": raw.get("subject"),
            "content": raw.get("content"),
            "durationMinutes": raw.get("durationMinutes"),
            "progressRate": raw.get("progressRate", 0),
            "completed": raw.get("progressRate", 0) == 100,
        }
        by_date.setdefault(raw["planDate"], []).append(
            {**item, "_sortOrder": raw.get("sortOrder", 0)}
        )

    days = []
    for plan_date in sorted(by_date.keys()):
        items = sorted(by_date[plan_date], key=lambda it: it["_sortOrder"])
        for it in items:
            del it["_sortOrder"]
        minutes = sum(it["durationMinutes"] or 0 for it in items)
        days.append({"date": plan_date, "minutes": minutes, "items": items})

    return {"days": days}


def fetch_plan_from_firestore(study_plan_id: str, credentials_path: str = "firebase-service-account.json") -> dict:
    """
    Firestore에서 해당 study_plan_id로 저장된 모든 항목을 읽어서
    group_items_by_date()로 캘린더 형태로 재구성한다. 항목이 하나도 없으면
    {"days": []}를 반환한다 (호출하는 쪽에서 404로 처리).
    """
    db = _get_firestore_client(credentials_path)
    docs = db.collection("study_plan_items").where("studyPlanId", "==", study_plan_id).stream()

    raw_items = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        raw_items.append(data)

    return group_items_by_date(raw_items)


def move_item_in_firestore(
    item_id: str,
    to_date: str,
    credentials_path: str = "firebase-service-account.json",
) -> None:
    """
    메인 달력에서 항목을 다른 날짜로 드래그했을 때 호출한다. 해당 문서의 planDate를
    바꾸고, 옮겨간 날짜의 맨 뒤(sortOrder 최댓값+1)로 붙인다.
    """
    from firebase_admin import firestore

    db = _get_firestore_client(credentials_path)
    collection = db.collection("study_plan_items")

    ref = collection.document(item_id)
    doc = ref.get()
    if not doc.exists:
        raise ValueError(f"항목을 찾을 수 없습니다: {item_id}")

    study_plan_id = doc.to_dict()["studyPlanId"]
    same_day_docs = collection.where("studyPlanId", "==", study_plan_id).where("planDate", "==", to_date).stream()
    next_sort_order = max((d.to_dict().get("sortOrder", 0) for d in same_day_docs), default=-1) + 1

    ref.update({
        "planDate": to_date,
        "sortOrder": next_sort_order,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })


if __name__ == "__main__":
    # 로컬 확인용. 사용법:
    #   python checklist_sync.py                          -> 예시 플랜 매핑 결과만 출력
    #   python checklist_sync.py <키파일경로>               -> 예시 플랜을 Firestore에 실제로 씀
    #   python checklist_sync.py <키파일경로> --read         -> Firestore에서 다시 읽어와 확인
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("credentials_path", nargs="?", help="firebase-service-account.json 경로")
    parser.add_argument("--read", action="store_true", help="쓰지 않고, Firestore에서 읽기만 확인")
    parser.add_argument("--study-plan-id", default="plan-guest")
    parser.add_argument("--member-id", default="test-uid-1")
    args = parser.parse_args()

    if args.read:
        if not args.credentials_path:
            raise SystemExit("--read는 키파일 경로가 필요합니다.")
        plan = fetch_plan_from_firestore(args.study_plan_id, credentials_path=args.credentials_path)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        raise SystemExit(0)

    example_plan = {
        "days": [
            {"date": "2026-09-01", "minutes": 120, "items": [
                {"title": "1장 개요", "subject": "리눅스 개론", "pagesToday": 12,
                 "totalPages": 12, "pageRange": "1~12p", "status": "완료"},
                {"title": "2장 파일시스템", "subject": "리눅스 개론", "pagesToday": 8,
                 "totalPages": 30, "pageRange": "13~20p", "status": "시작"},
            ]},
        ],
        "totalPages": 42, "totalMinutes": 120, "warnings": [],
    }

    mapped = build_study_plan_items(example_plan, member_id=args.member_id, study_plan_id=args.study_plan_id)
    print(json.dumps(mapped, ensure_ascii=False, indent=2))

    if args.credentials_path:
        count = push_plan_to_firestore(
            example_plan, member_id=args.member_id, study_plan_id=args.study_plan_id,
            credentials_path=args.credentials_path,
        )
        print(f"Firestore에 {count}개 문서를 썼습니다.")
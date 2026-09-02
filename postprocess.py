# -*- coding: utf-8 -*-
"""
LLM이 반환한 목차 파싱 결과(JSON)를 받아 후처리한다.
- endPage는 여기서 계산한다 (LLM에게 산수를 시키지 않는다).
- NON_CONTENT 키워드 2차 검증으로 LLM 분류 누락을 보정한다.
- JSON 파싱 실패에 대비한 안전 파서를 제공한다.
- 책이 여러 권(volume)으로 나뉘어 권마다 페이지 번호가 다시 시작되는 경우,
  권 경계를 넘어서까지 페이지를 이어 계산하면 endPage가 시작 페이지보다
  작아지는 등 말이 안 되는 값이 나온다. 그래서 모든 페이지 비교/계산은
  같은 volume 안에서만 이루어지도록 한다 (volume 필드가 없으면 1로 간주,
  즉 단일 권 책은 지금까지와 동일하게 동작한다).
"""
import json
import re

# contentType 2차 검증용 키워드 (문서 6-1절과 동일)
NON_CONTENT_KEYWORDS = [
    "머리말", "들어가며", "서문", "프롤로그", "에필로그", "저자", "감사의 글", "일러두기",
    "찾아보기", "색인", "참고문헌", "부록",
    "prologue", "epilogue", "index", "appendix", "preface", "acknowledg",
]


def safe_json_parse(raw_text: str) -> dict:
    """
    LLM 응답에서 JSON만 추출해 파싱한다.
    - 코드블록(```json ... ```)이 섞여 나오는 경우까지 방어.
    - 실패 시 예외를 던지므로 호출부에서 재시도 로직을 붙인다.
    """
    cleaned = raw_text.strip()
    # ```json ... ``` 혹은 ``` ... ``` 형태로 감싸져 오는 경우 제거
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    return json.loads(cleaned)


def _volume_of(item: dict) -> int:
    """volume 필드가 없으면 단일 권 책으로 보고 1을 기본값으로 쓴다."""
    return item.get("volume", 1)


def _flatten_ordered(chapters: list[dict]) -> list[dict]:
    """최상위 챕터들을 order 기준으로 정렬한 리스트를 반환 (subunits는 건드리지 않음)."""
    return sorted(chapters, key=lambda c: c.get("order", 0))


def _find_next_start_page(items: list[dict], from_index: int) -> int | None:
    """
    from_index 다음부터, **같은 volume 안에서** startPage가 실제로 존재하는
    첫 항목을 찾아 그 값을 반환한다.
    - "첫째마당/둘째마당" 같은 PART 구분자처럼 startPage가 null인 항목은
      끝까지 건너뛰고, 그 뒤에 있는 진짜 다음 챕터의 startPage를 사용한다.
    - 단, volume이 다른 항목을 만나면 그 순간 탐색을 멈춘다. 권이 바뀌면
      페이지 번호가 다시 시작되므로, 다른 권의 페이지로 endPage를 계산하면
      안 되기 때문이다.
    """
    current_volume = _volume_of(items[from_index])
    for item in items[from_index + 1:]:
        if _volume_of(item) != current_volume:
            return None
        if item.get("startPage") is not None:
            return item["startPage"]
    return None


def _find_next_start_page_across(chapters: list[dict], chapter_index: int, sub_index: int) -> int | None:
    """
    chapters[chapter_index]의 소단원 sub_index 다음부터 startPage를 찾되,
    같은 챕터 안에서 못 찾으면 이후 챕터들(자신의 startPage 또는 그 소단원들)까지
    이어서 탐색한다. 단, 여기서도 volume이 바뀌면 그 순간 탐색을 멈춘다.
    - SUBJECT 헤더처럼 챕터 자신은 startPage가 없고 소단원만 페이지를 가지는
      경우에도, 그 챕터의 마지막 소단원 endPage를 다음 챕터(혹은 그 소단원)의
      startPage로 정상적으로 이어 붙이기 위해 필요하다.
    """
    current_volume = _volume_of(chapters[chapter_index])
    subunits = sorted(chapters[chapter_index].get("subunits", []), key=lambda s: s.get("order", 0))
    for sub in subunits[sub_index + 1:]:
        if sub.get("startPage") is not None:
            return sub["startPage"]

    for chapter in chapters[chapter_index + 1:]:
        if _volume_of(chapter) != current_volume:
            return None
        if chapter.get("startPage") is not None:
            return chapter["startPage"]
        for sub in sorted(chapter.get("subunits", []), key=lambda s: s.get("order", 0)):
            if sub.get("startPage") is not None:
                return sub["startPage"]

    return None


def _resolve_total_pages(total_pages, volume: int, is_last_overall: bool) -> int | None:
    """
    마지막 챕터/소단원의 endPage를 채울 때 쓸 "그 권의 전체 페이지 수"를 결정한다.
    total_pages는 두 가지 형태를 받을 수 있다:
    - 정수 하나: 단일 권 책(혹은 다권 책의 마지막 권)의 전체 페이지 수.
      **문서 전체에서 정말로 마지막인 항목에만** 적용한다 (다른 권의 마지막
      챕터에 잘못 적용되면 엉뚱한 값이 되므로).
    - {volume: 페이지수} 형태의 dict: 권마다 전체 페이지 수를 알고 있을 때,
      해당 권의 마지막 항목에 적용한다.
    둘 다 없거나 해당 권 정보가 없으면 None을 반환해 needsFallback으로 남긴다.
    """
    if total_pages is None:
        return None
    if isinstance(total_pages, dict):
        return total_pages.get(volume)
    return total_pages if is_last_overall else None


def compute_end_pages(parsed: dict, total_pages=None) -> dict:
    """
    각 최상위 챕터의 endPage를 '다음에 오는 startPage가 있는 항목의 startPage - 1'로
    계산해 채워 넣는다. (같은 volume 안에서만 비교/계산한다.)
    - 바로 다음 항목이 PART 구분자 등으로 startPage가 null이면, 그 뒤를 계속 탐색해
      startPage가 있는 항목을 찾는다 (건너뛰기).
    - 같은 volume 안에서 다음 항목을 못 찾으면(=그 권의 마지막 챕터), total_pages로
      해당 권의 전체 페이지 수를 알 수 있으면 그 값을, 없으면 None을 사용한다.
    - 챕터 자신의 startPage가 null이면(예: SUBJECT 헤더 자체, PART 구분자 등)
      챕터 자신의 endPage 계산은 건너뛰고 needsFallback 플래그를 세운다.
      다만 이 경우에도 그 아래 소단원(subunits)들은 별도로 페이지를 갖고 있을 수
      있으므로, 소단원 endPage 계산은 챕터 자신의 상태와 무관하게 항상 수행한다.
    - 소단원의 마지막 항목처럼 같은 챕터 안에서 다음 startPage를 못 찾으면,
      챕터 경계를 넘어 다음 챕터(혹은 그 소단원)의 startPage까지 찾아본다
      (단, 같은 volume 안에서만).
    """
    chapters = _flatten_ordered(parsed.get("chapters", []))

    for i, chapter in enumerate(chapters):
        chapter_volume = _volume_of(chapter)
        is_last_overall = (i == len(chapters) - 1)

        if chapter.get("startPage") is None:
            chapter["needsFallback"] = True
            chapter["endPage"] = None
        else:
            chapter["needsFallback"] = False
            next_start = _find_next_start_page(chapters, i)
            if next_start is not None:
                chapter["endPage"] = next_start - 1
            else:
                resolved = _resolve_total_pages(total_pages, chapter_volume, is_last_overall)
                if resolved is not None:
                    chapter["endPage"] = resolved
                else:
                    # 같은 권 안에서 참조할 다음 페이지도 없고, 그 권의 전체
                    # 페이지 수도 모르는 "그 권의 진짜 마지막" 케이스
                    chapter["endPage"] = None
                    chapter["needsFallback"] = True

        # 소단원 endPage는 챕터 자신의 startPage 유무와 무관하게 항상 계산한다.
        subunits = sorted(chapter.get("subunits", []), key=lambda s: s.get("order", 0))
        for j, sub in enumerate(subunits):
            if sub.get("startPage") is None:
                sub["needsFallback"] = True
                sub["endPage"] = None
                continue
            sub["needsFallback"] = False
            sub_next_start = _find_next_start_page_across(chapters, i, j)
            if sub_next_start is not None:
                sub["endPage"] = sub_next_start - 1
            else:
                is_last_leaf_overall = is_last_overall and (j == len(subunits) - 1)
                resolved = _resolve_total_pages(total_pages, chapter_volume, is_last_leaf_overall)
                if resolved is not None:
                    sub["endPage"] = resolved
                else:
                    sub["endPage"] = None
                    sub["needsFallback"] = True
        chapter["subunits"] = subunits

        # 챕터 자신은 페이지가 없지만 소단원들은 있는 경우(SUBJECT 헤더 등),
        # 챕터의 endPage를 마지막 소단원의 endPage로 보완해 정보를 살려둔다.
        if chapter["endPage"] is None and subunits and subunits[-1].get("endPage") is not None:
            chapter["endPage"] = subunits[-1]["endPage"]

    parsed["chapters"] = chapters
    return parsed


def _get_leaf_items(parsed: dict) -> list[dict]:
    """
    스케줄링 대상이 되는 leaf 항목을 모아 반환한다.
    - 챕터에 subunits가 있고, 그 subunits 중 하나라도 실제 startPage를 갖고 있으면
      (예: SUBJECT->CHAPTER처럼 소단원이 자기만의 페이지를 갖는 책) subunits를 리프로 쓴다.
    - 챕터에 subunits가 아예 없거나, 있어도 전부 startPage가 null이면(예: 챕터 설명에
      나열된 소주제일 뿐 개별 페이지가 없는 책) subunits는 페이지 정보를 낼 수 없는
      장식용 목록일 뿐이므로, 페이지 범위를 실제로 알고 있는 챕터 자신을 리프로 쓴다.
    """
    leaves = []
    for chapter in parsed.get("chapters", []):
        subunits = chapter.get("subunits", [])
        subunits_have_pages = any(sub.get("startPage") is not None for sub in subunits)
        if subunits and subunits_have_pages:
            leaves.extend(subunits)
        else:
            leaves.append(chapter)
    return leaves


def add_estimated_page_counts(parsed: dict) -> dict:
    """
    스케줄링(목표일까지 진도 배분)에 쓸 'estimatedPageCount'를 leaf 항목마다 채워 넣는다.
    - endPage가 확정된 항목은 실제 페이지 수(endPage - startPage + 1)를 그대로 사용한다.
    - endPage를 모르는(needsFallback=True) 항목은, 같은 책 안에서 페이지 수가 확정된
      CONTENT 항목들의 평균 페이지 수로 대신 채운다.
    - 이 값은 어디까지나 스케줄 시간 배분용 추정치일 뿐이다. 실제 페이지 정보
      (startPage/endPage/needsFallback)는 그대로 유지해 왜곡하지 않는다 — 사용자에게는
      여전히 "확인 필요" 상태로 보여야 하고, estimatedPageCount는 그 확인 전까지
      스케줄이 끊기지 않게 하는 임시값일 뿐이다.
    - 페이지 수가 확정된 항목이 하나도 없어 평균조차 낼 수 없으면 None으로 둔다.
    """
    leaves = _get_leaf_items(parsed)

    known_counts = [
        leaf["endPage"] - leaf["startPage"] + 1
        for leaf in leaves
        if leaf.get("contentType", "CONTENT") == "CONTENT"
        and leaf.get("startPage") is not None
        and leaf.get("endPage") is not None
    ]
    average_count = round(sum(known_counts) / len(known_counts)) if known_counts else None

    for leaf in leaves:
        if leaf.get("startPage") is not None and leaf.get("endPage") is not None:
            leaf["estimatedPageCount"] = leaf["endPage"] - leaf["startPage"] + 1
        else:
            leaf["estimatedPageCount"] = average_count

    return parsed


def apply_non_content_keyword_filter(parsed: dict) -> dict:
    """
    LLM이 CONTENT로 분류했더라도, 제목에 NON_CONTENT 키워드가 포함되면
    NON_CONTENT로 재분류한다 (LLM 분류 누락 보정용 2차 검증).
    """
    for chapter in parsed.get("chapters", []):
        title_lower = chapter.get("title", "").lower()
        if any(kw.lower() in title_lower for kw in NON_CONTENT_KEYWORDS):
            chapter["contentType"] = "NON_CONTENT"
    return parsed


def detect_page_order_anomalies(parsed: dict) -> dict:
    """
    챕터의 startPage가 순서(order)대로 오름차순인지 자동 검증한다. (같은 volume
    안에서만 비교한다 — 권이 바뀌면 페이지 번호가 다시 시작되는 게 정상이므로,
    그걸 "역행했다"고 오판하면 안 된다.)
    - 사용자에게 절대 노출하지 않는다. 이 결과는 endPage 계산 전에 실행되어,
      이상치로 판정된 startPage를 null로 무효화한다 (이미 있는 '페이지 정보
      누락' 처리 경로 -> needsFallback/건너뛰기 로직을 그대로 재사용하기 위함).
    - order 기준으로 순회하면서 이전 값보다 작거나 같은 값이 나오면
      "믿을 수 없는 값"으로 보고 startPage를 null로 지운다.
    - volume이 이전 챕터와 다르면 비교 기준(prev_page)을 리셋한다.
    - 반드시 compute_end_pages보다 먼저 호출해야 한다. 그래야 잘못된 페이지
      번호가 다른 챕터의 endPage 계산까지 오염시키는 것을 막을 수 있다.
    """
    chapters = _flatten_ordered(parsed.get("chapters", []))
    has_anomaly = False
    prev_page = None
    prev_volume = None

    for chapter in chapters:
        chapter_volume = _volume_of(chapter)
        if chapter_volume != prev_volume:
            prev_page = None  # 권이 바뀜 -> 이전 권의 페이지와는 비교하지 않는다
        prev_volume = chapter_volume

        page = chapter.get("startPage")
        if page is None:
            prev_page = None  # 이미 페이지 정보가 없는 항목 -> 기준점 리셋
            continue
        if prev_page is not None and page <= prev_page:
            # 이전 챕터보다 작거나 같은 페이지 -> 명백히 잘못 읽은 값으로 간주
            chapter["startPage"] = None
            chapter["pageOrderAnomaly"] = True
            has_anomaly = True
            # prev_page는 갱신하지 않음 (이 값 자체를 못 믿으므로 기준에서 제외)
            continue
        chapter["pageOrderAnomaly"] = False
        prev_page = page

        # 소단원도 같은 방식으로 챕터 내부 기준 검사 (소단원은 항상 부모와 같은 volume)
        subunits = sorted(chapter.get("subunits", []), key=lambda s: s.get("order", 0))
        sub_prev = None
        for sub in subunits:
            sub_page = sub.get("startPage")
            if sub_page is None:
                sub_prev = None
                continue
            if sub_prev is not None and sub_page <= sub_prev:
                sub["startPage"] = None
                sub["pageOrderAnomaly"] = True
                has_anomaly = True
                continue
            sub["pageOrderAnomaly"] = False
            sub_prev = sub_page
        chapter["subunits"] = subunits

    parsed["chapters"] = chapters
    parsed["_hasPageOrderAnomaly"] = has_anomaly  # 내부용 플래그 (재검증 트리거용, 사용자 비노출)
    return parsed


def postprocess_toc_result(raw_llm_text: str, total_pages=None) -> dict:
    """
    파싱 -> 순서 이상치 탐지/제거 -> endPage 계산 -> 키워드 필터 -> 추정 페이지 수
    순으로 처리하는 진입점.
    (이상치 탐지를 endPage 계산보다 먼저 해야, 잘못된 페이지 번호가
     다른 항목의 endPage 계산까지 오염시키지 않는다.)

    total_pages: int(단일 권 혹은 다권 책의 마지막 권 전체 페이지 수) 또는
                 {volume: 페이지수} 형태의 dict(권마다 아는 만큼).
    """
    parsed = safe_json_parse(raw_llm_text)
    if "error" in parsed:
        return parsed
    parsed = detect_page_order_anomalies(parsed)
    parsed = compute_end_pages(parsed, total_pages=total_pages)
    parsed = apply_non_content_keyword_filter(parsed)
    parsed = add_estimated_page_counts(parsed)
    return parsed
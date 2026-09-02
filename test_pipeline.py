# -*- coding: utf-8 -*-
"""
API 키 없이도 검증 가능한 부분(후처리 로직)을 테스트한다.
실제 LLM이 반환할 법한 응답을 mock으로 만들어서 파이프라인을 검증.
"""
import json
from postprocess import postprocess_toc_result

# 실제 LLM이 반환할 것으로 예상되는 mock 응답
# (일부러 "부록"을 CONTENT로 잘못 분류해둠 -> 키워드 필터가 잡아내는지 검증)
MOCK_LLM_RESPONSE = """
```json
{
  "chapters": [
    { "order": 1, "title": "들어가며", "contentType": "NON_CONTENT", "startPage": 3, "estimatedDifficulty": "medium", "subunits": [] },
    { "order": 2, "title": "1장 개요", "contentType": "CONTENT", "startPage": 7,
      "estimatedDifficulty": "easy",
      "subunits": [
        { "order": 1, "title": "1.1 컴퓨터 시스템", "startPage": 7 },
        { "order": 2, "title": "1.2 프로그래밍 언어", "startPage": 15 }
      ]
    },
    { "order": 3, "title": "2장 자료구조", "contentType": "CONTENT", "startPage": 25,
      "estimatedDifficulty": "hard",
      "subunits": [
        { "order": 1, "title": "2.1 배열과 리스트", "startPage": 25 },
        { "order": 2, "title": "2.2 트리", "startPage": 40 }
      ]
    },
    { "order": 4, "title": "3장 알고리즘", "contentType": "CONTENT", "startPage": 60,
      "estimatedDifficulty": "hard",
      "subunits": [
        { "order": 1, "title": "3.1 정렬", "startPage": 60 },
        { "order": 2, "title": "3.2 탐색", "startPage": null }
      ]
    },
    { "order": 5, "title": "부록: 실습 문제 정답", "contentType": "CONTENT", "startPage": 200, "estimatedDifficulty": "medium", "subunits": [] }
  ]
}
```
"""


def run_test():
    result = postprocess_toc_result(MOCK_LLM_RESPONSE, total_pages=220)

    print("=" * 60)
    print("[검증 1] endPage 계산 결과")
    print("=" * 60)
    for ch in result["chapters"]:
        print(f"  order={ch['order']:<2} {ch['title']:<20} "
              f"startPage={ch['startPage']} endPage={ch['endPage']} "
              f"needsFallback={ch['needsFallback']}")
        for sub in ch.get("subunits", []):
            print(f"      └ {sub['title']:<20} startPage={sub['startPage']} "
                  f"endPage={sub['endPage']} needsFallback={sub['needsFallback']}")

    print()
    print("=" * 60)
    print("[검증 2] NON_CONTENT 키워드 2차 필터 (부록이 CONTENT로 잘못 온 케이스)")
    print("=" * 60)
    appendix = next(c for c in result["chapters"] if "부록" in c["title"])
    print(f"  '{appendix['title']}' -> contentType = {appendix['contentType']}")
    assert appendix["contentType"] == "NON_CONTENT", "키워드 필터가 부록을 못 잡았음!"
    print("  ✅ 통과: LLM이 CONTENT로 잘못 분류했어도 키워드 필터가 NON_CONTENT로 보정함")

    print()
    print("=" * 60)
    print("[검증 3] 페이지 번호 누락(startPage=null) 처리 (3.2 탐색)")
    print("=" * 60)
    ch3 = next(c for c in result["chapters"] if c["order"] == 4)
    missing_sub = next(s for s in ch3["subunits"] if s["title"] == "3.2 탐색")
    print(f"  '{missing_sub['title']}' -> startPage={missing_sub['startPage']}, "
          f"needsFallback={missing_sub['needsFallback']}")
    assert missing_sub["needsFallback"] is True
    print("  ✅ 통과: startPage 누락 항목이 fallback 대상으로 정확히 플래그됨")

    print()
    print("=" * 60)
    print("[검증 4] CONTENT만 필터링 (체크리스트에 노출될 항목)")
    print("=" * 60)
    content_only = [c for c in result["chapters"] if c["contentType"] == "CONTENT"]
    for c in content_only:
        print(f"  ✓ {c['title']}")
    assert len(content_only) == 3, "CONTENT 항목 개수가 예상과 다름"
    print(f"  ✅ 통과: 총 {len(content_only)}개 CONTENT 챕터만 체크리스트 대상으로 남음 "
          f"(들어가며/부록 제외)")

    print()
    print("=" * 60)
    print("전체 통과. 후처리 파이프라인(JSON 파싱/endPage 계산/키워드필터)은 정상 동작.")
    print("남은 것: 실제 목차 이미지/PDF + ANTHROPIC_API_KEY로 api_call.py 실제 호출 테스트")
    print("=" * 60)


# 실전 검증(자바 책 목차 사진)에서 발견된 버그에 대한 회귀 테스트
# PART 구분자("첫째마당" 등, startPage=null)가 챕터 사이에 끼어 있으면
# 구분자 바로 앞 챕터의 endPage가 null로 끊기던 문제
MOCK_LLM_RESPONSE_WITH_PART_DIVIDER = """
{
  "chapters": [
    { "order": 1, "title": "첫째마당 | 자바 기본 익히기", "contentType": "NON_CONTENT",
      "startPage": null, "estimatedDifficulty": "medium", "subunits": [] },
    { "order": 2, "title": "04 제어 흐름 이해하기", "contentType": "CONTENT",
      "startPage": 91, "estimatedDifficulty": "medium",
      "subunits": [
        { "order": 1, "title": "04-1 조건문이란?", "startPage": 91 },
        { "order": 2, "title": "04-2 반복문이란?", "startPage": 107 }
      ]
    },
    { "order": 3, "title": "둘째마당 | 객체 지향 프로그래밍", "contentType": "NON_CONTENT",
      "startPage": null, "estimatedDifficulty": "medium", "subunits": [] },
    { "order": 4, "title": "05 클래스와 객체", "contentType": "CONTENT",
      "startPage": 126, "estimatedDifficulty": "medium", "subunits": [] }
  ]
}
"""


def run_test_part_divider_regression():
    print()
    print("=" * 60)
    print("[회귀 테스트] PART 구분자가 끼어 있어도 endPage가 끊기지 않는지 확인")
    print("=" * 60)
    result = postprocess_toc_result(MOCK_LLM_RESPONSE_WITH_PART_DIVIDER, total_pages=200)

    ch04 = next(c for c in result["chapters"] if "04" in c["title"])
    print(f"  '{ch04['title']}' -> endPage = {ch04['endPage']} (기대값: 125, 05장 startPage 126의 -1)")
    assert ch04["endPage"] == 125, f"버그 재발! endPage가 {ch04['endPage']}로 나옴 (null이면 안 됨)"
    print("  ✅ 통과: 구분자를 건너뛰고 그 다음 진짜 챕터(05장, 126페이지)를 찾아 계산함")

    sub04_2 = next(s for s in ch04["subunits"] if s["order"] == 2)
    print(f"  └ '{sub04_2['title']}' -> endPage = {sub04_2['endPage']} (기대값: 125, 챕터 endPage 상속)")
    assert sub04_2["endPage"] == 125
    print("  ✅ 통과: 마지막 소단원도 챕터 endPage를 정상적으로 상속받음")


def run_test_true_last_chapter_no_total_pages():
    """
    뒤에 참조할 항목도 없고 total_pages도 안 넘긴, '진짜 마지막' 케이스.
    endPage는 null이 맞지만, needsFallback=True로 명시적으로 플래그되어야
    프론트에서 "페이지 정보 부족"임을 구분해 보여줄 수 있다.
    """
    print()
    print("=" * 60)
    print("[검증 5] 진짜 마지막 챕터, total_pages 미제공 -> needsFallback 플래그 확인")
    print("=" * 60)
    mock = """
    {
      "chapters": [
        { "order": 1, "title": "1장 개요", "contentType": "CONTENT",
          "startPage": 10, "estimatedDifficulty": "easy", "subunits": [] },
        { "order": 2, "title": "2장 마무리", "contentType": "CONTENT",
          "startPage": 50, "estimatedDifficulty": "easy", "subunits": [] }
      ]
    }
    """
    result = postprocess_toc_result(mock, total_pages=None)
    last_ch = result["chapters"][-1]
    print(f"  '{last_ch['title']}' -> endPage={last_ch['endPage']}, needsFallback={last_ch['needsFallback']}")
    assert last_ch["endPage"] is None
    assert last_ch["needsFallback"] is True
    print("  ✅ 통과: endPage는 null이지만 needsFallback=True로 명시되어 프론트에서 구분 가능")

    print()
    print("  (참고) total_pages=120으로 다시 계산하면:")
    result2 = postprocess_toc_result(mock, total_pages=120)
    last_ch2 = result2["chapters"][-1]
    print(f"  '{last_ch2['title']}' -> endPage={last_ch2['endPage']}, needsFallback={last_ch2['needsFallback']}")
    assert last_ch2["endPage"] == 120
    assert last_ch2["needsFallback"] is False
    print("  ✅ 통과: total_pages 제공 시 정상적으로 채워지고 needsFallback도 False로 내려감")


if __name__ == "__main__":
    run_test()
    run_test_part_divider_regression()
    run_test_true_last_chapter_no_total_pages()


def run_test_page_order_anomaly():
    """
    실전 검증(전기이론 교재)에서 발견된 사례 재현:
    CHAPTER 07(54) -> CHAPTER 08(82, 실제로는 76이어야 함) -> CHAPTER 09(null, 실제로는 82)
    처럼 순서가 어긋난 값이 오면, 사용자 개입 없이 자동으로 무효화되고
    needsFallback으로 안전하게 넘어가야 한다.
    """
    print()
    print("=" * 60)
    print("[검증 6] 페이지 순서 역전 자동 탐지 (사용자 비노출, 완전 자동 처리)")
    print("=" * 60)
    mock = """
    {
      "chapters": [
        { "order": 1, "title": "CHAPTER 06 전자유도 법칙과 인덕턴스", "contentType": "CONTENT",
          "startPage": 44, "estimatedDifficulty": "medium", "subunits": [] },
        { "order": 2, "title": "CHAPTER 07 교류회로", "contentType": "CONTENT",
          "startPage": 54, "estimatedDifficulty": "medium", "subunits": [] },
        { "order": 3, "title": "CHAPTER 08 3상 교류회로", "contentType": "CONTENT",
          "startPage": 82, "estimatedDifficulty": "medium", "subunits": [] },
        { "order": 4, "title": "CHAPTER 09 비정현파", "contentType": "CONTENT",
          "startPage": null, "estimatedDifficulty": "medium", "subunits": [] },
        { "order": 5, "title": "CHAPTER 10 다음 과목", "contentType": "CONTENT",
          "startPage": 88, "estimatedDifficulty": "medium", "subunits": [] }
      ]
    }
    """
    result = postprocess_toc_result(mock, total_pages=None)
    for ch in result["chapters"]:
        print(f"  {ch['title']:<25} startPage={ch['startPage']} endPage={ch['endPage']} "
              f"needsFallback={ch['needsFallback']} anomaly={ch.get('pageOrderAnomaly')}")

    ch08 = next(c for c in result["chapters"] if "08" in c["title"])
    ch09 = next(c for c in result["chapters"] if "09" in c["title"])

    # CHAPTER 08은 82라는 '이상치'가 무효화되어 startPage=None, needsFallback=True가 되어야 함
    assert ch08["startPage"] is None, "이상치가 무효화되지 않음!"
    assert ch08["needsFallback"] is True
    print("  ✅ 통과: CHAPTER 08의 잘못된 startPage(82)가 자동으로 무효화되고 fallback 처리됨")

    # CHAPTER 09는 원래도 null이었으니 그대로 needsFallback
    assert ch09["startPage"] is None
    assert ch09["needsFallback"] is True
    print("  ✅ 통과: CHAPTER 09도 fallback 대상으로 정상 처리됨")

    # CHAPTER 10(88)은 정상 값이므로 살아있어야 하고, endPage 계산의 기준점으로 쓰여야 함
    ch10 = next(c for c in result["chapters"] if "10" in c["title"])
    assert ch10["startPage"] == 88
    print("  ✅ 통과: 정상적인 다음 챕터(88페이지)는 그대로 유지됨")

    # 내부 플래그로 '재검증이 필요했다'는 신호가 남아있는지 (사용자에게는 노출 안 됨)
    assert result["_hasPageOrderAnomaly"] is True
    print("  ✅ 통과: 내부 신호(_hasPageOrderAnomaly)만 세워지고 사용자 노출 필드는 없음")
    print()
    print("  → 사용자는 이 과정을 전혀 모른 채, 08/09 구간만 조용히 균등 배분으로 넘어가")
    print("    최종 학습플랜에는 자연스럽게 반영됨 (별도 확인/수정 요청 없음)")


run_test_page_order_anomaly()
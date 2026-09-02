# -*- coding: utf-8 -*-
"""
Anthropic API 호출부.
- ANTHROPIC_API_KEY 환경변수가 필요하다 (아직 발급 전이면 이 파일은 호출만 안 될 뿐,
  나머지 파이프라인은 mock 데이터로 테스트 가능하다 -> test_pipeline.py 참고).
- 사진(vision) 경로는 1차 파싱 후, 같은 이미지로 자기검증(self-verification)을
  한 번 더 거친다. 채팅에서 사람이 결과와 사진을 대조해 오류를 잡아주던 것을
  자동화한 것 -> 사용자 개입 없이 정확도를 끌어올리는 목적.
- 목차 사진은 여러 장(예: 목차 1페이지 사진 + 2페이지 사진)으로 나뉠 수 있어서,
  parse_toc_from_images()는 여러 장을 한 메시지에 같이 넣어 하나의 목차로 이어 읽게 한다.
"""
import os
import json
from anthropic import Anthropic

from prompt import TOC_PARSING_PROMPT
from postprocess import postprocess_toc_result, safe_json_parse

MODEL_NAME = "claude-sonnet-5"

SELF_VERIFICATION_PROMPT = """방금 네가 이 목차 이미지를 분석해서 아래 JSON을 만들었다.

[1차 결과]
{first_pass_json}

이미지를 다시 자세히 보고, 특히 다음을 중점적으로 재검토해라:
1. 각 항목의 startPage가 이미지에 실제로 인쇄된 숫자와 정확히 일치하는가?
2. **가장 흔하고 치명적인 실수: 페이지 번호가 한 칸씩 밀려서 배정되는 것.**
   각 항목의 제목과 페이지 번호가 실제로 이미지에서 같은 가로줄(행)에
   있는 게 맞는지 하나씩 손가락으로 짚듯이 확인해라. 예를 들어 항목 A의
   페이지 번호로 되어 있는 값이 사실 이미지에서는 바로 다음 항목 B의 줄에
   더 가깝게 인쇄되어 있다면, 그건 밀림 실수다. 이 경우 A, B, C... 전체
   목록의 페이지 번호를 한 칸씩 앞으로 당겨서 다시 짝지어야 한다.
3. 페이지 번호가 챕터/섹션 순서대로 오름차순인가? (뒤 항목이 앞 항목보다 페이지가
   작거나 같으면 잘못 읽은 것이다. 단, 오름차순이라고 해서 안심하지 말 것 —
   전체가 한 칸씩 밀려도 오름차순 자체는 유지되므로 이 검사만으로는
   밀림을 걸러낼 수 없다. 반드시 2번처럼 행 단위로 직접 대조해라.)
4. startPage를 null로 남긴 항목이 있다면, 이미지에서 정말 안 보이는 게 맞는지
   다시 한번 확인해라 (특히 위아래 항목과 줄이 헷갈렸을 가능성을 의심해라)
5. 챕터/섹션 제목 자체가 정확한가?
6. 이미지가 여러 장 주어졌다면, 장 사이의 이어짐(예: 1번째 이미지 마지막 항목
   다음에 2번째 이미지 첫 항목이 자연스럽게 이어지는지)도 확인해라.

수정 과정을 짧게 텍스트로 정리해도 되지만, 최종 결과는 반드시 ```json
코드블록 하나로 감싸서 출력하고, 코드블록 안에는 JSON 외의 텍스트를 넣지 마라.
"""


def _get_client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다. "
            "console.anthropic.com에서 키를 발급받아 설정해주세요."
        )
    return Anthropic(api_key=api_key)


def parse_toc_from_text(toc_text: str, total_pages: int | None = None, max_retries: int = 2) -> dict:
    """PDF에서 추출한 목차 텍스트를 LLM에 넘겨 구조화된 JSON을 얻는다."""
    client = _get_client()
    last_error = None

    for attempt in range(max_retries + 1):
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=8000,
            messages=[
                {"role": "user", "content": TOC_PARSING_PROMPT + "\n\n[입력 목차 텍스트]\n" + toc_text}
            ],
        )
        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        try:
            return postprocess_toc_result(raw_text, total_pages=total_pages)
        except Exception as e:  # JSON 파싱 실패 등
            last_error = e
            continue

    raise RuntimeError(f"목차 파싱 실패 (재시도 {max_retries}회 소진): {last_error}")


def _call_vision_once(client: Anthropic, images: list[dict], prompt_text: str) -> str:
    """
    이미지 여러 장 + 프롬프트로 1회 호출하고 텍스트 응답을 반환하는 내부 헬퍼.
    images: [{"data": base64_str, "media_type": "image/jpeg"}, ...] 순서대로
            한 메시지 안에 같이 담아 보낸다 (여러 장이어도 API 호출은 1번).
    """
    content = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": img["media_type"], "data": img["data"]},
        }
        for img in images
    ]
    content.append({"type": "text", "text": prompt_text})

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=8000,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )


def parse_toc_from_images(images: list[dict], total_pages: int | None = None,
                           max_retries: int = 2, self_verify: bool = True) -> dict:
    """
    목차 사진 한 장 이상(base64 리스트)을 vision 모델에 한 번에 넘겨 구조화된 JSON을 얻는다.
    images: [{"data": base64_str, "media_type": "image/jpeg"}, ...]
    - 목차가 여러 장으로 나뉘어 촬영된 경우(예: 1페이지/2페이지 따로 찍음), 프롬프트가
      이걸 하나의 목차로 이어 붙여 처리하도록 지시한다.
    - self_verify=True(기본값)면, 1차 결과를 같은 이미지들로 한 번 더 검증/보정한다.
      이 과정은 전부 자동으로 이루어지며 사용자에게는 노출되지 않는다.
    """
    client = _get_client()
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            raw_text = _call_vision_once(client, images, TOC_PARSING_PROMPT)

            if self_verify:
                try:
                    first_pass_parsed = safe_json_parse(raw_text)
                    verify_prompt = SELF_VERIFICATION_PROMPT.format(
                        first_pass_json=json.dumps(first_pass_parsed, ensure_ascii=False, indent=2)
                    )
                    verified_text = _call_vision_once(client, images, verify_prompt)
                    raw_text = verified_text
                except Exception:
                    pass

            return postprocess_toc_result(raw_text, total_pages=total_pages)
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"목차 파싱 실패 (재시도 {max_retries}회 소진): {last_error}")


def parse_toc_from_image(image_base64: str, media_type: str = "image/jpeg",
                          total_pages: int | None = None, max_retries: int = 2,
                          self_verify: bool = True) -> dict:
    """
    목차 사진 한 장짜리 버전 (하위 호환용). 내부적으로 parse_toc_from_images를 호출한다.
    """
    return parse_toc_from_images(
        [{"data": image_base64, "media_type": media_type}],
        total_pages=total_pages, max_retries=max_retries, self_verify=self_verify,
    )
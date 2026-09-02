# -*- coding: utf-8 -*-
"""
PDF에서 목차로 추정되는 페이지의 텍스트를 추출한다.
텍스트 레이어가 있는 PDF 전제 (스캔본은 vision 경로로 처리 필요).
"""
import pdfplumber

# 목차 페이지를 자동으로 찾기 위한 단순 휴리스틱 키워드
TOC_HINT_KEYWORDS = ["목차", "차례", "Contents", "CONTENTS", "Table of Contents"]


def extract_text_from_pages(pdf_path: str, page_indices: list[int]) -> str:
    """지정한 페이지(0-indexed)들의 텍스트를 이어붙여 반환한다."""
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for idx in page_indices:
            if 0 <= idx < len(pdf.pages):
                page_text = pdf.pages[idx].extract_text() or ""
                texts.append(page_text)
    return "\n".join(texts)


def find_toc_page_candidates(pdf_path: str, max_scan_pages: int = 15) -> list[int]:
    """
    앞부분 max_scan_pages 페이지 중, 목차로 추정되는 페이지 인덱스를 찾는다.
    - 키워드("목차", "차례", "Contents")가 있거나
    - 페이지 번호 패턴(마침표 리더, 숫자로 끝나는 줄)이 많이 등장하는 페이지를 후보로 봄.
    """
    candidates = []
    with pdfplumber.open(pdf_path) as pdf:
        scan_range = min(max_scan_pages, len(pdf.pages))
        for i in range(scan_range):
            text = pdf.pages[i].extract_text() or ""
            if any(kw in text for kw in TOC_HINT_KEYWORDS):
                candidates.append(i)
                continue
            # 숫자로 끝나는 줄이 여러 개 있으면 목차일 가능성 (페이지번호 패턴)
            lines = text.splitlines()
            numeric_ending_lines = sum(
                1 for line in lines if line.strip() and line.strip()[-1].isdigit()
            )
            if numeric_ending_lines >= 5:
                candidates.append(i)
    return candidates


def extract_toc_text(pdf_path: str) -> str:
    """목차 후보 페이지들을 자동 탐색해서 텍스트로 반환하는 편의 함수."""
    candidates = find_toc_page_candidates(pdf_path)
    if not candidates:
        # 후보를 못 찾으면 앞 5페이지를 그냥 넘겨서 LLM이 스스로 판단하게 함
        candidates = list(range(min(5, 999)))
    return extract_text_from_pages(pdf_path, candidates)

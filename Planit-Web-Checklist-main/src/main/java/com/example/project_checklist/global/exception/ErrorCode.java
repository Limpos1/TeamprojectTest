package com.example.project_checklist.global.exception;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@RequiredArgsConstructor
public enum ErrorCode {

    STUDY_PLAN_ITEM_NOT_FOUND(HttpStatus.NOT_FOUND, "해당 학습 계획 항목을 찾을 수 없습니다."),
    STUDY_PLAN_ITEM_ACCESS_DENIED(HttpStatus.FORBIDDEN, "본인의 학습 계획 항목만 조회/체크할 수 있습니다."),
    INVALID_PROGRESS_RATE(HttpStatus.BAD_REQUEST, "진행률은 0, 25, 50, 75, 100 중 하나여야 합니다."),
    STUDY_PLAN_ITEMS_EMPTY_FOR_DATE(HttpStatus.BAD_REQUEST, "해당 날짜에 등록된 학습 계획이 없어 오늘 학습을 마무리할 수 없습니다.");

    private final HttpStatus status;
    private final String message;
}

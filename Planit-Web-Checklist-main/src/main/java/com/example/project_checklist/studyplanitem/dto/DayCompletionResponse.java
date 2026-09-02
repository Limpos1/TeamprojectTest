package com.example.project_checklist.studyplanitem.dto;

import java.time.LocalDate;
import java.time.LocalDateTime;
import lombok.Builder;
import lombok.Getter;

/** "오늘 학습 마무리하기" 요청에 대한 응답. */
@Getter
@Builder
public class DayCompletionResponse {

    private LocalDate date;
    private boolean completed;
    private LocalDateTime completedAt;
}

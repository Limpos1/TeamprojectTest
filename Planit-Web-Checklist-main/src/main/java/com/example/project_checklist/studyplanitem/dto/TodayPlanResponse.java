package com.example.project_checklist.studyplanitem.dto;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import lombok.Builder;
import lombok.Getter;

/**
 * "오늘 할 일" 화면 응답. items 는 항목별 리스트, todayProgressRate 는 그날 항목들의
 * progressRate 단순 평균(반올림, 0~100)입니다. 항목이 하나도 없으면 0입니다.
 *
 * dayCompleted 는 "오늘 학습 마무리하기" 버튼으로 이 날짜를 완료 처리했는지 여부입니다.
 * (items 가 전부 100%인지와는 별개로, 실제로 마무리 버튼을 눌러 기록을 남겼는지를 나타냅니다.)
 */
@Getter
@Builder
public class TodayPlanResponse {

    private LocalDate date;
    private int todayProgressRate;
    private boolean dayCompleted;
    private LocalDateTime dayCompletedAt;
    private List<StudyPlanItemResponse> items;
}

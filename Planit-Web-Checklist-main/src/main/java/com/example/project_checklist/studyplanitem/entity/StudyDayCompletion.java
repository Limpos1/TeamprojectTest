package com.example.project_checklist.studyplanitem.entity;

import com.google.cloud.Timestamp;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * Firestore "study_day_completions" 컬렉션 문서 매핑.
 *
 * "오늘 학습 마무리하기" 버튼을 눌러서 그 날짜의 학습을 완료 처리했다는 사실을 기록하는
 * 컬렉션입니다. 문서 id를 "{studyPlanId}_{planDate}" 형태로 고정해서, study_plan_id +
 * plan_date 조합이 자연스럽게 유일해지도록(하루 1회만 기록) 설계했습니다
 * (StudyDayCompletionRepository#docId 참고). 이미 기록이 있으면 새로 만들지 않고
 * 기존 기록을 그대로 반환합니다 (StudyPlanItemService#completeToday 참고).
 *
 * completedAt 은 별도 필드를 두지 않고 createdAt(이 문서가 생성된 시각 = 완료 처리한 시각)을
 * 그대로 사용합니다.
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StudyDayCompletion {

    private String studyPlanId;

    /** "yyyy-MM-dd" 형식의 ISO 날짜 문자열. */
    private String planDate;

    private Timestamp createdAt;
}

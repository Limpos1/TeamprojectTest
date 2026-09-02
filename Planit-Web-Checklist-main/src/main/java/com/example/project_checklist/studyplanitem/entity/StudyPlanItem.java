package com.example.project_checklist.studyplanitem.entity;

import com.google.cloud.Timestamp;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * Firestore "study_plan_items" 컬렉션 문서 매핑.
 * 담당 요구사항: REQ-F-050~056 (오늘의 학습 계획 조회/체크).
 *
 * [MySQL/JPA -> Firestore 전환 메모]
 * 예전에는 study_plan 테이블을 거쳐 회원을 조회했지만(관계형 FK), Firestore는 join을
 * 지원하지 않아서 조회에 필요한 memberId/studyPlanId 를 문서에 직접 저장합니다(비정규화).
 * 문서 id는 Firestore가 자동 생성하는 String 이라 기존 MySQL의 Long id와 타입이 다릅니다
 * (문서 안에는 저장하지 않고, 조회 시 documentId를 꺼내서 id 필드에 채워 넣습니다 -
 * StudyPlanItemRepository#toEntity 참고).
 *
 * 완료 여부는 boolean 이 아니라 0/25/50/75/100 다섯 단계의 진행률(progressRate)로 관리합니다.
 * "오늘 진행률"(당일 전체 진행률)은 별도로 저장하지 않고, 조회 시점에 그날 항목들의
 * progressRate 단순 평균으로 계산합니다 (StudyPlanItemService 참고).
 *
 * 화면 목업 기준 항목별 시간대 표시(예: "09:00 – 10:30", "저녁 · 30분")를 위해
 * startTime/endTime/durationMinutes 를 둡니다. 시간이 고정된 항목은 startTime/endTime을
 * "HH:mm" 문자열로 채우고, 시간이 고정되지 않은 항목(자동 추가된 복습 등)은 durationMinutes만
 * 채우고 startTime/endTime 은 null로 둡니다.
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StudyPlanItem {

    /** Firestore 문서 id. 문서 데이터 자체에는 저장하지 않습니다. */
    private String id;

    /** Firebase Auth uid (문자열). 로그인 파트가 세션에 저장하는 값과 동일하게 맞춘다. */
    private String memberId;

    private String studyPlanId;

    /** "yyyy-MM-dd" 형식의 ISO 날짜 문자열로 저장합니다. */
    private String planDate;

    private String subject;

    private String content;

    /** 계획된 시작 시각("HH:mm"). 시간대가 정해지지 않은 항목은 null. */
    private String startTime;

    /** 계획된 종료 시각("HH:mm"). startTime 과 함께 사용, null 가능. */
    private String endTime;

    /** startTime/endTime 이 없을 때 화면에 보여줄 예상 소요 시간(분). */
    private Integer durationMinutes;

    private int sortOrder;

    /** 0, 25, 50, 75, 100 중 하나. 100이면 완료로 간주합니다. */
    private int progressRate;

    private Timestamp completedAt;

    private Timestamp createdAt;

    private Timestamp updatedAt;

    /**
     * REQ-F-050~054: 학습 진행률 체크. progressRate 가 100이 되는 순간 완료 일시를 기록하고,
     * 100 미만으로 다시 바뀌면 완료 일시를 비웁니다.
     * 값 검증(0/25/50/75/100 인지)은 서비스 계층에서 먼저 확인한 뒤 호출합니다.
     */
    public void updateProgress(int progressRate) {
        this.progressRate = progressRate;
        this.completedAt = (progressRate == 100) ? Timestamp.now() : null;
    }

    public boolean isCompleted() {
        return this.progressRate == 100;
    }
}
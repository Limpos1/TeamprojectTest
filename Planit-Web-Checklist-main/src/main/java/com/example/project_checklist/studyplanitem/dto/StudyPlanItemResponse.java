package com.example.project_checklist.studyplanitem.dto;

import com.example.project_checklist.studyplanitem.entity.StudyPlanItem;
import com.google.cloud.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import lombok.Builder;
import lombok.Getter;

/**
 * [MySQL/JPA -> Firestore 전환 메모] id 가 Long -> String 으로 바뀌었습니다
 * (Firestore 문서 id는 자동 생성되는 문자열입니다). planDate/startTime/endTime 등
 * JSON으로 내려가는 모양은 기존과 동일하게 유지했습니다(내부적으로는 문자열로 저장되어 있는 값을
 * 여기서 LocalDate/시간 문자열로 변환).
 */
@Getter
@Builder
public class StudyPlanItemResponse {

    private String id;
    private String subject;
    private String content;
    private LocalDate planDate;
    private String startTime;
    private String endTime;
    private Integer durationMinutes;
    private int sortOrder;
    private int progressRate;
    private boolean completed;
    private LocalDateTime completedAt;

    public static StudyPlanItemResponse from(StudyPlanItem item) {
        return StudyPlanItemResponse.builder()
                .id(item.getId())
                .subject(item.getSubject())
                .content(item.getContent())
                .planDate(item.getPlanDate() != null ? LocalDate.parse(item.getPlanDate()) : null)
                .startTime(item.getStartTime())
                .endTime(item.getEndTime())
                .durationMinutes(item.getDurationMinutes())
                .sortOrder(item.getSortOrder())
                .progressRate(item.getProgressRate())
                .completed(item.isCompleted())
                .completedAt(toLocalDateTime(item.getCompletedAt()))
                .build();
    }

    private static LocalDateTime toLocalDateTime(Timestamp timestamp) {
        if (timestamp == null) {
            return null;
        }
        return LocalDateTime.ofInstant(
                Instant.ofEpochSecond(timestamp.getSeconds(), timestamp.getNanos()),
                ZoneId.systemDefault());
    }
}

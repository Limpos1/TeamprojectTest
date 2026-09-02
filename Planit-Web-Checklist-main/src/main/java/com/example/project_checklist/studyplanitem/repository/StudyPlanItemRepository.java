package com.example.project_checklist.studyplanitem.repository;

import com.example.project_checklist.studyplanitem.entity.StudyPlanItem;
import com.google.api.core.ApiFuture;
import com.google.cloud.Timestamp;
import com.google.cloud.firestore.DocumentReference;
import com.google.cloud.firestore.DocumentSnapshot;
import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.QueryDocumentSnapshot;
import com.google.cloud.firestore.QuerySnapshot;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ExecutionException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Repository;

/**
 * Firestore "study_plan_items" 컬렉션 접근 레이어.
 * 예전 JpaRepository 인터페이스 대신, Firestore Admin SDK(Firestore 빈)를 직접 감싼 클래스입니다.
 *
 * 주의: memberId + planDate 로 필터링하고 sortOrder 로 정렬하는 쿼리는 Firestore에서
 * 복합 색인(composite index)이 필요할 수 있습니다. 앱을 처음 실행하고 이 쿼리를 처음
 * 호출했을 때 콘솔/로그에 "The query requires an index..." 같은 에러와 함께 색인을 바로
 * 만들 수 있는 링크가 뜨면, 그 링크를 클릭해서 색인을 만들고 1~2분 기다린 뒤 다시 시도하세요.
 */
@Repository
@RequiredArgsConstructor
public class StudyPlanItemRepository {

    private static final String COLLECTION = "study_plan_items";

    private final Firestore firestore;

    /**
     * REQ-F-050~054: 특정 회원의 특정 날짜 학습 계획 리스트를
     * 하루 내 표시 순서(sortOrder) 기준으로 조회합니다.
     */
    public List<StudyPlanItem> findByMemberIdAndPlanDate(String memberId, LocalDate planDate) {
        try {
            ApiFuture<QuerySnapshot> future = firestore.collection(COLLECTION)
                    .whereEqualTo("memberId", memberId)
                    .whereEqualTo("planDate", planDate.toString())
                    .orderBy("sortOrder")
                    .get();
            List<QueryDocumentSnapshot> docs = future.get().getDocuments();
            return docs.stream().map(this::toEntity).toList();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Firestore 조회 중 인터럽트가 발생했습니다.", e);
        } catch (ExecutionException e) {
            throw new IllegalStateException("Firestore 조회에 실패했습니다.", e);
        }
    }

    public Optional<StudyPlanItem> findById(String id) {
        try {
            DocumentSnapshot doc = firestore.collection(COLLECTION).document(id).get().get();
            return doc.exists() ? Optional.of(toEntity(doc)) : Optional.empty();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Firestore 조회 중 인터럽트가 발생했습니다.", e);
        } catch (ExecutionException e) {
            throw new IllegalStateException("Firestore 조회에 실패했습니다.", e);
        }
    }

    /** 새 문서면 id를 자동 생성해서 저장하고, 기존 id가 있으면 그 문서를 덮어씁니다. */
    public StudyPlanItem save(StudyPlanItem item) {
        try {
            Timestamp now = Timestamp.now();
            DocumentReference ref = (item.getId() == null)
                    ? firestore.collection(COLLECTION).document()
                    : firestore.collection(COLLECTION).document(item.getId());

            ref.set(toMap(item, now)).get();

            item.setId(ref.getId());
            if (item.getCreatedAt() == null) {
                item.setCreatedAt(now);
            }
            item.setUpdatedAt(now);
            return item;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Firestore 저장 중 인터럽트가 발생했습니다.", e);
        } catch (ExecutionException e) {
            throw new IllegalStateException("Firestore 저장에 실패했습니다.", e);
        }
    }

    private Map<String, Object> toMap(StudyPlanItem item, Timestamp now) {
        Map<String, Object> data = new HashMap<>();
        data.put("memberId", item.getMemberId());
        data.put("studyPlanId", item.getStudyPlanId());
        data.put("planDate", item.getPlanDate());
        data.put("subject", item.getSubject());
        data.put("content", item.getContent());
        data.put("sortOrder", item.getSortOrder());
        data.put("progressRate", item.getProgressRate());
        data.put("completedAt", item.getCompletedAt());
        data.put("startTime", item.getStartTime());
        data.put("endTime", item.getEndTime());
        data.put("durationMinutes", item.getDurationMinutes());
        data.put("createdAt", item.getCreatedAt() != null ? item.getCreatedAt() : now);
        data.put("updatedAt", now);
        return data;
    }

    private StudyPlanItem toEntity(DocumentSnapshot doc) {
        return StudyPlanItem.builder()
                .id(doc.getId())
                .memberId(doc.getString("memberId"))
                .studyPlanId(doc.getString("studyPlanId"))
                .planDate(doc.getString("planDate"))
                .subject(doc.getString("subject"))
                .content(doc.getString("content"))
                .sortOrder(doc.getLong("sortOrder") == null ? 0 : doc.getLong("sortOrder").intValue())
                .progressRate(doc.getLong("progressRate") == null ? 0 : doc.getLong("progressRate").intValue())
                .completedAt(doc.getTimestamp("completedAt"))
                .startTime(doc.getString("startTime"))
                .endTime(doc.getString("endTime"))
                .durationMinutes(doc.getLong("durationMinutes") == null ? null : doc.getLong("durationMinutes").intValue())
                .createdAt(doc.getTimestamp("createdAt"))
                .updatedAt(doc.getTimestamp("updatedAt"))
                .build();
    }
}
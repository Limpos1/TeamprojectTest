package com.example.project_checklist.studyplanitem.repository;

import com.example.project_checklist.studyplanitem.entity.StudyDayCompletion;
import com.google.cloud.Timestamp;
import com.google.cloud.firestore.DocumentSnapshot;
import com.google.cloud.firestore.Firestore;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ExecutionException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Repository;

/**
 * Firestore "study_day_completions" 컬렉션 접근 레이어.
 * 문서 id를 "{studyPlanId}_{planDate}"로 고정해서 하루에 한 번만 기록되도록(멱등) 합니다.
 */
@Repository
@RequiredArgsConstructor
public class StudyDayCompletionRepository {

    private static final String COLLECTION = "study_day_completions";

    private final Firestore firestore;

    private String docId(String studyPlanId, LocalDate planDate) {
        return studyPlanId + "_" + planDate;
    }

    public Optional<StudyDayCompletion> findByStudyPlanIdAndPlanDate(String studyPlanId, LocalDate planDate) {
        try {
            DocumentSnapshot doc = firestore.collection(COLLECTION)
                    .document(docId(studyPlanId, planDate))
                    .get()
                    .get();
            if (!doc.exists()) {
                return Optional.empty();
            }
            return Optional.of(StudyDayCompletion.builder()
                    .studyPlanId(doc.getString("studyPlanId"))
                    .planDate(doc.getString("planDate"))
                    .createdAt(doc.getTimestamp("createdAt"))
                    .build());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Firestore 조회 중 인터럽트가 발생했습니다.", e);
        } catch (ExecutionException e) {
            throw new IllegalStateException("Firestore 조회에 실패했습니다.", e);
        }
    }

    public StudyDayCompletion save(StudyDayCompletion completion) {
        try {
            Timestamp now = Timestamp.now();
            Map<String, Object> data = new HashMap<>();
            data.put("studyPlanId", completion.getStudyPlanId());
            data.put("planDate", completion.getPlanDate());
            data.put("createdAt", now);

            firestore.collection(COLLECTION)
                    .document(docId(completion.getStudyPlanId(), LocalDate.parse(completion.getPlanDate())))
                    .set(data)
                    .get();

            completion.setCreatedAt(now);
            return completion;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Firestore 저장 중 인터럽트가 발생했습니다.", e);
        } catch (ExecutionException e) {
            throw new IllegalStateException("Firestore 저장에 실패했습니다.", e);
        }
    }
}

package com.example.project_checklist.studyplanitem.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;

import com.example.project_checklist.global.exception.CustomException;
import com.example.project_checklist.studyplanitem.dto.DayCompletionResponse;
import com.example.project_checklist.studyplanitem.dto.StudyPlanItemResponse;
import com.example.project_checklist.studyplanitem.dto.TodayPlanResponse;
import com.example.project_checklist.studyplanitem.entity.StudyDayCompletion;
import com.example.project_checklist.studyplanitem.entity.StudyPlanItem;
import com.example.project_checklist.studyplanitem.repository.StudyDayCompletionRepository;
import com.example.project_checklist.studyplanitem.repository.StudyPlanItemRepository;
import com.google.cloud.Timestamp;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

/**
 * [MySQL/JPA -> Firestore 전환 메모] 예전에는 StudyPlan/Member 스텁 엔티티로 연관관계를
 * 흉내내야 했지만, Firestore로 옮기면서 memberId/studyPlanId 를 평범한 필드로 직접 갖게 되어
 * 테스트가 훨씬 단순해졌습니다. 리포지토리들은 이제 인터페이스가 아니라 클래스라서
 * @Mock 이 Mockito로 그대로 목킹됩니다(생성자는 호출되지 않으므로 Firestore 빈 없이도 동작).
 */
@ExtendWith(MockitoExtension.class)
class StudyPlanItemServiceTest {

    @Mock
    private StudyPlanItemRepository studyPlanItemRepository;

    @Mock
    private StudyDayCompletionRepository studyDayCompletionRepository;

    private StudyPlanItemService studyPlanItemService;

    private StudyPlanItem itemOf(String memberId, String studyPlanId, String id, int progressRate) {
        return StudyPlanItem.builder()
                .id(id)
                .memberId(memberId)
                .studyPlanId(studyPlanId)
                .planDate(LocalDate.now().toString())
                .subject("자료구조")
                .content("3단원 정리")
                .sortOrder(1)
                .progressRate(progressRate)
                .build();
    }

    @Test
    void 오늘의_계획을_조회하면_항목_리스트와_함께_진행률_평균이_반환된다() {
        studyPlanItemService = new StudyPlanItemService(studyPlanItemRepository, studyDayCompletionRepository);
        LocalDate today = LocalDate.now();
        given(studyPlanItemRepository.findByMemberIdAndPlanDate("uid1", today))
                .willReturn(List.of(
                        itemOf("uid1", "plan1", "item100", 100),
                        itemOf("uid1", "plan1", "item101", 50),
                        itemOf("uid1", "plan1", "item102", 0),
                        itemOf("uid1", "plan1", "item103", 75)));

        TodayPlanResponse result = studyPlanItemService.getTodayPlan("uid1", today);

        assertThat(result.getItems()).hasSize(4);
        assertThat(result.getTodayProgressRate()).isEqualTo(56); // (100+50+0+75)/4 = 56.25 -> 반올림 56
        assertThat(result.isDayCompleted()).isFalse(); // 완료 기록이 없으므로 false
    }

    @Test
    void 항목이_없으면_오늘_진행률은_0이고_마무리_여부도_false다() {
        studyPlanItemService = new StudyPlanItemService(studyPlanItemRepository, studyDayCompletionRepository);
        LocalDate today = LocalDate.now();
        given(studyPlanItemRepository.findByMemberIdAndPlanDate("uid1", today)).willReturn(List.of());

        TodayPlanResponse result = studyPlanItemService.getTodayPlan("uid1", today);

        assertThat(result.getTodayProgressRate()).isEqualTo(0);
        assertThat(result.isDayCompleted()).isFalse();
    }

    @Test
    void 진행률을_100으로_체크하면_완료일시가_기록된다() {
        studyPlanItemService = new StudyPlanItemService(studyPlanItemRepository, studyDayCompletionRepository);
        StudyPlanItem item = itemOf("uid1", "plan1", "item100", 0);
        given(studyPlanItemRepository.findById("item100")).willReturn(Optional.of(item));

        StudyPlanItemResponse result = studyPlanItemService.updateProgress("uid1", "item100", 100);

        assertThat(result.getProgressRate()).isEqualTo(100);
        assertThat(result.isCompleted()).isTrue();
        assertThat(result.getCompletedAt()).isNotNull();
    }

    @Test
    void 완료된_항목의_진행률을_다시_낮추면_완료일시가_비워진다() {
        studyPlanItemService = new StudyPlanItemService(studyPlanItemRepository, studyDayCompletionRepository);
        StudyPlanItem item = itemOf("uid1", "plan1", "item100", 100);
        item.setCompletedAt(Timestamp.now());
        given(studyPlanItemRepository.findById("item100")).willReturn(Optional.of(item));

        StudyPlanItemResponse result = studyPlanItemService.updateProgress("uid1", "item100", 50);

        assertThat(result.getProgressRate()).isEqualTo(50);
        assertThat(result.getCompletedAt()).isNull();
    }

    @Test
    void 허용되지_않는_진행률_값이면_예외가_발생한다() {
        studyPlanItemService = new StudyPlanItemService(studyPlanItemRepository, studyDayCompletionRepository);

        assertThatThrownBy(() -> studyPlanItemService.updateProgress("uid1", "item100", 30))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 본인_소유가_아닌_항목을_체크하면_예외가_발생한다() {
        studyPlanItemService = new StudyPlanItemService(studyPlanItemRepository, studyDayCompletionRepository);
        StudyPlanItem item = itemOf("uid2", "plan1", "item100", 0); // 소유자는 memberId="uid2"

        given(studyPlanItemRepository.findById("item100")).willReturn(Optional.of(item));

        assertThatThrownBy(() -> studyPlanItemService.updateProgress("uid1", "item100", 50))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 모든_항목이_100퍼센트면_오늘_학습_마무리가_기록된다() {
        studyPlanItemService = new StudyPlanItemService(studyPlanItemRepository, studyDayCompletionRepository);
        LocalDate today = LocalDate.now();
        given(studyPlanItemRepository.findByMemberIdAndPlanDate("uid1", today))
                .willReturn(List.of(itemOf("uid1", "plan1", "item100", 100), itemOf("uid1", "plan1", "item101", 100)));
        given(studyDayCompletionRepository.findByStudyPlanIdAndPlanDate("plan1", today))
                .willReturn(Optional.empty());
        given(studyDayCompletionRepository.save(any(StudyDayCompletion.class)))
                .willAnswer(invocation -> {
                    StudyDayCompletion completion = invocation.getArgument(0);
                    completion.setCreatedAt(Timestamp.now());
                    return completion;
                });

        DayCompletionResponse result = studyPlanItemService.completeToday("uid1", today);

        assertThat(result.isCompleted()).isTrue();
        assertThat(result.getCompletedAt()).isNotNull();
    }

    @Test
    void 일부_항목만_완료했어도_오늘_학습_마무리가_기록된다() {
        studyPlanItemService = new StudyPlanItemService(studyPlanItemRepository, studyDayCompletionRepository);
        LocalDate today = LocalDate.now();
        given(studyPlanItemRepository.findByMemberIdAndPlanDate("uid1", today))
                .willReturn(List.of(
                        itemOf("uid1", "plan1", "item100", 100),
                        itemOf("uid1", "plan1", "item101", 25),
                        itemOf("uid1", "plan1", "item102", 0)));
        given(studyDayCompletionRepository.findByStudyPlanIdAndPlanDate("plan1", today))
                .willReturn(Optional.empty());
        given(studyDayCompletionRepository.save(any(StudyDayCompletion.class)))
                .willAnswer(invocation -> {
                    StudyDayCompletion completion = invocation.getArgument(0);
                    completion.setCreatedAt(Timestamp.now());
                    return completion;
                });

        DayCompletionResponse result = studyPlanItemService.completeToday("uid1", today);

        assertThat(result.isCompleted()).isTrue();
        assertThat(result.getCompletedAt()).isNotNull();
    }

    @Test
    void 항목이_없으면_마무리_요청은_예외가_발생한다() {
        studyPlanItemService = new StudyPlanItemService(studyPlanItemRepository, studyDayCompletionRepository);
        LocalDate today = LocalDate.now();
        given(studyPlanItemRepository.findByMemberIdAndPlanDate("uid1", today)).willReturn(List.of());

        assertThatThrownBy(() -> studyPlanItemService.completeToday("uid1", today))
                .isInstanceOf(CustomException.class);
    }
}
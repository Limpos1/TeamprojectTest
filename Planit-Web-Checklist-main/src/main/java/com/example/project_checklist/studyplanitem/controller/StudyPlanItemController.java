package com.example.project_checklist.studyplanitem.controller;

import com.example.project_checklist.studyplanitem.dto.DayCompletionResponse;
import com.example.project_checklist.studyplanitem.dto.StudyPlanItemResponse;
import com.example.project_checklist.studyplanitem.dto.TodayPlanResponse;
import com.example.project_checklist.studyplanitem.service.StudyPlanItemService;
import java.time.LocalDate;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/study-plan-items")
@RequiredArgsConstructor
public class StudyPlanItemController {

    private final StudyPlanItemService studyPlanItemService;

    /**
     * REQ-F-050~054: GET /api/study-plan-items?memberId=abc123uid&date=2026-08-25
     * date 를 생략하면 오늘 날짜로 조회합니다. 응답에는 항목 리스트, 오늘 진행률
     * (todayProgressRate), 오늘 마무리 여부(dayCompleted)가 같이 내려갑니다.
     *
     * memberId는 로그인 도메인(Planit-Web-Auth-Plan-Quiz)이 세션에 저장하는 Firebase Auth
     * uid(문자열)와 같은 값입니다. 지금은 파라미터로 직접 받지만, 이 컨트롤러도 그쪽의
     * AuthInterceptor/SessionUser로 세션에서 꺼내는 방식으로 나중에 교체할 수 있습니다.
     */
    @GetMapping
    public ResponseEntity<TodayPlanResponse> getTodayPlan(
            @RequestParam String memberId,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        return ResponseEntity.ok(studyPlanItemService.getTodayPlan(memberId, date));
    }

    /**
     * REQ-F-050~054: PATCH /api/study-plan-items/{id}/progress?memberId=abc123uid&progressRate=75
     * progressRate 는 0/25/50/75/100 중 하나만 허용됩니다. 클릭 즉시 반영되고 결과를 바로 반환합니다.
     *
     * [MySQL/JPA -> Firestore 전환 메모] {id} 가 더 이상 숫자가 아니라 Firestore 문서 id
     * (영문/숫자 섞인 문자열, 예: "aB3xY9Zq...")입니다. curl로 테스트할 때 GET 응답에 찍힌
     * items[].id 값을 그대로 복사해서 넣으면 됩니다.
     */
    @PatchMapping("/{id}/progress")
    public ResponseEntity<StudyPlanItemResponse> updateProgress(
            @RequestParam String memberId,
            @PathVariable("id") String itemId,
            @RequestParam int progressRate) {
        return ResponseEntity.ok(studyPlanItemService.updateProgress(memberId, itemId, progressRate));
    }

    /**
     * REQ-F-050~054: POST /api/study-plan-items/complete-day?memberId=abc123uid&date=2026-08-25
     * "오늘 학습 마무리하기" 버튼. 그날 항목을 전부 100%로 체크하지 못했더라도 마무리할 수 있습니다.
     * 다만 그날 등록된 항목이 하나도 없으면 400 에러를 반환합니다.
     */
    @PostMapping("/complete-day")
    public ResponseEntity<DayCompletionResponse> completeDay(
            @RequestParam String memberId,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        return ResponseEntity.ok(studyPlanItemService.completeToday(memberId, date));
    }
}
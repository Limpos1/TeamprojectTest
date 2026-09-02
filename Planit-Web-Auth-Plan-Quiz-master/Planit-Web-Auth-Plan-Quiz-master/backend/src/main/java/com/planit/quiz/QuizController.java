package com.planit.quiz;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.planit.auth.SessionUser;
import com.planit.quiz.QuizDtos.StartResponse;
import com.planit.quiz.QuizDtos.SubmitRequest;
import com.planit.quiz.QuizDtos.SubmitResponse;
import com.planit.quiz.QuizDtos.SummaryResponse;
import com.planit.quiz.QuizDtos.TodayPlanResponse;

import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;

/**
 * 퀴즈봇 API. 모든 경로는 로그인 필수 (WebConfig 의 AuthInterceptor 가 /api/quizzes/** 를 막는다).
 * 브라우저는 이 API 만 호출하고 Firestore 는 서버가 Admin SDK 로 처리한다.
 */
@RestController
@RequestMapping("/api/quizzes")
@RequiredArgsConstructor
public class QuizController {

	private final QuizService quizService;

	/** 오늘의 일과(study_plan.json 1일차) 조회 — 화면 표시용. */
	@GetMapping("/today-plan")
	public TodayPlanResponse todayPlan() {
		return quizService.todayPlan();
	}

	/** REQ-Q-001: 퀴즈 시작(생성). */
	@PostMapping
	public StartResponse start(HttpSession session) throws Exception {
		return quizService.start(SessionUser.uid(session));
	}

	/** REQ-Q-004, REQ-Q-005: 문제 제출. */
	@PostMapping("/{quizId}/answers/{questionNo}")
	public SubmitResponse submit(
		@PathVariable String quizId,
		@PathVariable int questionNo,
		@RequestBody SubmitRequest request,
		HttpSession session
	) throws Exception {
		return quizService.submit(SessionUser.uid(session), quizId, questionNo, request.selectedChoice());
	}

	/** REQ-Q-006: 결과 요약. */
	@GetMapping("/{quizId}/summary")
	public SummaryResponse summary(@PathVariable String quizId, HttpSession session) throws Exception {
		return quizService.summary(SessionUser.uid(session), quizId);
	}
}

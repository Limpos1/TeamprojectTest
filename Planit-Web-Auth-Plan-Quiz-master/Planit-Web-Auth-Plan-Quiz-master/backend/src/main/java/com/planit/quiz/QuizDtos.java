package com.planit.quiz;

import java.util.List;

/** 퀴즈 API 요청/응답 DTO 모음. */
public final class QuizDtos {

	private QuizDtos() {
	}

	/** 응시용 문제 (정답/풀이는 제출 전까지 내려주지 않는다). */
	public record QuestionView(
		int questionNo,
		String questionType,
		String questionText,
		String choice1,
		String choice2,
		String choice3,
		String choice4
	) {
	}

	public record StartResponse(String quizId, List<QuestionView> questions) {
	}

	public record SubmitRequest(Integer selectedChoice) {
	}

	/** REQ-Q-005: 제출 후 정답 여부 + 정답 번호 + 풀이. */
	public record SubmitResponse(int questionNo, boolean correct, int answerNo, String explanation) {
	}

	/** REQ-Q-006: 맞힌 문제 수 요약. */
	public record SummaryResponse(
		String quizId,
		int totalQuestionCount,
		int answeredCount,
		int correctCount
	) {
	}

	public record TodayPlanItem(String title, String pageRange, String status) {
	}

	/** 오늘의 일과(study_plan.json 1일차) + 출제 범위 문자열. */
	public record TodayPlanResponse(String date, Integer minutes, List<TodayPlanItem> items, String scope) {
	}
}

package com.planit.quiz;

/**
 * 생성된 문제 1개. AI(OpenAI)가 만들든 고정 예시든 이 형태로만 맞춰주면 QuizService 가 그대로 저장한다.
 * questionType: "BASIC" | "APPLIED", answerNo: 1~4.
 */
public record GeneratedQuestion(
	String questionType,
	String questionText,
	String choice1,
	String choice2,
	String choice3,
	String choice4,
	int answerNo,
	String explanation
) {
}

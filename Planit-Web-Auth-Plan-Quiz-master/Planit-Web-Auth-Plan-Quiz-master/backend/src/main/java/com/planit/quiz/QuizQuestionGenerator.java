package com.planit.quiz;

import java.util.List;

/**
 * 오늘 학습 범위로 퀴즈 문제를 만드는 방법을 감추는 인터페이스 (REQ-Q-002, REQ-Q-003).
 * 지금은 MockQuizQuestionGenerator 가 고정 예시 3개를 돌려준다.
 * OpenAI 연동(박지민 담당)이 정해지면 이 인터페이스를 구현하는 클래스를 @Primary 로 등록하면 된다.
 */
public interface QuizQuestionGenerator {

	/** 쉬운 문제(BASIC) 2개 + 응용 문제(APPLIED) 1개, 총 3개. */
	List<GeneratedQuestion> generate(String subjectName, String todayScope);
}

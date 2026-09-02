package com.planit.quiz;

import java.util.List;

import org.springframework.stereotype.Component;

/**
 * 개발/테스트용 기본 구현체. 입력과 무관하게 항상 같은 예시 3문제를 돌려준다.
 * 예시는 study_plan.json 1일차 범위(운영체제의 개요 / 리눅스의 기초)에 맞췄다.
 * BASIC 2 + APPLIED 1 (REQ-Q-002).
 */
@Component
public class MockQuizQuestionGenerator implements QuizQuestionGenerator {

	@Override
	public List<GeneratedQuestion> generate(String subjectName, String todayScope) {
		return List.of(
			new GeneratedQuestion(
				"BASIC",
				"운영체제의 주요 역할로 보기 어려운 것은?",
				"CPU·메모리 등 시스템 자원 관리",
				"사용자와 하드웨어 사이의 인터페이스 제공",
				"프로세스 생성과 스케줄링",
				"응용 프로그램의 소스 코드 컴파일",
				4,
				"운영체제는 자원 관리, 하드웨어 추상화, 프로세스·메모리·파일 관리를 담당한다. "
					+ "소스 코드를 기계어로 바꾸는 컴파일은 컴파일러(개발 도구)의 일이지 운영체제의 기능이 아니다."
			),
			new GeneratedQuestion(
				"BASIC",
				"리눅스에 대한 설명으로 옳은 것은?",
				"리누스 토르발스가 공개한 유닉스 계열 오픈소스 운영체제이다",
				"소스 코드가 공개되지 않은 상용 전용 운영체제이다",
				"커널 없이 셸(Shell)만으로 동작한다",
				"한 번에 한 명의 사용자만 로그인할 수 있다",
				1,
				"리눅스는 1991년 리누스 토르발스가 공개한 유닉스 계열 오픈소스 운영체제로, "
					+ "커널을 중심으로 다중 사용자·다중 작업(멀티태스킹)을 지원한다."
			),
			new GeneratedQuestion(
				"APPLIED",
				"현재 작업 디렉터리에 있는 파일들을 권한·소유자·크기까지 한 줄씩 자세히 확인하려고 한다. "
					+ "알맞은 명령은?",
				"ls -l",
				"cd -l",
				"pwd -a",
				"mkdir -l",
				1,
				"ls 는 디렉터리 내용을 보여주는 명령이고, -l 옵션을 붙이면 권한, 링크 수, 소유자, 그룹, "
					+ "크기, 수정 시각을 한 줄씩 출력한다. cd 는 디렉터리 이동, pwd 는 현재 경로 출력, "
					+ "mkdir 는 디렉터리 생성 명령이다."
			)
		);
	}
}

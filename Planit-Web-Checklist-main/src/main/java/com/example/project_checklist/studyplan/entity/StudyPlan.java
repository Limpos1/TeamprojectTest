package com.example.project_checklist.studyplan.entity;

/*
 * REMOVED: MySQL/JPA -> Firestore 전환하면서 더 이상 쓰지 않습니다.
 * study_plan_item 이 이 엔티티를 @ManyToOne 으로 참조하던 방식 대신, studyPlanId(String) 값을
 * 문서에 직접 저장하는 방식으로 바뀌었습니다 (StudyPlanItem.java 참고).
 *
 * 이 세션 환경에서는 파일을 완전히 삭제할 권한이 없어서 내용만 비워뒀습니다.
 * 프로젝트에서 이 파일(StudyPlan.java) 자체를 지우셔도 됩니다. (실제 학습 계획 입력
 * 도메인은 다른 팀원이 별도로 Firestore "study_plans" 컬렉션 등으로 설계할 예정입니다.)
 */

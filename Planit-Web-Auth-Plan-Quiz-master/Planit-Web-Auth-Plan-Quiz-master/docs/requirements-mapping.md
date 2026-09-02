# 요구사항 ID ↔ 코드 매핑 (김동호 담당)

`02_요구사항정의서.xlsx`의 요구사항 ID가 코드 어디에 있는지 찾는 표입니다. 화면 ID는
`planit화면흐름도_수정.pptx` 기준입니다.

**방식 B**: 로그인/회원가입만 브라우저에서 Firebase JS 로 처리하고, 그 외 데이터는 Spring 이
Firebase Admin SDK 로 Firestore 를 다룹니다. 브라우저는 Firestore 를 직접 건드리지 않습니다.
학습계획입력(REQ-B)은 다른 담당이라 여기 없습니다.

## 회원가입 / 로그인 (REQ-A-001 ~ REQ-A-015)

| 요구사항 ID | 내용 | 구현 위치 |
|---|---|---|
| REQ-A-001 | 회원가입 입력 (이름/이메일/비번/비번확인) | `frontend/login.html` (회원가입 뷰) |
| REQ-A-002 | 비밀번호 확인 일치 검증 | `frontend/login.html` (`su-btn` 핸들러) |
| REQ-A-003 | 이메일 형식 검증 | Firebase Auth (`auth/invalid-email`) |
| REQ-A-004 | 비밀번호 길이 검증 (6자 이상) | `frontend/login.html` (전송 전 검사, Firebase 자체 최소 6자) |
| REQ-A-005 | 이메일 중복 검사 | `frontend/login.html` → `POST /api/auth/email-available` → `AuthController#emailAvailable` (Admin SDK `getUserByEmail`). `createUserWithEmailAndPassword` 의 `auth/email-already-in-use` 는 2차 방어 |
| REQ-A-006 | 이메일 인증 | Firebase Auth 이메일 인증 기능 (콘솔 설정) |
| REQ-A-007 | 회원가입 완료 후 로그인 화면 이동 | `frontend/login.html` (가입 후 `signOut` → 로그인 뷰) |
| REQ-A-008 | 로그인 | `frontend/login.html` → `POST /api/auth/firebase-login` → `AuthController#firebaseLogin` |
| REQ-A-009 | 로그인 실패 처리 | `frontend/login.html#authErrorKey` |
| REQ-A-010 | 로그인 성공 시 이동 | `frontend/login.html#exchangeTokenAndGo` (→ `/quiz.html`) |
| REQ-A-011 | 세션 관리(로그인 상태 유지) | `AuthController` 가 세션에 uid/email 저장, `application.yml` session.timeout |
| REQ-A-012 | 로그아웃 | `POST /api/auth/logout` → `AuthController#logout` (세션 무효화) |
| (추가) | 회원 탈퇴 | `POST /api/auth/withdraw` → `AuthController#withdraw` (quizzes 삭제 + Firestore `users/{uid}` 문서 삭제 + Firebase 계정 삭제 + 세션 무효화). 타 도메인(`study_plan_items` 등) 정리는 팀 논의 필요 |
| REQ-A-013 | 로그인/회원가입 화면 전환 링크 | `frontend/login.html` (`to-signup` / `to-login`) |
| REQ-A-014 | Google 소셜 로그인 | `frontend/login.html#google-btn` (`signInWithPopup`) → 같은 토큰 교환 흐름 |
| REQ-A-015 | 미인증 계정 로그인 차단 | Firebase Auth (`auth/user-disabled`), Admin SDK `verifyIdToken` |

## 학습계획입력 (REQ-B-001 ~ REQ-B-011)

이 저장소에서는 다루지 않습니다 (다른 담당).

## 퀴즈봇 (REQ-Q-001 ~ REQ-Q-006)

| 요구사항 ID | 내용 | 구현 위치 |
|---|---|---|
| REQ-Q-001 | 퀴즈 응시 트리거 | `frontend/quiz.html#start-btn` → `POST /api/quizzes` → `QuizService#start` |
| REQ-Q-002 | 퀴즈 문제 구성 (기본2 + 응용1) | `MockQuizQuestionGenerator#generate` |
| REQ-Q-003 | 출제 범위 제한 | `QuizService#todayPlan` (study_plan.json 1일차 → scope) |
| REQ-Q-004 | 정답 선택 및 제출 | `POST /api/quizzes/{id}/answers/{no}` → `QuizService#submit` (Firestore `answers` 서브컬렉션) |
| REQ-Q-005 | 정답 확인 및 풀이 표시 | `QuizService#submit` 응답 + `frontend/quiz.html` 결과 렌더 |
| REQ-Q-006 | 퀴즈 결과 요약 | `GET /api/quizzes/{id}/summary` → `QuizService#summary` |

## 비기능 요구사항 (REQ-NF-009 ~ REQ-NF-023, 김동호 담당분)

| 요구사항 ID | 내용 | 구현 위치 |
|---|---|---|
| REQ-NF-009 | 비밀번호 암호화 저장 | Firebase Authentication 이 관리 (서버/브라우저 모두 비밀번호를 저장하지 않음) |
| REQ-NF-010 | 이메일 유일성 | Firebase Authentication |
| REQ-NF-011 | 세션 안전 저장 | 서버 세션(HttpOnly 쿠키) — `AuthController` |
| REQ-NF-012 | 인증 메일 유효시간 | Firebase Auth 설정 (콘솔) |
| REQ-NF-013 | 로그인 반복 실패 차단 | Firebase Auth (`auth/too-many-requests`) |
| REQ-NF-014 | 로그인/회원가입 2초 이내 응답 | 성능 목표 — 별도 코드 없음 |
| REQ-NF-015 | 입력 오류 안내 위치 | `frontend/*.html` 의 `.msg-error` (입력칸 아래 표시) |
| REQ-NF-016 | 예외 로그 | `GlobalExceptionHandler` (서버) + 페이지 `catch` |
| REQ-NF-017~019 | 목차 업로드/학습계획 접근 제한 | 학습계획입력 담당(다른 담당) |
| REQ-NF-019 | 본인 데이터만 접근 | `QuizService#requireOwnedQuiz` (quiz 의 uid == 세션 uid), `AuthInterceptor` |
| REQ-NF-022 | 브라우저 지원 | 정적 HTML + 바닐라 JS |
| REQ-NF-023 | 퀴즈 응시 기록 보존 | Firestore `quizzes/{id}/answers` (삭제 API 없음) |

## 팀 통합 스키마(`docs/schema.sql`) ↔ 이 저장소(방식 B) 매핑

팀 최종 통합 스키마는 "로그인/회원가입만 Firebase Auth, 나머지 전부 MySQL" 을 전제로 합니다.
이 저장소는 **방식 B** 로, 김동호 담당 데이터를 MySQL 대신 Firestore 에 두었습니다. 대응 관계:

| schema.sql (MySQL, 김동호 담당분) | 이 저장소(방식 B) 실제 구현 |
|---|---|
| `member` (`firebase_uid`, `name`, `is_deleted`, `created_at` …) | **테이블 없음.** 로그인 시 세션에 `uid`(=firebase_uid)·`email`·`name` 저장. 탈퇴는 `is_deleted` 대신 Firebase 계정 완전 삭제 (`AuthController#withdraw`) |
| `quiz` (`member_id`, `study_plan_id`, `quiz_date` …) | Firestore `quizzes/{quizId}` = `{ uid, subjectName, todayScope, quizDate, createdAt }` (`study_plan_id` 는 방식 B 에서 안 씀) |
| `quiz_question` (`quiz_id`, `question_no`, `question_type`, `choice1~4`, `answer_no`, `explanation` …) | 위 문서의 `questions[]` 배열 요소 |
| `quiz_answer` (`quiz_question_id`, `member_id`, `selected_choice`, `is_correct` …) | Firestore `quizzes/{quizId}/answers/{questionNo}` = `{ selectedChoice, correct, answeredAt }` |
| `study_plan`, `study_plan_time_slot`, `study_plan_weekday_minutes`, `study_plan_excluded_date` | **미구현.** 학습계획입력 화면은 프론트에서 제거됨. 실제 담당·구조는 유시우·박지민과 협의 필요 (schema.sql 의 "TODO 논의필요" 참고) |

> **확정: 김동호 파트는 Firestore(방식 B) 로 간다.** 팀 통합 스키마의 `member`/`quiz*`
> MySQL 테이블은 김동호 파트에 대해서는 위 매핑표대로 Firestore 로 대체한다.
> (`study_plan*` 등 다른 담당 테이블은 스키마 그대로 MySQL.)

## 아직 팀 논의가 필요한 항목

1. **퀴즈 문제 생성 방식**: 지금은 `MockQuizQuestionGenerator` 가 고정 예시 3문제 반환.
   OpenAI 연동(박지민 담당)이 정해지면 새 `QuizQuestionGenerator` 구현체를 `@Primary` 로 등록.
2. **퀴즈 결과 ↔ 체크리스트/계획 재조정 연동**: 유시우·김경태·박지민 담당 기능과 연결 필요. 미연결.
3. **서비스 계정 키**: `backend/src/main/resources/firebase-service-account.json` 이 있어야 서버가 Firestore 에
   접근합니다. 리더가 콘솔에서 발급해 전달하고, 절대 커밋하지 않습니다.

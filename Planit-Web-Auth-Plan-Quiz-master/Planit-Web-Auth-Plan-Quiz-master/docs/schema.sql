-- ============================================================
-- Planit 최종 통합 스키마 (MySQL 8.0)
-- 회원가입/로그인만 Firebase Authentication 사용, 나머지 전부 MySQL
-- 네이밍 규칙: 테이블 단수형 snake_case, PK=id, FK=참조테이블명_id,
--             불리언 is_ 접두사, 일시 _at 접미사, 날짜 _date 접미사
-- 담당: 김동호(member/study_plan/quiz), 유시우(study_plan_item/
--       study_day_completion), 박지민(book/study_unit 개념 반영),
--       본인(badge/member_badge, study_session 초안 반영)
-- ※ "TODO 논의필요" 주석 = 팀 확정 안 된 부분. 하단 요약 참고.
-- ============================================================

-- ------------------------------------------------------------
-- 1. 회원 (Firebase Auth 도입으로 구조 변경됨)
-- ------------------------------------------------------------
CREATE TABLE member (
  id            BIGINT PRIMARY KEY AUTO_INCREMENT,
  firebase_uid  VARCHAR(128) NOT NULL,          -- Firebase Authentication이 발급하는 식별자
  name          VARCHAR(30) NOT NULL,
  is_deleted    BOOLEAN NOT NULL DEFAULT FALSE, -- 탈퇴 시 실제 삭제 대신 이 값만 켬
  created_at    DATETIME NOT NULL,
  updated_at    DATETIME,
  UNIQUE KEY uk_member_firebase_uid (firebase_uid)
);
-- 삭제됨: email, password, is_email_verified, failed_login_count,
--        locked_until, email_verification 테이블 전체
--        → Firebase Authentication이 전부 대신 처리하므로 불필요

-- ------------------------------------------------------------
-- 2. 학습계획 (김동호 실제 코드 기준)
-- TODO 논의필요: 박지민의 book/study_unit 세분화 구조로 갈지,
--   지금처럼 subject_name(텍스트)+toc_file_url(파일) 단순 구조로
--   갈지 팀 미확정. quiz가 이미 이 테이블을 참조 중이라 구조를
--   바꾸면 quiz 쪽도 영향 있음.
-- ✅ 확정됨: 요일별 가용시간은 박지민 weekdayMinutes 방식 채택
--   (study_plan_weekday_minutes 테이블, 아래 2-1번)
-- ------------------------------------------------------------
CREATE TABLE study_plan (
  id                       BIGINT PRIMARY KEY AUTO_INCREMENT,
  member_id                BIGINT NOT NULL,
  subject_name             VARCHAR(100) NOT NULL,
  toc_file_url             VARCHAR(500),
  parsed_toc_json          JSON,                 -- TODO 논의필요: 박지민 파싱 결과(챕터/소단원) 저장 위치.
                                                   -- 정규화된 book/study_unit 테이블 대신 JSON 컬럼으로 단순화함.
                                                   -- "챕터 선택 화면"에서 재조회/재수정이 잦으면 정규화 테이블이 더 나을 수 있음.
  start_date               DATE NOT NULL,
  end_date                 DATE NOT NULL,
  include_review           BOOLEAN NOT NULL DEFAULT FALSE,
  status                   ENUM('NOT_STARTED','IN_PROGRESS','DONE') NOT NULL DEFAULT 'NOT_STARTED',
  created_at                DATETIME NOT NULL,
  updated_at                DATETIME,
  CONSTRAINT fk_study_plan_member FOREIGN KEY (member_id) REFERENCES member(id)
);

-- ------------------------------------------------------------
-- 2-1. 학습계획별 요일별 가용시간 (박지민 weekdayMinutes 채택 확정)
-- day_of_week: 박지민 실제 코드(Python date.weekday()) 기준과 맞춤
--              0=월, 1=화, 2=수, 3=목, 4=금, 5=토, 6=일
--              ⚠ 참고: 이전 초안(study_goal)의 "0=일~6=토" 방식과
--              다르니 다른 팀 코드에서 요일값 쓸 때 주의 필요.
-- ------------------------------------------------------------
CREATE TABLE study_plan_weekday_minutes (
  id                 BIGINT PRIMARY KEY AUTO_INCREMENT,
  study_plan_id      BIGINT NOT NULL,
  day_of_week        TINYINT NOT NULL,
  available_minutes  INT NOT NULL DEFAULT 0,   -- 0이면 그 요일은 학습 안 함
  CONSTRAINT fk_weekday_minutes_plan FOREIGN KEY (study_plan_id) REFERENCES study_plan(id),
  UNIQUE KEY uk_weekday_minutes_plan_day (study_plan_id, day_of_week)
);

-- ------------------------------------------------------------
-- 2-2. 학습계획 예외 날짜 (박지민 checkedDates 방식 반영)
-- 요일 패턴(study_plan_weekday_minutes)은 "매주 반복"이고, 이건
-- "이번 주만 예외로 쉼" 같은 개별 날짜 단위 예외를 표현함.
-- ------------------------------------------------------------
CREATE TABLE study_plan_excluded_date (
  id             BIGINT PRIMARY KEY AUTO_INCREMENT,
  study_plan_id  BIGINT NOT NULL,
  excluded_date  DATE NOT NULL,
  CONSTRAINT fk_excluded_plan FOREIGN KEY (study_plan_id) REFERENCES study_plan(id),
  UNIQUE KEY uk_excluded_plan_date (study_plan_id, excluded_date)
);

-- ------------------------------------------------------------
-- 3. 선호 학습 시간대 (김동호 실제 코드)
-- ------------------------------------------------------------
CREATE TABLE study_plan_time_slot (
  id             BIGINT PRIMARY KEY AUTO_INCREMENT,
  study_plan_id  BIGINT NOT NULL,
  time_slot      VARCHAR(20) NOT NULL,  -- 아침/오전/오후/저녁/심야/주말오전/주말오후/평일만
  created_at     DATETIME NOT NULL,
  CONSTRAINT fk_time_slot_plan FOREIGN KEY (study_plan_id) REFERENCES study_plan(id)
);

-- ------------------------------------------------------------
-- 4. 학습 계획 항목 (유시우 기준 + 박지민/김동호 필요 필드 통합)
-- ------------------------------------------------------------
CREATE TABLE study_plan_item (
  id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
  study_plan_id       BIGINT NOT NULL,
  plan_date           DATE NOT NULL,
  subject             VARCHAR(50) NOT NULL,
  content             VARCHAR(255) NOT NULL,
  sort_order          INT NOT NULL DEFAULT 0,
  progress_rate       TINYINT NOT NULL DEFAULT 0,  -- 0/25/50/75/100 (유시우 기준 확정)
  completed_at        DATETIME,
  pages_today         INT,                          -- 박지민 로직 결과
  total_pages         INT,
  page_range          VARCHAR(30),                  -- 예: "55~62p"
  is_manually_moved   BOOLEAN NOT NULL DEFAULT FALSE,-- 드래그 이동 시 true (자동 재배치 제외)
  created_at          DATETIME NOT NULL,
  updated_at          DATETIME NOT NULL,
  CONSTRAINT fk_item_plan FOREIGN KEY (study_plan_id) REFERENCES study_plan(id),
  KEY idx_item_plan_date (plan_date)
);
-- 제외됨(TODO 논의필요): start_time, end_time — "예정 시간"과 "실제 타이머 기록"은
--   다른 개념이라 여기 안 넣고 study_session으로 분리함. 예정 시간대 표시가
--   꼭 필요하면 여기 다시 추가 논의.
-- 제외됨(TODO 논의필요): status(시작/진행중/마무리/완료) — 챕터가 여러 날에
--   걸쳐 나뉠 때 "오늘이 몇 번째인지" 표시용. 화면에 이 문구가 필요한지에
--   따라 추가 여부 결정.

-- ------------------------------------------------------------
-- 5. 학습 세션 (타이머 기록 — 시간 트래킹)
-- TODO 논의필요: 이 테이블을 어느 코드베이스(로그인서버 후보 vs
--   마이페이지)가 관리할지 아직 팀 미확정. 스키마 자체는 확정.
-- ------------------------------------------------------------
CREATE TABLE study_session (
  id                        BIGINT PRIMARY KEY AUTO_INCREMENT,
  member_id                 BIGINT NOT NULL,
  study_plan_item_id        BIGINT NOT NULL,
  started_at                DATETIME NOT NULL,
  paused_duration_seconds   BIGINT NOT NULL DEFAULT 0,
  ended_at                  DATETIME,
  duration_seconds          BIGINT,               -- 종료 시 계산되어 저장 (통계 반복 SUM 방지)
  status                    VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS', -- IN_PROGRESS/PAUSED/COMPLETED
  created_at                DATETIME NOT NULL,
  updated_at                DATETIME,
  CONSTRAINT fk_session_member FOREIGN KEY (member_id) REFERENCES member(id),
  CONSTRAINT fk_session_item FOREIGN KEY (study_plan_item_id) REFERENCES study_plan_item(id),
  KEY idx_session_member_date (member_id, started_at)
);

-- ------------------------------------------------------------
-- 6. 학습 일일 완료 기록 (유시우 실제 코드)
-- ------------------------------------------------------------
CREATE TABLE study_day_completion (
  id             BIGINT PRIMARY KEY AUTO_INCREMENT,
  study_plan_id  BIGINT NOT NULL,
  plan_date      DATE NOT NULL,
  created_at     DATETIME NOT NULL,   -- "오늘 학습 마무리하기" 누른 시각
  updated_at     DATETIME,
  CONSTRAINT fk_completion_plan FOREIGN KEY (study_plan_id) REFERENCES study_plan(id),
  UNIQUE KEY uk_completion_plan_date (study_plan_id, plan_date)
);

-- ------------------------------------------------------------
-- 7. 퀴즈 (김동호 실제 코드)
-- ------------------------------------------------------------
CREATE TABLE quiz (
  id             BIGINT PRIMARY KEY AUTO_INCREMENT,
  member_id      BIGINT NOT NULL,
  study_plan_id  BIGINT NOT NULL,
  quiz_date      DATE NOT NULL,
  created_at     DATETIME NOT NULL,
  CONSTRAINT fk_quiz_member FOREIGN KEY (member_id) REFERENCES member(id),
  CONSTRAINT fk_quiz_plan FOREIGN KEY (study_plan_id) REFERENCES study_plan(id),
  UNIQUE KEY uk_quiz_member_plan_date (member_id, study_plan_id, quiz_date)
);

CREATE TABLE quiz_question (
  id             BIGINT PRIMARY KEY AUTO_INCREMENT,
  quiz_id        BIGINT NOT NULL,
  question_no    INT NOT NULL,              -- 1~3
  question_type  VARCHAR(10) NOT NULL,      -- BASIC / APPLIED
  question_text  TEXT NOT NULL,
  choice1        VARCHAR(255) NOT NULL,
  choice2        VARCHAR(255) NOT NULL,
  choice3        VARCHAR(255) NOT NULL,
  choice4        VARCHAR(255) NOT NULL,
  answer_no      INT NOT NULL,
  explanation    TEXT NOT NULL,
  created_at     DATETIME NOT NULL,
  CONSTRAINT fk_question_quiz FOREIGN KEY (quiz_id) REFERENCES quiz(id)
);

CREATE TABLE quiz_answer (
  id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
  quiz_question_id    BIGINT NOT NULL,
  member_id           BIGINT NOT NULL,
  selected_choice     INT NOT NULL,
  is_correct          BOOLEAN NOT NULL,
  answered_at         DATETIME NOT NULL,
  CONSTRAINT fk_answer_question FOREIGN KEY (quiz_question_id) REFERENCES quiz_question(id),
  CONSTRAINT fk_answer_member FOREIGN KEY (member_id) REFERENCES member(id),
  KEY idx_answer_member_date (member_id, answered_at)
);

-- ------------------------------------------------------------
-- 8. 뱃지 (본인, 겹치는 담당자 없음)
-- ------------------------------------------------------------
CREATE TABLE badge (
  id      BIGINT PRIMARY KEY AUTO_INCREMENT,
  code    VARCHAR(50) NOT NULL,
  label   VARCHAR(50) NOT NULL,
  icon    VARCHAR(10),
  UNIQUE KEY uk_badge_code (code)
);

CREATE TABLE member_badge (
  id          BIGINT PRIMARY KEY AUTO_INCREMENT,
  member_id   BIGINT NOT NULL,
  badge_id    BIGINT NOT NULL,
  earned_at   DATETIME NOT NULL,
  CONSTRAINT fk_member_badge_member FOREIGN KEY (member_id) REFERENCES member(id),
  CONSTRAINT fk_member_badge_badge FOREIGN KEY (badge_id) REFERENCES badge(id)
);

-- ============================================================
-- 제외된 테이블 (이전 초안에서 있었으나 이번 최종본에서 뺌)
-- - category(활동유형: 이론학습/문제풀이 등): 실제 동작 방식이
--   "책 페이지 진행" 기반이라 활동유형 구분 자체가 안 맞아 보여서 제외.
--   TODO 논의필요: 팀에서 이 개념이 정말 필요하면 다시 추가.
-- - schedule(나의 일정): study_plan_item의 plan_date로 대체 가능해
--   보여서 제외. TODO 논의필요: 학습과 무관한 개인 일정까지 다뤄야
--   하면 다시 필요.
-- ============================================================

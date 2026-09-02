# Planit — 김동호 파트 (방식 B)

**언어 / Language / 言語** — 아래에서 원하는 언어를 클릭하면 그 내용이 펼쳐집니다.
(GitHub README 는 스크립트를 못 써서 `<details>` 접기/펴기로 대신합니다.)

<!-- ================================================================= -->
<details open>
<summary><b>🇰🇷 한국어</b></summary>

<br>

회원가입/로그인(구글 포함), 로그아웃, 회원 탈퇴, 퀴즈봇을 담당합니다. 학습계획입력은
다른 사람 담당이라 여기 없습니다.

- 팀 전체 통합 스키마: [`docs/schema.sql`](docs/schema.sql) — 팀 문서라 MySQL 기준입니다. **이 저장소(김동호 파트)의 DB 는 아래 표대로 Firestore 입니다.**
- 요구사항 ID ↔ 코드 매핑 + 스키마 ↔ 방식 B 대응표: [`docs/requirements-mapping.md`](docs/requirements-mapping.md)

### 기술 스택

| 구분 | 선택 |
|---|---|
| 언어 / 프레임워크 | Java 17, Spring Boot 3.3.x |
| 인증 | Firebase Authentication (이메일/비밀번호, Google) |
| **DB** | **Cloud Firestore** (Firebase Admin SDK 로 접근) — **MySQL 안 씀** |
| 프론트 | 순수 HTML + 바닐라 JS (React/npm 없음) |
| 빌드 | Gradle |

> 팀 통합 스키마의 `member` / `quiz*` MySQL 테이블은 이 저장소에서 Firestore 로 대체됩니다
> (대응표 참고). `study_plan*` 등 다른 담당분은 스키마대로 MySQL.

### 구조 (방식 B)

```
[브라우저]  login.html
   1. Firebase JS 로 이메일/비번(또는 구글) 로그인
   2. user.getIdToken() 으로 ID 토큰 받음
   3. POST /api/auth/firebase-login { idToken }  로 Spring 에 전송
[Spring]
   4. Firebase Admin SDK 로 토큰 검증 → 세션에 uid/email 저장
[이후 모든 페이지]  quiz.html …
   세션 쿠키만으로 /api/* 호출
   Firestore 읽기/쓰기는 Spring 이 Admin SDK 로 처리
```

**핵심: 브라우저는 Firestore 를 직접 건드리지 않습니다.** 로그인만 JS 로 하고,
데이터는 항상 Spring 을 거칩니다. (`login.html` 은 `firebase-auth` 만 로드하고
`firebase-firestore` 는 로드하지 않습니다.)

- 브라우저: 순수 HTML + 바닐라 JS. React/npm 안 씁니다.
- 서버: Spring Boot 3.3.x + `firebase-admin`. MySQL/JPA 없음.
- 인증: Firebase Authentication (이메일/비번, 구글)
- 데이터: Cloud Firestore (`quizzes`), 접근은 서버만

### 폴더

백엔드(Spring)와 프론트엔드(정적 파일)를 폴더로 물리 분리했습니다.
빌드하면 Gradle 이 `frontend/` 를 정적 리소스로 복사하므로, 실행 URL 은 예전과 같습니다.

```
backend/                         ← Spring Boot (Java 17, Gradle)
  build.gradle                   processResources 가 ../frontend 를 static 으로 복사
  src/main/java/com/planit/
    PlanitApplication.java
    config/
      FirebaseConfig.java        서비스 계정 키로 Admin SDK 초기화
      WebConfig.java             /api/quizzes/** 에 로그인 인터셉터
    auth/
      AuthController.java        POST /api/auth/firebase-login, /logout, /withdraw, GET /me
      AuthInterceptor.java       세션 없으면 401
      SessionUser.java
    quiz/
      QuizController.java        GET /today-plan, POST /, POST /{id}/answers/{no}, GET /{id}/summary
      QuizService.java           Firestore(Admin SDK) 로 생성·채점·요약
      QuizQuestionGenerator.java / MockQuizQuestionGenerator.java   고정 예시 3문제
    global/
      ApiException.java / GlobalExceptionHandler.java
  src/main/resources/
    application.yml
    study_plan.json              퀴즈 "오늘의 일과" 예시 데이터 (서버가 읽음)

frontend/                        ← 순수 HTML + 바닐라 JS (React/npm 없음)
  login.html                     로그인/회원가입 (Firebase Auth compat CDN)
  quiz.html                      퀴즈봇 (Firebase SDK 안 씀, /api/* 만 호출)
  app.css                        공용 스타일 (목업 팔레트)
  index.html                     옛날 7화면 목업 — 참고용 (동작 안 함)
```

### 실행

**1. 서비스 계정 키 넣기 (리더가 발급 → 전달)**

Firebase 콘솔 → 프로젝트 설정(⚙️) → **서비스 계정** → **새 비공개 키 생성** → 받은 JSON 을
`backend/src/main/resources/` 에 둡니다. 파일명은 둘 중 아무거나:

- `firebase-service-account.json` 으로 이름 바꿔서, 또는
- 콘솔에서 받은 원래 이름 그대로 (예: `planit-ccfff-firebase-adminsdk-xxxx.json`)

`FirebaseConfig` 가 두 경우 다 자동으로 찾습니다. 절대경로로 지정하려면 환경변수
`FIREBASE_CREDENTIALS=/path/to/key.json` 도 됩니다.

이 키는 진짜 비밀키입니다. **커밋 금지** (`.gitignore` 에 `*-firebase-adminsdk-*.json` 등록됨),
노션/드라이브로만 전달합니다. `login.html` 안의 `firebaseConfig`(apiKey 등)와는 완전히 다른
값입니다 — 그건 공개돼도 됩니다.

**2. 서버 실행**

```bash
cd backend
./gradlew bootRun        # http://localhost:8080
```

`http://localhost:8080/login.html` 에서 로그인 → 자동으로 `quiz.html` 로 이동합니다.
키 파일이 없으면 서버는 뜨지만 `/api/auth/firebase-login` 이 503 을 돌려줍니다.

> 프론트엔드는 `frontend/` 안의 정적 파일입니다. 별도 dev 서버 없이 `backend` 빌드에
> 포함돼 서빙됩니다. `frontend/` 만 고쳤을 때는 `bootRun` 을 다시 실행하세요.

### Firestore 구조

```
quizzes/{quizId}                       { uid, subjectName, todayScope, quizDate,
                                         createdAt, questions[] }
quizzes/{quizId}/answers/{questionNo}  { selectedChoice, correct, answeredAt }
```

`questions[]` 는 정답 번호·풀이까지 저장하고, 응시용 응답(`POST /api/quizzes`)에서는 빼고 내려줍니다.

### Firebase 콘솔 설정

1. Authentication → 로그인 방법 → **이메일/비밀번호**, **Google** 둘 다 사용 설정
   (Google 은 지원 이메일 지정, 승인된 도메인에 `localhost` 확인)
2. Firestore Database 생성
3. Firestore 보안 규칙: 서버는 Admin SDK 로 규칙을 우회하지만, 클라이언트 직접 접근을
   막기 위해 규칙은 계속 켜 둡니다 (기본 잠금 상태 그대로 두면 됨).
4. 서비스 계정 키 발급 (위 실행 1번)

### 회원 탈퇴

`quiz.html` 의 "회원 탈퇴" 버튼 → `POST /api/auth/withdraw` (로그인 세션 필요).
서버가 Admin SDK 로 ① 그 사용자의 `quizzes` 데이터 삭제 ② Firestore `users/{uid}` 문서
삭제(하위 컬렉션까지 `recursiveDelete`) ③ Firebase Auth 계정 삭제 ④ 세션 무효화 를
처리합니다. 브라우저에서는 `localStorage` 의 저장된 이메일도 지웁니다.

다른 도메인(`study_plan_items` 등) 데이터는 아직 **건드리지 않습니다** — 팀 조율이
필요합니다 (아래 참고).

### 아직 안 한 것

- 퀴즈 문제가 고정 3개입니다. OpenAI 연동은 박지민 담당이고, 정해지면
  `MockQuizQuestionGenerator` 대신 새 `QuizQuestionGenerator` 구현체를 `@Primary` 로 등록하면 됩니다.
- 퀴즈 결과를 체크리스트/계획 재조정과 연결하는 부분은 아직입니다.
- 탈퇴 시 타 도메인 데이터(`study_plan_items` 등)까지 정리하는 방법(예: Auth `onDelete`
  Cloud Function 하나로 전부 삭제)은 팀 논의가 필요합니다.

</details>

<!-- ================================================================= -->
<details>
<summary><b>🇯🇵 日本語</b></summary>

<br>

新規登録／ログイン（Google含む）、ログアウト、退会、クイズボットを担当します。学習計画入力は
別の担当なので、このリポジトリにはありません。

- チーム全体の統合スキーマ: [`docs/schema.sql`](docs/schema.sql) — チームの文書なので MySQL ベースです。**このリポジトリ（キム・ドンホ担当分）の DB は下表のとおり Firestore です。**
- 要件ID ↔ コード対応 + スキーマ ↔ 方式B 対応表: [`docs/requirements-mapping.md`](docs/requirements-mapping.md)

### 技術スタック

| 区分 | 選択 |
|---|---|
| 言語 / フレームワーク | Java 17, Spring Boot 3.3.x |
| 認証 | Firebase Authentication（メール/パスワード、Google） |
| **DB** | **Cloud Firestore**（Firebase Admin SDK 経由）— **MySQL は使いません** |
| フロント | 素の HTML + バニラ JS（React/npm なし） |
| ビルド | Gradle |

> チーム統合スキーマの `member` / `quiz*` MySQL テーブルは、このリポジトリでは Firestore に
> 置き換わります（対応表参照）。`study_plan*` など他担当分はスキーマどおり MySQL。

### 全体の流れ（方式B）

```
[ブラウザ]  login.html
   1. Firebase JS でメール/パスワード（またはGoogle）ログイン
   2. user.getIdToken() で IDトークンを取得
   3. POST /api/auth/firebase-login { idToken }  を Spring へ送信
[Spring]
   4. Firebase Admin SDK でトークンを検証 → セッションに uid/email を保存
[以降のすべてのページ]  quiz.html …
   セッションクッキーだけで /api/* を呼ぶ
   Firestore の読み書きは Spring が Admin SDK で処理する
```

**要点：ブラウザは Firestore に直接アクセスしません。** ログインだけを JS で行い、
データは必ず Spring を経由します。（`login.html` は `firebase-auth` のみを読み込み、
`firebase-firestore` は読み込みません。）

- ブラウザ：素の HTML + バニラ JS。React／npm は使いません。
- サーバー：Spring Boot 3.3.x + `firebase-admin`。MySQL/JPA なし。
- 認証：Firebase Authentication（メール/パスワード、Google）
- データ：Cloud Firestore（`quizzes`）、アクセスはサーバーのみ

### 構成

バックエンド（Spring）とフロントエンド（静的ファイル）をフォルダで物理的に分離しています。
ビルド時に Gradle が `frontend/` を静的リソースへコピーするため、実行 URL は従来どおりです。

```
backend/                         ← Spring Boot（Java 17, Gradle）
  build.gradle                   processResources が ../frontend を static へコピー
  src/main/java/com/planit/
    PlanitApplication.java
    config/
      FirebaseConfig.java        サービスアカウントキーで Admin SDK を初期化
      WebConfig.java             /api/quizzes/** にログインインターセプター
    auth/
      AuthController.java        POST /api/auth/firebase-login, /logout, /withdraw, GET /me
      AuthInterceptor.java       セッションが無ければ 401
      SessionUser.java
    quiz/
      QuizController.java        GET /today-plan, POST /, POST /{id}/answers/{no}, GET /{id}/summary
      QuizService.java           Firestore（Admin SDK）で生成・採点・集計
      QuizQuestionGenerator.java / MockQuizQuestionGenerator.java   固定サンプル3問
    global/
      ApiException.java / GlobalExceptionHandler.java
  src/main/resources/
    application.yml
    study_plan.json              クイズの「今日の予定」用サンプルデータ（サーバーが読む）

frontend/                        ← 素の HTML + バニラ JS（React/npm なし）
  login.html                     ログイン/新規登録（Firebase Auth compat CDN）
  quiz.html                      クイズボット（Firebase SDK 未使用、/api/* のみ呼ぶ）
  app.css                        共通スタイル（モックアップのパレット）
  index.html                     旧・7画面モックアップ — 参考用（動作しません）
```

### 実行方法

**1. サービスアカウントキーを置く（リーダーが発行して共有）**

Firebase コンソール → プロジェクトの設定（⚙️）→ **サービス アカウント** → **新しい秘密鍵の生成**
→ 受け取った JSON を `backend/src/main/resources/` に置きます。ファイル名はどちらでも可：

- `firebase-service-account.json` にリネームする、または
- コンソールで受け取った元の名前のまま（例：`planit-ccfff-firebase-adminsdk-xxxx.json`）

`FirebaseConfig` が両方を自動で探します。絶対パスを指定する場合は環境変数
`FIREBASE_CREDENTIALS=/path/to/key.json` でも可。

このキーは本物の秘密鍵です。**絶対にコミットしないでください**（`.gitignore` に
`*-firebase-adminsdk-*.json` を登録済み）。Notion／ドライブでのみ共有します。
`login.html` 内の `firebaseConfig`（apiKey など）とはまったく別物です — そちらは公開されて問題ありません。

**2. サーバーの起動**

```bash
cd backend
./gradlew bootRun        # http://localhost:8080
```

`http://localhost:8080/login.html` でログインすると、自動的に `quiz.html` へ移動します。
キーファイルが無くてもサーバーは起動しますが、`/api/auth/firebase-login` は 503 を返します。

> フロントエンドは `frontend/` 内の静的ファイルです。専用の dev サーバーは無く、`backend`
> のビルドに含まれて配信されます。`frontend/` だけ変更したときは `bootRun` を再実行してください。

### Firestore の構造

```
quizzes/{quizId}                       { uid, subjectName, todayScope, quizDate,
                                         createdAt, questions[] }
quizzes/{quizId}/answers/{questionNo}  { selectedChoice, correct, answeredAt }
```

`questions[]` には正解番号・解説まで保存しますが、出題用レスポンス（`POST /api/quizzes`）では
それらを除いて返します。

### Firebase コンソールの設定

1. Authentication → ログイン方法 → **メール/パスワード** と **Google** の両方を有効化
   （Google はサポートメールを指定、承認済みドメインに `localhost` があるか確認）
2. Firestore データベースを作成
3. Firestore のルール：サーバーは Admin SDK でルールを回避しますが、クライアントからの
   直接アクセスを防ぐためルールは有効のまま（デフォルトのロック状態でOK）にしておきます。
4. サービスアカウントキーを発行（上記「実行方法」1）

### 退会

`quiz.html` の「회원 탈퇴」ボタン → `POST /api/auth/withdraw`（ログインセッションが必要）。
サーバーが Admin SDK で、(1) そのユーザーの `quizzes` データを削除、(2) Firestore の
`users/{uid}` ドキュメントを削除（サブコレクションごと `recursiveDelete`）、(3) Firebase Auth の
アカウントを削除、(4) セッションを無効化します。ブラウザ側では `localStorage` に保存した
メールアドレスも消します。

他ドメインのデータ（`study_plan_items` など）にはまだ**触れません** — チームでの調整が
必要です（下記参照）。

### まだやっていないこと

- クイズの問題は固定の3問です。OpenAI 連携はパク・ジミン担当で、方式が決まったら
  `MockQuizQuestionGenerator` の代わりに新しい `QuizQuestionGenerator` 実装を `@Primary` で登録します。
- クイズ結果をチェックリスト／再計画機能とつなぐ部分はまだです。
- 退会時に他ドメインのデータ（`study_plan_items` など）まで削除する方法（例：Auth の `onDelete`
  Cloud Function ひとつで全部消す）はチームでの検討が必要です。

</details>

<!-- ================================================================= -->
<details>
<summary><b>🇬🇧 English</b></summary>

<br>

Covers sign-up / login (including Google), logout, account withdrawal, and the quiz bot.
Study-plan input is someone else's area and isn't in this repo.

- Team-wide integrated schema: [`docs/schema.sql`](docs/schema.sql) — it's a team doc, so it's MySQL-based. **This repo (Kim Dongho's part) uses Firestore for its DB, per the table below.**
- Requirement-ID ↔ code mapping + schema ↔ Approach B table: [`docs/requirements-mapping.md`](docs/requirements-mapping.md)

### Tech stack

| Area | Choice |
|---|---|
| Language / framework | Java 17, Spring Boot 3.3.x |
| Auth | Firebase Authentication (email/password, Google) |
| **DB** | **Cloud Firestore** (via the Firebase Admin SDK) — **no MySQL** |
| Frontend | Plain HTML + vanilla JS (no React/npm) |
| Build | Gradle |

> The `member` / `quiz*` MySQL tables in the team schema are replaced by Firestore in this
> repo (see the mapping table). Other owners' tables like `study_plan*` stay in MySQL.

### How it fits together (Approach B)

```
[Browser]  login.html
   1. Sign in with Firebase JS (email/password or Google)
   2. Get an ID token via user.getIdToken()
   3. POST /api/auth/firebase-login { idToken }  to Spring
[Spring]
   4. Verify the token with the Firebase Admin SDK → store uid/email in the session
[Every page after that]  quiz.html …
   Call /api/* with the session cookie only
   Spring does all Firestore reads/writes through the Admin SDK
```

**The key rule: the browser never touches Firestore directly.** Only login runs in JS;
all data goes through Spring. (`login.html` loads `firebase-auth` only, never
`firebase-firestore`.)

- Browser: plain HTML + vanilla JS. No React, no npm.
- Server: Spring Boot 3.3.x + `firebase-admin`. No MySQL/JPA.
- Auth: Firebase Authentication (email/password, Google)
- Data: Cloud Firestore (`quizzes`), server access only

### Layout

Backend (Spring) and frontend (static files) are split into separate folders.
At build time Gradle copies `frontend/` into the static resources, so the runtime URLs
are unchanged.

```
backend/                         ← Spring Boot (Java 17, Gradle)
  build.gradle                   processResources copies ../frontend into static
  src/main/java/com/planit/
    PlanitApplication.java
    config/
      FirebaseConfig.java        Initializes the Admin SDK from the service-account key
      WebConfig.java             Login interceptor on /api/quizzes/**
    auth/
      AuthController.java        POST /api/auth/firebase-login, /logout, /withdraw, GET /me
      AuthInterceptor.java       401 if there's no session
      SessionUser.java
    quiz/
      QuizController.java        GET /today-plan, POST /, POST /{id}/answers/{no}, GET /{id}/summary
      QuizService.java           Create / grade / summarize via Firestore (Admin SDK)
      QuizQuestionGenerator.java / MockQuizQuestionGenerator.java   fixed sample of 3 questions
    global/
      ApiException.java / GlobalExceptionHandler.java
  src/main/resources/
    application.yml
    study_plan.json              Sample data for the quiz's "today's plan" (read by the server)

frontend/                        ← Plain HTML + vanilla JS (no React/npm)
  login.html                     Login / sign-up (Firebase Auth compat CDN)
  quiz.html                      Quiz bot (no Firebase SDK; calls /api/* only)
  app.css                        Shared styles (mockup palette)
  index.html                     Old 7-screen mockup — reference only (doesn't work)
```

### Running it

**1. Add the service-account key (the lead generates and shares it)**

Firebase console → Project settings (⚙️) → **Service accounts** → **Generate new private key**
→ put the JSON under `backend/src/main/resources/`. Either filename works:

- rename it to `firebase-service-account.json`, or
- keep the original name from the console (e.g. `planit-ccfff-firebase-adminsdk-xxxx.json`)

`FirebaseConfig` finds both. To point at an absolute path, set the env var
`FIREBASE_CREDENTIALS=/path/to/key.json`.

This key is a real secret. **Never commit it** (`*-firebase-adminsdk-*.json` is in `.gitignore`);
share it only over Notion/Drive. It's completely different from the `firebaseConfig`
(apiKey etc.) in `login.html` — that one is fine to be public.

**2. Start the server**

```bash
cd backend
./gradlew bootRun        # http://localhost:8080
```

Log in at `http://localhost:8080/login.html` → you're taken to `quiz.html` automatically.
If the key file is missing the server still starts, but `/api/auth/firebase-login` returns 503.

> The frontend is the static files in `frontend/`. There's no separate dev server — it's
> bundled into the `backend` build and served from there. Re-run `bootRun` after editing
> `frontend/`.

### Firestore shape

```
quizzes/{quizId}                       { uid, subjectName, todayScope, quizDate,
                                         createdAt, questions[] }
quizzes/{quizId}/answers/{questionNo}  { selectedChoice, correct, answeredAt }
```

`questions[]` stores the answer number and explanation too; the play response
(`POST /api/quizzes`) strips those out.

### Firebase console setup

1. Authentication → Sign-in method → enable both **Email/Password** and **Google**
   (set a support email for Google; check `localhost` is in the authorized domains)
2. Create a Firestore database
3. Firestore rules: the server bypasses them with the Admin SDK, but leave the rules on
   (locked by default is fine) to block direct client access.
4. Generate the service-account key (step 1 above)

### Account withdrawal

The "회원 탈퇴" button in `quiz.html` → `POST /api/auth/withdraw` (needs a login session).
The server, via the Admin SDK: (1) deletes that user's `quizzes` data, (2) deletes the
Firestore `users/{uid}` document (`recursiveDelete`, subcollections included), (3) deletes
the Firebase Auth account, (4) invalidates the session. The browser also clears the saved
email from `localStorage`.

It does **not** yet touch other domains' data (`study_plan_items`, etc.) — that needs a
team decision (see below).

### Not done yet

- The quiz has a fixed set of 3 questions. OpenAI integration is Park Jimin's area; once
  it's decided, register a new `QuizQuestionGenerator` implementation as `@Primary` in place
  of `MockQuizQuestionGenerator`.
- Wiring quiz results into the checklist / re-planning features isn't done yet.
- Cleaning up other-domain data (`study_plan_items`, etc.) on withdrawal (e.g. one Auth
  `onDelete` Cloud Function that wipes everything) needs a team decision.

</details>

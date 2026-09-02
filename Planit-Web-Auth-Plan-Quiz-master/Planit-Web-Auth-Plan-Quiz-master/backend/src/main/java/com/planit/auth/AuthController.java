package com.planit.auth;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.google.cloud.firestore.DocumentReference;
import com.google.cloud.firestore.FieldValue;
import com.google.cloud.firestore.Firestore;
import com.google.firebase.FirebaseApp;
import com.google.firebase.auth.AuthErrorCode;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseAuthException;
import com.google.firebase.auth.FirebaseToken;
import com.google.firebase.auth.UserRecord;
import com.google.firebase.cloud.FirestoreClient;
import com.planit.global.ApiException;
import com.planit.quiz.QuizService;

import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

/**
 * 방식 B 인증 흐름.
 *  1) 브라우저: Firebase JS 로 이메일/비밀번호(또는 구글) 로그인 → user.getIdToken()
 *  2) 브라우저 → POST /api/auth/firebase-login { idToken }
 *  3) 여기서 Firebase Admin SDK 로 토큰 검증 → 세션에 uid/email 저장 + Firestore users/{uid} upsert
 *  4) 이후 모든 데이터 API 는 세션 쿠키만으로 인증 (브라우저는 Firestore 를 직접 건드리지 않음)
 *
 * 회원가입은 브라우저에서 Firebase Auth 계정만 만들고(방식 B: 브라우저는 Firestore 접근 안 함),
 * users/{uid} 프로필 문서는 첫 로그인 때 서버가 만든다(아래 upsertUserProfile).
 */
@Slf4j
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

	private final QuizService quizService;

	/**
	 * REQ-A-005: 이메일 중복 확인. body: { "email": "..." } → { "available": true/false }
	 * 방식 B 에서 회원가입은 브라우저가 하므로, 가입 전에 이 API 로 서버(Admin SDK)에 중복 여부를 물어본다.
	 * (Firebase 콘솔의 email enumeration protection 설정과 무관하게 Admin SDK 는 정확히 판정한다.)
	 */
	@PostMapping("/email-available")
	public Map<String, Boolean> emailAvailable(@RequestBody Map<String, String> body) throws FirebaseAuthException {
		requireFirebaseInitialized();

		String email = body.get("email");
		if (email == null || email.isBlank()) {
			throw ApiException.badRequest("email 이 없습니다");
		}

		try {
			FirebaseAuth.getInstance().getUserByEmail(email.trim());
			return Map.of("available", false); // 조회되면 이미 쓰는 이메일
		} catch (FirebaseAuthException e) {
			if (e.getAuthErrorCode() == AuthErrorCode.USER_NOT_FOUND) {
				return Map.of("available", true);
			}
			throw e;
		}
	}

	/** REQ-A-008 ~ REQ-A-011: 로그인. body: { "idToken": "..." } */
	@PostMapping("/firebase-login")
	public Map<String, String> firebaseLogin(@RequestBody Map<String, String> body, HttpSession session)
		throws Exception {
		requireFirebaseInitialized();

		String idToken = body.get("idToken");
		if (idToken == null || idToken.isBlank()) {
			throw ApiException.badRequest("idToken 이 없습니다");
		}

		FirebaseToken decoded = FirebaseAuth.getInstance().verifyIdToken(idToken);
		String uid = decoded.getUid();
		String email = decoded.getEmail();
		String name = resolveDisplayName(decoded);

		session.setAttribute(SessionUser.UID, uid);
		session.setAttribute(SessionUser.EMAIL, email);
		session.setAttribute(SessionUser.NAME, name);

		upsertUserProfile(uid, email, name);

		log.info("[login] uid={} email={} name={}", uid, email, name);
		return Map.of("uid", uid, "email", nullSafe(email), "name", nullSafe(name));
	}

	/**
	 * Firestore users/{uid} 프로필 문서를 만든다(없으면) / 최신화한다(있으면).
	 * 회원가입 직후 첫 로그인에서 문서가 처음 생성되고, createdAt 은 그때 한 번만 박힌다.
	 * 프로필 문서 쓰기가 실패해도 로그인 자체는 막지 않는다(다음 로그인에서 다시 시도).
	 */
	private void upsertUserProfile(String uid, String email, String name) {
		try {
			Firestore db = FirestoreClient.getFirestore();
			DocumentReference ref = db.collection("users").document(uid);

			if (ref.get().get().exists()) {
				Map<String, Object> update = new HashMap<>();
				if (email != null) {
					update.put("email", email);
				}
				if (name != null) {
					update.put("name", name);
				}
				if (!update.isEmpty()) {
					ref.update(update).get();
				}
				return;
			}

			Map<String, Object> doc = new LinkedHashMap<>();
			doc.put("email", nullSafe(email));
			doc.put("name", nullSafe(name));
			doc.put("createdAt", FieldValue.serverTimestamp());
			ref.set(doc).get();
			log.info("[login] uid={} users 문서 생성", uid);
		} catch (Exception e) {
			log.warn("[login] uid={} users 프로필 upsert 실패(로그인은 계속): {}", uid, e.getMessage());
		}
	}

	/** REQ-A-012: 로그아웃. 세션 무효화. */
	@PostMapping("/logout")
	public Map<String, String> logout(HttpSession session) {
		session.invalidate();
		return Map.of("message", "로그아웃되었습니다");
	}

	/**
	 * 회원 탈퇴. 로그인 세션 필요.
	 *  1) 이 사용자의 Firestore 데이터(퀴즈 기록) 삭제
	 *  2) Firestore users/{uid} 프로필 문서 삭제 (하위 컬렉션까지)
	 *  3) Firebase Authentication 계정 삭제 (Admin SDK)
	 *  4) 세션 무효화
	 * 되돌릴 수 없다.
	 */
	@PostMapping("/withdraw")
	public Map<String, String> withdraw(HttpSession session) throws Exception {
		requireFirebaseInitialized();
		String uid = SessionUser.uid(session);
		if (uid == null) {
			throw new ApiException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다");
		}

		quizService.deleteAllForUser(uid);
		deleteUserDocument(uid);
		FirebaseAuth.getInstance().deleteUser(uid);
		session.invalidate();

		log.info("[withdraw] uid={} 탈퇴 완료", uid);
		return Map.of("message", "탈퇴가 완료되었습니다");
	}

	/** 탈퇴 시 Firestore 의 users/{uid} 문서와 그 하위 컬렉션을 통째로 삭제한다. */
	private void deleteUserDocument(String uid) throws Exception {
		Firestore db = FirestoreClient.getFirestore();
		db.recursiveDelete(db.collection("users").document(uid)).get();
		log.info("[withdraw] uid={} users 문서 삭제 완료", uid);
	}

	/** 현재 로그인 상태 확인. 로그인 안 되어 있으면 401. */
	@GetMapping("/me")
	public Map<String, String> me(HttpSession session) {
		String uid = SessionUser.uid(session);
		if (uid == null) {
			throw new ApiException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다");
		}
		return Map.of(
			"uid", uid,
			"email", nullSafe(SessionUser.email(session)),
			"name", nullSafe(SessionUser.name(session))
		);
	}

	/**
	 * 표시 이름(회원가입 때 입력한 이름). ID 토큰의 name 클레임이 비어 있으면
	 * (updateProfile 직후 토큰이 아직 갱신 안 된 경우 등) Firebase 사용자 레코드에서 직접 조회한다.
	 */
	private String resolveDisplayName(FirebaseToken decoded) {
		if (decoded.getName() != null && !decoded.getName().isBlank()) {
			return decoded.getName();
		}
		try {
			UserRecord record = FirebaseAuth.getInstance().getUser(decoded.getUid());
			return record.getDisplayName();
		} catch (Exception e) {
			log.warn("[login] displayName 조회 실패 uid={}: {}", decoded.getUid(), e.getMessage());
			return null;
		}
	}

	private void requireFirebaseInitialized() {
		if (FirebaseApp.getApps().isEmpty()) {
			throw ApiException.serviceUnavailable(
				"서버에 Firebase 서비스 계정 키가 설정되지 않았습니다. "
					+ "backend/src/main/resources/firebase-service-account.json 을 두고 서버를 재시작하세요.");
		}
	}

	private String nullSafe(String v) {
		return v == null ? "" : v;
	}
}

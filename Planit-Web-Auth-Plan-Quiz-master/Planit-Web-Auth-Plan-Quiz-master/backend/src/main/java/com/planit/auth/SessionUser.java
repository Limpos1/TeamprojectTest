package com.planit.auth;

import jakarta.servlet.http.HttpSession;

/**
 * 로그인 세션에 저장된 사용자 정보 읽기 헬퍼.
 * AuthController 가 Firebase ID 토큰을 검증한 뒤 uid/email/name 을 세션에 넣는다.
 */
public final class SessionUser {

	public static final String UID = "uid";
	public static final String EMAIL = "email";
	public static final String NAME = "name";

	private SessionUser() {
	}

	/** 로그인 안 되어 있으면 null. */
	public static String uid(HttpSession session) {
		return session == null ? null : (String) session.getAttribute(UID);
	}

	public static String email(HttpSession session) {
		return session == null ? null : (String) session.getAttribute(EMAIL);
	}

	/** displayName(ID 토큰의 name 클레임). 설정 안 했으면 null. */
	public static String name(HttpSession session) {
		return session == null ? null : (String) session.getAttribute(NAME);
	}
}

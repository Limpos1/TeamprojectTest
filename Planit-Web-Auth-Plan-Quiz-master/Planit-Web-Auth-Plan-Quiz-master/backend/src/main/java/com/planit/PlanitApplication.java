package com.planit;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Planit 애플리케이션 (방식 B).
 *
 * - 로그인/회원가입: 브라우저에서 Firebase JS 로 처리하고, ID 토큰을 Spring 에 보내 검증받는다.
 * - 그 외 모든 데이터: Spring 이 Firebase Admin SDK 로 Firestore 를 읽고 쓴다.
 * - 브라우저는 Firestore 를 직접 건드리지 않고 /api/* 만 호출한다.
 * - MySQL/JPA 는 쓰지 않는다.
 */
@SpringBootApplication
public class PlanitApplication {

	public static void main(String[] args) {
		SpringApplication.run(PlanitApplication.class, args);
	}
}

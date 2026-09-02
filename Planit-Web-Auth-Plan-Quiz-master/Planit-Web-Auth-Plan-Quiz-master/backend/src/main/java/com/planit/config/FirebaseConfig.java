package com.planit.config;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;

import com.google.auth.oauth2.GoogleCredentials;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;

import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;

/**
 * Firebase Admin SDK 초기화 (방식 B).
 *
 * 서비스 계정 키를 찾는 순서:
 *   1) 환경변수 또는 시스템 프로퍼티 FIREBASE_CREDENTIALS (키 파일 절대경로)
 *   2) 클래스패스의 firebase-service-account.json
 *   3) backend/src/main/resources/ 안의 *-firebase-adminsdk-*.json (콘솔에서 받은 원래 파일명 그대로 둬도 됨)
 *
 * 이 키는 진짜 비밀값이라 절대 커밋하지 않는다(.gitignore 참고). 리더가 발급해서
 * 노션/드라이브로만 전달한다. login.html 의 firebaseConfig(apiKey 등)와는 완전히 다른 값이다.
 *
 * 키를 못 찾으면 앱은 그대로 뜨지만, 토큰 검증/Firestore 를 쓰는 API 는 503 을 돌려준다.
 */
@Slf4j
@Configuration
public class FirebaseConfig {

	private static final String DEFAULT_NAME = "firebase-service-account.json";
	private static final String RESOURCES_DIR = "src/main/resources";
	private static final String ADMINSDK_GLOB = "*-firebase-adminsdk-*.json";

	@PostConstruct
	public void init() {
		if (!FirebaseApp.getApps().isEmpty()) {
			return;
		}

		try (InputStream in = openServiceAccount()) {
			if (in == null) {
				log.warn("[Firebase] 서비스 계정 키를 찾지 못했습니다. 토큰 검증/Firestore API 는 동작하지 않습니다.\n"
					+ "  Firebase 콘솔 > 프로젝트 설정 > 서비스 계정 > 새 비공개 키 생성 으로 받은 JSON 을\n"
					+ "  backend/src/main/resources/firebase-service-account.json 으로 저장하거나, 원래 파일명(예:\n"
					+ "  planit-ccfff-firebase-adminsdk-xxxx.json) 그대로 backend/src/main/resources/ 에 두세요.");
				return;
			}
			FirebaseOptions options = FirebaseOptions.builder()
				.setCredentials(GoogleCredentials.fromStream(in))
				.build();
			FirebaseApp.initializeApp(options);
			log.info("[Firebase] Admin SDK 초기화 완료");
		} catch (IOException e) {
			log.error("[Firebase] 초기화 실패: {}", e.getMessage(), e);
		}
	}

	private InputStream openServiceAccount() throws IOException {
		// 1) 명시적 경로
		String explicit = System.getProperty("FIREBASE_CREDENTIALS", System.getenv("FIREBASE_CREDENTIALS"));
		if (explicit != null && !explicit.isBlank()) {
			Path p = Paths.get(explicit);
			if (Files.exists(p)) {
				log.info("[Firebase] 키: {}", p.toAbsolutePath());
				return Files.newInputStream(p);
			}
			log.warn("[Firebase] FIREBASE_CREDENTIALS 경로에 파일이 없습니다: {}", explicit);
		}

		// 2) 클래스패스의 고정 이름
		ClassPathResource fixed = new ClassPathResource(DEFAULT_NAME);
		if (fixed.exists()) {
			log.info("[Firebase] 키: classpath:{}", DEFAULT_NAME);
			return fixed.getInputStream();
		}

		// 3) backend/src/main/resources/*-firebase-adminsdk-*.json (콘솔에서 받은 원래 파일명)
		Path dir = Paths.get(RESOURCES_DIR);
		if (Files.isDirectory(dir)) {
			try (DirectoryStream<Path> stream = Files.newDirectoryStream(dir, ADMINSDK_GLOB)) {
				for (Path p : stream) {
					log.info("[Firebase] 키: {}", p.toAbsolutePath());
					return Files.newInputStream(p);
				}
			}
		}

		return null;
	}
}

package com.planit.global;

import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import com.google.firebase.auth.FirebaseAuthException;

import lombok.extern.slf4j.Slf4j;

/** REST 컨트롤러 예외를 { "message": ... } JSON 으로 통일한다. */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

	@ExceptionHandler(ApiException.class)
	public ResponseEntity<Map<String, String>> handleApi(ApiException e) {
		return ResponseEntity.status(e.getStatus()).body(Map.of("message", e.getMessage()));
	}

	@ExceptionHandler(FirebaseAuthException.class)
	public ResponseEntity<Map<String, String>> handleFirebaseAuth(FirebaseAuthException e) {
		log.warn("[FirebaseAuthException] {}", e.getMessage());
		return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
			.body(Map.of("message", "로그인 인증에 실패했습니다"));
	}

	/** 브라우저가 자동 요청하는 /favicon.ico 등 없는 정적 리소스 → 스택트레이스 없이 조용히 404. */
	@ExceptionHandler(NoResourceFoundException.class)
	public ResponseEntity<Map<String, String>> handleNoResource(NoResourceFoundException e) {
		return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("message", "리소스를 찾을 수 없습니다"));
	}

	/** 요청 본문 JSON 이 깨졌을 때 → 500 이 아니라 400. */
	@ExceptionHandler(HttpMessageNotReadableException.class)
	public ResponseEntity<Map<String, String>> handleUnreadable(HttpMessageNotReadableException e) {
		return ResponseEntity.badRequest().body(Map.of("message", "요청 본문 형식이 올바르지 않습니다"));
	}

	@ExceptionHandler(Exception.class)
	public ResponseEntity<Map<String, String>> handleEtc(Exception e) {
		log.error("[Unhandled] {}", e.getMessage(), e);
		return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
			.body(Map.of("message", "서버 오류가 발생했습니다"));
	}
}

package com.planit.global;

import org.springframework.http.HttpStatus;

import lombok.Getter;

/** 예상 가능한 실패(권한 없음, 없는 리소스, 중복 제출 등)에 던지는 예외. GlobalExceptionHandler 가 JSON 으로 변환. */
@Getter
public class ApiException extends RuntimeException {

	private final HttpStatus status;

	public ApiException(HttpStatus status, String message) {
		super(message);
		this.status = status;
	}

	public static ApiException notFound(String message) {
		return new ApiException(HttpStatus.NOT_FOUND, message);
	}

	public static ApiException forbidden(String message) {
		return new ApiException(HttpStatus.FORBIDDEN, message);
	}

	public static ApiException badRequest(String message) {
		return new ApiException(HttpStatus.BAD_REQUEST, message);
	}

	public static ApiException conflict(String message) {
		return new ApiException(HttpStatus.CONFLICT, message);
	}

	public static ApiException serviceUnavailable(String message) {
		return new ApiException(HttpStatus.SERVICE_UNAVAILABLE, message);
	}
}

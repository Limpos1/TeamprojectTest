package com.planit.auth;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * 로그인(세션 uid)이 없는 요청을 401 JSON 으로 막는다.
 * WebConfig 에서 /api/quizzes/** 에만 건다. (로그인/정적 페이지는 제외)
 */
@Component
public class AuthInterceptor implements HandlerInterceptor {

	@Override
	public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
		throws Exception {
		if (SessionUser.uid(request.getSession(false)) != null) {
			return true;
		}
		response.setStatus(HttpStatus.UNAUTHORIZED.value());
		response.setContentType(MediaType.APPLICATION_JSON_VALUE);
		response.setCharacterEncoding("UTF-8");
		response.getWriter().write("{\"message\":\"로그인이 필요합니다\"}");
		return false;
	}
}

package com.planit.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import com.planit.auth.AuthInterceptor;

import lombok.RequiredArgsConstructor;

@Configuration
@RequiredArgsConstructor
public class WebConfig implements WebMvcConfigurer {

	private final AuthInterceptor authInterceptor;

	@Override
	public void addInterceptors(InterceptorRegistry registry) {
		// 데이터 API 는 로그인 필수. 로그인/로그아웃/정적 페이지는 그대로 열어둔다.
		registry.addInterceptor(authInterceptor).addPathPatterns("/api/quizzes/**");
	}
}

package com.example.project_checklist.global.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;

/**
 * 임시 설정입니다.
 *
 * 인증 도메인(회원가입/로그인 담당)의 실제 SecurityConfig 가 머지되면 이 클래스는 삭제하고
 * 그쪽 설정을 사용하세요. 지금은 study-plan-item API 를 memberId 파라미터로 바로 테스트할 수
 * 있도록 전체 요청을 permitAll 처리만 해 둔 상태입니다. (Spring Security 기본값을 켜두면
 * 로그인 없이는 전부 401 이 나서 이 도메인만 따로 개발/테스트하기 어렵습니다.)
 */
@Configuration
public class TempSecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .authorizeHttpRequests(auth -> auth.anyRequest().permitAll());
        return http.build();
    }
}

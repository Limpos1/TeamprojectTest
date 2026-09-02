package com.planit.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 우리 React 프론트엔드(Vite 개발 서버, localhost:5173 / localhost:3000)가
 * 이 서버(8081번 포트)의 로그인 API를 브라우저에서 직접 호출할 수 있게 허용한다.
 *
 * 로그인은 원래 이 프로젝트 자신의 정적 페이지(login.html)에서만 호출하도록
 * 만들어져서 CORS 설정 자체가 없었다 - 같은 출처(origin)라 브라우저가 막을
 * 이유가 없었기 때문. 그런데 우리는 React 앱(다른 포트)에서 이 서버를
 * 부르므로 CORS를 열어줘야 한다.
 *
 * 로그인은 세션 쿠키(HttpSession)를 쓰기 때문에, 체크리스트 서버의
 * CorsConfig처럼 allowedOrigins("*")로 전부 열어버리면 안 된다 - "출처
 * 와일드카드 + 쿠키 전송"조합은 브라우저가 아예 막는다. 그래서 여기는
 * 출처를 정확히 나열하고 allowCredentials(true)를 같이 켠다.
 */
@Configuration
public class CorsConfig {

    @Bean
    public WebMvcConfigurer corsConfigurer() {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/api/**")
                        .allowedOrigins("http://localhost:5173", "http://localhost:3000")
                        .allowedMethods("GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS")
                        .allowCredentials(true);
            }
        };
    }
}
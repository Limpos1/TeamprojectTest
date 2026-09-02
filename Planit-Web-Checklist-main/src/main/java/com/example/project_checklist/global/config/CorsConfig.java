package com.example.project_checklist.global.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * TEMP: 아직 실제 프론트엔드가 없어서, 로컬 데모 HTML(file:// 로 여는 정적 파일)이나
 * 다른 포트에서 API를 직접 호출해 테스트/시연할 수 있도록 임시로 모든 오리진을 허용합니다.
 * TODO: 실제 프론트엔드 배포 도메인이 정해지면 allowedOrigins를 그 도메인으로 제한하세요.
 */
@Configuration
public class CorsConfig {

    @Bean
    public WebMvcConfigurer corsConfigurer() {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/api/**")
                        .allowedOrigins("*")
                        .allowedMethods("GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS");
            }
        };
    }
}

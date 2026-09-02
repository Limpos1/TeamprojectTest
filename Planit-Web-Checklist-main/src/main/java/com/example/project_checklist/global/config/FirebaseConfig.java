package com.example.project_checklist.global.config;

import com.google.auth.oauth2.GoogleCredentials;
import com.google.cloud.firestore.Firestore;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.cloud.FirestoreClient;
import java.io.IOException;
import java.io.InputStream;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;

/**
 * Firebase(Firestore) 연결 설정.
 *
 * 1) Firebase 콘솔(https://console.firebase.google.com) 접속 -> 팀 프로젝트 선택
 * 2) 톱니바퀴(프로젝트 설정) -> "서비스 계정" 탭 -> "새 비공개 키 생성" -> JSON 다운로드
 * 3) 다운로드한 파일을 src/main/resources/firebase-service-account.json 이름으로 저장
 *
 * 중요: 이 키 파일은 절대 git에 커밋하면 안 됩니다. 이 계정으로 우리 팀 Firebase 전체에
 * 접근할 수 있는 비밀 키라서, 커밋하면 DB 비밀번호를 그대로 공개 저장소에 올리는 것과 같습니다.
 * .gitignore 에 이미 추가해 뒀습니다 - git status 에 이 파일이 안 뜨는지 꼭 확인하세요.
 */
@Configuration
public class FirebaseConfig {

    @Value("${firebase.credentials-path:firebase-service-account.json}")
    private String credentialsPath;

    @Bean
    public Firestore firestore() throws IOException {
        if (FirebaseApp.getApps().isEmpty()) {
            try (InputStream serviceAccount = new ClassPathResource(credentialsPath).getInputStream()) {
                FirebaseOptions options = FirebaseOptions.builder()
                        .setCredentials(GoogleCredentials.fromStream(serviceAccount))
                        .build();
                FirebaseApp.initializeApp(options);
            }
        }
        return FirestoreClient.getFirestore();
    }
}

package com.example.project_checklist.global.entity;

/*
 * REMOVED: MySQL/JPA -> Firestore 전환하면서 더 이상 쓰지 않습니다.
 * (JPA의 @MappedSuperclass/@CreatedDate 는 Firestore 엔티티에 적용할 수 없어서,
 *  각 Firestore 문서 클래스가 createdAt/updatedAt 을 직접 필드로 들고 있습니다.)
 *
 * 이 세션 환경에서는 파일을 완전히 삭제할 권한이 없어서 내용만 비워뒀습니다.
 * 프로젝트에서 이 파일(BaseTimeEntity.java) 자체를 지우셔도 됩니다.
 */

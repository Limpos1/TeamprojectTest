package com.planit.quiz;

import java.io.InputStream;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.cloud.firestore.DocumentReference;
import com.google.cloud.firestore.DocumentSnapshot;
import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.QueryDocumentSnapshot;
import com.google.firebase.FirebaseApp;
import com.google.firebase.cloud.FirestoreClient;
import com.planit.global.ApiException;
import com.planit.quiz.QuizDtos.QuestionView;
import com.planit.quiz.QuizDtos.StartResponse;
import com.planit.quiz.QuizDtos.SubmitResponse;
import com.planit.quiz.QuizDtos.SummaryResponse;
import com.planit.quiz.QuizDtos.TodayPlanItem;
import com.planit.quiz.QuizDtos.TodayPlanResponse;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

/**
 * 퀴즈봇 (REQ-Q-001 ~ REQ-Q-006). 방식 B: 저장소는 Firestore 이고, 접근은 전부 여기(Spring)를 거친다.
 * 브라우저는 Firestore 를 직접 건드리지 않는다.
 *
 * Firestore 구조:
 *   quizzes/{quizId}                      { uid, subjectName, todayScope, quizDate, createdAt, questions[] }
 *   quizzes/{quizId}/answers/{questionNo} { selectedChoice, correct, answeredAt }
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class QuizService {

	private static final String STUDY_PLAN_RESOURCE = "study_plan.json";

	private final ObjectMapper objectMapper;
	private final QuizQuestionGenerator questionGenerator;

	/** study_plan.json 1일차를 읽어 화면 표시용 항목과 출제 범위 문자열을 만든다. */
	public TodayPlanResponse todayPlan() {
		JsonNode day1;
		try (InputStream in = new ClassPathResource(STUDY_PLAN_RESOURCE).getInputStream()) {
			JsonNode root = objectMapper.readTree(in);
			JsonNode days = root.path("days");
			if (!days.isArray() || days.isEmpty()) {
				throw ApiException.notFound("study_plan.json 에 days 가 없습니다");
			}
			day1 = days.get(0);
		} catch (java.io.IOException e) {
			throw ApiException.notFound("study_plan.json 을 읽지 못했습니다");
		}

		List<TodayPlanItem> items = new ArrayList<>();
		List<String> scopeParts = new ArrayList<>();
		for (JsonNode it : day1.path("items")) {
			String title = it.path("title").asText("");
			String pageRange = it.hasNonNull("pageRange") ? it.get("pageRange").asText() : null;
			String status = it.path("status").asText("");
			items.add(new TodayPlanItem(title, pageRange, status));
			scopeParts.add(pageRange != null ? title + "(" + pageRange + ")" : title);
		}
		if (items.isEmpty()) {
			throw ApiException.notFound("1일차 학습 항목이 없습니다");
		}

		return new TodayPlanResponse(
			day1.path("date").asText(""),
			day1.path("minutes").isNumber() ? day1.get("minutes").asInt() : null,
			items,
			String.join(", ", scopeParts)
		);
	}

	/** REQ-Q-001 ~ REQ-Q-003: 오늘 학습 범위로 퀴즈 1세트 생성 → Firestore 저장. 정답/풀이는 응답에서 뺀다. */
	public StartResponse start(String uid) throws Exception {
		TodayPlanResponse plan = todayPlan();
		List<GeneratedQuestion> generated = questionGenerator.generate("quiz", plan.scope());

		List<Map<String, Object>> questionDocs = new ArrayList<>();
		int no = 1;
		for (GeneratedQuestion g : generated) {
			Map<String, Object> q = new LinkedHashMap<>();
			q.put("questionNo", no++);
			q.put("questionType", g.questionType());
			q.put("questionText", g.questionText());
			q.put("choice1", g.choice1());
			q.put("choice2", g.choice2());
			q.put("choice3", g.choice3());
			q.put("choice4", g.choice4());
			q.put("answerNo", g.answerNo());
			q.put("explanation", g.explanation());
			questionDocs.add(q);
		}

		Map<String, Object> quizDoc = new LinkedHashMap<>();
		quizDoc.put("uid", uid);
		quizDoc.put("subjectName", "quiz");
		quizDoc.put("todayScope", plan.scope());
		quizDoc.put("quizDate", LocalDate.now().toString());
		quizDoc.put("createdAt", com.google.cloud.firestore.FieldValue.serverTimestamp());
		quizDoc.put("questions", questionDocs);

		DocumentReference ref = db().collection("quizzes").document();
		ref.set(quizDoc).get();

		List<QuestionView> views = new ArrayList<>();
		for (Map<String, Object> q : questionDocs) {
			views.add(new QuestionView(
				(int) q.get("questionNo"),
				(String) q.get("questionType"),
				(String) q.get("questionText"),
				(String) q.get("choice1"),
				(String) q.get("choice2"),
				(String) q.get("choice3"),
				(String) q.get("choice4")
			));
		}
		return new StartResponse(ref.getId(), views);
	}

	/** REQ-Q-004, REQ-Q-005: 문제 하나 제출 → 채점 결과와 풀이. 문제당 1회만. */
	public SubmitResponse submit(String uid, String quizId, int questionNo, Integer selectedChoice)
		throws Exception {
		if (selectedChoice == null || selectedChoice < 1 || selectedChoice > 4) {
			throw ApiException.badRequest("보기 번호는 1~4 중 하나여야 합니다");
		}

		DocumentReference quizRef = db().collection("quizzes").document(quizId);
		DocumentSnapshot quizSnap = quizRef.get().get();
		requireOwnedQuiz(quizSnap, uid);

		Map<String, Object> question = findQuestion(quizSnap, questionNo);
		if (question == null) {
			throw ApiException.notFound("퀴즈 문제를 찾을 수 없습니다");
		}

		DocumentReference answerRef = quizRef.collection("answers").document(String.valueOf(questionNo));
		if (answerRef.get().get().exists()) {
			throw ApiException.conflict("이미 제출한 문제입니다");
		}

		int answerNo = ((Number) question.get("answerNo")).intValue();
		String explanation = (String) question.get("explanation");
		boolean correct = selectedChoice == answerNo;

		Map<String, Object> answerDoc = new LinkedHashMap<>();
		answerDoc.put("selectedChoice", selectedChoice);
		answerDoc.put("correct", correct);
		answerDoc.put("answeredAt", com.google.cloud.firestore.FieldValue.serverTimestamp());
		answerRef.set(answerDoc).get();

		return new SubmitResponse(questionNo, correct, answerNo, explanation);
	}

	/** REQ-Q-006: 제출한 답안을 모아 맞힌 개수 요약. */
	public SummaryResponse summary(String uid, String quizId) throws Exception {
		DocumentReference quizRef = db().collection("quizzes").document(quizId);
		DocumentSnapshot quizSnap = quizRef.get().get();
		requireOwnedQuiz(quizSnap, uid);

		int total = questionsOf(quizSnap).size();

		List<QueryDocumentSnapshot> answers = quizRef.collection("answers").get().get().getDocuments();
		int correct = 0;
		for (QueryDocumentSnapshot a : answers) {
			if (Boolean.TRUE.equals(a.getBoolean("correct"))) {
				correct++;
			}
		}
		return new SummaryResponse(quizId, total, answers.size(), correct);
	}

	/** 계정 탈퇴 시 해당 사용자의 퀴즈 데이터(quizzes 및 answers 서브컬렉션)를 모두 삭제한다. */
	public void deleteAllForUser(String uid) throws Exception {
		List<QueryDocumentSnapshot> quizzes =
			db().collection("quizzes").whereEqualTo("uid", uid).get().get().getDocuments();
		for (QueryDocumentSnapshot quiz : quizzes) {
			DocumentReference quizRef = quiz.getReference();
			for (DocumentReference answer : quizRef.collection("answers").listDocuments()) {
				answer.delete().get();
			}
			quizRef.delete().get();
		}
		log.info("[withdraw] uid={} 퀴즈 {}건 삭제", uid, quizzes.size());
	}

	// ---- 내부 헬퍼 ----

	private Firestore db() {
		if (FirebaseApp.getApps().isEmpty()) {
			throw ApiException.serviceUnavailable(
				"서버에 Firebase 서비스 계정 키가 없습니다. "
					+ "backend/src/main/resources/firebase-service-account.json 을 두고 서버를 재시작하세요.");
		}
		return FirestoreClient.getFirestore();
	}

	private void requireOwnedQuiz(DocumentSnapshot quizSnap, String uid) {
		if (!quizSnap.exists()) {
			throw ApiException.notFound("퀴즈를 찾을 수 없습니다");
		}
		if (!uid.equals(quizSnap.getString("uid"))) {
			throw ApiException.forbidden("본인의 퀴즈만 응시할 수 있습니다");
		}
	}

	@SuppressWarnings("unchecked")
	private List<Map<String, Object>> questionsOf(DocumentSnapshot quizSnap) {
		Object raw = quizSnap.get("questions");
		return raw instanceof List ? (List<Map<String, Object>>) raw : List.of();
	}

	private Map<String, Object> findQuestion(DocumentSnapshot quizSnap, int questionNo) {
		for (Map<String, Object> q : questionsOf(quizSnap)) {
			if (((Number) q.get("questionNo")).intValue() == questionNo) {
				return q;
			}
		}
		return null;
	}
}

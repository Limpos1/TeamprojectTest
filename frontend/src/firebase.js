// =========================================================================
// Firebase 클라이언트 초기화 — 로그인 백엔드(Planit-Web-Auth-Plan-Quiz)와
// 우리 React 앱을 연결하는 첫 번째 지점.
//
// 여기서 만드는 firebaseConfig는 팀원의 login.html에 있던 값을 그대로 옮겨온
// 것이다. apiKey는 "비밀번호" 같은 게 아니라 "이 앱이 어느 Firebase 프로젝트를
// 쓰는지" 식별만 하는 공개 값이라, 브라우저 코드에 그대로 들어가도 괜찮다
// (진짜 비밀값인 서비스 계정 키(firebase-service-account.json)와는 완전히
// 다른 것 - 그건 절대 프론트엔드 코드에 넣으면 안 된다).
//
// auth를 export해두면, 로그인 화면(LoginScreen.jsx)이 이걸로 Firebase에
// 직접 로그인/회원가입한다. 즉 아이디/비밀번호는 우리 서버를 거치지 않고
// 브라우저에서 곧바로 구글의 Firebase로 간다 - 우리는 비밀번호를 아예
// 본 적도 없다.
// =========================================================================
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyARjWc5NK1owKyP2WsXRGVILj_BLBRnEb4",
  authDomain: "planit-ccfff.firebaseapp.com",
  projectId: "planit-ccfff",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
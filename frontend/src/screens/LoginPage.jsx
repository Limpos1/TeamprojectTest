import { useState } from "react";
import { signInWithEmailAndPassword, signInWithPopup, GoogleAuthProvider } from "firebase/auth";
import { auth } from "../firebase";
import "./AuthPage.css";

// =========================================================================
// 로그인 페이지 — Planit-Web-Auth-Plan-Quiz(김동호)의 login.html 로직을
// React로 그대로 옮긴 버전. Firebase 설정(firebase.js)과 백엔드 엔드포인트,
// 에러 메시지까지 원본과 동일하게 맞췄다.
//
// 원본과 다른 점 하나: 로그인 성공 후 이동 경로를 하드코딩(/quiz.html)하지
// 않고, 부모(App.jsx)가 넘겨준 onLoggedIn(uid)을 호출한다. 그러면 App.jsx가
// "기존 플랜이 있으면 메인, 없으면 마법사 처음"으로 알아서 보내준다
// (PlanGeneratingAndMainPage/App.jsx의 handleLoggedIn 참고).
// =========================================================================

const AUTH_API_BASE = "http://localhost:8081";
const REMEMBER_KEY = "planit.rememberedEmail";
const googleProvider = new GoogleAuthProvider();

function authErrorMessage(err) {
  switch (err && err.code) {
    case "auth/invalid-email":
      return "이메일 형식이 올바르지 않습니다.";
    case "auth/email-already-in-use":
      return "이미 사용 중인 이메일입니다.";
    case "auth/weak-password":
      return "비밀번호는 6자 이상이어야 합니다.";
    case "auth/user-not-found":
    case "auth/wrong-password":
    case "auth/invalid-credential":
      return "이메일 또는 비밀번호가 올바르지 않습니다.";
    case "auth/too-many-requests":
      return "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.";
    case "auth/network-request-failed":
      return "네트워크 오류가 발생했습니다. 연결 상태를 확인해 주세요.";
    case "auth/popup-blocked":
      return "브라우저가 팝업을 차단했습니다. 팝업을 허용한 뒤 다시 시도해 주세요.";
    case "auth/popup-closed-by-user":
    case "auth/cancelled-popup-request":
      return "";
    default:
      return (err && err.message) || "로그인에 실패했습니다.";
  }
}

export default function LoginPage({ onLoggedIn, onGoSignup }) {
  const [email, setEmail] = useState(() => {
    try {
      return localStorage.getItem(REMEMBER_KEY) || "";
    } catch {
      return "";
    }
  });
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(() => {
    try {
      return !!localStorage.getItem(REMEMBER_KEY);
    } catch {
      return false;
    }
  });
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  // idToken을 서버에 보내 세션 발급받는 부분 — login.html의 exchangeTokenAndGo와 동일
  const exchangeTokenAndGo = async (user) => {
    const idToken = await user.getIdToken();
    const res = await fetch(`${AUTH_API_BASE}/api/auth/firebase-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ idToken }),
    });
    if (!res.ok) throw new Error("서버 인증에 실패했습니다. 잠시 후 다시 시도해 주세요.");
    const data = await res.json(); // { uid, email, name }
    localStorage.setItem("userId", data.uid);
    onLoggedIn(data.uid);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setMsg("");
    if (!email.trim() || !password) {
      setMsg("이메일과 비밀번호를 입력해 주세요.");
      return;
    }
    setLoading(true);
    try {
      const cred = await signInWithEmailAndPassword(auth, email.trim(), password);
      if (remember) localStorage.setItem(REMEMBER_KEY, email.trim());
      else localStorage.removeItem(REMEMBER_KEY);
      await exchangeTokenAndGo(cred.user);
    } catch (err) {
      setMsg(authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setMsg("");
    setLoading(true);
    try {
      const cred = await signInWithPopup(auth, googleProvider);
      await exchangeTokenAndGo(cred.user);
    } catch (err) {
      setMsg(authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <h1>로그인</h1>
      <div className="auth-card">
        <p className="auth-sub">이어서 계획을 확인하려면 로그인하세요.</p>

        <form onSubmit={handleLogin}>
          <div className="auth-field">
            <label htmlFor="login-email">이메일</label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="login-password">비밀번호</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <label className="auth-check">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            <span>아이디 저장하기</span>
          </label>

          {msg && <p className="auth-msg-error">{msg}</p>}

          <button type="submit" className="btn btn-lav btn-block" disabled={loading}>
            {loading ? "로그인 중…" : "로그인"}
          </button>
        </form>

        <div className="auth-divider"><span>또는</span></div>

        <button type="button" className="btn btn-white btn-block" onClick={handleGoogleLogin} disabled={loading}>
          구글로 로그인하기
        </button>

        <p className="auth-switch-line">
          계정이 없으신가요?{" "}
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              onGoSignup();
            }}
          >
            회원가입
          </a>
        </p>
      </div>
    </main>
  );
}

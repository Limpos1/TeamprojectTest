import { useState } from "react";
import { createUserWithEmailAndPassword, updateProfile, signOut } from "firebase/auth";
import { auth } from "../firebase";
import "./AuthPage.css";

// =========================================================================
// 회원가입 페이지 — login.html의 회원가입 로직을 React로 옮긴 버전.
// 이메일 중복 확인(서버 Admin SDK) → Firebase 가입 → 프로필 이름 설정 →
// 로그아웃 후 로그인 화면으로 전환(원본과 동일: 가입 직후 자동 로그인하지
// 않고 로그인 화면으로 돌려보냄).
// =========================================================================

const AUTH_API_BASE = "http://localhost:8081";

function authErrorMessage(err) {
  switch (err && err.code) {
    case "auth/invalid-email":
      return "이메일 형식이 올바르지 않습니다.";
    case "auth/email-already-in-use":
      return "이미 사용 중인 이메일입니다.";
    case "auth/weak-password":
      return "비밀번호는 6자 이상이어야 합니다.";
    case "auth/network-request-failed":
      return "네트워크 오류가 발생했습니다. 연결 상태를 확인해 주세요.";
    default:
      return (err && err.message) || "회원가입에 실패했습니다.";
  }
}

export default function SignupPage({ onGoLogin }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [msg, setMsg] = useState("");
  const [emailMsg, setEmailMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSignup = async (e) => {
    e.preventDefault();
    setMsg("");
    setEmailMsg("");

    if (!name.trim()) return setMsg("이름을 입력해 주세요.");
    if (!email.trim()) return setEmailMsg("이메일을 입력해 주세요.");
    if (password.length < 6) return setMsg("비밀번호는 6자 이상이어야 합니다.");
    if (password !== password2) return setMsg("비밀번호가 일치하지 않습니다.");

    setLoading(true);
    try {
      // 이메일 중복 확인 (서버가 Admin SDK로 판정)
      const chkRes = await fetch(`${AUTH_API_BASE}/api/auth/email-available`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      if (chkRes.ok) {
        const chk = await chkRes.json();
        if (!chk.available) {
          setEmailMsg("사용할 수 없는 이메일입니다.");
          setLoading(false);
          return;
        }
      }

      const cred = await createUserWithEmailAndPassword(auth, email.trim(), password);
      await updateProfile(cred.user, { displayName: name.trim() });
      // 가입 후 로그아웃하고 로그인 화면으로 (원본과 동일한 흐름)
      await signOut(auth);
      onGoLogin();
    } catch (err) {
      if (err && err.code === "auth/email-already-in-use") {
        setEmailMsg("사용할 수 없는 이메일입니다.");
      } else {
        setMsg(authErrorMessage(err));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <h1>회원가입</h1>
      <div className="auth-card">
        <p className="auth-sub">1분이면 충분해요. 가입하면 로그인 화면으로 이동합니다.</p>

        <form onSubmit={handleSignup}>
          <div className="auth-field">
            <label htmlFor="su-name">이름</label>
            <input
              id="su-name"
              type="text"
              autoComplete="name"
              placeholder="홍길동"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="su-email">이메일</label>
            <input
              id="su-email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {emailMsg && <p className="auth-msg-error">{emailMsg}</p>}
          </div>
          <div className="auth-field">
            <label htmlFor="su-password">비밀번호</label>
            <input
              id="su-password"
              type="password"
              autoComplete="new-password"
              placeholder="6자 이상"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="su-password2">비밀번호 확인</label>
            <input
              id="su-password2"
              type="password"
              autoComplete="new-password"
              placeholder="다시 입력"
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
            />
          </div>

          {msg && <p className="auth-msg-error">{msg}</p>}

          <button type="submit" className="btn btn-lav btn-block" disabled={loading}>
            {loading ? "처리 중…" : "회원가입 완료"}
          </button>
        </form>

        <p className="auth-switch-line">
          이미 계정이 있으신가요?{" "}
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              onGoLogin();
            }}
          >
            로그인
          </a>
        </p>
      </div>
    </main>
  );
}

import { useState } from "react";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  updateProfile,
} from "firebase/auth";
import { auth } from "../firebase";
import { s, theme } from "../theme";

// =========================================================================
// 로그인 화면 — "로그인 백엔드(Planit-Web-Auth-Plan-Quiz, 8081번 포트)"를
// 우리 React 앱에 실제로 연결하는 지점.
//
// 전체 흐름 (팀원 쪽에서 "방식 B"라고 부르던 것):
//   1) 브라우저가 Firebase Auth로 직접 로그인/회원가입한다(firebase.js의
//      auth 사용). 비밀번호는 우리 서버로 안 가고 구글의 Firebase로 바로 감.
//   2) 성공하면 Firebase가 "이 사람이 방금 로그인했다"를 증명하는 idToken을
//      돌려준다 (JWT 토큰, 몇 분마다 갱신되는 임시 증명서라고 생각하면 됨).
//   3) 그 idToken을 로그인 서버의 POST /api/auth/firebase-login 으로 보낸다.
//      서버가 Admin SDK로 "이 토큰 진짜 맞아?"를 검증하고, 맞으면 세션
//      쿠키를 만들어서 브라우저에 내려준다 (그 뒤로는 이 쿠키만으로 로그인
//      상태가 유지됨 - idToken을 프론트가 계속 들고 다닐 필요 없음).
//   4) 서버 응답에 진짜 회원 식별자(uid)가 담겨 온다. 이 uid를
//      localStorage의 "userId"에 저장하는 순간부터, 파이썬 플랜 서버
//      (checklist_sync.py)와 체크리스트 서버가 이 사람을 이 uid로 인식한다
//      - 지금까지 "guest"였던 자리에 이제 진짜 로그인한 사람이 들어가는 것.
//
// 주의: 이 fetch 호출들은 credentials: "include"를 꼭 넣어야 한다. 그래야
// 브라우저가 세션 쿠키를 같이 보내고 받는다. 서버 쪽(CorsConfig.java)도
// allowedOrigins에 우리 프론트 주소를 정확히 적고 allowCredentials(true)를
// 켜둬야 브라우저가 이걸 허용한다 (와일드카드 "*" + credentials 조합은
// 브라우저가 아예 막아버림).
// =========================================================================

const AUTH_API_BASE = "http://localhost:8081";

// 구글 로그인도 이메일/비밀번호와 흐름은 완전히 똑같다 - 어떤 방식으로
// idToken을 받았는지는 로그인 서버(AuthController.firebaseLogin)가 아예
// 신경 쓰지 않는다. 브라우저에서 Firebase로 로그인해서 idToken만 받으면
// 그 다음부터는 exchangeTokenAndLogin() 하나로 이메일/비밀번호 로그인과
// 완전히 같은 경로를 탄다.
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
    default:
      return null;
  }
}

export default function LoginScreen({ onLoggedIn }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Firebase 로그인/회원가입이 끝난 뒤 항상 이 함수를 거친다 - 위 설명의
  // 2)~4)번, 즉 "다리를 건너는" 부분이 전부 여기 들어있다.
  const exchangeTokenAndLogin = async (firebaseUser) => {
    const idToken = await firebaseUser.getIdToken();
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
    setError("");
    if (!email.trim() || !password) {
      setError("이메일과 비밀번호를 입력해 주세요.");
      return;
    }
    setLoading(true);
    try {
      const cred = await signInWithEmailAndPassword(auth, email.trim(), password);
      await exchangeTokenAndLogin(cred.user);
    } catch (err) {
      setError(authErrorMessage(err) || err.message || "로그인에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError("");
    setLoading(true);
    try {
      const cred = await signInWithPopup(auth, googleProvider);
      await exchangeTokenAndLogin(cred.user);
    } catch (err) {
      if (err && err.code === "auth/popup-closed-by-user") {
        // 사용자가 팝업을 그냥 닫은 것 - 에러로 보여줄 필요 없음.
      } else {
        setError(authErrorMessage(err) || err.message || "구글 로그인에 실패했습니다.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError("");
    if (!name.trim()) return setError("이름을 입력해 주세요.");
    if (!email.trim()) return setError("이메일을 입력해 주세요.");
    if (password.length < 6) return setError("비밀번호는 6자 이상이어야 합니다.");
    if (password !== password2) return setError("비밀번호가 일치하지 않습니다.");

    setLoading(true);
    try {
      // 이메일 중복 확인도 로그인 서버(Admin SDK)한테 물어본다. 세션이
      // 필요 없는 단순 조회라 credentials는 안 넣어도 된다.
      const chkRes = await fetch(`${AUTH_API_BASE}/api/auth/email-available`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      if (chkRes.ok) {
        const chk = await chkRes.json();
        if (!chk.available) {
          setError("사용할 수 없는 이메일입니다.");
          setLoading(false);
          return;
        }
      }

      const cred = await createUserWithEmailAndPassword(auth, email.trim(), password);
      await updateProfile(cred.user, { displayName: name.trim() });
      // 팀원의 원래 login.html은 가입 후 로그인 화면으로 돌려보내는데, 우리는
      // 화면 전환을 한 번 줄이려고 가입하자마자 바로 로그인까지 이어서 한다.
      await exchangeTokenAndLogin(cred.user);
    } catch (err) {
      if (err && err.code === "auth/email-already-in-use") {
        setError("사용할 수 없는 이메일입니다.");
      } else {
        setError(authErrorMessage(err) || err.message || "회원가입에 실패했습니다.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={s.page}>
      <div style={s.header}>
        <span style={s.logoDot} />
        <span style={s.logoText}>Planit</span>
      </div>

      <div style={s.card}>
        <h2 style={s.title}>{mode === "login" ? "로그인" : "회원가입"}</h2>
        <p style={s.subtitle}>
          {mode === "login"
            ? "이어서 학습 계획을 확인하려면 로그인하세요."
            : "몇 가지만 입력하면 바로 시작할 수 있어요."}
        </p>

        <form
          onSubmit={mode === "login" ? handleLogin : handleSignup}
          style={{ display: "flex", flexDirection: "column", gap: 10 }}
        >
          {mode === "signup" && (
            <input
              style={s.input}
              placeholder="이름"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          )}
          <input
            style={s.input}
            type="email"
            autoComplete="email"
            placeholder="이메일"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            style={s.input}
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            placeholder="비밀번호"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {mode === "signup" && (
            <input
              style={s.input}
              type="password"
              autoComplete="new-password"
              placeholder="비밀번호 확인"
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
            />
          )}

          {error && <p style={s.errorText}>{error}</p>}

          <div style={s.btnRow}>
            <button type="submit" disabled={loading} style={s.btnPrimary(loading)}>
              {loading ? "처리 중..." : mode === "login" ? "로그인" : "회원가입"}
            </button>
          </div>
        </form>

        <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "18px 0" }}>
          <div style={{ flex: 1, height: 1, background: theme.colors.border }} />
          <span style={{ fontSize: 12, color: theme.colors.textSoft }}>또는</span>
          <div style={{ flex: 1, height: 1, background: theme.colors.border }} />
        </div>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={loading}
          style={{ ...s.btnSecondary, width: "100%", opacity: loading ? 0.6 : 1 }}
        >
          Google로 로그인하기
        </button>

        <p style={{ marginTop: 18, fontSize: 13, color: theme.colors.textSoft }}>
          {mode === "login" ? (
            <>
              계정이 없으신가요?{" "}
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  setError("");
                  setMode("signup");
                }}
                style={{ color: theme.colors.primary, fontWeight: 700 }}
              >
                회원가입
              </a>
            </>
          ) : (
            <>
              이미 계정이 있으신가요?{" "}
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  setError("");
                  setMode("login");
                }}
                style={{ color: theme.colors.primary, fontWeight: 700 }}
              >
                로그인
              </a>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
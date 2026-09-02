import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import UploadScreen from "./screens/UploadScreen";
import SelectUnitsScreen from "./screens/SelectUnitsScreen";
import CalendarScreen from "./screens/CalendarScreen";
import AvailabilityScreen from "./screens/AvailabilityScreen";
import GeneratingScreen from "./screens/GeneratingScreen";
import MainScreen from "./screens/MainScreen";
import LoginScreen from "./screens/LoginScreen";
import LandingPage from "./screens/LandingPage";
import LoginPage from "./screens/LoginPage";
import SignupPage from "./screens/SignupPage";
import { filterParsedToc, rangeMinutes } from "./lib/toc";
import { s } from "./theme";

const API_BASE = "http://localhost:8000";
const AUTH_API_BASE = "http://localhost:8081";
const MAIN_PAGE_URL = "/main";
const WEEKDAY_KEYS = ["일", "월", "화", "수", "목", "금", "토"];

const STEP_ROUTES = [
  { path: "/upload", label: "목차 업로드" },
  { path: "/select", label: "과목 선택" },
  { path: "/calendar", label: "학습 기간" },
  { path: "/availability", label: "가용 시간" },
  { path: "/generating", label: "생성 중" },
];

function buildWeekdayMinutes({ weekdayRange, weekendRange, weekendExcluded }) {
  const weekdayMinutes = rangeMinutes(weekdayRange);
  const weekendMinutes = weekendExcluded ? 0 : rangeMinutes(weekendRange);
  const result = {};
  WEEKDAY_KEYS.forEach((name, idx) => {
    const isWeekend = idx === 0 || idx === 6;
    result[name] = isWeekend ? weekendMinutes : weekdayMinutes;
  });
  return result;
}

// handleLoggedIn과 같은 "기존 플랜 있으면 메인, 없으면 마법사" 판단을
// 별도 컴포넌트로 뺀 것 — AppRoutes 렌더링 중간에 바로 실행하면 안 되고
// (부수효과는 useEffect 안에서만), 화면엔 아무것도 안 그리고 판단이 끝나는
// 즉시 navigate로 실제 화면으로 넘어간다.
function RootRedirect({ userId }) {
  const navigate = useNavigate();
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/plans/${userId}`)
      .then((res) => {
        if (!cancelled) navigate(res.ok ? MAIN_PAGE_URL : "/upload", { replace: true });
      })
      .catch(() => {
        if (!cancelled) navigate("/upload", { replace: true });
      });
    return () => {
      cancelled = true;
    };
  }, [userId, navigate]);
  return null;
}

function AppRoutes() {
  const navigate = useNavigate();
  const location = useLocation();

  const [parsedToc, setParsedToc] = useState(null);
  const [filteredToc, setFilteredToc] = useState(null);
  const [calendarInfo, setCalendarInfo] = useState(null);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  // 로그인 게이트 — 로그인 백엔드(Planit-Web-Auth-Plan-Quiz)와 연결되는 지점.
  // localStorage에 "userId"가 있으면(=예전에 로그인해서 저장해둔 uid가 있으면)
  // 로그인된 걸로 보고 앱을 그대로 보여준다. 없으면 무슨 경로로 들어왔든
  // LoginScreen부터 보여준다. LoginScreen이 로그인에 성공하면
  // onLoggedIn(uid)를 호출하는데, 그게 바로 아래 setUserId다 - 그 순간
  // 이 컴포넌트가 다시 렌더링되면서 로그인 게이트를 통과하게 된다.
  const [userId, setUserId] = useState(() => localStorage.getItem("userId"));

  // localStorage에 userId가 남아있다고 해서 실제 로그인 세션이 살아있다는
  // 보장은 없다 - 서버가 재시작됐거나 세션이 만료됐으면 로그인 서버 입장에선
  // 이미 로그아웃 상태인데 브라우저만 "로그인된 줄" 착각하는 상황이 생긴다.
  // 그래서 로그인 백엔드의 GET /api/auth/me로 "이 세션 진짜 살아있어?"를 한 번
  // 물어보고, 죽어있으면(401) userId를 지워서 로그인 화면으로 돌려보낸다.
  // 네트워크 오류(서버가 아직 안 켜졌을 때 등)는 세션이 없다고 단정 짓지
  // 않는다 - 그냥 원래 로그인 상태를 유지한다.
  const [sessionChecked, setSessionChecked] = useState(false);
  useEffect(() => {
    const stored = localStorage.getItem("userId");
    if (!stored) {
      setSessionChecked(true);
      return;
    }
    fetch(`${AUTH_API_BASE}/api/auth/me`, { credentials: "include" })
      .then((res) => {
        if (!res.ok) {
          localStorage.removeItem("userId");
          setUserId(null);
        }
      })
      .catch(() => {})
      .finally(() => setSessionChecked(true));
  }, []);

  const handleParsed = (data) => {
    setParsedToc(data);
    navigate("/select");
  };

  const handleUnitsSelected = (excludedKeys) => {
    setFilteredToc(filterParsedToc(parsedToc, excludedKeys));
    navigate("/calendar");
  };

  const handleCalendarNext = (info) => {
    setCalendarInfo(info);
    navigate("/availability");
  };

  const handleAvailabilityNext = async (availability) => {
    navigate("/generating");
    setError("");
    setDone(false);
    const weekdayMinutes = buildWeekdayMinutes(availability);
    // 로그인 붙은 뒤: 이 시점엔 아래 로그인 게이트를 통과한 뒤라 항상 진짜
    // uid가 들어있다("guest"는 로그인 화면 자체를 테스트할 때만 나올 수 있는 값).
    const userId = localStorage.getItem("userId") || "guest";

    try {
      const res = await fetch(`${API_BASE}/generate-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parsedToc: filteredToc,
          startDate: calendarInfo.startDate,
          targetDate: calendarInfo.targetDate,
          weekdayMinutes,
          checkedDates: calendarInfo.checkedDates,
          userId,
        }),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `서버 오류 (${res.status})`);
      }
      await res.json();
      setDone(true);
      setTimeout(() => {
        navigate(MAIN_PAGE_URL);
      }, 1500);
    } catch (e) {
      setError(e.message || "플랜 생성 중 오류가 발생했습니다.");
      navigate("/availability");
    }
  };

  // 로그인 성공 직후 어디로 보낼지 정한다. 예전엔 무조건 "/upload"(마법사
  // 처음)로 보내서, 이미 만들어둔 플랜이 Firestore에 그대로 있는데도 로그인할
  // 때마다 목차 사진부터 새로 찍어야 하는 것처럼 보였다 - 실제로 데이터가
  // 지워진 게 아니라, 그 플랜이 있는지 확인도 안 하고 매번 마법사 처음으로
  // 보내버린 것뿐이었다. 그래서 GET /plans/{uid}로 "이 사람 플랜이 이미
  // 있나?"를 먼저 물어보고, 있으면(200) 바로 메인 캘린더로, 없으면(404,
  // 첫 로그인) 마법사 처음으로 보낸다.
  const handleLoggedIn = async (uid) => {
    setUserId(uid);
    try {
      const res = await fetch(`${API_BASE}/plans/${uid}`);
      navigate(res.ok ? MAIN_PAGE_URL : "/upload");
    } catch {
      navigate("/upload");
    }
  };

  // 세션 확인이 끝나기 전에는 로그인 화면과 메인 화면 중 뭘 보여줄지
  // 아직 모른다 - 성급하게 아무거나 그렸다가 확인 끝나고 바뀌면 화면이
  // 깜빡이므로, 확인 끝날 때까지는 빈 화면만 보여준다(보통 수십 ms 안에 끝남).
  if (!sessionChecked) {
    return null;
  }

  // 로그인 안 돼 있으면 어떤 경로로 들어왔든 로그인 화면부터 보여준다
  // (마법사/메인페이지 둘 다 이 아래에서 막힌다).
if (!userId) {
  if (location.pathname === "/login") {
    return <LoginPage onLoggedIn={handleLoggedIn} onGoSignup={() => navigate("/signup")} />;
  }
  if (location.pathname === "/signup") {
    return <SignupPage onGoLogin={() => navigate("/login")} />;
  }
  return <LandingPage onNavigate={navigate} />;
}

  // 이미 로그인된 채로(브라우저에 userId가 남아있는 채로) 사이트 루트("/")로
  // 들어온 경우 — 예: 주소창에 직접 쳐서 들어오거나 새로고침. 아래 STEP_ROUTES/
  // Routes 어디에도 "/"가 없어서 그냥 두면 "*"에 걸려 무조건 /upload로
  // 보내버린다(로그인 직후 판단 로직을 안 거침). handleLoggedIn과 똑같은 기준
  // (기존 플랜 있으면 메인, 없으면 마법사)으로 여기서도 판단해준다.
  if (location.pathname === "/") {
    return <RootRedirect userId={userId} />;
  }

  // "/main"은 팀 전체 메인페이지 — 마법사 껍데기(스텝바/카드) 없이 MainScreen이
  // 자기 레이아웃을 통째로 그린다. 그 외 경로는 좁은 마법사 카드 안에서 보여준다.
  if (location.pathname === "/main") {
    return <MainScreen />;
  }

  const currentStepIndex = STEP_ROUTES.findIndex((r) => r.path === location.pathname);

  return (
    <div style={s.page}>
      <div style={s.header}>
        <span style={s.logoDot} />
        <span style={s.logoText}>Planit</span>
      </div>

      <div style={s.stepBar}>
        {STEP_ROUTES.map((r, i) => (
          <span key={r.path} style={s.stepPill(i === currentStepIndex)}>
            {i + 1}. {r.label}
          </span>
        ))}
      </div>

      {error && <p style={s.errorText}>{error}</p>}

      <div style={s.card}>
        <Routes>
          <Route path="/upload" element={<UploadScreen onParsed={handleParsed} />} />
          <Route
            path="/select"
            element={
              <SelectUnitsScreen parsedToc={parsedToc} onNext={handleUnitsSelected} onBack={() => navigate("/upload")} />
            }
          />
          <Route
            path="/calendar"
            element={<CalendarScreen onNext={handleCalendarNext} onBack={() => navigate("/select")} />}
          />
          <Route
            path="/availability"
            element={<AvailabilityScreen onNext={handleAvailabilityNext} onBack={() => navigate("/calendar")} />}
          />
          <Route path="/generating" element={<GeneratingScreen done={done} />} />
          <Route path="*" element={<Navigate to="/upload" replace />} />
        </Routes>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
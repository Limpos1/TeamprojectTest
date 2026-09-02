import { useMemo, useState } from "react";
import { s, theme } from "../theme";

const WEEKDAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];

function fmt(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function addDays(date, n) {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

function getMonthGrid(year, month) {
  const first = new Date(year, month, 1);
  const startWeekday = first.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells = [];
  for (let i = 0; i < startWeekday; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));
  while (cells.length % 7 !== 0) cells.push(null);

  const weeks = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return weeks;
}

export default function CalendarScreen({ onNext, onBack }) {
  const [startMode, setStartMode] = useState("today");
  const today = useMemo(() => {
    const t = new Date();
    t.setHours(0, 0, 0, 0);
    return t;
  }, []);
  const startDate = startMode === "today" ? today : addDays(today, 1);

  const [targetDateStr, setTargetDateStr] = useState(null);
  const [checkedDates, setCheckedDates] = useState(new Set());
  const [viewDate, setViewDate] = useState(startDate);

  const weeks = getMonthGrid(viewDate.getFullYear(), viewDate.getMonth());

  const isBeforeStart = (date) => fmt(date) < fmt(startDate);

  const handlePickTarget = (date) => {
    if (isBeforeStart(date)) return;
    const targetStr = fmt(date);
    setTargetDateStr(targetStr);
    const range = new Set();
    let d = new Date(startDate);
    while (fmt(d) <= targetStr) {
      range.add(fmt(d));
      d = addDays(d, 1);
    }
    setCheckedDates(range);
  };

  const toggleDate = (date) => {
    const key = fmt(date);
    if (key < fmt(startDate) || key > targetDateStr) return;
    setCheckedDates((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const resetTarget = () => {
    setTargetDateStr(null);
    setCheckedDates(new Set());
  };

  const handleStartModeChange = (mode) => {
    setStartMode(mode);
    resetTarget();
  };

  const goNext = () => {
    onNext({
      startDate: fmt(startDate),
      targetDate: targetDateStr,
      checkedDates: Array.from(checkedDates).sort(),
    });
  };

  const excludedCount =
    targetDateStr &&
    (() => {
      let total = 0;
      let d = new Date(startDate);
      while (fmt(d) <= targetDateStr) {
        total++;
        d = addDays(d, 1);
      }
      return total - checkedDates.size;
    })();

  return (
    <div>
      <span style={s.tag}>🗓️ 학습 기간</span>
      <h2 style={s.title}>학습 기간을 설정하세요</h2>

      <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
          <input
            type="radio"
            checked={startMode === "today"}
            onChange={() => handleStartModeChange("today")}
            style={{ accentColor: theme.colors.primary }}
          />
          오늘부터 시작 ({fmt(today)})
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
          <input
            type="radio"
            checked={startMode === "tomorrow"}
            onChange={() => handleStartModeChange("tomorrow")}
            style={{ accentColor: theme.colors.primary }}
          />
          내일부터 시작 ({fmt(addDays(today, 1))})
        </label>
      </div>

      <p style={s.subtitle}>
        {targetDateStr
          ? "체크된 날짜가 학습 가능일이에요. 못 하는 날짜는 클릭해서 체크를 해제하세요."
          : "목표일을 달력에서 클릭하세요."}
      </p>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <button
          onClick={() => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1))}
          style={{ ...s.btnSecondary, padding: "6px 12px" }}
        >
          ◀
        </button>
        <strong>{viewDate.getFullYear()}년 {viewDate.getMonth() + 1}월</strong>
        <button
          onClick={() => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1))}
          style={{ ...s.btnSecondary, padding: "6px 12px" }}
        >
          ▶
        </button>
      </div>

      <table style={{ borderCollapse: "collapse", width: "100%", marginBottom: 16 }}>
        <thead>
          <tr>
            {WEEKDAY_LABELS.map((w) => (
              <th key={w} style={{ padding: 6, color: theme.colors.textSoft, fontWeight: 500, fontSize: 13 }}>
                {w}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {weeks.map((week, wi) => (
            <tr key={wi}>
              {week.map((date, di) => {
                if (!date) return <td key={di} />;
                const key = fmt(date);
                const disabled = key < fmt(startDate);
                const isTarget = key === targetDateStr;
                const inRange = targetDateStr && key >= fmt(startDate) && key <= targetDateStr;
                const isChecked = checkedDates.has(key);

                let bg = "transparent";
                let color = theme.colors.text;
                if (disabled) color = "#D8D3E0";
                else if (isTarget) bg = theme.colors.primary;
                else if (inRange && isChecked) bg = theme.colors.primarySoft;
                else if (inRange && !isChecked) bg = "#F1EEF6";
                if (isTarget) color = "#fff";
                else if (inRange && !isChecked) color = "#B7B0C4";

                return (
                  <td key={di} style={{ padding: 4, textAlign: "center" }}>
                    <button
                      disabled={disabled}
                      onClick={() => (targetDateStr ? toggleDate(date) : handlePickTarget(date))}
                      style={{
                        width: 34,
                        height: 34,
                        borderRadius: theme.radius.sm,
                        border: "none",
                        background: bg,
                        color,
                        fontWeight: isTarget ? 700 : 500,
                        cursor: disabled ? "not-allowed" : "pointer",
                        textDecoration: inRange && !isChecked && !isTarget ? "line-through" : "none",
                      }}
                    >
                      {date.getDate()}
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {targetDateStr && (
        <p style={{ color: theme.colors.textSoft, fontSize: 13 }}>
          목표일: <b style={{ color: theme.colors.text }}>{targetDateStr}</b> · 학습 가능일 {checkedDates.size}일 (제외 {excludedCount}일){" "}
          <button onClick={resetTarget} style={{ ...s.btnSecondary, padding: "4px 12px", fontSize: 12, marginLeft: 8 }}>
            목표일 다시 정하기
          </button>
        </p>
      )}

      <div style={s.btnRow}>
        <button onClick={onBack} style={s.btnSecondary}>이전</button>
        <button
          onClick={goNext}
          disabled={!targetDateStr || checkedDates.size === 0}
          style={s.btnPrimary(!targetDateStr || checkedDates.size === 0)}
        >
          다음
        </button>
      </div>
    </div>
  );
}
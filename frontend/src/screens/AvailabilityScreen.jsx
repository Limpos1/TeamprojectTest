import { useState } from "react";
import { s, theme } from "../theme";

export default function AvailabilityScreen({ onNext, onBack }) {
  const [weekdayRange, setWeekdayRange] = useState({ start: "20:00", end: "22:00" });
  const [weekendRange, setWeekendRange] = useState({ start: "10:00", end: "14:00" });
  const [weekendExcluded, setWeekendExcluded] = useState(false);

  const weekdayValid = weekdayRange.end > weekdayRange.start;
  const weekendValid = weekendExcluded || weekendRange.end > weekendRange.start;

  const handleNext = () => {
    onNext({ weekdayRange, weekendRange, weekendExcluded });
  };

  return (
    <div>
      <span style={s.tag}>⏱️ 가용 시간</span>
      <h2 style={s.title}>공부 가능 시간을 알려주세요</h2>
      <p style={s.subtitle}>평일과 주말의 공부 가능 시간대를 각각 정해주세요.</p>

      <div style={{ display: "flex", flexDirection: "column", gap: 20, marginBottom: 8 }}>
        <div style={{ background: "#FBF9FE", border: `1px solid ${theme.colors.border}`, borderRadius: theme.radius.md, padding: 16 }}>
          <strong style={{ fontSize: 14 }}>평일 (월~금)</strong>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10 }}>
            <input
              type="time"
              value={weekdayRange.start}
              onChange={(e) => setWeekdayRange((r) => ({ ...r, start: e.target.value }))}
              style={s.input}
            />
            <span style={{ color: theme.colors.textSoft }}>~</span>
            <input
              type="time"
              value={weekdayRange.end}
              onChange={(e) => setWeekdayRange((r) => ({ ...r, end: e.target.value }))}
              style={s.input}
            />
          </div>
          {!weekdayValid && <p style={s.errorText}>종료 시간이 시작 시간보다 늦어야 해요.</p>}
        </div>

        <div style={{ background: "#FBF9FE", border: `1px solid ${theme.colors.border}`, borderRadius: theme.radius.md, padding: 16 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <strong style={{ fontSize: 14 }}>주말 (토·일)</strong>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: theme.colors.textSoft }}>
              <input
                type="checkbox"
                checked={weekendExcluded}
                onChange={(e) => setWeekendExcluded(e.target.checked)}
                style={{ accentColor: theme.colors.primary }}
              />
              주말 학습 제외
            </label>
          </div>
          {!weekendExcluded && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10 }}>
              <input
                type="time"
                value={weekendRange.start}
                onChange={(e) => setWeekendRange((r) => ({ ...r, start: e.target.value }))}
                style={s.input}
              />
              <span style={{ color: theme.colors.textSoft }}>~</span>
              <input
                type="time"
                value={weekendRange.end}
                onChange={(e) => setWeekendRange((r) => ({ ...r, end: e.target.value }))}
                style={s.input}
              />
            </div>
          )}
          {!weekendValid && <p style={s.errorText}>종료 시간이 시작 시간보다 늦어야 해요.</p>}
        </div>
      </div>

      <div style={s.btnRow}>
        <button onClick={onBack} style={s.btnSecondary}>이전</button>
        <button onClick={handleNext} disabled={!weekdayValid || !weekendValid} style={s.btnPrimary(!weekdayValid || !weekendValid)}>
          플랜 생성하기
        </button>
      </div>
    </div>
  );
}
function downloadJson(plan) {
  const blob = new Blob([JSON.stringify(plan, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "study_plan.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function ResultScreen({ plan, onRestart }) {
  if (!plan) return null;

  return (
    <div>
      <h2>6. 생성된 학습 플랜</h2>

      {plan.warnings?.length > 0 && (
        <div style={{ background: "#fff8e1", border: "1px solid #ffe082", borderRadius: 8, padding: 12, marginBottom: 16 }}>
          {plan.warnings.map((w, i) => (
            <p key={i} style={{ margin: 0, color: "#8a6d00" }}>
              ⚠ {w}
            </p>
          ))}
        </div>
      )}

      <p style={{ color: "#555" }}>
        총 {plan.totalPages}페이지 · 총 {plan.totalMinutes}분 배정
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
        {plan.days.map((day) => (
          <div key={day.date} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12 }}>
            <strong>
              {day.date} ({day.minutes}분)
            </strong>
            {day.items.length === 0 ? (
              <p style={{ color: "#aaa", margin: "6px 0 0" }}>배정된 항목 없음</p>
            ) : (
              <ul style={{ margin: "6px 0 0" }}>
                {day.items.map((item, i) => (
                  <li key={i}>
                    {item.title} — {item.pageRange ? item.pageRange : `${item.pagesToday}p`}
                    {" "}
                    <span style={{ color: "#999" }}>
                      ({item.pagesToday}p / {item.totalPages}p)
                    </span>
                    {" "}
                    ({item.status})
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>

      <p style={{ color: "#888", fontSize: 13 }}>
        이 데이터가 다음 파트(스케줄 저장/화면 표시)로 전달됩니다.
      </p>

      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={() => downloadJson(plan)}>JSON으로 저장</button>
        <button onClick={onRestart}>처음부터 다시</button>
      </div>
    </div>
  );
}
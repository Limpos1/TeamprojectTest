import { theme } from "../theme";

export default function GeneratingScreen({ done }) {
  return (
    <div style={{ textAlign: "center", padding: "50px 0" }}>
      <div
        style={{
          width: 56,
          height: 56,
          margin: "0 auto 20px",
          borderRadius: "50%",
          background: theme.colors.primarySoft,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 26,
        }}
      >
        {done ? "✅" : "⏳"}
      </div>
      {done ? (
        <>
          <h2 style={{ margin: "0 0 6px", fontWeight: 800 }}>플랜이 완성됐어요!</h2>
          <p style={{ color: theme.colors.textSoft, margin: 0 }}>잠시 후 메인페이지로 이동합니다...</p>
        </>
      ) : (
        <>
          <h2 style={{ margin: "0 0 6px", fontWeight: 800 }}>플랜을 생성하고 있어요...</h2>
          <p style={{ color: theme.colors.textSoft, margin: 0 }}>선택하신 과목과 기간에 맞춰 학습 분량을 나누고 있습니다.</p>
        </>
      )}
    </div>
  );
}
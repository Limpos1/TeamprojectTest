import { useState } from "react";
import { getLeafUnits } from "../lib/toc";
import { s, theme } from "../theme";

export default function SelectUnitsScreen({ parsedToc, onNext, onBack }) {
  const leaves = getLeafUnits(parsedToc);
  const [checked, setChecked] = useState(() => {
    const initial = {};
    leaves.forEach((l) => (initial[l.key] = true));
    return initial;
  });

  const toggle = (key) => setChecked((prev) => ({ ...prev, [key]: !prev[key] }));

  const excludedKeys = Object.keys(checked).filter((k) => !checked[k]);
  const checkedCount = leaves.length - excludedKeys.length;

  return (
    <div>
      <span style={s.tag}>✅ 결과 확인</span>
      <h2 style={s.title}>학습할 과목을 선택하세요</h2>
      <p style={s.subtitle}>기본적으로 전부 체크되어 있어요. 이번에 공부하지 않을 항목은 체크를 해제하세요.</p>

      <div style={s.listBox}>
        {leaves.map((leaf) => (
          <label key={leaf.key} style={s.listRow}>
            <input
              type="checkbox"
              checked={checked[leaf.key]}
              onChange={() => toggle(leaf.key)}
              style={{ width: 16, height: 16, accentColor: theme.colors.primary }}
            />
            <span style={{ flex: 1, fontSize: 14 }}>
              {leaf.parentTitle && <span style={{ color: theme.colors.textSoft }}>{leaf.parentTitle} · </span>}
              {leaf.title}
            </span>
            <span style={{ color: theme.colors.textSoft, fontSize: 12 }}>{leaf.pageInfo}</span>
          </label>
        ))}
        {leaves.length === 0 && <p style={{ color: theme.colors.textSoft, padding: 12 }}>선택 가능한 학습 항목이 없어요.</p>}
      </div>

      <p style={{ color: theme.colors.textSoft, fontSize: 13, fontWeight: 600 }}>
        {checkedCount} / {leaves.length}개 선택됨
      </p>

      <div style={s.btnRow}>
        <button onClick={onBack} style={s.btnSecondary}>이전</button>
        <button onClick={() => onNext(excludedKeys)} disabled={checkedCount === 0} style={s.btnPrimary(checkedCount === 0)}>
          다음
        </button>
      </div>
    </div>
  );
}
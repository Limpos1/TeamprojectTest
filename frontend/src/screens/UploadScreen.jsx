import { useState } from "react";
import { s, theme } from "../theme";

const API_BASE = "http://localhost:8000";

let nextId = 1;
function newSubject() {
  return { id: nextId++, name: "", files: [], fileKind: "image" };
}

export default function UploadScreen({ onParsed }) {
  const [subjects, setSubjects] = useState([newSubject()]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [progressMsg, setProgressMsg] = useState("");

  const updateSubject = (id, patch) => {
    setSubjects((prev) => prev.map((sub) => (sub.id === id ? { ...sub, ...patch } : sub)));
  };

  const handleFileChange = (id, e) => {
    const selected = Array.from(e.target.files || []);
    if (selected.length === 0) return;
    const hasPdf = selected.some((f) => f.type === "application/pdf");
    if (hasPdf) {
      updateSubject(id, { files: [selected[0]], fileKind: "pdf" });
    } else {
      updateSubject(id, { files: selected, fileKind: "image" });
    }
    setError("");
  };

  const addSubject = () => {
    setSubjects((prev) => [...prev, newSubject()]);
  };

  const removeSubject = (id) => {
    setSubjects((prev) => (prev.length > 1 ? prev.filter((sub) => sub.id !== id) : prev));
  };

  const parseOneSubject = async (subject) => {
    const formData = new FormData();
    if (subject.fileKind === "pdf") {
      formData.append("file", subject.files[0]);
    } else {
      subject.files.forEach((f) => formData.append("files", f));
    }
    const endpoint = subject.fileKind === "pdf" ? "/parse-toc/pdf" : "/parse-toc/image";

    const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST", body: formData });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `서버 오류 (${res.status})`);
    }
    const data = await res.json();
    if (data.error) {
      throw new Error(`"${subject.name}" 목차를 찾지 못했어요. 다른 사진/파일로 시도해주세요.`);
    }
    return data;
  };

  const handleUpload = async () => {
    const invalid = subjects.find((sub) => !sub.name.trim() || sub.files.length === 0);
    if (invalid) {
      setError("모든 과목에 이름과 목차 파일을 채워주세요.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const allChapters = [];
      for (const subject of subjects) {
        setProgressMsg(`"${subject.name}" 분석 중... (${subjects.indexOf(subject) + 1}/${subjects.length})`);
        const data = await parseOneSubject(subject);
        const tagged = (data.chapters || []).map((c) => ({ ...c, subject: subject.name }));
        allChapters.push(...tagged);
      }
      onParsed({ chapters: allChapters });
    } catch (e) {
      setError(e.message || "업로드 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
      setProgressMsg("");
    }
  };

  return (
    <div>
      <span style={s.tag}>📷 목차 업로드</span>
      <h2 style={s.title}>과목별로 목차 사진을 넣어주세요</h2>
      <p style={s.subtitle}>
        과목(책)이 여러 개면 "과목 추가"로 나눠서 각각 이름을 정하고 목차를 넣으세요.
        한 과목 안에서는 사진 여러 장을 하나의 목차로 이어서 분석해요.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 16, marginBottom: 20 }}>
        {subjects.map((subject, idx) => (
          <div
            key={subject.id}
            style={{
              border: `1px solid ${theme.colors.border}`,
              borderRadius: theme.radius.md,
              padding: 16,
              background: "#FBF9FE",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <input
                type="text"
                placeholder={`과목 ${idx + 1} 이름 (예: 리눅스 개론)`}
                value={subject.name}
                onChange={(e) => updateSubject(subject.id, { name: e.target.value })}
                style={{ ...s.input, flex: 1 }}
              />
              {subjects.length > 1 && (
                <button onClick={() => removeSubject(subject.id)} style={s.btnSecondary}>
                  삭제
                </button>
              )}
            </div>

            <input
              type="file"
              accept="image/*,.pdf"
              multiple
              onChange={(e) => handleFileChange(subject.id, e)}
            />

            {subject.files.length > 0 && (
              <ul style={{ margin: "10px 0 0", padding: 0, listStyle: "none" }}>
                {subject.files.map((f, i) => (
                  <li key={i} style={{ fontSize: 13, color: theme.colors.textSoft, padding: "4px 0" }}>
                    {f.name}
                  </li>
                ))}
              </ul>
            )}
            {subject.fileKind === "image" && subject.files.length > 1 && (
              <p style={{ ...s.subtitle, margin: "8px 0 0" }}>
                사진 {subject.files.length}장을 하나의 목차로 이어서 분석합니다.
              </p>
            )}
          </div>
        ))}
      </div>

      <div style={s.btnRow}>
        <button onClick={addSubject} style={s.btnSecondary} disabled={loading}>
          + 과목 추가
        </button>
        <button onClick={handleUpload} disabled={loading} style={s.btnPrimary(loading)}>
          {loading ? progressMsg || "분석 중..." : "업로드 및 분석"}
        </button>
      </div>

      {error && <p style={s.errorText}>{error}</p>}
    </div>
  );
}
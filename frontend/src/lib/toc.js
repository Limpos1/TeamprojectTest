// postprocess.py / schedule.py의 "리프(leaf) 항목" 규칙을 프론트에서도 그대로 따른다.
// key는 chapter.order가 아니라 배열 안에서의 위치(인덱스)로 만든다 — 여러 과목을
// 합쳤을 때 서로 다른 과목의 chapter.order가 겹칠 수 있기 때문이다 (각 과목은
// 독립적으로 파싱되어서 챕터 번호가 1부터 다시 시작한다).
export function getLeafUnits(parsedToc) {
  const leaves = [];
  (parsedToc?.chapters ?? []).forEach((chapter, chapterIdx) => {
    if (chapter.contentType !== "CONTENT") return;
    const subunits = chapter.subunits ?? [];
    const subunitsHavePages = subunits.some((s) => s.startPage != null);
    const subjectPrefix = chapter.subject ? `${chapter.subject} · ` : "";
    if (subunits.length > 0 && subunitsHavePages) {
      subunits.forEach((sub, subIdx) => {
        leaves.push({
          key: `${chapterIdx}-${subIdx}`,
          chapterOrder: chapter.order,
          subOrder: sub.order,
          title: sub.title,
          parentTitle: `${subjectPrefix}${chapter.title}`,
          pageInfo:
            sub.startPage != null
              ? `${sub.startPage}p ~ ${sub.endPage ?? "?"}p`
              : "페이지 확인 필요",
        });
      });
    } else {
      leaves.push({
        key: `${chapterIdx}`,
        chapterOrder: chapter.order,
        subOrder: null,
        title: chapter.title,
        parentTitle: chapter.subject || null,
        pageInfo:
          chapter.startPage != null
            ? `${chapter.startPage}p ~ ${chapter.endPage ?? "?"}p`
            : "페이지 확인 필요",
      });
    }
  });
  return leaves;
}

// 사용자가 체크 해제한 리프(key 목록)를 실제로 parsedToc에서 제거해
// 백엔드(schedule.py)로 보낼 최종 목차를 만든다. key 규칙은 getLeafUnits와 동일하게
// 배열 인덱스 기준이어야 한다.
export function filterParsedToc(parsedToc, excludedKeys) {
  const excluded = new Set(excludedKeys);
  const chapters = (parsedToc?.chapters ?? [])
    .map((chapter, chapterIdx) => {
      const subunits = chapter.subunits ?? [];
      const subunitsHavePages = subunits.some((s) => s.startPage != null);
      if (chapter.contentType === "CONTENT" && subunits.length > 0 && subunitsHavePages) {
        const keptSubunits = subunits.filter(
          (sub, subIdx) => !excluded.has(`${chapterIdx}-${subIdx}`)
        );
        return { ...chapter, subunits: keptSubunits };
      }
      if (chapter.contentType === "CONTENT" && excluded.has(`${chapterIdx}`)) {
        return null;
      }
      return chapter;
    })
    .filter(Boolean);

  return { ...parsedToc, chapters };
}

export function parseHHMM(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export function rangeMinutes(range) {
  const start = parseHHMM(range.start);
  const end = parseHHMM(range.end);
  return Math.max(0, end - start);
}
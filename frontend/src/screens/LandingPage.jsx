import React from 'react';
import './LandingPage.css';

/**
 * 초기화면 (랜딩 페이지)
 *
 * props:
 *  - onNavigate(path: string): 페이지 이동 함수. App.jsx에서 react-router의
 *      navigate를 연결해서 넘겨줌.
 */
const LOGIN_PATH = '/login';
const SIGNUP_PATH = '/signup';

const FEATURES = [
  {
    tag: '단원 인식',
    title: '목차 사진 한 장',
    desc: 'PDF 및 이미지로 목차를 업로드하면 AI가 단원과 분량을 자동으로 읽어냅니다.',
  },
  {
    tag: '현실적 배분',
    title: '가능 시간에 맞춘 일정',
    desc: '시작일, 종료일, 선호 학습 시간대를 반영해 무리 없는 일정을 만들어 드립니다.',
  },
  {
    tag: '자동 재조정',
    title: '밀려도 괜찮아요',
    desc: '일정을 직접 옮기면 이후 계획이 자동으로 재배치되고, 며칠 쉬었다면 리플래닝 버튼 하나로 정리됩니다.',
  },
];

const TESTIMONIALS = [
  { quote: '유저리뷰1', who: '학습자1' },
  { quote: '유저리뷰2', who: '학습자2' },
  { quote: '유저리뷰3', who: '학습자3' },
];

export default function LandingPage({ onNavigate }) {
  const goLogin = () => onNavigate(LOGIN_PATH);
  const goSignup = () => onNavigate(SIGNUP_PATH);

  const scrollToFeatures = () => {
    document.getElementById('feat')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="landing">
      <nav className="landing-nav">
        <div className="landing-logo">
          <span className="dot"></span>Planit
        </div>
        <div>
          <button className="btn btn-white" onClick={goLogin}>
            로그인
          </button>{' '}
          <button className="btn btn-lav" onClick={goSignup}>
            회원가입
          </button>
        </div>
      </nav>

      <section className="hero">
        <div className="eyebrow">🪻 AI 학습 플래너</div>
        <h1>
          나에게 맞는 학습 계획을
          <br />
          AI가 직접 만들어드려요
        </h1>
        <p>
          목차 사진 한 장이면 충분해요. 시험일과 하루 가능 시간만 알려주면 AI가
          현실적인 학습 일정을 세우고, 밀리면 알아서 다시 짜드려요.
        </p>
        <div className="hero-actions">
          <button className="btn btn-white" onClick={scrollToFeatures}>
            더 알아보기 ↓
          </button>
        </div>
      </section>

      <section className="section" id="feat">
        <h2>이렇게 작동해요</h2>
        <p>복잡한 세팅 없이, 세 가지만 알려주면 나머지는 AI가 계산합니다.</p>
        <div className="feature-grid">
          {FEATURES.map((f) => (
            <div className="feature-card" key={f.title}>
              <div className="tag">{f.tag}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="testimonial-grid">
          {TESTIMONIALS.map((t) => (
            <div key={t.who}>
              <div>"{t.quote}"</div>
              <div className="who">— {t.who}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="cta-band">
          <h2>오늘, 계획을 세워보세요</h2>
          <button className="btn btn-lav" onClick={goSignup}>
            Planit 시작하기
          </button>
        </div>
      </section>

      <footer className="landing-footer">
        <span>© 2026 Planit</span>
        <span>ABOUT · PRIVACY · CONTACT</span>
      </footer>
    </div>
  );
}

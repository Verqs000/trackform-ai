"""
TrackForm AI - Main Web App
Run with: streamlit run app.py
"""

import streamlit as st
import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.pose_extractor import PoseExtractor
from models.event_classifier import EventClassifier
from models.technique_judge import TechniqueJudge
from auth import can_analyze, increment_usage, save_analysis, get_tier, get_usage_this_week, sign_out
from login_page import show_login_page
from coach_page import show_coach_page
from progress_page import show_progress_page
from leaderboard_page import show_leaderboard_page

st.set_page_config(
    page_title="TrackForm AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background-color: #0a0a0a; color: #e8e8e8; }
.stApp { background: #0a0a0a; }
[data-testid="stSidebar"] { background: #111111; border-right: 1px solid #1e1e1e; }
[data-testid="stSidebar"] * { color: #e8e8e8 !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
.hero-title { font-family: 'Bebas Neue', sans-serif; font-size: 5rem; line-height: 0.9; letter-spacing: 2px; color: #ffffff; margin-bottom: 0; }
.hero-accent { color: #ff3b3b; }
.hero-sub { font-size: 0.95rem; color: #666; letter-spacing: 3px; text-transform: uppercase; margin-top: 0.5rem; margin-bottom: 2rem; }
[data-testid="stFileUploader"] { background: #111 !important; border: 1px dashed #2a2a2a !important; border-radius: 12px !important; }
[data-testid="stFileUploader"]:hover { border-color: #ff3b3b !important; }
[data-testid="stFileUploader"] * { color: #888 !important; }
.stButton > button { background: #ff3b3b !important; color: #fff !important; border: none !important; border-radius: 6px !important; font-family: 'Bebas Neue', sans-serif !important; font-size: 1.2rem !important; letter-spacing: 2px !important; padding: 0.6rem 2rem !important; transition: background 0.2s !important; width: 100% !important; }
.stButton > button:hover { background: #cc2a2a !important; }
.score-card { background: #111; border: 1px solid #1e1e1e; border-radius: 16px; padding: 2rem; text-align: center; }
.score-number { font-family: 'Bebas Neue', sans-serif; font-size: 5rem; line-height: 1; margin: 0; }
.score-label { font-size: 0.75rem; letter-spacing: 3px; text-transform: uppercase; color: #555; margin-top: 0.3rem; }
.event-badge { display: inline-block; background: #ff3b3b; color: #fff; font-family: 'Bebas Neue', sans-serif; font-size: 1.4rem; letter-spacing: 3px; padding: 0.3rem 1.2rem; border-radius: 4px; margin-bottom: 0.5rem; }
.confidence-bar-wrap { background: #1e1e1e; border-radius: 99px; height: 4px; margin-top: 0.6rem; overflow: hidden; }
.confidence-bar-fill { background: #ff3b3b; height: 4px; border-radius: 99px; }
.error-high { background: #1a0a0a; border-left: 3px solid #ff3b3b; border-radius: 0 10px 10px 0; padding: 1.2rem 1.4rem; margin-bottom: 1rem; }
.error-medium { background: #141008; border-left: 3px solid #f59e0b; border-radius: 0 10px 10px 0; padding: 1.2rem 1.4rem; margin-bottom: 1rem; }
.error-low { background: #0a100a; border-left: 3px solid #22c55e; border-radius: 0 10px 10px 0; padding: 1.2rem 1.4rem; margin-bottom: 1rem; }
.error-title { font-family: 'Bebas Neue', sans-serif; font-size: 1.2rem; letter-spacing: 1px; color: #fff; margin-bottom: 0.5rem; }
.error-meta { font-size: 0.8rem; color: #888; margin-bottom: 0.3rem; }
.error-fix { font-size: 0.88rem; color: #ccc; margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid #1e1e1e; }
.drill-pill { display: inline-block; background: #161616; border: 1px solid #2a2a2a; color: #ccc; font-size: 0.82rem; padding: 0.35rem 0.9rem; border-radius: 99px; margin: 0.25rem; }
.section-header { font-family: 'Bebas Neue', sans-serif; font-size: 1.8rem; letter-spacing: 2px; color: #fff; border-bottom: 1px solid #1e1e1e; padding-bottom: 0.5rem; margin-bottom: 1.2rem; margin-top: 2rem; }
.usage-bar-wrap { background: #1e1e1e; border-radius: 99px; height: 4px; margin-top: 0.4rem; overflow: hidden; }
.usage-bar-fill { background: #ff3b3b; height: 4px; border-radius: 99px; }
.tip-box { background: #111; border: 1px solid #1e1e1e; border-radius: 10px; padding: 1.2rem; font-size: 0.85rem; color: #777; line-height: 1.8; }
.tip-box strong { color: #aaa; }
.summary-box { background: #111; border: 1px solid #1e1e1e; border-radius: 10px; padding: 1.2rem 1.5rem; font-size: 0.95rem; color: #aaa; line-height: 1.6; }
[data-testid="stMetric"] { background: #111; border: 1px solid #1e1e1e; border-radius: 10px; padding: 1rem; }
[data-testid="stMetricLabel"] { color: #666 !important; }
[data-testid="stMetricValue"] { color: #fff !important; font-family: 'Bebas Neue', sans-serif !important; font-size: 2rem !important; }
[data-testid="stExpander"] { background: #111 !important; border: 1px solid #1e1e1e !important; border-radius: 10px !important; }
[data-testid="stDownloadButton"] > button { background: transparent !important; border: 1px solid #2a2a2a !important; color: #888 !important; font-size: 0.85rem !important; font-family: 'DM Sans', sans-serif !important; letter-spacing: 0 !important; width: auto !important; }
[data-testid="stDownloadButton"] > button:hover { border-color: #ff3b3b !important; color: #fff !important; }
.stProgress > div > div { background: #ff3b3b !important; }
[data-baseweb="select"] { background: #111 !important; }
</style>
"""

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── AUTH GATE ─────────────────────────────────────────────────────────────────

if "user" not in st.session_state:
    show_login_page()
    st.stop()

user = st.session_state["user"]
user_id = user.id
tier = get_tier(user_id)
used_this_week = get_usage_this_week(user_id)
can_go, remaining = can_analyze(user_id)
FREE_LIMIT = 5

# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 1.5rem 0;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:3px;color:#fff;">
            TRACK<span style="color:#ff3b3b;">FORM</span>
        </div>
        <div style="font-size:0.7rem;letter-spacing:3px;text-transform:uppercase;color:#444;margin-top:2px;">
            AI Technique Coach
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.7rem;letter-spacing:3px;text-transform:uppercase;color:#444;margin-bottom:0.6rem;">NAVIGATE</div>', unsafe_allow_html=True)

    if "page" not in st.session_state:
        st.session_state["page"] = "analyze"

    pages = [
        ("⚡", "Analyze", "analyze"),
        ("📊", "My Progress", "progress"),
        ("🏆", "Leaderboard", "leaderboard"),
        ("🎯", "Coach Dashboard", "coach"),
    ]

    for icon, label, key in pages:
        if st.button(f"{icon}  {label}", key=f"nav_{key}"):
            st.session_state["page"] = key
            st.rerun()

    st.divider()

    if tier == "free":
        usage_pct = int((used_this_week / FREE_LIMIT) * 100)
        usage_color = "#22c55e" if used_this_week < 3 else "#f59e0b" if used_this_week < 5 else "#ff3b3b"
        st.markdown(f"""
        <div style="margin-bottom:1rem;">
            <div style="font-size:0.7rem;letter-spacing:3px;text-transform:uppercase;color:#444;margin-bottom:0.4rem;">WEEKLY USAGE</div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;color:{usage_color};">{used_this_week} / {FREE_LIMIT}</div>
            <div class="usage-bar-wrap"><div class="usage-bar-fill" style="width:{usage_pct}%;background:{usage_color};"></div></div>
            <div style="font-size:0.72rem;color:#444;margin-top:0.4rem;">{remaining} analyses left this week</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#111;border:1px solid #1e1e1e;border-radius:8px;padding:0.8rem;margin-bottom:1rem;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:0.9rem;letter-spacing:2px;color:#ff3b3b;">UPGRADE TO PRO</div>
            <div style="font-size:0.75rem;color:#555;margin-top:0.3rem;">Unlimited analyses + progress tracking</div>
            <div style="font-size:0.72rem;color:#333;margin-top:0.5rem;">$9.99/mo · trackformai@gmail.com</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        tier_color = "#ff3b3b" if tier == "coach" else "#f59e0b"
        st.markdown(f"""
        <div style="background:#111;border:1px solid #1e1e1e;border-radius:8px;padding:0.8rem;margin-bottom:1rem;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:0.9rem;letter-spacing:2px;color:{tier_color};">{tier.upper()} PLAN</div>
            <div style="font-size:0.75rem;color:#555;margin-top:0.3rem;">Unlimited analyses ✓</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.7rem;letter-spacing:3px;text-transform:uppercase;color:#444;margin-bottom:0.6rem;">SUPPORTED EVENTS</div>', unsafe_allow_html=True)
    for icon, name in [("⚡","Sprint blocks"),("🏋️","Shot put"),("💿","Discus"),("🏹","Javelin")]:
        st.markdown(f'<div style="display:flex;align-items:center;gap:0.6rem;padding:0.4rem 0;border-bottom:1px solid #1a1a1a;font-size:0.85rem;color:#666;"><span style="width:6px;height:6px;border-radius:50%;background:#ff3b3b;display:inline-block;flex-shrink:0;"></span>{icon} {name}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.75rem;color:#333;margin-bottom:0.4rem;">Signed in as<br><span style="color:#555;">{user.email}</span></div>', unsafe_allow_html=True)
    if st.button("Sign Out", key="signout"):
        sign_out()
        st.rerun()
    st.markdown('<div style="margin-top:1rem;font-size:0.65rem;color:#1e1e1e;letter-spacing:1px;">Built with MediaPipe + Streamlit</div>', unsafe_allow_html=True)


# ── PAGE ROUTING ──────────────────────────────────────────────────────────────

page = st.session_state.get("page", "analyze")

if page == "leaderboard":
    show_leaderboard_page(user)
    st.stop()

if page == "coach":
    show_coach_page(user)
    st.stop()

if page == "progress":
    show_progress_page(user)
    st.stop()

# ── ANALYZE PAGE ──────────────────────────────────────────────────────────────

st.markdown("""
<div style="margin-bottom:2rem;">
    <div class="hero-title">TRACK<span class="hero-accent">FORM</span><br>AI</div>
    <div class="hero-sub">⚡ Elite technique analysis — free</div>
</div>
""", unsafe_allow_html=True)

if not can_go:
    st.markdown(f"""
    <div style="background:#1a0a0a;border:1px solid #ff3b3b;border-radius:12px;padding:2rem;text-align:center;margin-bottom:2rem;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:2.5rem;letter-spacing:2px;color:#ff3b3b;margin-bottom:0.5rem;">WEEKLY LIMIT REACHED</div>
        <div style="color:#666;font-size:0.95rem;margin-bottom:1rem;">You've used all {FREE_LIMIT} free analyses this week. Your limit resets Monday.</div>
        <div style="background:#111;border:1px solid #1e1e1e;border-radius:8px;padding:1rem;display:inline-block;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:2px;color:#ff3b3b;">UPGRADE TO PRO — $9.99/mo</div>
            <div style="font-size:0.8rem;color:#555;margin-top:0.3rem;">Unlimited analyses + progress tracking + priority support</div>
            <div style="font-size:0.75rem;color:#333;margin-top:0.5rem;">Email: trackformai@gmail.com</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

uploaded_file = st.file_uploader(
    "Drop your video here — side view works best",
    type=['mp4', 'mov', 'avi', 'mkv', 'webm'],
)

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(uploaded_file.read())
        video_path = tmp.name

    col_vid, col_tip = st.columns([2, 1])
    with col_vid:
        st.video(uploaded_file)
    with col_tip:
        st.markdown("""
        <div class="tip-box">
            <strong>📐 Best results:</strong><br>
            · Side / profile view<br>
            · Full body in frame<br>
            · Good lighting<br>
            · 5–10 seconds is plenty
        </div>
        """, unsafe_allow_html=True)
        if tier == "free":
            st.markdown(f"""
            <div style="background:#111;border:1px solid #1e1e1e;border-radius:8px;padding:0.8rem;margin-top:0.8rem;">
                <div style="font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;color:#444;">THIS WEEK</div>
                <div style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;color:#fff;">{remaining} left</div>
                <div style="font-size:0.72rem;color:#444;">of {FREE_LIMIT} free analyses</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

    if st.button("⚡  ANALYZE MY TECHNIQUE"):
        progress_bar = st.progress(0)
        status = st.empty()

        try:
            status.markdown('<div style="color:#555;font-size:0.85rem;letter-spacing:2px;text-transform:uppercase;">Step 1 / 3 — Tracking body positions...</div>', unsafe_allow_html=True)
            progress_bar.progress(20)

            extractor = PoseExtractor()
            pose_data = extractor.extract_from_video(video_path, sample_every=2)

            if pose_data['poses_extracted'] < 5:
                st.error("Couldn't detect a body clearly. Try better lighting or a cleaner side view.")
                st.stop()

            status.markdown('<div style="color:#555;font-size:0.85rem;letter-spacing:2px;text-transform:uppercase;">Step 2 / 3 — Identifying event...</div>', unsafe_allow_html=True)
            progress_bar.progress(50)

            classifier = EventClassifier()
            classification = classifier.classify(pose_data)
            event_type = classification['event']
            confidence = classification['confidence']

            # DEBUG — remove after fixing classifier
            

            status.markdown('<div style="color:#555;font-size:0.85rem;letter-spacing:2px;text-transform:uppercase;">Step 3 / 3 — Judging technique...</div>', unsafe_allow_html=True)
            progress_bar.progress(80)

            judge = TechniqueJudge(event_type)
            analysis = judge.analyze(pose_data)
            analysis['overall_score'] = max(1, min(100, round(float(analysis['overall_score']) * 100)))

            increment_usage(user_id)
            save_analysis(
                user_id, event_type, analysis['overall_score'],
                analysis['errors'], analysis['recommended_drills'], analysis['metrics']
            )

            progress_bar.progress(100)
            status.empty()

            st.markdown('<div class="section-header">ANALYSIS RESULTS</div>', unsafe_allow_html=True)

            score = analysis['overall_score']
            score_color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ff3b3b"

            col_score, col_event, col_errors = st.columns(3)

            with col_score:
                st.markdown(f"""
                <div class="score-card">
                    <div class="score-number" style="color:{score_color};">{score}</div>
                    <div class="score-label">Technique Score / 100</div>
                </div>
                """, unsafe_allow_html=True)

            with col_event:
                bar_width = int(confidence * 100)
                st.markdown(f"""
                <div class="score-card">
                    <div class="event-badge">{event_type.replace('_',' ').upper()}</div>
                    <div class="score-label">Detected Event</div>
                    <div class="confidence-bar-wrap">
                        <div class="confidence-bar-fill" style="width:{bar_width}%;"></div>
                    </div>
                    <div style="font-size:0.75rem;color:#444;margin-top:0.4rem;">{bar_width}% confidence</div>
                </div>
                """, unsafe_allow_html=True)

            with col_errors:
                st.markdown(f"""
                <div class="score-card">
                    <div class="score-number" style="color:#fff;">{analysis['errors_found']}</div>
                    <div class="score-label">Issues Found</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f'<div class="summary-box" style="margin-top:1rem;">{analysis["summary"]}</div>', unsafe_allow_html=True)

            if analysis['errors']:
                st.markdown('<div class="section-header">ISSUES IDENTIFIED</div>', unsafe_allow_html=True)
                severity_colors = {'high': 'error-high', 'medium': 'error-medium', 'low': 'error-low'}
                severity_labels = {'high': '🔴 HIGH', 'medium': '🟡 MEDIUM', 'low': '🟢 LOW'}
                for i, error in enumerate(analysis['errors'], 1):
                    css_class = severity_colors.get(error['severity'], 'error-medium')
                    sev_label = severity_labels.get(error['severity'], error['severity'].upper())
                    drills_html = ''.join([f'<span class="drill-pill">{d}</span>' for d in error.get('drills', [])])
                    st.markdown(f"""
                    <div class="{css_class}">
                        <div class="error-title">{i}. {error['description']}</div>
                        <div class="error-meta">{sev_label} &nbsp;·&nbsp; Yours: <strong style="color:#ccc;">{error['your_value']}</strong> &nbsp;·&nbsp; Elite: <strong style="color:#ccc;">{error['ideal_value']}</strong></div>
                        <div class="error-fix">💡 {error['fix']}</div>
                        <div style="margin-top:0.6rem;">{drills_html}</div>
                    </div>
                    """, unsafe_allow_html=True)

            if analysis['recommended_drills']:
                st.markdown('<div class="section-header">RECOMMENDED DRILLS</div>', unsafe_allow_html=True)
                drills_html = ''.join([f'<span class="drill-pill" style="font-size:0.9rem;padding:0.5rem 1.1rem;">{d}</span>' for d in analysis['recommended_drills']])
                st.markdown(f"""
                <div style="background:#111;border:1px solid #1e1e1e;border-radius:12px;padding:1.5rem;">
                    {drills_html}
                    <div style="margin-top:1rem;font-size:0.8rem;color:#444;letter-spacing:1px;">
                        3 sets · 6–8 reps · focus on form over speed · re-film after 2 weeks
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with st.expander("Technical details"):
                st.json({'metrics': analysis['metrics'], 'phases': analysis['phases_detected'][:10], 'all_scores': classification['all_scores']})

            report = {
                'event': event_type,
                'score': analysis['overall_score'],
                'errors': analysis['errors'],
                'drills': analysis['recommended_drills'],
                'metrics': analysis['metrics']
            }
            st.download_button(
                "↓ Download report (JSON)",
                data=json.dumps(report, indent=2),
                file_name=f"trackform_{event_type}.json",
                mime="application/json"
            )

        except Exception as e:
            st.error(f"Analysis error: {str(e)}")
            st.exception(e)

else:
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:#333;">
        <div style="font-size:4rem;">⚡</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:2.5rem;letter-spacing:2px;color:#2a2a2a;">UPLOAD A VIDEO TO START</div>
        <div style="font-size:0.85rem;letter-spacing:2px;text-transform:uppercase;color:#2a2a2a;">Sprint · Shot · Discus · Javelin</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div style="margin-top:3rem;font-size:0.7rem;color:#1e1e1e;letter-spacing:2px;text-align:center;">TRACKFORM AI · MEDIAPIPE + STREAMLIT · FREE & OPEN SOURCE</div>', unsafe_allow_html=True)
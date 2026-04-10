"""
TrackForm AI — Main Web App (Production Ready)
Run with: streamlit run app.py
"""

import streamlit as st
import sys
import os
import tempfile
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.pose_extractor import PoseExtractor
from models.technique_judge import TechniqueJudge

from auth import (
    can_analyze, increment_usage, save_analysis,
    get_tier, get_usage_this_week, sign_out, handle_stripe_success,
    create_stripe_checkout
)
from login_page import show_login_page
from coach_page import show_coach_page
from progress_page import show_progress_page
from leaderboard_page import show_leaderboard_page

# =============================================================================
# CONFIGURATION
# =============================================================================
FREE_LIMIT = 5
STRIPE_PRICES = {
    "pro":   "price_1TJlDZFSa4OLK6hEpZDb8tNl",
    "coach": "price_1TJlGMFSa4OLK6hEaBXB4bQp",
}
EVENT_OPTIONS = {
    "⚡ Sprint / Block Start": "sprint",
    "🚧 Hurdles":              "hurdles",
    "🏋️ Shot Put":             "shot_put",
    "💿 Discus":               "discus",
    "🏹 Javelin":              "javelin",
}

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="TrackForm AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# SESSION STATE
# =============================================================================
if "sidebar_open"     not in st.session_state: st.session_state.sidebar_open     = True
if "page"             not in st.session_state: st.session_state.page             = "analyze"
if "analysis_results" not in st.session_state: st.session_state.analysis_results = None
if "processed_session" not in st.session_state: st.session_state.processed_session = None

# =============================================================================
# GLOBAL CSS
# =============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0a0a;
    color: #e8e8e8;
}
.stApp { background: #0a0a0a; }

[data-testid="stSidebar"] {
    background: #111111 !important;
    border-right: 1px solid #1e1e1e !important;
    min-width: 240px !important;
    max-width: 240px !important;
}
[data-testid="stSidebarCollapseButton"] { display: none !important; }

.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 5.2rem;
    line-height: 0.9;
    letter-spacing: 2px;
    color: #fff;
}
.hero-accent { color: #ff3b3b; }

.stButton > button {
    background: #ff3b3b !important;
    color: #fff !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1.2rem !important;
    width: 100% !important;
    transition: all 0.2s ease;
}
.stButton > button:hover { background: #ff5555 !important; transform: translateY(-1px); }

.nav-item .stButton > button {
    background: transparent !important;
    border: 1px solid #1e1e1e !important;
    color: #888 !important;
    text-align: left !important;
}
.nav-item-active .stButton > button {
    background: #1a0a0a !important;
    border: 1px solid #ff3b3b !important;
    color: #ff3b3b !important;
}
.toggle-btn .stButton > button {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    font-size: 1.5rem !important;
    color: #888 !important;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# AUTH
# =============================================================================
if "user" not in st.session_state:
    show_login_page()
    st.stop()

user    = st.session_state["user"]
user_id = user.id

# =============================================================================
# STRIPE PAYMENT VERIFICATION
# =============================================================================
params = st.query_params
if params.get("payment") == "success":
    session_id = params.get("session_id")
    if session_id and st.session_state.get("processed_session") != session_id:
        try:
            import stripe
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                uid        = session.metadata.get("user_id")
                tier_param = session.metadata.get("tier")
                if uid == user_id and tier_param in ["pro", "coach"]:
                    handle_stripe_success(uid, tier_param)
                    st.session_state.processed_session = session_id
                    st.query_params.clear()
                    st.success(f"🎉 Payment confirmed! Your account is now {tier_param.upper()}.")
                    st.rerun()
        except Exception:
            st.error("Payment verification failed.")

# =============================================================================
# USER DATA
# =============================================================================
tier           = get_tier(user_id)
used_this_week = get_usage_this_week(user_id)
can_go, remaining = can_analyze(user_id)

# =============================================================================
# SIDEBAR
# =============================================================================
if st.session_state.sidebar_open:
    with st.sidebar:
        st.markdown("""
        <div style="padding:1.8rem 0 1.8rem 0;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:2.1rem;letter-spacing:3px;color:#fff;">
                TRACK<span style="color:#ff3b3b;">FORM</span>
            </div>
            <div style="font-size:0.72rem;letter-spacing:3px;color:#444;">AI Technique Coach</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**NAVIGATE**")
        nav_items = [
            ("⚡", "Analyze",          "analyze"),
            ("📊", "My Progress",      "progress"),
            ("🏆", "Leaderboard",      "leaderboard"),
            ("🎯", "Coach Dashboard",  "coach"),
        ]
        for icon, label, key in nav_items:
            active = "nav-item-active" if st.session_state.page == key else "nav-item"
            st.markdown(f'<div class="{active}">', unsafe_allow_html=True)
            if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        # ── USAGE & UPGRADE ───────────────────────────────────────────────────
        if tier == "free":
            pct = min(int((used_this_week / FREE_LIMIT) * 100), 100)
            st.markdown(f"""
            <div style="background:#111;border:1px solid #1e1e1e;border-radius:12px;padding:1.2rem;">
                <div style="font-size:0.75rem;color:#666;">WEEKLY USAGE</div>
                <div style="font-size:2rem;font-family:'Bebas Neue',sans-serif;color:#ff3b3b;">{used_this_week}/{FREE_LIMIT}</div>
                <div style="height:6px;background:#1e1e1e;border-radius:10px;margin:8px 0;">
                    <div style="height:6px;width:{pct}%;background:#ff3b3b;border-radius:10px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("⚡ Upgrade to PRO — $9.99/mo", key="upgrade_pro", use_container_width=True):
                checkout = create_stripe_checkout(user_id, user.email, STRIPE_PRICES["pro"], "pro")
                st.session_state["checkout_result"] = checkout

            if st.button("🏆 Upgrade to COACH — $29.99/mo", key="upgrade_coach", use_container_width=True):
                checkout = create_stripe_checkout(user_id, user.email, STRIPE_PRICES["coach"], "coach")
                st.session_state["checkout_result"] = checkout

            if "checkout_result" in st.session_state:
                checkout = st.session_state["checkout_result"]
                if checkout.get("success") and checkout.get("url"):
                    st.link_button("👉 Click here to pay", checkout["url"])
                else:
                    st.error(f"Error: {checkout.get('error', 'Unknown')}")

        elif tier == "pro":
            st.success("✅ PRO Plan — Unlimited")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🏆 Upgrade to COACH — $29.99/mo", key="upgrade_coach", use_container_width=True):
                checkout = create_stripe_checkout(user_id, user.email, STRIPE_PRICES["coach"], "coach")
                st.session_state["checkout_result"] = checkout
            if "checkout_result" in st.session_state:
                checkout = st.session_state["checkout_result"]
                if checkout.get("success") and checkout.get("url"):
                    st.link_button("👉 Click here to pay", checkout["url"])
                else:
                    st.error(f"Error: {checkout.get('error', 'Unknown')}")

        else:
            st.success("✅ COACH Plan — Unlimited")

        st.divider()
        if st.button("🚪 Sign Out", use_container_width=True):
            sign_out()
            st.rerun()

# =============================================================================
# HAMBURGER TOGGLE
# =============================================================================
col_toggle, _ = st.columns([0.08, 0.92])
with col_toggle:
    icon = "✕" if st.session_state.sidebar_open else "☰"
    st.markdown('<div class="toggle-btn">', unsafe_allow_html=True)
    if st.button(icon, key="sidebar_toggle"):
        st.session_state.sidebar_open = not st.session_state.sidebar_open
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr style='border-color:#1a1a1a;margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# =============================================================================
# PAGE ROUTING
# =============================================================================
if st.session_state.page != "analyze":
    if st.session_state.page == "progress":
        show_progress_page(user)
    elif st.session_state.page == "leaderboard":
        show_leaderboard_page(user)
    elif st.session_state.page == "coach":
        show_coach_page(user)
    st.stop()

# =============================================================================
# ANALYZE PAGE
# =============================================================================
st.markdown('<div class="hero-title">TRACK<span class="hero-accent">FORM</span><br>AI</div>', unsafe_allow_html=True)
st.markdown('<div style="color:#666;font-size:1.1rem;letter-spacing:3px;">ELITE TECHNIQUE ANALYSIS</div>', unsafe_allow_html=True)

if not can_go:
    st.markdown("""
    <div style="background:#111;border:1px solid #ff3b3b;border-radius:12px;padding:2rem;text-align:center;margin-top:2rem;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;color:#ff3b3b;">WEEKLY LIMIT REACHED</div>
        <div style="color:#666;margin-top:0.5rem;">Upgrade to Pro for unlimited analyses — use the buttons in the sidebar.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.markdown("<br>", unsafe_allow_html=True)

selected_label = st.selectbox("Select Event", list(EVENT_OPTIONS.keys()))
selected_event = EVENT_OPTIONS[selected_label]

uploaded_file = st.file_uploader(
    "Drop your video here — side view works best",
    type=["mp4", "mov", "avi", "mkv", "webm"]
)

if uploaded_file and st.button("⚡ ANALYZE MY TECHNIQUE", type="primary", use_container_width=True):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(uploaded_file.read())
        video_path = tmp.name

    try:
        with st.spinner("🔍 Analyzing your technique... (10-30 seconds)"):
            extractor = PoseExtractor()
            poses, fps = extractor.extract_from_video(video_path, event=selected_event)
            judge   = TechniqueJudge()
            results = judge.analyze(poses, event=selected_event, fps=fps)

        increment_usage(user_id)
        save_analysis(
            user_id,
            selected_event,
            results.get("overall_score", 0),
            results.get("errors", []),
            results.get("drills", []),
            results.get("metrics", {})
        )

        st.success("✅ Analysis Complete!")
        st.markdown("<br>", unsafe_allow_html=True)

        # ── SCORE + SUMMARY ───────────────────────────────────────────────────
        score = results.get("overall_score", 0)
        color = "#3bff3b" if score >= 80 else "#ffaa3b" if score >= 60 else "#ff3b3b"

        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown(f"""
            <div style="background:#111;border:1px solid #1e1e1e;border-radius:16px;
                        padding:2.5rem 2rem;text-align:center;height:100%;">
                <div style="font-size:1.1rem;color:#ff3b3b;letter-spacing:2px;">
                    {selected_event.replace('_', ' ').upper()}
                </div>
                <div style="font-size:7rem;font-family:'Bebas Neue',sans-serif;
                            color:{color};line-height:1;">{score}</div>
                <div style="font-size:0.85rem;letter-spacing:2px;color:#555;">OVERALL SCORE</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            summary = results.get("summary", "")
            if summary:
                st.markdown(f"""
                <div style="background:#111;border:1px solid #1e1e1e;border-radius:12px;
                            padding:1.2rem 1.5rem;margin-bottom:1rem;">
                    <div style="font-size:0.75rem;letter-spacing:2px;color:#555;margin-bottom:0.4rem;">SUMMARY</div>
                    <div style="color:#ccc;font-size:1rem;line-height:1.5;">{summary}</div>
                </div>
                """, unsafe_allow_html=True)

            # ── KEY METRICS ───────────────────────────────────────────────────
            metrics = results.get("metrics", {})
            if metrics:
                st.markdown("""
                <div style="font-size:0.75rem;letter-spacing:2px;color:#555;margin-bottom:0.6rem;">
                    KEY METRICS
                </div>
                """, unsafe_allow_html=True)

                metric_cols = st.columns(2)
                for i, (k, v) in enumerate(metrics.items()):
                    if not isinstance(v, (int, float)):
                        continue
                    label = k.replace("_", " ").title()
                    if "angle" in k or "lean" in k:
                        display = f"{v:.1f}°"
                    elif "sec" in k or "duration" in k:
                        display = f"{v:.2f}s"
                    elif "frames" in k:
                        display = f"{int(v)} frames"
                    else:
                        display = f"{v:.2f}"

                    with metric_cols[i % 2]:
                        st.markdown(f"""
                        <div style="background:#0f0f0f;border:1px solid #1a1a1a;border-radius:8px;
                                    padding:0.8rem 1rem;margin-bottom:0.5rem;">
                            <div style="font-size:0.72rem;color:#555;letter-spacing:1px;">{label.upper()}</div>
                            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;
                                        color:#fff;">{display}</div>
                        </div>
                        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── ERRORS / ISSUES ───────────────────────────────────────────────────
        errors = results.get("errors", [])
        if errors:
            st.markdown("""
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;
                        letter-spacing:2px;color:#fff;margin-bottom:0.8rem;">
                ⚠️ ISSUES FOUND
            </div>
            """, unsafe_allow_html=True)

            for err in errors:
                severity    = err.get("severity", "medium")
                border_color = "#ff3b3b" if severity == "high" else "#ffaa3b" if severity == "medium" else "#3bff3b"
                label       = severity.upper()
                description = err.get("description", "")
                fix         = err.get("fix", "")

                st.markdown(f"""
                <div style="border-left:4px solid {border_color};background:#111;
                            border-radius:0 10px 10px 0;padding:1rem 1.2rem;margin-bottom:0.8rem;">
                    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;">
                        <span style="background:{border_color};color:#000;font-size:0.7rem;
                                     font-weight:700;padding:0.15rem 0.5rem;border-radius:4px;">
                            {label}
                        </span>
                        <span style="color:#ddd;font-size:0.95rem;font-weight:500;">{description}</span>
                    </div>
                    <div style="color:#888;font-size:0.88rem;margin-top:0.3rem;">
                        💡 <strong style="color:#aaa;">How to fix:</strong> {fix}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#0a1a0a;border:1px solid #1a3a1a;border-radius:10px;
                        padding:1rem 1.2rem;color:#3bff3b;font-size:0.95rem;">
                ✅ No major technique issues detected — great work!
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── RECOMMENDED DRILLS ────────────────────────────────────────────────
        drills = results.get("drills", [])
        if drills:
            st.markdown("""
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;
                        letter-spacing:2px;color:#fff;margin-bottom:0.8rem;">
                💡 RECOMMENDED DRILLS
            </div>
            """, unsafe_allow_html=True)

            for i, drill in enumerate(drills, 1):
                st.markdown(f"""
                <div style="background:#111;border:1px solid #1e1e1e;border-radius:10px;
                            padding:0.9rem 1.2rem;margin-bottom:0.5rem;display:flex;
                            align-items:flex-start;gap:0.8rem;">
                    <div style="background:#ff3b3b;color:#fff;font-family:'Bebas Neue',sans-serif;
                                font-size:1rem;min-width:1.8rem;height:1.8rem;border-radius:50%;
                                display:flex;align-items:center;justify-content:center;">{i}</div>
                    <div style="color:#ccc;font-size:0.95rem;padding-top:0.1rem;">{drill}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── DOWNLOAD REPORT ───────────────────────────────────────────────────
        st.download_button(
            "↓ Download Full Report",
            data=json.dumps(results, indent=2),
            file_name=f"trackform_{selected_event}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )

    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
    finally:
        if os.path.exists(video_path):
            os.unlink(video_path)

else:
    st.markdown("""
    <div style="background:#111;border:1px dashed #2a2a2a;border-radius:12px;
                padding:3rem;text-align:center;margin-top:1rem;">
        <div style="font-size:3rem;margin-bottom:1rem;">🎥</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;
                    letter-spacing:2px;color:#333;">UPLOAD A VIDEO TO BEGIN</div>
        <div style="color:#444;font-size:0.85rem;margin-top:0.5rem;">
            Side view works best • MP4, MOV, AVI, MKV, WEBM
        </div>
    </div>
    """, unsafe_allow_html=True)
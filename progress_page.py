"""
progress_page.py - Athlete progress tracking
"""

import streamlit as st
from auth import get_analysis_history, get_tier
from datetime import datetime


def show_progress_page(user):
    user_id = user.id
    tier = get_tier(user_id)

    st.markdown("""
    <style>
    .section-header {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.8rem;
        letter-spacing: 2px;
        color: #fff;
        border-bottom: 1px solid #1e1e1e;
        padding-bottom: 0.5rem;
        margin-bottom: 1.2rem;
        margin-top: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-bottom:2rem;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:3rem;letter-spacing:3px;color:#fff;">
            MY <span style="color:#ff3b3b;">PROGRESS</span>
        </div>
        <div style="font-size:0.75rem;letter-spacing:3px;text-transform:uppercase;color:#444;">
            Track your technique improvement over time
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Gate for free users
    if tier == "free":
        st.markdown("""
        <div style="background:#111;border:1px solid #ff3b3b;border-radius:12px;padding:2rem;text-align:center;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;letter-spacing:2px;color:#ff3b3b;margin-bottom:0.5rem;">
                PRO FEATURE
            </div>
            <div style="color:#666;font-size:0.9rem;margin-bottom:1rem;">
                Upgrade to Pro ($9.99/mo) to track your progress over time and see your improvement graphs.
            </div>
            <div style="color:#444;font-size:0.8rem;">
                Contact us to upgrade: trackformai@gmail.com
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    history = get_analysis_history(user_id, limit=50)

    if not history:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#333;">
            <div style="font-size:3rem;">📊</div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:2px;color:#2a2a2a;">
                NO ANALYSES YET
            </div>
            <div style="font-size:0.85rem;color:#2a2a2a;">Upload your first video to start tracking progress</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Summary stats
    scores = [a["score"] for a in history if a.get("score")]
    avg = int(sum(scores) / len(scores)) if scores else 0
    best = max(scores) if scores else 0
    latest = scores[0] if scores else 0
    trend = latest - scores[-1] if len(scores) > 1 else 0

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("Total Analyses", len(history), "#fff"),
        ("Average Score", avg, "#f59e0b" if avg >= 60 else "#ff3b3b"),
        ("Best Score", best, "#22c55e"),
        ("Trend", f"+{trend}" if trend > 0 else str(trend), "#22c55e" if trend > 0 else "#ff3b3b"),
    ]
    for col, (label, val, color) in zip([c1, c2, c3, c4], cards):
        with col:
            st.markdown(f"""
            <div style="background:#111;border:1px solid #1e1e1e;border-radius:10px;padding:1.2rem;text-align:center;">
                <div style="font-family:'Bebas Neue',sans-serif;font-size:2.2rem;color:{color};">{val}</div>
                <div style="font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;color:#444;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    # Score chart
    st.markdown('<div class="section-header">SCORE HISTORY</div>', unsafe_allow_html=True)

    if len(scores) >= 2:
        import pandas as pd
        chart_data = []
        for a in reversed(history):
            if a.get("score"):
                date_str = a["created_at"][:10]
                chart_data.append({"Date": date_str, "Score": a["score"], "Event": a.get("event_type", "unknown").replace("_", " ").title()})

        df = pd.DataFrame(chart_data)
        st.line_chart(df.set_index("Date")["Score"], color="#ff3b3b")
    else:
        st.markdown('<div style="color:#444;font-size:0.85rem;">Upload more videos to see your progress chart.</div>', unsafe_allow_html=True)

    # History list
    st.markdown('<div class="section-header">ANALYSIS HISTORY</div>', unsafe_allow_html=True)

    # Filter by event
    all_events = list(set([a.get("event_type", "unknown") for a in history]))
    selected_event = st.selectbox("Filter by event", ["All"] + [e.replace("_", " ").title() for e in all_events])

    for a in history:
        event = a.get("event_type", "unknown")
        if selected_event != "All" and event.replace("_", " ").title() != selected_event:
            continue

        score = a.get("score", 0)
        score_color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ff3b3b"
        event_display = event.replace("_", " ").upper()
        created = a.get("created_at", "")[:10]
        errors = a.get("errors", []) or []
        drills = a.get("drills", []) or []

        with st.expander(f"{event_display}  ·  Score: {score}  ·  {created}"):
            col_s, col_e = st.columns(2)
            with col_s:
                st.markdown(f"""
                <div style="text-align:center;padding:1rem;">
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:3rem;color:{score_color};">{score}</div>
                    <div style="font-size:0.7rem;letter-spacing:2px;color:#444;">TECHNIQUE SCORE</div>
                </div>
                """, unsafe_allow_html=True)
            with col_e:
                st.markdown(f"""
                <div style="padding:1rem;">
                    <div style="font-size:0.7rem;letter-spacing:2px;color:#444;margin-bottom:0.5rem;">ISSUES FOUND</div>
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;color:#fff;">{len(errors)}</div>
                </div>
                """, unsafe_allow_html=True)

            if errors:
                st.markdown('<div style="font-size:0.75rem;letter-spacing:2px;text-transform:uppercase;color:#444;margin-top:0.5rem;">ERRORS</div>', unsafe_allow_html=True)
                for e in errors:
                    severity_color = "#ff3b3b" if e.get("severity") == "high" else "#f59e0b" if e.get("severity") == "medium" else "#22c55e"
                    st.markdown(f"""
                    <div style="border-left:3px solid {severity_color};padding:0.5rem 0.8rem;margin:0.3rem 0;background:#0a0a0a;border-radius:0 6px 6px 0;font-size:0.85rem;color:#aaa;">
                        {e.get('description', '')}
                    </div>
                    """, unsafe_allow_html=True)

            if drills:
                st.markdown('<div style="font-size:0.75rem;letter-spacing:2px;text-transform:uppercase;color:#444;margin-top:0.8rem;">RECOMMENDED DRILLS</div>', unsafe_allow_html=True)
                drills_html = "".join([f'<span style="display:inline-block;background:#161616;border:1px solid #2a2a2a;color:#ccc;font-size:0.8rem;padding:0.3rem 0.8rem;border-radius:99px;margin:0.2rem;">{d}</span>' for d in drills])
                st.markdown(drills_html, unsafe_allow_html=True)
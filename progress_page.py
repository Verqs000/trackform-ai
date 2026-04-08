"""
progress_page.py - Athlete progress tracking
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from auth import get_analysis_history, get_tier


def show_progress_page(user):
    user_id = user.id
    tier = get_tier(user_id)

    # Custom CSS
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
    .stat-card {
        background: #111;
        border: 1px solid #1e1e1e;
        border-radius: 12px;
        padding: 1.3rem 1rem;
        text-align: center;
    }
    .stat-value {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.4rem;
        font-weight: 400;
    }
    </style>
    """, unsafe_allow_html=True)

    # Page Header
    st.markdown("""
    <div style="margin-bottom:2.5rem;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:3rem;letter-spacing:3px;color:#fff;">
            MY <span style="color:#ff3b3b;">PROGRESS</span>
        </div>
        <div style="font-size:0.78rem;letter-spacing:3px;text-transform:uppercase;color:#444;">
            Track your technique improvement over time
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tier Gate (Free users)
    if tier == "free":
        st.markdown("""
        <div style="background:#111; border:1px solid #ff3b3b; border-radius:12px; padding:2.5rem; text-align:center;">
            <div style="font-family:'Bebas Neue',sans-serif; font-size:2.2rem; letter-spacing:2px; color:#ff3b3b; margin-bottom:0.8rem;">
                PRO FEATURE
            </div>
            <div style="color:#666; font-size:0.95rem; margin-bottom:1.2rem; line-height:1.5;">
                Upgrade to Pro ($9.99/mo) to unlock progress tracking, 
                score history charts, and detailed improvement insights.
            </div>
            <div style="color:#444; font-size:0.85rem;">
                Contact us to upgrade: trackformai@gmail.com
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Load history
    with st.spinner("Loading your progress..."):
        history = get_analysis_history(user_id, limit=100)

    if not history:
        st.markdown("""
        <div style="text-align:center; padding:4rem 1rem; color:#333;">
            <div style="font-size:4rem; margin-bottom:1rem;">📈</div>
            <div style="font-family:'Bebas Neue',sans-serif; font-size:1.8rem; letter-spacing:2px; color:#2a2a2a;">
                NO ANALYSES YET
            </div>
            <p style="color:#555; font-size:0.95rem;">
                Upload your first video analysis to start tracking your progress.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Calculate stats
    scores = [a.get("score", 0) for a in history if a.get("score") is not None]
    avg_score = int(sum(scores) / len(scores)) if scores else 0
    best_score = max(scores) if scores else 0
    latest_score = scores[0] if scores else 0
    oldest_score = scores[-1] if len(scores) > 1 else latest_score
    trend = latest_score - oldest_score

    # Summary Stats Cards
    st.markdown('<div class="section-header">SUMMARY</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value" style="color:#fff;">{len(history)}</div>
            <div style="font-size:0.75rem; letter-spacing:2px; text-transform:uppercase; color:#444; margin-top:0.4rem;">
                TOTAL ANALYSES
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        color = "#22c55e" if avg_score >= 80 else "#f59e0b" if avg_score >= 60 else "#ff3b3b"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value" style="color:{color};">{avg_score}</div>
            <div style="font-size:0.75rem; letter-spacing:2px; text-transform:uppercase; color:#444; margin-top:0.4rem;">
                AVERAGE SCORE
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value" style="color:#22c55e;">{best_score}</div>
            <div style="font-size:0.75rem; letter-spacing:2px; text-transform:uppercase; color:#444; margin-top:0.4rem;">
                BEST SCORE
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        trend_color = "#22c55e" if trend >= 0 else "#ff3b3b"
        trend_symbol = "↑" if trend > 0 else "↓" if trend < 0 else "→"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value" style="color:{trend_color};">{trend_symbol} {abs(trend)}</div>
            <div style="font-size:0.75rem; letter-spacing:2px; text-transform:uppercase; color:#444; margin-top:0.4rem;">
                TREND
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Score History Chart
    st.markdown('<div class="section-header">SCORE HISTORY</div>', unsafe_allow_html=True)

    if len(scores) >= 2:
        # Prepare chart data (newest to oldest → reverse for chronological order)
        chart_data = []
        for a in reversed(history):   # Oldest first for line chart
            if a.get("score") is not None:
                date_str = a["created_at"][:10]
                chart_data.append({
                    "Date": date_str,
                    "Score": a["score"],
                    "Event": a.get("event_type", "unknown").replace("_", " ").title()
                })

        df = pd.DataFrame(chart_data)

        # Line chart
        st.line_chart(
            df.set_index("Date")["Score"],
            color="#ff3b3b",
            use_container_width=True
        )

        # Optional: Show data table toggle
        if st.checkbox("Show raw data table", value=False):
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Upload at least 2 analyses to see your progress trend chart.")

    # Analysis History List
    st.markdown('<div class="section-header">ANALYSIS HISTORY</div>', unsafe_allow_html=True)

    # Event filter
    all_events = sorted(list(set(a.get("event_type", "unknown") for a in history)))
    event_options = ["All Events"] + [e.replace("_", " ").title() for e in all_events]
    selected_event = st.selectbox("Filter by event", event_options)

    filtered_history = history
    if selected_event != "All Events":
        filter_event_raw = selected_event.lower().replace(" ", "_")
        filtered_history = [a for a in history if a.get("event_type") == filter_event_raw]

    for a in filtered_history:
        score = a.get("score", 0)
        score_color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ff3b3b"
        event_display = a.get("event_type", "unknown").replace("_", " ").upper()
        created_date = a.get("created_at", "")[:10]

        with st.expander(f"{event_display} — Score: **{score}** — {created_date}"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"""
                <div style="text-align:center; padding:1.2rem 0;">
                    <div style="font-family:'Bebas Neue',sans-serif; font-size:3.2rem; color:{score_color};">{score}</div>
                    <div style="font-size:0.75rem; letter-spacing:2px; color:#555; margin-top:0.3rem;">TECHNIQUE SCORE</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                errors = a.get("errors", []) or []
                st.markdown(f"""
                <div style="padding:1.2rem 0;">
                    <div style="font-size:0.75rem; letter-spacing:2px; color:#444;">ISSUES DETECTED</div>
                    <div style="font-family:'Bebas Neue',sans-serif; font-size:2.8rem; color:#fff; margin-top:0.2rem;">{len(errors)}</div>
                </div>
                """, unsafe_allow_html=True)

            # Errors
            if errors:
                st.markdown("**Issues Found:**")
                for err in errors:
                    severity = err.get("severity", "medium")
                    color = "#ff3b3b" if severity == "high" else "#f59e0b" if severity == "medium" else "#22c55e"
                    st.markdown(f"""
                    <div style="border-left: 4px solid {color}; padding: 0.6rem 1rem; margin: 0.4rem 0; 
                               background:#0f0f0f; border-radius: 0 8px 8px 0; font-size: 0.9rem;">
                        {err.get('description', 'Unknown issue')}
                    </div>
                    """, unsafe_allow_html=True)

            # Recommended Drills
            drills = a.get("drills", []) or []
            if drills:
                st.markdown("**Recommended Drills:**")
                drill_tags = "".join([
                    f'<span style="background:#1a1a1a; border:1px solid #333; color:#ccc; '
                    f'padding:0.35rem 0.9rem; border-radius:20px; margin:0.2rem; display:inline-block; font-size:0.85rem;">{d}</span>'
                    for d in drills
                ])
                st.markdown(drill_tags, unsafe_allow_html=True)

    st.caption("Showing most recent analyses first • Limited to last 100")
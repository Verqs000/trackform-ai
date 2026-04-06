"""
leaderboard_page.py - Global leaderboard for logged in users
Ranks by: best score, average score, most analyses
"""

import requests
import streamlit as st

SUPABASE_URL = "https://iensdzgzmrkujqvvjbnk.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImllbnNkemd6bXJrdWpxdnZqYm5rIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTM1Njk2NCwiZXhwIjoyMDkwOTMyOTY0fQ.ztfA_HCXMZ4fjvylijFzz-Q4amW2FsoH4f1hxSJXVFs"

ADMIN_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json"
}

MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}
EVENT_ICONS = {
    "sprint": "⚡",
    "shot_put": "🏋️",
    "discus": "💿",
    "javelin": "🏹",
    "unknown": "🏃"
}


def _get_all_analyses():
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/analyses?select=user_id,score,event_type,created_at&order=created_at.desc",
            headers=ADMIN_HEADERS
        )
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Leaderboard fetch error: {e}")
    return []


def _get_all_profiles():
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles?select=id,email",
            headers=ADMIN_HEADERS
        )
        if res.status_code == 200:
            return {p["id"]: p["email"] for p in res.json()}
    except Exception as e:
        print(f"Profiles fetch error: {e}")
    return {}


def _mask_email(email: str) -> str:
    """Show first 3 chars then *** for privacy"""
    if not email or "@" not in email:
        return "athlete***"
    local, domain = email.split("@", 1)
    masked_local = local[:3] + "***" if len(local) > 3 else local[0] + "***"
    return f"{masked_local}@{domain}"


def _build_stats(analyses: list, profiles: dict) -> dict:
    """Build per-user stats from raw analyses"""
    stats = {}
    for a in analyses:
        uid = a.get("user_id")
        score = a.get("score", 0) or 0
        event = a.get("event_type", "unknown")
        if not uid:
            continue
        if uid not in stats:
            stats[uid] = {
                "email": profiles.get(uid, "Unknown"),
                "scores": [],
                "events": [],
                "count": 0
            }
        stats[uid]["scores"].append(score)
        stats[uid]["events"].append(event)
        stats[uid]["count"] += 1

    # Calculate derived stats
    result = []
    for uid, s in stats.items():
        scores = s["scores"]
        events = s["events"]
        best_event = max(set(events), key=events.count) if events else "unknown"
        result.append({
            "user_id": uid,
            "email": s["email"],
            "best_score": max(scores) if scores else 0,
            "avg_score": round(sum(scores) / len(scores)) if scores else 0,
            "total_analyses": s["count"],
            "best_event": best_event
        })
    return result


def show_leaderboard_page(current_user):
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
    .lb-row {
        display: flex;
        align-items: center;
        background: #111;
        border: 1px solid #1e1e1e;
        border-radius: 10px;
        padding: 0.9rem 1.2rem;
        margin-bottom: 0.5rem;
        gap: 1rem;
    }
    .lb-row-you {
        border-color: #ff3b3b !important;
        background: #1a0a0a !important;
    }
    .lb-rank {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.4rem;
        color: #333;
        min-width: 2rem;
        text-align: center;
    }
    .lb-email {
        flex: 1;
        font-size: 0.88rem;
        color: #aaa;
    }
    .lb-score {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.5rem;
        min-width: 3rem;
        text-align: right;
    }
    .lb-meta {
        font-size: 0.75rem;
        color: #444;
        min-width: 5rem;
        text-align: right;
    }
    .tab-btn {
        background: #111;
        border: 1px solid #2a2a2a;
        border-radius: 6px;
        color: #666;
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1rem;
        letter-spacing: 2px;
        padding: 0.4rem 1rem;
        cursor: pointer;
    }
    .tab-btn-active {
        background: #ff3b3b !important;
        border-color: #ff3b3b !important;
        color: #fff !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div style="margin-bottom:2rem;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:3rem;letter-spacing:3px;color:#fff;">
            LEADER<span style="color:#ff3b3b;">BOARD</span>
        </div>
        <div style="font-size:0.75rem;letter-spacing:3px;text-transform:uppercase;color:#444;">
            Top athletes ranked by technique
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load data
    with st.spinner("Loading leaderboard..."):
        analyses = _get_all_analyses()
        profiles = _get_all_profiles()
        stats = _build_stats(analyses, profiles)

    if not stats:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#333;">
            <div style="font-size:3rem;">🏆</div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:2px;color:#2a2a2a;">
                NO DATA YET
            </div>
            <div style="font-size:0.85rem;color:#2a2a2a;">Be the first to submit an analysis!</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Ranking mode tabs
    mode = st.radio(
        "Rank by",
        ["🏆 Best Score", "📊 Average Score", "🔥 Most Analyses"],
        horizontal=True,
        label_visibility="collapsed"
    )

    # Filter by event
    all_events = ["All Events"] + list(set([a.get("event_type", "unknown") for a in analyses if a.get("event_type")]))
    event_filter = st.selectbox(
        "Filter by event",
        all_events,
        label_visibility="collapsed"
    )

    # Apply event filter
    if event_filter != "All Events":
        filtered_analyses = [a for a in analyses if a.get("event_type") == event_filter]
        filtered_stats = _build_stats(filtered_analyses, profiles)
    else:
        filtered_stats = stats

    # Sort based on mode
    if mode == "🏆 Best Score":
        sorted_stats = sorted(filtered_stats, key=lambda x: x["best_score"], reverse=True)
        score_key = "best_score"
        score_label = "BEST"
    elif mode == "📊 Average Score":
        sorted_stats = sorted(filtered_stats, key=lambda x: x["avg_score"], reverse=True)
        score_key = "avg_score"
        score_label = "AVG"
    else:
        sorted_stats = sorted(filtered_stats, key=lambda x: x["total_analyses"], reverse=True)
        score_key = "total_analyses"
        score_label = "RUNS"

    # Your rank
    current_uid = current_user.id
    your_rank = next((i + 1 for i, s in enumerate(sorted_stats) if s["user_id"] == current_uid), None)

    if your_rank:
        your_score = next((s[score_key] for s in sorted_stats if s["user_id"] == current_uid), 0)
        score_color = "#22c55e" if your_score >= 80 else "#f59e0b" if your_score >= 60 else "#ff3b3b"
        st.markdown(f"""
        <div style="background:#1a0a0a;border:1px solid #ff3b3b;border-radius:10px;padding:1rem 1.5rem;margin-bottom:1.5rem;display:flex;align-items:center;justify-content:space-between;">
            <div>
                <div style="font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;color:#ff3b3b;">YOUR RANKING</div>
                <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;color:#fff;">#{your_rank} of {len(sorted_stats)}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;color:#444;">{score_label}</div>
                <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;color:{score_color};">{your_score}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Top 3 podium
    if len(sorted_stats) >= 3:
        st.markdown('<div class="section-header">TOP 3</div>', unsafe_allow_html=True)
        p1, p2, p3 = st.columns(3)
        podium = [(p2, sorted_stats[1], 2), (p1, sorted_stats[0], 1), (p3, sorted_stats[2], 3)]

        for col, athlete, rank in podium:
            score = athlete[score_key]
            score_color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ff3b3b"
            medal = MEDAL.get(rank, "")
            event_icon = EVENT_ICONS.get(athlete["best_event"], "🏃")
            is_you = athlete["user_id"] == current_uid
            border = "#ff3b3b" if is_you else "#1e1e1e"
            height = "130px" if rank == 1 else "100px"

            with col:
                st.markdown(f"""
                <div style="background:#111;border:1px solid {border};border-radius:12px;padding:1.2rem;text-align:center;margin-bottom:0.5rem;">
                    <div style="font-size:1.8rem;">{medal}</div>
                    <div style="font-size:0.85rem;color:#aaa;margin:0.3rem 0;">
                        {_mask_email(athlete['email'])}{"  👈 you" if is_you else ""}
                    </div>
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:2.5rem;color:{score_color};">{score}</div>
                    <div style="font-size:0.7rem;letter-spacing:2px;color:#444;">{score_label}</div>
                    <div style="font-size:0.8rem;color:#333;margin-top:0.3rem;">{event_icon} {athlete['best_event'].replace('_',' ').title()}</div>
                </div>
                """, unsafe_allow_html=True)

    # Full rankings list
    st.markdown('<div class="section-header">FULL RANKINGS</div>', unsafe_allow_html=True)

    for i, athlete in enumerate(sorted_stats[:50], 1):
        score = athlete[score_key]
        score_color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ff3b3b"
        medal = MEDAL.get(i, f"#{i}")
        event_icon = EVENT_ICONS.get(athlete["best_event"], "🏃")
        is_you = athlete["user_id"] == current_uid
        you_badge = ' <span style="color:#ff3b3b;font-size:0.75rem;">YOU</span>' if is_you else ""
        row_class = "lb-row-you" if is_you else ""

        st.markdown(f"""
        <div class="lb-row {row_class}">
            <div class="lb-rank">{medal}</div>
            <div style="font-size:1.2rem;">{event_icon}</div>
            <div class="lb-email">{_mask_email(athlete['email'])}{you_badge}</div>
            <div class="lb-meta">{athlete['total_analyses']} run{"s" if athlete['total_analyses'] != 1 else ""}</div>
            <div class="lb-score" style="color:{score_color};">{score}</div>
        </div>
        """, unsafe_allow_html=True)
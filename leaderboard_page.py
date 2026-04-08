"""
leaderboard_page.py - Global leaderboard for logged in users
Ranks by: best score, average score, most analyses
"""

import streamlit as st
import requests
from typing import List, Dict, Any

# ── CONFIG (Move these to environment variables or secrets in production!) ──
SUPABASE_URL = "https://iensdzgzmrkujqvvjbnk.supabase.co"

# ⚠️ WARNING: Do NOT hardcode service key in frontend code for production!
# Use st.secrets or a backend proxy instead.
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_SERVICE_KEY = st.secrets["supabase"]["service_key"]

ADMIN_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json"
}

MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}
EVENT_ICONS = {
    "sprint": "⚡", "shot_put": "🏋️", "discus": "💿",
    "javelin": "🏹", "unknown": "🏃"
}


def _get_all_analyses() -> List[Dict]:
    """Fetch all analyses (consider limiting rows in production)"""
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/analyses?select=user_id,score,event_type,created_at&order=created_at.desc&limit=1000",
            headers=ADMIN_HEADERS,
            timeout=10
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error("Failed to load leaderboard data. Please try again later.")
        print(f"Leaderboard fetch error: {e}")
        return []


def _get_all_profiles() -> Dict:
    """Fetch user profiles for email mapping"""
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles?select=id,email",
            headers=ADMIN_HEADERS,
            timeout=10
        )
        res.raise_for_status()
        return {p["id"]: p["email"] for p in res.json()}
    except Exception as e:
        print(f"Profiles fetch error: {e}")
        return {}


def _mask_email(email: str) -> str:
    """Mask email for privacy (e.g., joh***@gmail.com)"""
    if not email or "@" not in email:
        return "athlete***@***"
    local, domain = email.split("@", 1)
    masked = local[:3] + "***" if len(local) > 3 else local + "***"
    return f"{masked}@{domain}"


def _build_leaderboard_stats(analyses: List[Dict], profiles: Dict) -> List[Dict]:
    """Build aggregated stats per user"""
    from collections import defaultdict
    user_stats = defaultdict(lambda: {
        "scores": [], 
        "events": [], 
        "count": 0
    })

    for a in analyses:
        uid = a.get("user_id")
        if not uid:
            continue
        score = a.get("score") or 0
        event = a.get("event_type", "unknown")

        user_stats[uid]["scores"].append(score)
        user_stats[uid]["events"].append(event)
        user_stats[uid]["count"] += 1
        user_stats[uid]["email"] = profiles.get(uid, "Unknown Athlete")

    # Convert to final leaderboard format
    leaderboard = []
    for uid, data in user_stats.items():
        scores = data["scores"]
        events = data["events"]
        best_event = max(set(events), key=events.count) if events else "unknown"

        leaderboard.append({
            "user_id": uid,
            "email": data["email"],
            "best_score": max(scores) if scores else 0,
            "avg_score": round(sum(scores) / len(scores)) if scores else 0,
            "total_analyses": data["count"],
            "best_event": best_event
        })

    return leaderboard


def show_leaderboard_page(current_user):
    st.markdown("""
    <style>
    .section-header {
        font-family: 'Bebas Neue', sans-serif; font-size: 1.8rem; letter-spacing: 2px;
        color: #fff; border-bottom: 1px solid #1e1e1e; padding-bottom: 0.5rem;
        margin-bottom: 1.2rem; margin-top: 1.5rem;
    }
    .lb-row {
        display: flex; align-items: center; background: #111; border: 1px solid #1e1e1e;
        border-radius: 10px; padding: 0.9rem 1.2rem; margin-bottom: 0.5rem; gap: 1rem;
    }
    .lb-row-you { border-color: #ff3b3b !important; background: #1a0a0a !important; }
    .lb-rank { font-family: 'Bebas Neue', sans-serif; font-size: 1.4rem; color: #333; min-width: 2.5rem; text-align: center; }
    .lb-email { flex: 1; font-size: 0.9rem; color: #aaa; }
    .lb-score { font-family: 'Bebas Neue', sans-serif; font-size: 1.6rem; min-width: 3.5rem; text-align: right; }
    .lb-meta { font-size: 0.78rem; color: #555; min-width: 5rem; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

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
    with st.spinner("🏆 Loading global leaderboard..."):
        analyses = _get_all_analyses()
        profiles = _get_all_profiles()
        stats = _build_leaderboard_stats(analyses, profiles)

    if not stats:
        st.info("No analyses submitted yet. Be the first to upload a video!")
        return

    # Ranking options
    mode = st.radio(
        "Rank by",
        ["🏆 Best Score", "📊 Average Score", "🔥 Most Analyses"],
        horizontal=True,
        label_visibility="collapsed"
    )

    # Event filter
    all_events = ["All Events"] + sorted(list({a.get("event_type", "unknown") for a in analyses if a.get("event_type")}))
    event_filter = st.selectbox("Filter by event", all_events, label_visibility="collapsed")

    # Apply filter
    if event_filter != "All Events":
        filtered_analyses = [a for a in analyses if a.get("event_type") == event_filter]
        filtered_stats = _build_leaderboard_stats(filtered_analyses, profiles)
    else:
        filtered_stats = stats

    # Sort data
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

    current_uid = current_user.id
    your_entry = next((s for s in sorted_stats if s["user_id"] == current_uid), None)

    if your_entry:
        your_rank = sorted_stats.index(your_entry) + 1
        your_score = your_entry[score_key]
        color = "#22c55e" if your_score >= 80 else "#f59e0b" if your_score >= 60 else "#ff3b3b"

        st.markdown(f"""
        <div style="background:#1a0a0a;border:1px solid #ff3b3b;border-radius:12px;padding:1.2rem 1.6rem;margin:1.5rem 0;display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="color:#ff3b3b;font-size:0.75rem;letter-spacing:2px;">YOUR RANK</div>
                <div style="font-family:'Bebas Neue',sans-serif;font-size:2.2rem;color:#fff;">#{your_rank}</div>
            </div>
            <div style="text-align:right;">
                <div style="color:#666;font-size:0.75rem;">{score_label} SCORE</div>
                <div style="font-family:'Bebas Neue',sans-serif;font-size:2.4rem;color:{color};">{your_score}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Top 3 Podium
    if len(sorted_stats) >= 3:
        st.markdown('<div class="section-header">🏆 TOP 3</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for col, rank in zip(cols, [1, 0, 2]):   # Center = 1st place visually
            athlete = sorted_stats[rank]
            medal = MEDAL.get(rank + 1, "🏅")
            score = athlete[score_key]
            color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ff3b3b"
            is_you = athlete["user_id"] == current_uid

            with col:
                st.markdown(f"""
                <div style="background:#111;border:2px solid {'#ff3b3b' if is_you else '#1e1e1e'};border-radius:12px;padding:1.4rem 0.8rem;text-align:center;height:100%;">
                    <div style="font-size:2rem;margin-bottom:0.5rem;">{medal}</div>
                    <div style="font-size:0.85rem;color:#aaa;">{_mask_email(athlete['email'])}</div>
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:2.8rem;color:{color};margin:0.4rem 0;">{score}</div>
                    <div style="font-size:0.75rem;color:#555;">{score_label}</div>
                </div>
                """, unsafe_allow_html=True)

    # Full Leaderboard
    st.markdown('<div class="section-header">FULL RANKINGS</div>', unsafe_allow_html=True)

    for i, athlete in enumerate(sorted_stats[:50], 1):
        score = athlete[score_key]
        color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ff3b3b"
        is_you = athlete["user_id"] == current_uid

        st.markdown(f"""
        <div class="lb-row {'lb-row-you' if is_you else ''}">
            <div class="lb-rank">{"🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"#{i}"}</div>
            <div style="font-size:1.3rem;">{EVENT_ICONS.get(athlete['best_event'], '🏃')}</div>
            <div class="lb-email">{_mask_email(athlete['email'])}{" 👈 YOU" if is_you else ""}</div>
            <div class="lb-meta">{athlete['total_analyses']} run{"s" if athlete['total_analyses'] != 1 else ""}</div>
            <div class="lb-score" style="color:{color};">{score}</div>
        </div>
        """, unsafe_allow_html=True)

    if len(sorted_stats) > 50:
        st.caption(f"... and {len(sorted_stats)-50} more athletes")
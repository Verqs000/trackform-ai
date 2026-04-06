"""
coach_page.py - Coach dashboard with team management
"""

import streamlit as st
from auth import (
    get_my_teams, create_team, get_team_members,
    add_athlete_to_team, get_team_analyses, get_tier
)


def show_coach_page(user):
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
    .team-card {
        background: #111;
        border: 1px solid #1e1e1e;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }
    .athlete-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.6rem 0;
        border-bottom: 1px solid #1a1a1a;
        font-size: 0.88rem;
        color: #aaa;
    }
    .score-pill {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1rem;
        padding: 0.2rem 0.7rem;
        border-radius: 99px;
    }
    .stat-mini {
        background: #111;
        border: 1px solid #1e1e1e;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .stat-mini-val {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.2rem;
        color: #fff;
    }
    .stat-mini-label {
        font-size: 0.7rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #444;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div style="margin-bottom:2rem;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:3rem;letter-spacing:3px;color:#fff;">
            COACH <span style="color:#ff3b3b;">DASHBOARD</span>
        </div>
        <div style="font-size:0.75rem;letter-spacing:3px;text-transform:uppercase;color:#444;">
            Manage your athletes and track their progress
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Gate for non-coach users
    if tier not in ["coach"]:
        st.markdown("""
        <div style="background:#111;border:1px solid #ff3b3b;border-radius:12px;padding:2rem;text-align:center;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;letter-spacing:2px;color:#ff3b3b;margin-bottom:0.5rem;">
                COACH TIER REQUIRED
            </div>
            <div style="color:#666;font-size:0.9rem;margin-bottom:1rem;">
                Upgrade to Coach ($29.99/mo) to manage teams and track athlete progress.
            </div>
            <div style="color:#444;font-size:0.8rem;">
                Contact us to upgrade: trackformai@gmail.com
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Get teams
    teams = get_my_teams(user_id)

    # Create new team
    st.markdown('<div class="section-header">MY TEAMS</div>', unsafe_allow_html=True)

    with st.expander("➕ Create New Team"):
        team_name = st.text_input("Team Name", placeholder="e.g. Westview Track & Field")
        if st.button("CREATE TEAM"):
            if team_name:
                result = create_team(user_id, team_name)
                if result["success"]:
                    st.success(f"Team '{team_name}' created!")
                    st.rerun()
                else:
                    st.error(result["error"])
            else:
                st.error("Please enter a team name.")

    if not teams:
        st.markdown("""
        <div style="text-align:center;padding:2rem;color:#333;">
            <div style="font-size:2rem;">🏃</div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;letter-spacing:2px;color:#2a2a2a;">
                NO TEAMS YET
            </div>
            <div style="font-size:0.8rem;color:#2a2a2a;">Create your first team above</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Show each team
    for team in teams:
        st.markdown(f"""
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.3rem;letter-spacing:2px;color:#fff;margin-top:1.5rem;">
            {team['name'].upper()}
        </div>
        """, unsafe_allow_html=True)

        members = get_team_members(team["id"])
        analyses = get_team_analyses(team["id"])

        # Team stats
        if analyses:
            scores = [a["score"] for a in analyses if a.get("score")]
            avg_score = int(sum(scores) / len(scores)) if scores else 0
            events = [a["event_type"] for a in analyses]
            most_common = max(set(events), key=events.count) if events else "N/A"

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="stat-mini">
                    <div class="stat-mini-val">{len(members)}</div>
                    <div class="stat-mini-label">Athletes</div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                color = "#22c55e" if avg_score >= 80 else "#f59e0b" if avg_score >= 60 else "#ff3b3b"
                st.markdown(f"""
                <div class="stat-mini">
                    <div class="stat-mini-val" style="color:{color};">{avg_score}</div>
                    <div class="stat-mini-label">Avg Score</div>
                </div>
                """, unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div class="stat-mini">
                    <div class="stat-mini-val">{len(analyses)}</div>
                    <div class="stat-mini-label">Total Analyses</div>
                </div>
                """, unsafe_allow_html=True)

        # Add athlete
        with st.expander(f"➕ Add Athlete to {team['name']}"):
            athlete_email = st.text_input("Athlete Email", key=f"add_{team['id']}", placeholder="athlete@email.com")
            if st.button("ADD ATHLETE", key=f"btn_add_{team['id']}"):
                if athlete_email:
                    result = add_athlete_to_team(team["id"], athlete_email)
                    if result["success"]:
                        st.success("Athlete added!")
                        st.rerun()
                    else:
                        st.error(result["error"])

        # Members list
        if members:
            st.markdown('<div class="section-header" style="font-size:1rem;margin-top:1rem;">ATHLETES</div>', unsafe_allow_html=True)
            for m in members:
                email = m.get("profiles", {}).get("email", "Unknown") if m.get("profiles") else "Unknown"
                # Get their latest score
                their_analyses = [a for a in analyses if a.get("user_id") == m["athlete_id"]]
                latest_score = their_analyses[0]["score"] if their_analyses else None
                score_color = "#22c55e" if latest_score and latest_score >= 80 else "#f59e0b" if latest_score and latest_score >= 60 else "#ff3b3b"
                score_display = f"{latest_score}/100" if latest_score else "No analyses yet"

                st.markdown(f"""
                <div class="athlete-row">
                    <span>📧 {email}</span>
                    <span style="color:{score_color};font-family:'Bebas Neue',sans-serif;font-size:1rem;">
                        {score_display}
                    </span>
                </div>
                """, unsafe_allow_html=True)

        # Recent analyses
        if analyses:
            st.markdown('<div class="section-header" style="font-size:1rem;margin-top:1rem;">RECENT ANALYSES</div>', unsafe_allow_html=True)
            for a in analyses[:10]:
                score = a.get("score", 0)
                score_color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ff3b3b"
                event = a.get("event_type", "unknown").replace("_", " ").upper()
                created = a.get("created_at", "")[:10]
                errors = a.get("errors", [])
                error_count = len(errors) if errors else 0
                athlete_email = a.get("profiles", {}).get("email", "Unknown") if a.get("profiles") else "Unknown"

                st.markdown(f"""
                <div style="background:#111;border:1px solid #1e1e1e;border-radius:10px;padding:1rem;margin-bottom:0.6rem;display:flex;align-items:center;justify-content:space-between;">
                    <div>
                        <div style="font-size:0.75rem;color:#444;">{created} · {athlete_email}</div>
                        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.1rem;color:#fff;letter-spacing:1px;">{event}</div>
                        <div style="font-size:0.8rem;color:#555;">{error_count} issue{"s" if error_count != 1 else ""} found</div>
                    </div>
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;color:{score_color};">{score}</div>
                </div>
                """, unsafe_allow_html=True)
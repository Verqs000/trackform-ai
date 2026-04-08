"""
coach_page.py - Coach dashboard with team management + invite system
"""

import streamlit as st
from auth import (
    get_my_teams, create_team, delete_team, get_team_members,
    invite_athlete_to_team, remove_athlete_from_team,
    get_team_analyses, get_tier, get_pending_invites, respond_to_invite
)


def show_coach_page(user):
    user_id = user.id
    tier = get_tier(user_id)

    # Custom CSS (unchanged, just moved up)
    st.markdown("""
    <style>
    .section-header {
        font-family: 'Bebas Neue', sans-serif; font-size: 1.8rem; letter-spacing: 2px;
        color: #fff; border-bottom: 1px solid #1e1e1e; padding-bottom: 0.5rem;
        margin-bottom: 1.2rem; margin-top: 1.5rem;
    }
    .team-card { background: #111; border: 1px solid #1e1e1e; border-radius: 12px; padding: 1.2rem 1.5rem; margin-bottom: 1rem; }
    .athlete-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.6rem 0; border-bottom: 1px solid #1a1a1a; font-size: 0.88rem; color: #aaa;
    }
    .stat-mini { background: #111; border: 1px solid #1e1e1e; border-radius: 10px; padding: 1rem; text-align: center; }
    .stat-mini-val { font-family: 'Bebas Neue', sans-serif; font-size: 2.2rem; color: #fff; }
    .stat-mini-label { font-size: 0.7rem; letter-spacing: 2px; text-transform: uppercase; color: #444; }
    .invite-card {
        background: #111; border: 1px solid #2a2a2a; border-radius: 10px;
        padding: 1rem 1.2rem; margin-bottom: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

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

    # ── PENDING INVITES ───────────────────────────────────────────────────────
    pending_invites = get_pending_invites(user_id)
    if pending_invites:
        st.markdown('<div class="section-header">📬 TEAM INVITES</div>', unsafe_allow_html=True)
        for inv in pending_invites:
            col_info, col_accept, col_decline = st.columns([3, 1, 1])
            with col_info:
                st.markdown(f"""
                <div class="invite-card">
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:1.1rem;color:#fff;letter-spacing:1px;">
                        {inv['team_name'].upper()}
                    </div>
                    <div style="font-size:0.8rem;color:#555;margin-top:0.2rem;">
                        Coach: {inv['coach_email']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col_accept:
                if st.button("✅ Accept", key=f"accept_{inv['id']}"):
                    result = respond_to_invite(inv["id"], user_id, accept=True)
                    if result["success"]:
                        st.success("✅ Joined the team!")
                        st.rerun()
                    else:
                        st.error(result.get("error", "Unknown error"))
            with col_decline:
                if st.button("❌ Decline", key=f"decline_{inv['id']}"):
                    result = respond_to_invite(inv["id"], user_id, accept=False)
                    if result["success"]:
                        st.rerun()
                    else:
                        st.error(result.get("error", "Unknown error"))

    # ── COACH TIER GATE ───────────────────────────────────────────────────────
    if tier != "coach":
        st.markdown("""
        <div style="background:#111;border:1px solid #ff3b3b;border-radius:12px;padding:2rem;text-align:center;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;letter-spacing:2px;color:#ff3b3b;margin-bottom:0.5rem;">
                COACH TIER REQUIRED
            </div>
            <div style="color:#666;font-size:0.9rem;margin-bottom:1rem;">
                Upgrade to Coach ($29.99/mo) to manage teams and track athlete progress.
            </div>
            <div style="color:#444;font-size:0.8rem;">Contact: trackformai@gmail.com</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── MY TEAMS SECTION ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">MY TEAMS</div>', unsafe_allow_html=True)

    with st.expander("➕ Create New Team", expanded=False):
        team_name = st.text_input("Team Name", placeholder="e.g. Westview Track & Field", key="new_team_name")
        if st.button("CREATE TEAM", type="primary", key="btn_create_team"):
            if team_name.strip():
                result = create_team(user_id, team_name.strip())
                if result["success"]:
                    st.success(f"Team '{team_name}' created successfully!")
                    st.rerun()
                else:
                    st.error(result.get("error", "Failed to create team."))
            else:
                st.error("Please enter a team name.")

    teams = get_my_teams(user_id)

    if not teams:
        st.markdown("""
        <div style="text-align:center;padding:3rem 1rem;color:#333;">
            <div style="font-size:3rem; margin-bottom:1rem;">🏃‍♂️</div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.6rem;letter-spacing:2px;color:#2a2a2a;">
                NO TEAMS YET
            </div>
            <div style="font-size:0.9rem;color:#555;">Create your first team above to get started</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Delete confirmation state (single key for simplicity)
    if "confirm_delete_team_id" not in st.session_state:
        st.session_state.confirm_delete_team_id = None

    for team in teams:
        team_id = team["id"]
        members = get_team_members(team_id)
        analyses = get_team_analyses(team_id)

        # Team Header
        col_name, col_del = st.columns([5, 1])
        with col_name:
            st.markdown(f"""
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.45rem;letter-spacing:2px;color:#fff;margin:1.2rem 0 0.8rem;">
                {team['name'].upper()}
            </div>
            """, unsafe_allow_html=True)
        with col_del:
            if st.button("🗑 Delete Team", key=f"del_btn_{team_id}"):
                st.session_state.confirm_delete_team_id = team_id

        # Confirm Delete
        if st.session_state.confirm_delete_team_id == team_id:
            st.warning(f"⚠️ Delete **{team['name']}** and all its data? This action cannot be undone.")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Yes, Delete", type="secondary", key=f"yes_del_{team_id}"):
                    result = delete_team(team_id, user_id)
                    if result["success"]:
                        st.success("Team deleted.")
                        st.session_state.confirm_delete_team_id = None
                        st.rerun()
                    else:
                        st.error(result.get("error", "Failed to delete team."))
                        st.session_state.confirm_delete_team_id = None
            with col_no:
                if st.button("Cancel", key=f"no_del_{team_id}"):
                    st.session_state.confirm_delete_team_id = None
                    st.rerun()
            st.markdown("---")
            continue  # Skip rest of this team card while confirming

        # Render Team Content
        render_team_content(team, members, analyses, user_id)


def render_team_content(team, members, analyses, user_id):
    """Helper to render the main content of a team card."""
    team_id = team["id"]

    # Stats Row
    if analyses:
        scores = [a["score"] for a in analyses if a.get("score") is not None]
        avg_score = int(sum(scores) / len(scores)) if scores else 0
        events = [a.get("event_type") for a in analyses if a.get("event_type")]
        most_common = max(set(events), key=events.count) if events else "N/A"

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="stat-mini">
                <div class="stat-mini-val">{len(members)}</div>
                <div class="stat-mini-label">ATHLETES</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            color = "#22c55e" if avg_score >= 80 else "#f59e0b" if avg_score >= 60 else "#ff3b3b"
            st.markdown(f"""
            <div class="stat-mini">
                <div class="stat-mini-val" style="color:{color};">{avg_score}</div>
                <div class="stat-mini-label">AVG SCORE</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="stat-mini">
                <div class="stat-mini-val">{len(analyses)}</div>
                <div class="stat-mini-label">ANALYSES</div>
            </div>
            """, unsafe_allow_html=True)

    # Invite Section
    with st.expander(f"➕ Invite Athlete to {team['name']}", expanded=False):
        athlete_email = st.text_input("Athlete Email", placeholder="athlete@email.com", key=f"invite_email_{team_id}")
        if st.button("SEND INVITE", key=f"btn_invite_{team_id}", type="primary"):
            if athlete_email.strip():
                result = invite_athlete_to_team(team_id, user_id, athlete_email.strip())
                if result["success"]:
                    st.success(f"Invite sent to {athlete_email}!")
                    st.rerun()
                else:
                    st.error(result.get("error", "Failed to send invite."))
            else:
                st.error("Please enter an email address.")

    # Athletes List
    if members:
        st.markdown('<div style="font-family:\'Bebas Neue\',sans-serif;font-size:1rem;letter-spacing:2px;color:#555;margin:1.2rem 0 0.4rem;">ATHLETES</div>', unsafe_allow_html=True)
        for m in members:
            email = m.get("profile", {}).get("email", "Unknown")
            their_analyses = [a for a in analyses if a.get("user_id") == m["athlete_id"]]
            latest_score = their_analyses[0].get("score") if their_analyses else None

            score_color = "#22c55e" if latest_score and latest_score >= 80 else "#f59e0b" if latest_score and latest_score >= 60 else "#ff3b3b"
            score_display = f"{latest_score}/100" if latest_score is not None else "No analyses"

            col_e, col_s, col_r = st.columns([3, 1.2, 1])
            with col_e:
                st.markdown(f'<div style="padding:0.6rem 0;font-size:0.9rem;color:#ccc;">📧 {email}</div>', unsafe_allow_html=True)
            with col_s:
                st.markdown(f'<div style="padding:0.6rem 0;font-family:\'Bebas Neue\',sans-serif;font-size:1.05rem;color:{score_color};">{score_display}</div>', unsafe_allow_html=True)
            with col_r:
                if st.button("Remove", key=f"rm_{team_id}_{m['athlete_id']}", help="Remove athlete from team"):
                    result = remove_athlete_from_team(team_id, m["athlete_id"])
                    if result["success"]:
                        st.rerun()
                    else:
                        st.error(result.get("error", "Failed to remove athlete."))

    # Recent Analyses
    if analyses:
        st.markdown('<div style="font-family:\'Bebas Neue\',sans-serif;font-size:1rem;letter-spacing:2px;color:#555;margin:1.2rem 0 0.4rem;">RECENT ANALYSES</div>', unsafe_allow_html=True)
        for a in analyses[:10]:
            score = a.get("score", 0)
            score_color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ff3b3b"
            event = a.get("event_type", "unknown").replace("_", " ").upper()
            created = a.get("created_at", "")[:10]
            error_count = len(a.get("errors") or [])
            athlete_email = a.get("athlete_email", "Unknown")

            st.markdown(f"""
            <div style="background:#111;border:1px solid #1e1e1e;border-radius:10px;padding:1.1rem;margin-bottom:0.7rem;display:flex;align-items:center;justify-content:space-between;">
                <div>
                    <div style="font-size:0.78rem;color:#555;">{created} · {athlete_email}</div>
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:1.15rem;color:#fff;letter-spacing:1px;">{event}</div>
                    <div style="font-size:0.82rem;color:#666;">{error_count} issue{"s" if error_count != 1 else ""}</div>
                </div>
                <div style="font-family:'Bebas Neue',sans-serif;font-size:2.4rem;color:{score_color};">{score}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#1a1a1a;margin:2.5rem 0 1rem;'>", unsafe_allow_html=True)
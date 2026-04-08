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

    # ── PENDING INVITES (shown to all users, not just coaches) ────────────────
    pending_invites = get_pending_invites(user_id)
    if pending_invites:
        st.markdown('<div class="section-header">📬 TEAM INVITES</div>', unsafe_allow_html=True)
        for inv in pending_invites:
            col_info, col_accept, col_decline = st.columns([3, 1, 1])
            with col_info:
                st.markdown(f"""
                <div class="invite-card">
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:1.1rem;color:#fff;letter-spacing:1px;">{inv['team_name'].upper()}</div>
                    <div style="font-size:0.8rem;color:#555;margin-top:0.2rem;">Coach: {inv['coach_email']}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_accept:
                if st.button("✅ Accept", key=f"accept_{inv['id']}"):
                    result = respond_to_invite(inv["id"], user_id, accept=True)
                    if result["success"]:
                        st.success("Joined!")
                        st.rerun()
                    else:
                        st.error(result["error"])
            with col_decline:
                if st.button("❌ Decline", key=f"decline_{inv['id']}"):
                    result = respond_to_invite(inv["id"], user_id, accept=False)
                    if result["success"]:
                        st.rerun()
                    else:
                        st.error(result["error"])

    # ── COACH GATE ────────────────────────────────────────────────────────────
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

    # ── MY TEAMS ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">MY TEAMS</div>', unsafe_allow_html=True)

    with st.expander("➕ Create New Team"):
        team_name = st.text_input("Team Name", placeholder="e.g. Westview Track & Field", key="new_team_name")
        if st.button("CREATE TEAM", key="btn_create_team"):
            if team_name:
                result = create_team(user_id, team_name)
                if result["success"]:
                    st.success(f"Team '{team_name}' created!")
                    st.rerun()
                else:
                    st.error(result["error"])
            else:
                st.error("Please enter a team name.")

    teams = get_my_teams(user_id)

    if not teams:
        st.markdown("""
        <div style="text-align:center;padding:2rem;color:#333;">
            <div style="font-size:2rem;">🏃</div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;letter-spacing:2px;color:#2a2a2a;">NO TEAMS YET</div>
            <div style="font-size:0.8rem;color:#2a2a2a;">Create your first team above</div>
        </div>
        """, unsafe_allow_html=True)
        return

    for team in teams:
        members  = get_team_members(team["id"])
        analyses = get_team_analyses(team["id"])

        # Team header row with delete button
        col_name, col_del = st.columns([5, 1])
        with col_name:
            st.markdown(f"""
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.4rem;letter-spacing:2px;color:#fff;margin-top:1.5rem;">
                {team['name'].upper()}
            </div>
            """, unsafe_allow_html=True)
        with col_del:
            st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
            if st.button("🗑 Delete", key=f"del_team_{team['id']}"):
                st.session_state[f"confirm_delete_{team['id']}"] = True

        # Confirm delete
        if st.session_state.get(f"confirm_delete_{team['id']}"):
            st.warning(f"Are you sure you want to delete **{team['name']}**? This cannot be undone.")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Yes, delete", key=f"yes_del_{team['id']}"):
                    result = delete_team(team["id"], user_id)
                    if result["success"]:
                        st.session_state.pop(f"confirm_delete_{team['id']}", None)
                        st.rerun()
                    else:
                        st.error(result["error"])
            with col_no:
                if st.button("Cancel", key=f"no_del_{team['id']}"):
                    st.session_state.pop(f"confirm_delete_{team['id']}", None)
                    st.rerun()
            continue

        # Team stats
        if analyses:
            scores     = [a["score"] for a in analyses if a.get("score")]
            avg_score  = int(sum(scores) / len(scores)) if scores else 0
            events     = [a["event_type"] for a in analyses]
            most_common = max(set(events), key=events.count) if events else "N/A"
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="stat-mini"><div class="stat-mini-val">{len(members)}</div><div class="stat-mini-label">Athletes</div></div>', unsafe_allow_html=True)
            with c2:
                color = "#22c55e" if avg_score >= 80 else "#f59e0b" if avg_score >= 60 else "#ff3b3b"
                st.markdown(f'<div class="stat-mini"><div class="stat-mini-val" style="color:{color};">{avg_score}</div><div class="stat-mini-label">Avg Score</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="stat-mini"><div class="stat-mini-val">{len(analyses)}</div><div class="stat-mini-label">Total Analyses</div></div>', unsafe_allow_html=True)

        # Invite athlete
        with st.expander(f"➕ Invite Athlete to {team['name']}"):
            athlete_email = st.text_input("Athlete Email", key=f"invite_{team['id']}", placeholder="athlete@email.com")
            if st.button("SEND INVITE", key=f"btn_invite_{team['id']}"):
                if athlete_email:
                    result = invite_athlete_to_team(team["id"], user_id, athlete_email)
                    if result["success"]:
                        st.success(f"Invite sent to {athlete_email}! They'll see it when they log in.")
                        st.rerun()
                    else:
                        st.error(result["error"])
                else:
                    st.error("Please enter an email.")

        # Athletes list
        if members:
            st.markdown('<div style="font-family:\'Bebas Neue\',sans-serif;font-size:1rem;letter-spacing:2px;color:#555;margin-top:1rem;margin-bottom:0.5rem;">ATHLETES</div>', unsafe_allow_html=True)
            for m in members:
                email = m.get("profile", {}).get("email", "Unknown")
                their_analyses = [a for a in analyses if a.get("user_id") == m["athlete_id"]]
                latest_score   = their_analyses[0]["score"] if their_analyses else None
                score_color    = "#22c55e" if latest_score and latest_score >= 80 else "#f59e0b" if latest_score and latest_score >= 60 else "#ff3b3b"
                score_display  = f"{latest_score}/100" if latest_score else "No analyses yet"

                col_email, col_score, col_remove = st.columns([3, 1, 1])
                with col_email:
                    st.markdown(f'<div style="padding:0.5rem 0;font-size:0.88rem;color:#aaa;">📧 {email}</div>', unsafe_allow_html=True)
                with col_score:
                    st.markdown(f'<div style="padding:0.5rem 0;font-family:\'Bebas Neue\',sans-serif;font-size:1rem;color:{score_color};">{score_display}</div>', unsafe_allow_html=True)
                with col_remove:
                    if st.button("Remove", key=f"rm_{team['id']}_{m['athlete_id']}"):
                        result = remove_athlete_from_team(team["id"], m["athlete_id"])
                        if result["success"]:
                            st.rerun()
                        else:
                            st.error(result["error"])

        # Recent analyses
        if analyses:
            st.markdown('<div style="font-family:\'Bebas Neue\',sans-serif;font-size:1rem;letter-spacing:2px;color:#555;margin-top:1rem;margin-bottom:0.5rem;">RECENT ANALYSES</div>', unsafe_allow_html=True)
            for a in analyses[:10]:
                score        = a.get("score", 0)
                score_color  = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ff3b3b"
                event        = a.get("event_type", "unknown").replace("_", " ").upper()
                created      = a.get("created_at", "")[:10]
                error_count  = len(a.get("errors", []) or [])
                athlete_email = a.get("athlete_email", "Unknown")

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

        st.markdown("<hr style='border-color:#1a1a1a;margin:2rem 0;'>", unsafe_allow_html=True)
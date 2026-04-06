"""
Auth system using Supabase REST API
Uses requests only - no supabase package needed
Matches existing tables: profiles, usage, analyses, teams, team_members
"""

import requests
import streamlit as st
from datetime import datetime, timedelta

SUPABASE_URL = "https://iensdzgzmrkujqvvjbnk.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImllbnNkemd6bXJrdWpxdnZqYm5rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUzNTY5NjQsImV4cCI6MjA5MDkzMjk2NH0.pYZNta8Qn0_OuiFlmW4pTEONdRm0Wk9_cwxKb1glKxA"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImllbnNkemd6bXJrdWpxdnZqYm5rIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTM1Njk2NCwiZXhwIjoyMDkwOTMyOTY0fQ.ztfA_HCXMZ4fjvylijFzz-Q4amW2FsoH4f1hxSJXVFs"

FREE_TIER_LIMIT = 5

ANON_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json"
}

ADMIN_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


class SimpleUser:
    def __init__(self, id, email):
        self.id = id
        self.email = email


# ── AUTH ─────────────────────────────────────────────────────────────────────

def  sign_up(email: str, password: str) -> dict:
    url = f"{SUPABASE_URL}/auth/v1/signup"
    try:
        res = requests.post(url, headers=ANON_HEADERS, json={"email": email, "password": password})
        data = res.json()
        
        # Success if we got an id back (user object returned directly)
        user_id = data.get("id") or (data.get("user") or {}).get("id")
        
        if res.status_code in [200, 201] and user_id:
            _ensure_profile(user_id, email)
            return {"success": True}
        else:
            msg = data.get("msg") or data.get("message") or data.get("error_description") or "Signup failed"
            return {"success": False, "error": msg}
    except Exception as e:
        return {"success": False, "error": str(e)}

def sign_in(email: str, password: str) -> dict:
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    try:
        res = requests.post(url, headers=ANON_HEADERS, json={"email": email, "password": password})
        data = res.json()
        print(f"Sign in response: {res.status_code} - {data}")
        
        # User can be at top level or nested
        user_data = data.get("user") or data
        user_id = user_data.get("id")
        user_email = user_data.get("email")
        
        if res.status_code == 200 and user_id:
            user = SimpleUser(user_id, user_email)
            _ensure_profile(user_id, user_email)
            return {"success": True, "user": user}
        else:
            msg = data.get("error_description") or data.get("msg") or data.get("message") or "Invalid email or password"
            return {"success": False, "error": msg}
    except Exception as e:
        return {"success": False, "error": str(e)}


def sign_out():
    for key in ["user", "session", "access_token"]:
        st.session_state.pop(key, None)


def _ensure_profile(user_id: str, email: str):
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
            headers=ADMIN_HEADERS
        )
        if res.status_code == 200 and len(res.json()) == 0:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/profiles",
                headers=ADMIN_HEADERS,
                json={"id": user_id, "email": email, "tier": "free"}
            )
    except Exception as e:
        print(f"Ensure profile error: {e}")


# ── TIER & PROFILE ────────────────────────────────────────────────────────────

def get_profile(user_id: str) -> dict:
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}&select=*",
            headers=ADMIN_HEADERS
        )
        if res.status_code == 200 and res.json():
            return res.json()[0]
    except Exception as e:
        print(f"Get profile error: {e}")
    return {}


def get_tier(user_id: str) -> str:
    profile = get_profile(user_id)
    return profile.get("tier", "free")


def upgrade_tier(user_id: str, new_tier: str) -> bool:
    try:
        res = requests.patch(
            f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
            headers=ADMIN_HEADERS,
            json={"tier": new_tier}
        )
        return res.status_code in [200, 204]
    except:
        return False


# ── USAGE ─────────────────────────────────────────────────────────────────────

def _get_week_start() -> str:
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def get_usage_this_week(user_id: str) -> int:
    try:
        week_start = _get_week_start()
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/usage?user_id=eq.{user_id}&week_start=eq.{week_start}&select=analysis_count",
            headers=ADMIN_HEADERS
        )
        if res.status_code == 200 and res.json():
            return res.json()[0].get("analysis_count", 0)
    except Exception as e:
        print(f"Get usage error: {e}")
    return 0


def increment_usage(user_id: str):
    try:
        week_start = _get_week_start()
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/usage?user_id=eq.{user_id}&week_start=eq.{week_start}",
            headers=ADMIN_HEADERS
        )
        if res.status_code == 200 and res.json():
            current = res.json()[0].get("analysis_count", 0)
            row_id = res.json()[0].get("id")
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/usage?id=eq.{row_id}",
                headers=ADMIN_HEADERS,
                json={"analysis_count": current + 1}
            )
        else:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/usage",
                headers=ADMIN_HEADERS,
                json={"user_id": user_id, "week_start": week_start, "analysis_count": 1}
            )
    except Exception as e:
        print(f"Increment usage error: {e}")


def can_analyze(user_id: str) -> tuple:
    tier = get_tier(user_id)
    if tier in ["pro", "coach"]:
        return True, 999
    used = get_usage_this_week(user_id)
    remaining = max(0, FREE_TIER_LIMIT - used)
    return remaining > 0, remaining


# ── ANALYSES ──────────────────────────────────────────────────────────────────

def save_analysis(user_id: str, event_type: str, score: int, errors: list, drills: list, metrics: dict):
    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/analyses",
            headers=ADMIN_HEADERS,
            json={
                "user_id": user_id,
                "event_type": event_type,
                "score": score,
                "errors": errors,
                "drills": drills,
                "metrics": metrics
            }
        )
        if res.status_code not in [200, 201]:
            print(f"Save analysis error: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Save analysis exception: {e}")


def get_analysis_history(user_id: str, limit: int = 20) -> list:
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/analyses?user_id=eq.{user_id}&order=created_at.desc&limit={limit}",
            headers=ADMIN_HEADERS
        )
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Get history error: {e}")
    return []


# ── TEAMS ─────────────────────────────────────────────────────────────────────

def create_team(coach_id: str, team_name: str) -> dict:
    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/teams",
            headers=ADMIN_HEADERS,
            json={"name": team_name, "coach_id": coach_id}
        )
        if res.status_code in [200, 201]:
            return {"success": True, "team": res.json()[0] if res.json() else {}}
        return {"success": False, "error": res.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_my_teams(coach_id: str) -> list:
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/teams?coach_id=eq.{coach_id}&order=created_at.desc",
            headers=ADMIN_HEADERS
        )
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Get teams error: {e}")
    return []


def add_athlete_to_team(team_id: str, athlete_email: str) -> dict:
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles?email=eq.{athlete_email}&select=id,email",
            headers=ADMIN_HEADERS
        )
        if res.status_code != 200 or not res.json():
            return {"success": False, "error": "No account found with that email. They need to sign up first."}

        athlete_id = res.json()[0]["id"]

        check = requests.get(
            f"{SUPABASE_URL}/rest/v1/team_members?team_id=eq.{team_id}&athlete_id=eq.{athlete_id}",
            headers=ADMIN_HEADERS
        )
        if check.status_code == 200 and check.json():
            return {"success": False, "error": "Athlete is already on this team."}

        add = requests.post(
            f"{SUPABASE_URL}/rest/v1/team_members",
            headers=ADMIN_HEADERS,
            json={"team_id": team_id, "athlete_id": athlete_id}
        )
        if add.status_code in [200, 201]:
            return {"success": True}
        return {"success": False, "error": add.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_team_members(team_id: str) -> list:
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/team_members?team_id=eq.{team_id}",
            headers=ADMIN_HEADERS
        )
        if res.status_code == 200:
            members = res.json()
            enriched = []
            for m in members:
                profile_res = requests.get(
                    f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{m['athlete_id']}&select=email,tier",
                    headers=ADMIN_HEADERS
                )
                if profile_res.status_code == 200 and profile_res.json():
                    m["profile"] = profile_res.json()[0]
                else:
                    m["profile"] = {"email": "Unknown", "tier": "free"}
                enriched.append(m)
            return enriched
    except Exception as e:
        print(f"Get members error: {e}")
    return []


def get_team_analyses(team_id: str) -> list:
    try:
        members = get_team_members(team_id)
        all_analyses = []
        for m in members:
            res = requests.get(
                f"{SUPABASE_URL}/rest/v1/analyses?user_id=eq.{m['athlete_id']}&order=created_at.desc&limit=5",
                headers=ADMIN_HEADERS
            )
            if res.status_code == 200:
                for a in res.json():
                    a["athlete_email"] = m["profile"].get("email", "Unknown")
                    all_analyses.append(a)
        return sorted(all_analyses, key=lambda x: x.get("created_at", ""), reverse=True)
    except Exception as e:
        print(f"Get team analyses error: {e}")
    return []
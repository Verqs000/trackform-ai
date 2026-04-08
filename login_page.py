"""
login_page.py - Login and signup UI with plan picker + Stripe checkout
"""

import streamlit as st
from auth import sign_in, sign_up, create_stripe_checkout, handle_stripe_success, upgrade_tier

STRIPE_PRICES = {
    "pro":   "price_1TJlDZFSa4OLK6hEpZDb8tNl",
    "coach": "price_1TJlGMFSa4OLK6hEaBXB4bQp",
}


def show_login_page():
    # Handle Stripe redirect back to app
    params = st.query_params
    if params.get("payment") == "success":
        uid   = params.get("uid", "")
        tier  = params.get("tier", "")
        if uid and tier in ["pro", "coach"]:
            upgrade_tier(uid, tier)
            st.query_params.clear()
            st.success(f"🎉 Payment confirmed! Your account has been upgraded to {tier.upper()}. Please sign in.")

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #0a0a0a; color: #e8e8e8; }
    .stApp { background: #0a0a0a; }
    #MainMenu, footer, header { visibility: hidden; }
    .stTextInput > div > div > input {
        background: #0a0a0a !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 8px !important;
        color: #e8e8e8 !important;
        padding: 0.6rem 1rem !important;
    }
    .stTextInput > div > div > input:focus { border-color: #ff3b3b !important; box-shadow: none !important; }
    .stTextInput label { color: #666 !important; font-size: 0.8rem !important; letter-spacing: 1px !important; }
    .stButton > button {
        background: #ff3b3b !important; color: #fff !important; border: none !important;
        border-radius: 8px !important; font-family: 'Bebas Neue', sans-serif !important;
        font-size: 1.2rem !important; letter-spacing: 2px !important;
        width: 100% !important; padding: 0.6rem !important; margin-top: 0.5rem !important;
    }
    .stButton > button:hover { background: #cc2a2a !important; }
    .plan-card {
        background: #0a0a0a;
        border: 1px solid #1e1e1e;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        cursor: pointer;
        transition: border-color 0.2s;
    }
    .plan-card.selected { border-color: #ff3b3b !important; }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])

    with col:
        st.markdown("""
        <div style="text-align:center;margin-bottom:2rem;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:4rem;letter-spacing:3px;color:#fff;">
                TRACK<span style="color:#ff3b3b;">FORM</span>
            </div>
            <div style="font-size:0.75rem;letter-spacing:3px;text-transform:uppercase;color:#444;">
                AI Technique Coach
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

        # ── SIGN IN ───────────────────────────────────────────────────────────
        with tab_login:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            email    = st.text_input("Email", key="login_email", placeholder="you@email.com")
            password = st.text_input("Password", type="password", key="login_password", placeholder="••••••••")

            if st.button("SIGN IN", key="btn_login"):
                if not email or not password:
                    st.error("Please enter email and password.")
                else:
                    with st.spinner("Signing in..."):
                        result = sign_in(email, password)
                        if result["success"]:
                            st.session_state["user"] = result["user"]
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")

        # ── SIGN UP ───────────────────────────────────────────────────────────
        with tab_signup:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

            # Plan selector
            st.markdown('<div style="font-size:0.7rem;letter-spacing:3px;text-transform:uppercase;color:#444;margin-bottom:0.6rem;">CHOOSE YOUR PLAN</div>', unsafe_allow_html=True)

            if "selected_plan" not in st.session_state:
                st.session_state["selected_plan"] = "free"

            c1, c2, c3 = st.columns(3)

            with c1:
                free_border = "#ff3b3b" if st.session_state["selected_plan"] == "free" else "#1e1e1e"
                st.markdown(f"""
                <div style="background:#0a0a0a;border:2px solid {free_border};border-radius:10px;padding:1rem;text-align:center;">
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:2px;color:#fff;">FREE</div>
                    <div style="font-size:1.3rem;font-weight:600;color:#fff;">$0</div>
                    <div style="font-size:0.72rem;color:#555;margin-top:0.3rem;">5 analyses/week</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Select Free", key="plan_free", use_container_width=True):
                    st.session_state["selected_plan"] = "free"
                    st.rerun()

            with c2:
                pro_border = "#ff3b3b" if st.session_state["selected_plan"] == "pro" else "#1e1e1e"
                st.markdown(f"""
                <div style="background:#0a0a0a;border:2px solid {pro_border};border-radius:10px;padding:1rem;text-align:center;">
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:2px;color:#ff3b3b;">PRO</div>
                    <div style="font-size:1.3rem;font-weight:600;color:#fff;">$9.99<span style="font-size:0.72rem;color:#555;">/mo</span></div>
                    <div style="font-size:0.72rem;color:#555;margin-top:0.3rem;">Unlimited + history</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Select Pro", key="plan_pro", use_container_width=True):
                    st.session_state["selected_plan"] = "pro"
                    st.rerun()

            with c3:
                coach_border = "#ff3b3b" if st.session_state["selected_plan"] == "coach" else "#1e1e1e"
                st.markdown(f"""
                <div style="background:#0a0a0a;border:2px solid {coach_border};border-radius:10px;padding:1rem;text-align:center;">
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:2px;color:#fff;">COACH</div>
                    <div style="font-size:1.3rem;font-weight:600;color:#fff;">$29.99<span style="font-size:0.72rem;color:#555;">/mo</span></div>
                    <div style="font-size:0.72rem;color:#555;margin-top:0.3rem;">Teams + dashboard</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Select Coach", key="plan_coach", use_container_width=True):
                    st.session_state["selected_plan"] = "coach"
                    st.rerun()

            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

            new_email    = st.text_input("Email", key="signup_email", placeholder="you@email.com")
            new_password = st.text_input("Password", type="password", key="signup_password", placeholder="At least 6 characters")
            confirm      = st.text_input("Confirm Password", type="password", key="signup_confirm", placeholder="••••••••")

            plan = st.session_state["selected_plan"]
            btn_label = "CREATE FREE ACCOUNT" if plan == "free" else f"CONTINUE TO PAYMENT →"

            if st.button(btn_label, key="btn_signup"):
                if not new_email or not new_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm:
                    st.error("Passwords don't match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    with st.spinner("Creating account..."):
                        result = sign_up(new_email, new_password)

                    if result["success"]:
                        if plan == "free":
                            st.success("Account created! Check your email to confirm, then sign in.")
                        else:
                            # Sign them in to get user_id for Stripe metadata
                            sign_result = sign_in(new_email, new_password)
                            if sign_result["success"]:
                                user = sign_result["user"]
                                price_id = STRIPE_PRICES[plan]
                                checkout = create_stripe_checkout(user.id, new_email, price_id, plan)
                                if checkout["success"]:
                                    st.markdown(f"""
                                    <div style="background:#111;border:1px solid #22c55e;border-radius:10px;padding:1.2rem;text-align:center;margin-top:1rem;">
                                        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.2rem;color:#22c55e;letter-spacing:2px;">ACCOUNT CREATED!</div>
                                        <div style="font-size:0.85rem;color:#aaa;margin:0.5rem 0;">Click below to complete your {plan.upper()} subscription</div>
                                        <a href="{checkout['url']}" target="_self" style="display:inline-block;background:#ff3b3b;color:#fff;font-family:'Bebas Neue',sans-serif;font-size:1.1rem;letter-spacing:2px;padding:0.6rem 2rem;border-radius:6px;text-decoration:none;margin-top:0.5rem;">
                                            PAY WITH CARD →
                                        </a>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.warning(f"Account created but payment setup failed: {checkout['error']}. Sign in and upgrade from settings.")
                            else:
                                st.success("Account created! Please confirm your email then sign in.")
                    else:
                        err = result["error"]
                        if "already registered" in err.lower():
                            st.error("An account with that email already exists.")
                        else:
                            st.error(f"Signup failed: {err}")
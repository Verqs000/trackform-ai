"""
login_page.py - Login & Signup with Stripe Integration
"""

import streamlit as st
from auth import sign_in, sign_up, create_stripe_checkout, upgrade_tier, reset_password

STRIPE_PRICES = {
    "pro":   "price_1TJlDZFSa4OLK6hEpZDb8tNl",
    "coach": "price_1TJlGMFSa4OLK6hEaBXB4bQp",
}


def show_login_page():
    # Handle Stripe redirect
    params = st.query_params
    if params.get("payment") == "success":
        uid  = params.get("uid", "")
        tier = params.get("tier", "")
        if uid and tier in ["pro", "coach"]:
            upgrade_tier(uid, tier)
            st.query_params.clear()
            st.success(f"🎉 Payment successful! Your account is now {tier.upper()}. Please sign in below.")
            st.rerun()

    # CSS
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #0a0a0a; color: #e8e8e8; }
    .stApp { background: #0a0a0a; }
    #MainMenu, footer, header { visibility: hidden; }
    .stTextInput > div > div > input {
        background: #111 !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 8px !important;
        color: #e8e8e8 !important;
        padding: 0.75rem 1rem !important;
    }
    .stTextInput > div > div > input:focus { border-color: #ff3b3b !important; }
    .stButton > button {
        background: #ff3b3b !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 1.25rem !important;
        letter-spacing: 2px !important;
        padding: 0.75rem !important;
        width: 100% !important;
        margin-top: 0.5rem !important;
    }
    .stButton > button:hover { background: #e02e2e !important; }
    .plan-card {
        background: #111;
        border: 2px solid #1e1e1e;
        border-radius: 12px;
        padding: 1.2rem 0.8rem;
        text-align: center;
        transition: all 0.2s ease;
    }
    .plan-card.selected {
        border-color: #ff3b3b;
        box-shadow: 0 0 0 3px rgba(255,59,59,0.15);
    }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<div style="font-family:\'Bebas Neue\',sans-serif;font-size:4.2rem;letter-spacing:3px;color:#fff;text-align:center;">TRACK<span style="color:#ff3b3b;">FORM</span></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.78rem;letter-spacing:3px;text-transform:uppercase;color:#666;text-align:center;margin-bottom:2rem;">AI TECHNIQUE COACH</div>', unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["Sign In", "Create Account"])

        # ── SIGN IN ───────────────────────────────────────────────────────────
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)
            email    = st.text_input("Email Address", key="login_email", placeholder="you@email.com")
            password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")

            if st.button("SIGN IN", key="btn_login", use_container_width=True):
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    with st.spinner("Signing in..."):
                        result = sign_in(email, password)
                    if result.get("success"):
                        st.session_state["user"] = result["user"]
                        st.rerun()
                    else:
                        error = result.get("error", "")
                        if "not confirmed" in error.lower():
                            st.error("Please confirm your email first. Check your inbox for a confirmation link.")
                        else:
                            st.error("Invalid email or password.")

            # ── Forgot Password ────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("**Forgot your password?**")
            reset_email = st.text_input("Enter your email address", key="reset_email", placeholder="you@email.com")
            if st.button("SEND RESET LINK", key="btn_reset"):
                if reset_email:
                    reset_password(reset_email)
                    st.success("If that email is registered, a reset link has been sent. Check your inbox.")
                else:
                    st.error("Please enter your email address.")

        # ── SIGN UP ───────────────────────────────────────────────────────────
        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown('<div style="font-size:0.75rem;letter-spacing:2px;text-transform:uppercase;color:#666;margin-bottom:0.8rem;">CHOOSE YOUR PLAN</div>', unsafe_allow_html=True)

            if "selected_plan" not in st.session_state:
                st.session_state.selected_plan = "free"

            c1, c2, c3 = st.columns(3)

            with c1:
                is_selected = st.session_state.selected_plan == "free"
                st.markdown(f"""
                <div class="plan-card {'selected' if is_selected else ''}">
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:1.3rem;color:#fff;">FREE</div>
                    <div style="font-size:1.8rem;font-weight:700;color:#fff;margin:0.3rem 0;">$0</div>
                    <div style="font-size:0.8rem;color:#888;">5 analyses / week</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Select Free", key="free_btn", use_container_width=True):
                    st.session_state.selected_plan = "free"
                    st.rerun()

            with c2:
                is_selected = st.session_state.selected_plan == "pro"
                st.markdown(f"""
                <div class="plan-card {'selected' if is_selected else ''}">
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:1.3rem;color:#ff3b3b;">PRO</div>
                    <div style="font-size:1.8rem;font-weight:700;color:#fff;margin:0.3rem 0;">$9.99<span style="font-size:0.75rem;">/mo</span></div>
                    <div style="font-size:0.8rem;color:#888;">Unlimited + History</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Select Pro", key="pro_btn", use_container_width=True):
                    st.session_state.selected_plan = "pro"
                    st.rerun()

            with c3:
                is_selected = st.session_state.selected_plan == "coach"
                st.markdown(f"""
                <div class="plan-card {'selected' if is_selected else ''}">
                    <div style="font-family:'Bebas Neue',sans-serif;font-size:1.3rem;color:#fff;">COACH</div>
                    <div style="font-size:1.8rem;font-weight:700;color:#fff;margin:0.3rem 0;">$29.99<span style="font-size:0.75rem;">/mo</span></div>
                    <div style="font-size:0.8rem;color:#888;">Team Dashboard</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Select Coach", key="coach_btn", use_container_width=True):
                    st.session_state.selected_plan = "coach"
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

            new_email        = st.text_input("Email Address", key="signup_email", placeholder="you@email.com")
            new_password     = st.text_input("Password", type="password", key="signup_password", placeholder="Minimum 6 characters")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")

            plan         = st.session_state.selected_plan
            button_label = "CREATE FREE ACCOUNT" if plan == "free" else f"CREATE ACCOUNT & PAY ${'9.99' if plan == 'pro' else '29.99'}/mo"

            if st.button(button_label, key="btn_signup", use_container_width=True):
                if not new_email or not new_password:
                    st.error("Email and password are required.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    with st.spinner("Creating your account..."):
                        result = sign_up(new_email, new_password)

                    if result.get("success"):
                        if plan == "free":
                            st.success("✅ Account created! Please check your email to confirm, then sign in.")
                        else:
                            sign_result = sign_in(new_email, new_password)
                            if sign_result.get("success"):
                                user     = sign_result["user"]
                                price_id = STRIPE_PRICES[plan]
                                checkout = create_stripe_checkout(user.id, new_email, price_id, plan)
                                if checkout.get("success") and checkout.get("url"):
                                    st.markdown(f"""
                                    <div style="background:#111;border:2px solid #22c55e;border-radius:12px;padding:2rem;text-align:center;margin:1.5rem 0;">
                                        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;color:#22c55e;letter-spacing:2px;">ACCOUNT CREATED!</div>
                                        <div style="color:#aaa;font-size:0.9rem;margin:0.5rem 0;">Click below to complete your {plan.upper()} subscription.</div>
                                        <a href="{checkout['url']}" target="_blank" style="display:inline-block;background:#ff3b3b;color:white;padding:0.9rem 2.5rem;border-radius:8px;text-decoration:none;font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:2px;margin-top:1rem;">
                                            PROCEED TO PAYMENT →
                                        </a>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.warning("Account created but payment link failed. Please contact trackformai@gmail.com")
                            else:
                                st.success("Account created! Please confirm your email then sign in.")
                    else:
                        err = result.get("error", "")
                        if "already registered" in err.lower():
                            st.error("An account with that email already exists. Try signing in.")
                        else:
                            st.error(f"Signup failed: {err}")

            # ToS link
            st.markdown("""
            <div style="font-size:0.72rem;color:#444;text-align:center;margin-top:1.2rem;">
                By creating an account you agree to our
                <a href="https://trackform-ai.streamlit.app/tos" target="_blank" style="color:#ff3b3b;text-decoration:none;">Terms of Service</a>
            </div>
            """, unsafe_allow_html=True)
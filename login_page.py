"""
login_page.py - Login and signup UI
"""

import streamlit as st
from auth import sign_in, sign_up

def show_login_page():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #0a0a0a; color: #e8e8e8; }
    .stApp { background: #0a0a0a; }
    #MainMenu, footer, header { visibility: hidden; }

    .login-wrap {
        max-width: 420px;
        margin: 4rem auto;
        padding: 2.5rem;
        background: #111;
        border: 1px solid #1e1e1e;
        border-radius: 16px;
    }

    .login-logo {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 3rem;
        letter-spacing: 3px;
        text-align: center;
        margin-bottom: 0.2rem;
    }

    .login-sub {
        text-align: center;
        font-size: 0.75rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #444;
        margin-bottom: 2rem;
    }

    .stTextInput > div > div > input {
        background: #0a0a0a !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 8px !important;
        color: #e8e8e8 !important;
        padding: 0.6rem 1rem !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #ff3b3b !important;
        box-shadow: none !important;
    }

    .stTextInput label { color: #666 !important; font-size: 0.8rem !important; letter-spacing: 1px !important; }

    .stButton > button {
        background: #ff3b3b !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 1.2rem !important;
        letter-spacing: 2px !important;
        width: 100% !important;
        padding: 0.6rem !important;
        margin-top: 0.5rem !important;
    }

    .stButton > button:hover { background: #cc2a2a !important; }

    .tier-card {
        background: #0a0a0a;
        border: 1px solid #1e1e1e;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        text-align: center;
    }

    .tier-name {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.3rem;
        letter-spacing: 2px;
        color: #fff;
    }

    .tier-price {
        font-size: 1.5rem;
        font-weight: 600;
        color: #ff3b3b;
    }

    .tier-feature {
        font-size: 0.8rem;
        color: #666;
        margin-top: 0.3rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Center the form
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

        with tab_login:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            email = st.text_input("Email", key="login_email", placeholder="you@email.com")
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

        with tab_signup:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

            # Show tiers
            st.markdown("""
            <div style="margin-bottom:1.2rem;">
                <div style="font-size:0.7rem;letter-spacing:3px;text-transform:uppercase;color:#444;margin-bottom:0.8rem;">CHOOSE YOUR PLAN</div>
                <div style="display:flex;gap:0.8rem;">
                    <div style="flex:1;background:#0a0a0a;border:1px solid #1e1e1e;border-radius:10px;padding:1rem;text-align:center;">
                        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:2px;color:#fff;">FREE</div>
                        <div style="font-size:1.3rem;font-weight:600;color:#fff;">$0</div>
                        <div style="font-size:0.75rem;color:#555;margin-top:0.3rem;">5 analyses / week</div>
                    </div>
                    <div style="flex:1;background:#0a0a0a;border:1px solid #ff3b3b;border-radius:10px;padding:1rem;text-align:center;">
                        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:2px;color:#ff3b3b;">PRO</div>
                        <div style="font-size:1.3rem;font-weight:600;color:#fff;">$9.99<span style="font-size:0.75rem;color:#555;">/mo</span></div>
                        <div style="font-size:0.75rem;color:#555;margin-top:0.3rem;">Unlimited + history</div>
                    </div>
                    <div style="flex:1;background:#0a0a0a;border:1px solid #1e1e1e;border-radius:10px;padding:1rem;text-align:center;">
                        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:2px;color:#fff;">COACH</div>
                        <div style="font-size:1.3rem;font-weight:600;color:#fff;">$29.99<span style="font-size:0.75rem;color:#555;">/mo</span></div>
                        <div style="font-size:0.75rem;color:#555;margin-top:0.3rem;">Teams + dashboard</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            new_email = st.text_input("Email", key="signup_email", placeholder="you@email.com")
            new_password = st.text_input("Password", type="password", key="signup_password", placeholder="At least 6 characters")
            confirm = st.text_input("Confirm Password", type="password", key="signup_confirm", placeholder="••••••••")

            if st.button("CREATE FREE ACCOUNT", key="btn_signup"):
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
                        st.success("Account created! Check your email to confirm, then sign in.")
                    else:
                        err = result["error"]
                        if "already registered" in err.lower():
                            st.error("An account with that email already exists.")
                        else:
                            st.error(f"Signup failed: {err}")
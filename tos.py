"""
tos.py - Terms of Service page
"""

import streamlit as st

def show_tos_page():
    st.markdown("""
    <style>
    .section-header {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.8rem;
        letter-spacing: 3px;
        color: #fff;
        margin-bottom: 1.5rem;
    }
    .tos-content {
        max-width: 800px;
        margin: 0 auto;
        line-height: 1.7;
        font-size: 1.02rem;
        color: #ddd;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">TERMS OF SERVICE</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="tos-content">

    Last updated: April 2026

    ### 1. Acceptance of Terms
    By accessing and using TrackForm AI, you accept and agree to be bound by the terms and provision of this agreement.

    ### 2. Description of Service
    TrackForm AI provides AI-powered technique analysis for track & field athletes and coaches. 
    The service includes video analysis, technique scoring, progress tracking, and team management tools.

    ### 3. User Accounts
    - You must provide accurate and complete information when creating an account.
    - You are responsible for maintaining the confidentiality of your password.
    - Free users are limited to 5 analyses per week.
    - Paid subscriptions (Pro & Coach) are billed monthly via Stripe.

    ### 4. Subscription and Payments
    - Subscriptions automatically renew unless cancelled.
    - You can cancel your subscription anytime from your account.
    - No refunds for partial months.

    ### 5. Acceptable Use
    You agree not to:
    - Upload videos that violate any laws or contain inappropriate content.
    - Attempt to reverse engineer or misuse the AI models.
    - Share your account credentials with others.
    - Use the service for any illegal purpose.

    ### 6. Intellectual Property
    All AI models, analysis outputs, and platform design are owned by TrackForm AI.

    ### 7. Limitation of Liability
    The service is provided "as is". We are not liable for any damages arising from use of the service.

    ### 8. Termination
    We reserve the right to suspend or terminate accounts that violate these terms.

    ### 9. Changes to Terms
    We may update these Terms of Service from time to time. Continued use of the service constitutes acceptance of the new terms.

    ### Contact Us
    If you have any questions about these Terms, please contact us at:
    **trackformai@gmail.com**

    </div>
    """, unsafe_allow_html=True)

    st.caption("© 2026 TrackForm AI. All rights reserved.")
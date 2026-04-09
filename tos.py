import streamlit as st

def show_tos_page():
    st.title("Terms of Service")
    st.write("Last updated: April 2026")
    
    st.markdown("""
    By using TrackForm AI, you agree to the following:

    - You must be at least 13 years old to use this service.
    - Free users are limited to 5 video analyses per week.
    - Paid subscriptions (Pro & Coach) are billed monthly through Stripe.
    - You are responsible for the videos you upload.
    - We reserve the right to terminate accounts that violate these terms.

    For questions, contact: trackformai@gmail.com
    """)
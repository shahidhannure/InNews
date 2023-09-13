# authenticator.py
import streamlit as st
from authenticator import Authenticator, OAuthProvider

def authenticate():
    authenticator = Authenticator()

    # Configure Google OAuth provider
    google_oauth = OAuthProvider(
        name="Google",
        client_id="789483772771-52nucghsdot8spmbe4qn5p1e97lder01.apps.googleusercontent.com",
        client_secret="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",
        redirect_uri="http://localhost:8501/"
    )

    # Add the OAuth provider
    authenticator.add_provider(google_oauth)

    return authenticator.authenticate()


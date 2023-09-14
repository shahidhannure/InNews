import streamlit as st
import sqlite3
from passlib.hash import pbkdf2_sha256

st.session_state.authenticated = False

if 'show_registration' not in st.session_state:
    st.session_state.show_registration = False

# Initialize SQLite database
conn = sqlite3.connect('user.db')
c = conn.cursor()

# Create a users table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)''')
conn.commit()

# User Authentication
def authenticate(username, password):
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    if user and pbkdf2_sha256.verify(password, user[2]):  # Verify the hashed password
        return True
    return False

# User Registration
def register(username, password):
    # Hash the password before storing it in the database
    hashed_password = pbkdf2_sha256.hash(password)
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
    conn.commit()

# Login Form
def login():
    st.write('## Login')
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    if st.button('Log In'):
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.success('Login successful.')
        else:
            st.error('Login failed. Please try again.')

def show_registration_form():
    st.write('## Registration')
    new_username = st.text_input('New Username')
    new_password = st.text_input('New Password', type='password')
    confirm_password = st.text_input('Confirm Password', type='password')
    if new_password == confirm_password:
        if st.button('Register'):
            # Check if the username already exists in the database
            c.execute("SELECT * FROM users WHERE username=?", (new_username,))
            existing_user = c.fetchone()
            if existing_user:
                st.error('Username already exists. Please choose a different one.')
            else:
                register(new_username, new_password)
                st.success('Registration successful. You can now log in.')
                st.button("Log In") 
                st.session_state.show_registration = False  # Set it back to False after successful registration
    else:
        st.error('Passwords do not match. Please try again.')

# Main App
def main():
    st.title("NewsBite: A Summarised News📰")

    if not st.session_state.authenticated:
        login_successful = login()
        if not st.session_state.authenticated:
            if st.button("Don't have an account? Register below."):
                st.session_state.show_registration = True

    if st.session_state.authenticated:
        # Display the main app functionality here
        st.write("Welcome to the main app!")
    elif st.session_state.show_registration:
        show_registration_form()

# Separate registration page
def registration_page():
    st.title("Registration")
    show_registration_form()
    if not st.session_state.show_registration:
        st.write("Registration successful. You can now log in.")

# Run the app
if st.session_state.show_registration:
    registration_page()
else:
    main()

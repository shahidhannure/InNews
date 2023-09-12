import streamlit as st
from PIL import Image
from bs4 import BeautifulSoup as soup
from urllib.request import urlopen
from newspaper import Article
import io
import nltk
import sqlite3
import hashlib

# Initialize SQLite database
conn = sqlite3.connect('user_profiles.db')
cursor = conn.cursor()

# Create user profiles table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_profiles (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        favorite_topics TEXT,
        favorite_sources TEXT,
        saved_articles TEXT
    )
''')
conn.commit()

# Function to get user profile from the database
def get_user_profile(username):
    cursor.execute("SELECT * FROM user_profiles WHERE username=?", (username,))
    user_data = cursor.fetchone()
    if user_data:
        return {
            'username': user_data[0],
            'password_hash': user_data[1],
            'favorite_topics': user_data[2].split(',') if user_data[2] else [],
            'favorite_sources': user_data[3].split(',') if user_data[3] else [],
            'saved_articles': user_data[4].split(',') if user_data[4] else [],
        }
    else:
        return None

# Function to create or update a user profile in the database
def create_or_update_user_profile(username, password_hash, favorite_topics, favorite_sources, saved_articles):
    cursor.execute("INSERT OR REPLACE INTO user_profiles VALUES (?, ?, ?, ?, ?)",
                   (username, password_hash, ','.join(favorite_topics), ','.join(favorite_sources), ','.join(saved_articles)))
    conn.commit()
    
nltk.download('punkt')

st.set_page_config(page_title='InNews🇮🇳: A Summarised News📰 Portal', page_icon='./Meta/newspaper.ico')


def fetch_news_search_topic(topic):
    site = 'https://news.google.com/rss/search?q={}'.format(topic)
    op = urlopen(site)  # Open that site
    rd = op.read()  # read data from site
    op.close()  # close the object
    sp_page = soup(rd, 'xml')  # scrapping data from site
    news_list = sp_page.find_all('item')  # finding news
    return news_list


def fetch_top_news():
    site = 'https://news.google.com/news/rss'
    op = urlopen(site)  # Open that site
    rd = op.read()  # read data from site
    op.close()  # close the object
    sp_page = soup(rd, 'xml')  # scrapping data from site
    news_list = sp_page.find_all('item')  # finding news
    return news_list


def fetch_category_news(topic):
    site = 'https://news.google.com/news/rss/headlines/section/topic/{}'.format(topic)
    op = urlopen(site)  # Open that site
    rd = op.read()  # read data from site
    op.close()  # close the object
    sp_page = soup(rd, 'xml')  # scrapping data from site
    news_list = sp_page.find_all('item')  # finding news
    return news_list


def fetch_news_poster(poster_link):
    try:
        u = urlopen(poster_link)
        raw_data = u.read()
        image = Image.open(io.BytesIO(raw_data))
        st.image(image, use_column_width=True)
    except:
        image = Image.open('./Meta/no_image.jpg')
        st.image(image, use_column_width=True)


def display_news(list_of_news, news_quantity):
    c = 0
    for news in list_of_news:
        c += 1
        # st.markdown(f"({c})[ {news.title.text}]({news.link.text})")
        st.write('**({}) {}**'.format(c, news.title.text))
        news_data = Article(news.link.text)
        try:
            news_data.download()
            news_data.parse()
            news_data.nlp()
        except Exception as e:
            st.error(e)
        fetch_news_poster(news_data.top_image)
        with st.expander(news.title.text):
            st.markdown(
                '''<h6 style='text-align: justify;'>{}"</h6>'''.format(news_data.summary),
                unsafe_allow_html=True)
            st.markdown("[Read more at {}...]({})".format(news.source.text, news.link.text))
        st.success("Published Date: " + news.pubDate.text)
        if c >= news_quantity:
            break
            
def run():
    st.title("InNews🇮🇳: A Summarised News📰")
    image = Image.open('./Meta/newspaper.png')

    col1, col2, col3 = st.columns([3, 5, 3])

    with col1:
        st.write("")

    with col2:
        st.image(image, use_column_width=False)

    with col3:
        st.write("")
    category = ['--Select--', 'Trending🔥 News', 'Favourite💙 Topics', 'Search🔍 Topic']
    cat_op = st.selectbox('Select your Category', category)
    if cat_op == category[0]:
        st.warning('Please select Type!!')
    elif cat_op == category[1]:
        st.subheader("✅ Here is the Trending🔥 news for you")
        no_of_news = st.slider('Number of News:', min_value=5, max_value=25, step=1)
        news_list = fetch_top_news()
        display_news(news_list, no_of_news)
    elif cat_op == category[2]:
        av_topics = ['Choose Topic', 'WORLD', 'NATION', 'BUSINESS', 'TECHNOLOGY', 'ENTERTAINMENT', 'SPORTS', 'SCIENCE',
                     'HEALTH']
        st.subheader("Choose your favourite Topic")
        chosen_topic = st.selectbox("Choose your favourite Topic", av_topics)
        if chosen_topic == av_topics[0]:
            st.warning("Please Choose the Topic")
        else:
            no_of_news = st.slider('Number of News:', min_value=5, max_value=25, step=1)
            news_list = fetch_category_news(chosen_topic)
            if news_list:
                st.subheader("✅ Here are the some {} News for you".format(chosen_topic))
                display_news(news_list, no_of_news)
            else:
                st.error("No News found for {}".format(chosen_topic))

    elif cat_op == category[3]:
        user_topic = st.text_input("Enter your Topic🔍")
        no_of_news = st.slider('Number of News:', min_value=5, max_value=15, step=1)

        if st.button("Search") and user_topic != '':
            user_topic_pr = user_topic.replace(' ', '')
            news_list = fetch_news_search_topic(topic=user_topic_pr)
            if news_list:
                st.subheader("✅ Here are the some {} News for you".format(user_topic.capitalize()))
                display_news(news_list, no_of_news)
            else:
                st.error("No News found for {}".format(user_topic))
        else:
            st.warning("Please write Topic Name to Search🔍")


run()



if not logged_in_username:
    username = st.text_input("Username:")
    password = st.text_input("Password:", type="password")
    
    if st.button("Register"):
        # Check if the username is available
        existing_user = get_user_profile(username)
        if existing_user:
            st.error("Username already exists. Please choose another username.")
        else:
            # Hash the password for security
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            create_or_update_user_profile(username, password_hash, [], [], [])
            st.success("Registration successful! You can now log in.")
    
    if st.button("Login"):
        user_profile = get_user_profile(username)
        if user_profile and user_profile['password_hash'] == hashlib.sha256(password.encode()).hexdigest():
            logged_in_username = username
            st.success(f"Welcome, {username}!")
        else:
            st.error("Invalid username or password. Please try again.")

# User Profile Page
if logged_in_username:
    user_profile = get_user_profile(logged_in_username)
    st.title(f"Welcome, {logged_in_username}!")

    # Display and edit favorite topics, sources, and saved articles
    favorite_topics = st.multiselect("Favorite Topics:", available_topics, user_profile['favorite_topics'])
    favorite_sources = st.multiselect("Favorite Sources:", available_sources, user_profile['favorite_sources'])

    # Save the changes to the user's profile
    create_or_update_user_profile(logged_in_username, user_profile['password_hash'], favorite_topics, favorite_sources, user_profile['saved_articles'])
    

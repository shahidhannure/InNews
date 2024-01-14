import streamlit as st
from PIL import Image
from bs4 import BeautifulSoup as soup
from urllib.request import urlopen
from newspaper import Article
import io
import nltk
import transformers
import requests
import sqlite3
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi

nltk.download('punkt')
nltk.download('stopwords')


# Initialize the SQLite database
conn = sqlite3.connect('user_bookmarks.db')
c = conn.cursor()

# Create a users table and a bookmarks table if they don't exist
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS bookmarks (
        user_id TEXT,
        bookmarked_url TEXT
    )
''')

st.set_page_config(page_title='Scalable NewBite: A Summarised News📰 Portal', page_icon='./Meta/newspaper.ico')


# Function to get or create the session state
def get_session_state():
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
        st.session_state.bookmarks = []
        st.session_state.is_authenticated = False
    return st.session_state
def is_authenticated():
    return get_session_state().is_authenticated
# Function to save user information
def save_user_info(user_id):
    c.execute('INSERT OR REPLACE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()

# Function to save a bookmark for a user
def save_bookmark(user_id, bookmarked_url):
    # Make sure the user exists in the users table
    save_user_info(user_id)
    
    # Associate the bookmark with the user
    c.execute('INSERT INTO bookmarks (user_id, bookmarked_url) VALUES (?, ?)', (user_id, bookmarked_url))
    conn.commit()

# Function to get user bookmarks
def get_user_bookmarks(user_id):
    c.execute('SELECT bookmarked_url FROM bookmarks WHERE user_id=?', (user_id,))
    return [row[0] for row in c.fetchall()]



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


def display_news(list_of_news, news_quantity, user_id):
    c = 0
    for news in list_of_news:
        c += 1
        st.write('**({}) {}**'.format(c, news.title.text))
        news_data = Article(news.link.text)
        try:
            news_data.download()
            news_data.parse()
            news_data.nlp()
        except Exception as e:
            st.error(e)
        
        # New Feature: Bookmarking
        bookmark_button = st.button("Bookmark", key=f"bookmark_{c}")
        if bookmark_button:
            if news.link.text not in get_user_bookmarks(user_id):
                save_bookmark(user_id, news.link.text)
            else:
                user_id['bookmarks'].remove(news.link.text)
        
        if news.link.text in get_user_bookmarks(user_id):
            st.write("Bookmarked ✅")

        fetch_news_poster(news_data.top_image)
        with st.expander(news.title.text):
            st.markdown(
                '''<h6 style='text-align: justify;'>{}"</h6>'''.format(news_data.summary),
                unsafe_allow_html=True)
            st.markdown("[Read more at {}...]({})".format(news.source.text, news.link.text))
        st.success("Published Date: " + news.pubDate.text)
        if c >= news_quantity:
            break
def fetch_youtube_transcript(youtube_url):
    try:
        # Get YouTube video ID
        video_id = YouTube(youtube_url).video_id

        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except Exception as e:
        return f"Error: {str(e)}"

def summarize_youtube_video(youtube_url):
    transcript = fetch_youtube_transcript(youtube_url)

    if isinstance(transcript, list):
        # Concatenate the text from each entry in the transcript
        full_text = " ".join(entry['text'] for entry in transcript)

        # Display initial output (transcription)
        st.subheader("YouTube Video Transcription:")
        st.write(full_text)

        # Generate summary using your summarization function
        summary = summarize_text_with_api(full_text)
        return summary
    else:
        return transcript
# Function for summarizing text with API
def summarize_text_with_api(input_text):
    try:
        api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        headers = {"Authorization": "Bearer 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"}  # Replace with your Hugging Face API key

        # Adjust max_length dynamically based on the length of the input text
        max_length = len(input_text) // 3
        payload = {"inputs": input_text, "options": {"task": "summarization", "max_length": max_length, "min_length": 1}}

        response = None
        max_retries = 5  # Define the maximum number of retries

        for _ in range(max_retries):
            response = requests.post(api_url, headers=headers, json=payload)

            if response.status_code == 503:
                estimated_time = response.json().get("estimated_time", 10)
                st.warning(f"Model is currently loading. Retrying in {estimated_time} seconds...")
                time.sleep(estimated_time)
            elif response.status_code == 200:
                break
            else:
                st.error(f"Error in summarization API call. Status Code: {response.status_code}, Response: {response.content.decode('utf-8')}")
                return ""
        
        if response.status_code == 200:
            response_data = response.json()
            if isinstance(response_data, list):
                response_data = response_data[0]  # Use the first item if it's a list
            return response_data["summary_text"]
        else:
            st.error(f"Failed to generate a summary. Please try again later.")
            return ""
    except Exception as e:
        st.error(f"An error occurred while summarizing: {str(e)}")
        return ""

# Streamlit UI
# Streamlit UI
def main():
    st.title("Scalable NewBite: A Summarised News📰 Portal")
    st.sidebar.title("Navigation")
    
    session_state = get_session_state()
    page_options = ["Home", "YouTube Feature", "UserProfile", "Trending News"]
    page_selection = st.sidebar.radio("Go to", page_options)

    if page_selection == "Home":
        home(session_state)
    elif not is_authenticated() and page_selection != "Home":
        st.warning("Please enter your username on the Home page before navigating to other pages.")
    else:
        if page_selection == "YouTube Feature":
            youtube_feature(session_state)
        elif page_selection == "UserProfile":
            user_profile(session_state)
        elif page_selection == "Trending News":
            trending_news(session_state)
def home(session_state):
    st.subheader("Welcome to Scalable NewBite!")
    session_state = get_session_state()
    session_state.user_id = st.text_input("Enter your username")
    if session_state.user_id:
        session_state.is_authenticated = True
        st.write(f"Welcome, {session_state.user_id}!")
    st.write("This is the home page. Choose a section from the sidebar to explore.")

def user_profile(session_state):
    st.subheader("User Profile")
    if not is_authenticated():
        st.warning("Please enter your username on the Home page before accessing the User Profile.")
        return
    st.write(f"User ID: {session_state.user_id}")
    view_bookmarked_articles(session_state.user_id)

def youtube_feature(session_state):
    st.subheader("YouTube Feature")
    if not is_authenticated():
        st.warning("Please enter your username on the Home page before accessing the YouTube Feature.")
        return
    youtube_url = st.text_input("Enter YouTube Video URL")
    
    if st.button("Get Transcription"):
        if youtube_url:
            st.info("Fetching transcription... This may take a moment.")
            video_summary = summarize_youtube_video(youtube_url)
        
            if video_summary:
                st.subheader("YouTube Video Summary:")
                st.write(video_summary)
            else:
                st.error("Failed to generate a summary. Please check the YouTube Video URL and try again.")
        else:
            st.warning("Please enter a valid YouTube Video URL.")

def trending_news(session_state):
    st.subheader("Trending News")
    if not is_authenticated():
        st.warning("Please enter your username on the Home page before accessing the Trending News.")
        return
    no_of_news = st.slider('Number of News:', min_value=5, max_value=25, step=1)
    news_list = fetch_top_news()
    display_news(news_list, no_of_news, get_session_state().user_id)  # Adjust user_id as needed

def view_bookmarked_articles(user_id):
    st.subheader("Saved Bookmarks")
    bookmarks = get_user_bookmarks(user_id)
    if not bookmarks:
        st.write("You haven't saved any bookmarks.")
    else:
        st.write("Your bookmarked articles:")
        for bookmark in bookmarks:
            st.markdown(f"- {bookmark}")

# The try-except block should be aligned with the outer function indentation

if __name__ == "__main__":
    main()

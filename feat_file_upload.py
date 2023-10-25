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
from docx import Document
import PyPDF2

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

# Modify the extract_text_from_file function to limit the number of words
def extract_text_from_file(file_extension, file_contents):
    if file_extension == "pdf":
        # Extract text from a PDF file

        pdf_reader = PyPDF2.PdfFileReader(io.BytesIO(file_contents))
        text = ""
        for page_num in range(pdf_reader.getNumPages()):
            text += pdf_reader.getPage(page_num).extractText()
    elif file_extension == "docx":
        # Extract text from a .docx file

        doc = Document(io.BytesIO(file_contents))
        text = " ".join([paragraph.text for paragraph in doc.paragraphs])
    else:
        text = ""

    return text











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

# Streamlit UI
def run():
    st.title("NewsBite: A Summarised News📰")
    image = Image.open('./Meta/newspaper.png')

    col1, col2, col3 = st.columns([3, 5, 3])

    with col1:
        st.write("")

    with col2:
        st.image(image, use_column_width=False)

    with col3:
        st.write("")

   # User profile handling
    user_id = st.text_input("Enter your username")

    if user_id:
        category = ['--Select--', 'Trending🔥 News', 'Favourite💙 Topics', 'Search🔍 Topic', 'Get Summary','View Bookmarks','Upload and Summarize']
        cat_op = st.selectbox('Select your Category', category, key='select_category')

        if cat_op == category[0]:
            st.warning('Please select Type!!')
        elif cat_op == category[1]:
            st.subheader("✅ Here is the Trending🔥 news for you")
            no_of_news = st.slider('Number of News:', min_value=5, max_value=25, step=1)
            news_list = fetch_top_news()
            display_news(news_list, no_of_news, user_id)
        elif cat_op == category[2]:
            av_topics = ['Choose Topic', 'WORLD', 'NATION', 'BUSINESS', 'TECHNOLOGY', 'ENTERTAINMENT', 'SPORTS', 'SCIENCE',
                         'HEALTH']
            st.subheader("Choose your favourite Topic")
            chosen_topic = st.selectbox("Choose your favourite Topic", av_topics, key='select_favourite_topic')
            if chosen_topic == av_topics[0]:
                st.warning("Please Choose the Topic")
            else:
                no_of_news = st.slider('Number of News:', min_value=5, max_value=25, step=1)
                news_list = fetch_category_news(chosen_topic)
                if news_list:
                    st.subheader("✅ Here are some {} News for you".format(chosen_topic))
                    display_news(news_list, no_of_news, user_id)
                else:
                    st.error("No News found for {}".format(chosen_topic))
        elif cat_op == category[3]:
            user_topic = st.text_input("Enter your Topic🔍")
            no_of_news = st.slider('Number of News:', min_value=5, max_value=15, step=1)

            if st.button("Search") and user_topic != '':
                user_topic_pr = user_topic.replace(' ', '')
                news_list = fetch_news_search_topic(topic=user_topic_pr)
                if news_list:
                    st.subheader("✅ Here are some {} News for you".format(user_topic.capitalize()))
                    display_news(news_list, no_of_news, user_id)
                else:
                    st.error("No News found for {}".format(user_topic))
            else:
                st.warning("Please write Topic Name to Search🔍")      
        elif cat_op == category[4]:
            user_input = st.text_area("Enter an article link or a long paragraph to summarize:")

            if st.button("Get Summary") and user_input.strip():
                summarized_text = summarize_text_with_api(user_input)
                if summarized_text:
                    st.subheader("Summarized Text:")
                    st.write(summarized_text)
                else:
                    st.error("Failed to generate a summary. Please try again later.")

        elif cat_op == category[5]:
            view_bookmarked_articles(user_id)

        elif cat_op == category[6]:
            st.subheader("Upload a .pdf or .docx document for summarization:")
            uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"])
            
            # Add a radio button for selecting summary length
            summary_length = st.radio("Select Summary Length", ["150 words", "300 words", "500 words", "1000 words"])
            
            if uploaded_file is not None:
                file_extension = uploaded_file.name.split(".")[-1]
                summary_length = int(summary_length.split()[0])  # Extract the numeric part

                if file_extension in ["pdf", "docx"]:
                    file_contents = uploaded_file.read()
                    text = extract_text_from_file(file_extension, file_contents)
                    summarized_text = summarize_text_with_api(text, summary_length)

                    if summarized_text:
                        st.subheader(f"Summarized Text ({summary_length} words):")
                        st.write(summarized_text)
                    else:
                        st.error("Failed to generate a summary. Please try again later.")
                else:
                    st.error("Unsupported file format. Please upload a .pdf or .docx file.")


        
        
def view_bookmarked_articles(user_id):
    st.subheader("Saved Bookmarks")
    bookmarks = get_user_bookmarks(user_id)
    if not bookmarks:
        st.write("You haven't saved any bookmarks.")
    else:
        st.write("Your bookmarked articles:")
        for bookmark in bookmarks:
            st.markdown(f"- {bookmark}")
def summarize_text_with_api(input_text, target_word_count):
    try:
        api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        headers = {"Authorization": "Bearer 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"}  # Replace with your Hugging Face API key
        payload = {
            "inputs": input_text,
            "options": {
                "task": "summarization",
                "max_length": target_word_count,
                "min_length": 0  # You can adjust this if needed
            }
        }
        
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
            
            # Post-process the summary to achieve the target word count
            summarized_text = response_data["summary_text"]
            word_count = len(summarized_text.split())
            if word_count > target_word_count:
                # Truncate the summary to the target word count
                summarized_text = ' '.join(summarized_text.split()[:target_word_count])
            
            return summarized_text
        else:
            st.error(f"Failed to generate a summary. Please try again later.")
            return ""
    except Exception as e:
        st.error(f"An error occurred while summarizing: {str(e)}")
        return ""

run()

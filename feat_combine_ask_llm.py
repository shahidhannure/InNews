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
import PyPDF2
from docx import Document
import textract
import os
import openai
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceInstructEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from htmlTemplates import css, bot_template, user_template
from langchain.llms import HuggingFaceHub

nltk.download('punkt')
nltk.download('stopwords')

load_dotenv()

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
if not os.path.exists("uploads"):
    os.makedirs("uploads")


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

def summarize_youtube_video_openai(youtube_url):
    transcript = fetch_youtube_transcript(youtube_url)

    if isinstance(transcript, list):
        # Concatenate the text from each entry in the transcript
        full_text = " ".join(entry['text'] for entry in transcript)

        # Display initial output (transcription)
        st.subheader("YouTube Video Transcription:")
        st.write(full_text)

        # Generate summary using your summarization function
        summary = summarize_with_openai(full_text)
        return summary
    else:
        return transcript

def summarize_file_content(file_path):
    file_extension = file_path.split('.')[-1].lower()

    if file_extension == 'pdf':
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ''
            for page_number in range(len(pdf_reader.pages)):
                text += pdf_reader.pages[page_number].extract_text()
    elif file_extension == 'docx':
        doc = Document(file_path)
        text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    elif file_extension == 'txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
    else:
        return "Unsupported file format. Please upload a PDF, DOCX, or TXT file."

    summarized_text = summarize_text_with_api(text)
    return summarized_text


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
    # Initialize session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
   # User profile handling
    user_id = st.text_input("Enter your username")

    if user_id:
        category = ['--Select--', 'Trending🔥 News', 'Favourite💙 Topics', 'Search🔍 Topic', 'Get Summary','View Bookmarks','Youtube link','File Summary','Chat with PDF']
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
            summarization_model = st.radio("Select Summarization Model", ["Hugging Face", "OpenAI"])

            if st.button("Get Summary") and user_input.strip():
                if summarization_model == "Hugging Face":
                    summarized_text = summarize_text_with_api(user_input)
                else:  # OpenAI
                    summarized_text = summarize_with_openai(user_input)

                if summarized_text:
                    st.subheader("Summarized Text:")
                    st.write(summarized_text)
                else:
                    st.error("Failed to generate a summary. Please try again later.")
            



        elif cat_op == category[5]:
            view_bookmarked_articles(user_id)
            
        elif cat_op == category[6]:  # Corrected to number 6
            youtube_url = st.text_input("Enter YouTube Video URL")
            summarization_model = st.radio("Select Summarization Model", ["Hugging Face", "OpenAI"])
        
            if st.button("Get Transcription"):
                if youtube_url:
                    st.info("Fetching transcription... This may take a moment.")
                    if summarization_model == "Hugging Face":
                        video_summary = summarize_youtube_video(youtube_url)
                
                    else:
                        video_summary = summarize_youtube_video_openai(youtube_url)
                    
                    if video_summary:
                        st.subheader("YouTube Video Summary:")
                        st.write(video_summary)
                    else:
                        st.error("Failed to generate a summary. Please check the YouTube Video URL and try again.")
                else:
                    st.warning("Please enter a valid YouTube Video URL.")
        elif cat_op == category[7]:  # Option for summarizing uploaded files
            uploaded_file = st.file_uploader("Upload a file (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"])

            if uploaded_file is not None:
                file_path = os.path.join("uploads", uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.read())  # Use read() instead of getvalue()

                st.success(f"File uploaded successfully: {uploaded_file.name}")

                if st.button("Get Summary"):
                    summarized_text = summarize_file_content(file_path)
                    if summarized_text:
                        st.subheader("Summarized Text:")
                        st.write(summarized_text)
                    else:
                        st.error("Failed to generate a summary. Please try again later.")

        elif cat_op == category[8]:
            # Code for Chat with PDFs
            st.write("Upload PDF files to start chatting.")
            pdf_files = st.file_uploader("Upload PDF Files", type=["pdf"], accept_multiple_files=True)

            if st.button("Start Chatting") and pdf_files:
                with st.spinner("Processing"):
                    process_pdfs(pdf_files)

            if st.session_state.conversation:
                st.subheader("Chat with PDFs")
                user_question = st.text_input("You: ")

                if st.button("Send"):
                    response = st.session_state.conversation({'question': user_question})
                    st.session_state.chat_history = response['chat_history']

                    for i, message in enumerate(st.session_state.chat_history):
                        if i % 2 == 0:
                            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
                        else:
                            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.error("Category not recognized. Please select a valid category.")
    else:
        st.warning("Please enter a username.")



def view_bookmarked_articles(user_id):
    st.subheader("Saved Bookmarks")
    bookmarks = get_user_bookmarks(user_id)
    if not bookmarks:
        st.write("You haven't saved any bookmarks.")
    else:
        st.write("Your bookmarked articles:")
        for bookmark in bookmarks:
            st.markdown(f"- {bookmark}")

def summarize_text_with_api(input_text):
    try:
        api_url = "https://api-inference.huggingface.co/models/shahidhannure/finetune-large-cnn"
        headers = {"Authorization": "Bearer "}  # Replace with your Hugging Face API key

        # Adjust max_length dynamically based on the length of the input text
        max_length = len(input_text) // 3
        payload = {"inputs": input_text, "options": {"task": "summarization", "max_length": 1000, "min_length": 1}}

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
            return response_data["generated_text"]
        else:
            st.error(f"Failed to generate a summary. Please try again later.")
            return ""
    except Exception as e:
        st.error(f"An error occurred while summarizing: {str(e)}")
        return ""


def summarize_with_openai(input_text):
    try:
        openai.api_key = ''
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",  # Specify the model name
            messages=[
                {"role": "system", "content": "Instruct"},
                {"role": "user", "content": input_text}
            ],
            max_tokens=800,  # Adjust based on your needs
            temperature=0,
            top_p=1,
            presence_penalty=0,
            frequency_penalty=0
        )

        return response.choices[0].message["content"].strip()
    except Exception as e:
        print(f"An error occurred while summarizing with OpenAI GPT-3.5: {str(e)}")
        return ""

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def process_pdfs(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PyPDF2.PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()

    # Get text chunks
    text_chunks = get_text_chunks(text)

    # Create vector store
    vectorstore = get_vectorstore(text_chunks)

    # Create conversation chain
    st.session_state.conversation = get_conversation_chain(vectorstore)

def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks


def get_vectorstore(text_chunks):
    embeddings = OpenAIEmbeddings()
    # embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore


def get_conversation_chain(vectorstore):
    llm = ChatOpenAI()
    # llm = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature":0.5, "max_length":512})

    memory = ConversationBufferMemory(
        memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    #st.session_state.conversation = get_conversation_chain(vectorstore)
    return conversation_chain


def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)


run()


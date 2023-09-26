import streamlit as st
from PIL import Image
from bs4 import BeautifulSoup as soup
from urllib.request import urlopen
from newspaper import Article
import io
import nltk
import transformers
import requests
nltk.download('punkt')

nltk.download('punkt')
nltk.download('stopwords')

st.set_page_config(page_title='Scalable NewBite: A Summarised News📰 Portal', page_icon='./Meta/newspaper.ico')


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

    category = ['--Select--', 'Trending🔥 News', 'Favourite💙 Topics', 'Search🔍 Topic', 'Get Summary']
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
    elif cat_op == category[4]:
        user_input = st.text_area("Enter an article link or a long paragraph to summarize:")

        if st.button("Get Summary") and user_input.strip():
            summarized_text = summarize_text_with_api(user_input)
            
            if summarized_text:
                st.subheader("Summarized Text:")
                st.write(summarized_text)
            else:
                st.error("Failed to generate a summary. Please try again later.")
def summarize_text_with_api(input_text):
    try:
        api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        headers = {"Authorization": "Bearer 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"}  # Replace with your Hugging Face API key
        payload = {"inputs": input_text, "options": {"task": "summarization", "max_length": 300, "min_length": 150}}
        
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

run()

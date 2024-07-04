import streamlit as st
import os
from pytube import YouTube
from pytube.exceptions import VideoUnavailable

def download_youtube_content(url, output_path="."):
    try:
        yt = YouTube(url)
        video = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        
        if not video:
            return "No suitable video stream found."
        
        output_file = video.download(output_path)
        return f"Downloaded: {os.path.basename(output_file)}"

    except VideoUnavailable:
        return "This video is unavailable."
    except Exception as e:
        return f"An error occurred: {str(e)}"

st.title('YouTube Video Downloader')

url = st.text_input('Enter YouTube URL:')
output_path = st.text_input('Enter output path:', value='/home/god/Videos')

if st.button('Download'):
    if url:
        with st.spinner('Downloading...'):
            result = download_youtube_content(url, output_path)
        st.write(result)
    else:
        st.error('Please enter a YouTube URL')

st.markdown("""
### How to use:
1. Enter the YouTube video URL
2. (Optional) Change the output path
3. Click the 'Download' button
4. Wait for the download to complete
""")
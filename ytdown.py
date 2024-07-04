import streamlit as st
import yt_dlp
import os
from pathlib import Path
from threading import Thread
from queue import Queue

def get_available_formats(url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info['formats']
        # Filter for formats with both video and audio, or video-only formats
        video_formats = [f for f in formats if f.get('vcodec', 'none') != 'none']
        # Sort by quality (assuming higher resolution is better quality)
        video_formats.sort(key=lambda f: f.get('height', 0), reverse=True)
        # Create a list of unique resolutions
        unique_resolutions = []
        seen_resolutions = set()
        for f in video_formats:
            resolution = f.get('height', 0)
            if resolution not in seen_resolutions:
                seen_resolutions.add(resolution)
                unique_resolutions.append((f['format_id'], f'{resolution}p - {f["ext"]}'))
        
        # Add audio-only MP3 option
        unique_resolutions.append(('bestaudio/best', 'Audio Only (MP3)'))
        
        return unique_resolutions

def download_video(url, format_id, progress_queue):
    download_path = str(Path.home() / "Downloads")
    ydl_opts = {
        'format': f'{format_id}+bestaudio/best' if format_id != 'bestaudio/best' else 'bestaudio/best',
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'progress_hooks': [lambda d: progress_queue.put(d)],
    }
    
    # If audio-only is selected, add postprocessing for MP3 conversion
    if format_id == 'bestaudio/best':
        ydl_opts.update({
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        progress_queue.put({'error': str(e)})

def update_progress(progress_queue, progress_bar):
    while True:
        d = progress_queue.get()
        if 'error' in d:
            st.error(f"An error occurred during download: {d['error']}")
            break
        if d['status'] == 'downloading':
            percent = d['_percent_str']
            try:
                progress_bar.progress(float(percent.strip('%').strip()) / 100)
            except ValueError:
                pass
        elif d['status'] == 'finished':
            progress_bar.progress(1.0)
            st.success("Download completed!")
            break

st.title("Video Downloader")

url = st.text_input("Enter the video URL:")

if url:
    try:
        formats = get_available_formats(url)
        if not formats:
            st.warning("No suitable formats found. Falling back to best available format.")
            formats = [("best", "Best available quality")]
        
        format_dict = dict(formats)
        selected_format = st.selectbox("Choose format:", [f[1] for f in formats])
        selected_format_id = [k for k, v in format_dict.items() if v == selected_format][0]

        if st.button("Download"):
            progress_bar = st.progress(0)
            progress_queue = Queue()
            download_thread = Thread(target=download_video, args=(url, selected_format_id, progress_queue))
            download_thread.start()
            update_progress(progress_queue, progress_bar)
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
else:
    st.info("Please enter a valid URL to start.")

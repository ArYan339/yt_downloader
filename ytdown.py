import streamlit as st
import yt_dlp
import tempfile
import os
import io

def get_available_formats(url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            formats = info['formats']
            video_formats = [f for f in formats if f.get('vcodec', 'none') != 'none']
            video_formats.sort(key=lambda f: f.get('height', 0), reverse=True)
            unique_resolutions = []
            seen_resolutions = set()
            for f in video_formats:
                resolution = f.get('height', 0)
                if resolution not in seen_resolutions:
                    seen_resolutions.add(resolution)
                    unique_resolutions.append((f['format_id'], f'{resolution}p - {f["ext"]}'))
            
            unique_resolutions.append(('bestaudio/best', 'Audio Only (MP3)'))
            
            return unique_resolutions
        except Exception as e:
            st.error(f"Error fetching video information: {str(e)}")
            return []

def download_video(url, format_id, progress_bar):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                'format': f'{format_id}+bestaudio/best' if format_id != 'bestaudio/best' else 'bestaudio/best',
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'progress_hooks': [lambda d: update_progress(d, progress_bar)],
            }
            
            if format_id == 'bestaudio/best':
                ydl_opts.update({
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            downloaded_files = os.listdir(temp_dir)
            if downloaded_files:
                file_path = os.path.join(temp_dir, downloaded_files[0])
                with open(file_path, "rb") as file:
                    return io.BytesIO(file.read()), os.path.basename(file_path)
    except Exception as e:
        st.error(f"Error during download: {str(e)}")
        st.stop()
    
    return None, None

def update_progress(d, progress_bar):
    if d['status'] == 'downloading':
        percent = d['_percent_str']
        try:
            progress_bar.progress(float(percent.strip('%').strip()) / 100)
        except ValueError:
            pass
    elif d['status'] == 'finished':
        progress_bar.progress(1.0)

st.set_page_config(page_title="Video Downloader", page_icon="🎥")
st.title("Video Downloader")

url = st.text_input("Enter the video URL:")

if url:
    formats = get_available_formats(url)
    if not formats:
        st.warning("No suitable formats found or unable to fetch video information.")
    else:
        format_dict = dict(formats)
        selected_format = st.selectbox("Choose format:", [f[1] for f in formats])
        selected_format_id = [k for k, v in format_dict.items() if v == selected_format][0]

        if st.button("Download"):
            try:
                progress_bar = st.progress(0)
                file_content, file_name = download_video(url, selected_format_id, progress_bar)
                if file_content and file_name:
                    st.success("Download completed!")
                    st.download_button(
                        label="Click here to download",
                        data=file_content,
                        file_name=file_name,
                        mime="application/octet-stream"
                    )
                else:
                    st.error("Failed to download the file.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
else:
    st.info("Please enter a valid URL to start.")

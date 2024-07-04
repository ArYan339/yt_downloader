import streamlit as st
import yt_dlp
import os
import tempfile
import logging
from pathlib import Path
import signal
from contextlib import contextmanager
import time
import sys

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def get_available_formats(url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
        logger.error(f"Error in get_available_formats: {str(e)}")
        raise

def download_video(url, format_id, progress_bar):
    with tempfile.TemporaryDirectory() as temp_dir:
        ydl_opts = {
            'format': f'{format_id}+bestaudio/best' if format_id != 'bestaudio/best' else 'bestaudio/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: update_progress(d, progress_bar)],
            'verbose': True,
        }
        
        if format_id == 'bestaudio/best':
            ydl_opts.update({
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        
        try:
            with time_limit(300):  # 5 minutes timeout
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            
            # After successful download, move the file to the user's download directory
            download_path = str(Path.home() / "Downloads")
            os.makedirs(download_path, exist_ok=True)
            files_moved = False
            for filename in os.listdir(temp_dir):
                src = os.path.join(temp_dir, filename)
                dst = os.path.join(download_path, filename)
                os.rename(src, dst)
                files_moved = True
                logger.info(f"File moved to: {dst}")
            
            if not files_moved:
                raise Exception("No files were downloaded")
            
            return True
        except TimeoutException:
            logger.error("Download timed out")
            raise
        except Exception as e:
            logger.error(f"Error in download_video: {str(e)}")
            logger.error(f"Python version: {sys.version}")
            logger.error(f"yt-dlp version: {yt_dlp.version.__version__}")
            raise

def update_progress(d, progress_bar):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%')
        try:
            progress = float(percent.strip('%')) / 100
            progress_bar.progress(min(progress, 1.0))
        except ValueError:
            pass
    elif d['status'] == 'finished':
        progress_bar.progress(1.0)

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
            try:
                success = download_video(url, selected_format_id, progress_bar)
                if success:
                    st.success("Download completed!")
                else:
                    st.error("Download failed. Please try again.")
            except TimeoutException:
                st.error("Download timed out. Please try again or choose a different format.")
            except Exception as e:
                st.error(f"Download failed: {str(e)}")
                logger.exception("Detailed error information:")
    except Exception as e:
        logger.exception(f"An error occurred:")
        st.error(f"An error occurred: {str(e)}")
else:
    st.info("Please enter a valid URL to start.")

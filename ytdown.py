import streamlit as st
import yt_dlp
import os
import tempfile
import logging
from pathlib import Path
import threading
import time
import sys
import traceback
import requests
from urllib.error import HTTPError

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def download_video(url, format_id, progress_bar, result, status_placeholder):
    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            status_placeholder.text(f"Download attempt {attempt + 1} of {max_retries}")
            with tempfile.TemporaryDirectory() as temp_dir:
                ydl_opts = {
                    'format': f'{format_id}+bestaudio/best' if format_id != 'bestaudio/best' else 'bestaudio/best',
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'progress_hooks': [lambda d: update_progress(d, progress_bar, status_placeholder)],
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
                
                result['success'] = True
                return  # Successfully downloaded and moved the file

        except (requests.exceptions.ConnectionError, HTTPError) as e:
            logger.error(f"Connection error on attempt {attempt + 1}: {str(e)}")
            status_placeholder.text(f"Connection error. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        except OSError as e:
            if e.errno == 32:  # Broken pipe
                logger.error(f"Broken pipe error on attempt {attempt + 1}: {str(e)}")
                status_placeholder.text(f"Download interrupted. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"OS error on attempt {attempt + 1}: {str(e)}")
                result['success'] = False
                result['error'] = f"OS error: {str(e)}"
                return
        except Exception as e:
            logger.error(f"Error in download_video on attempt {attempt + 1}: {str(e)}")
            logger.error(traceback.format_exc())
            result['success'] = False
            result['error'] = str(e)
            return

    # If we've exhausted all retries
    result['success'] = False
    result['error'] = "Download failed after multiple attempts. Please try again later or choose a different format."

def update_progress(d, progress_bar, status_placeholder):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%')
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        status_placeholder.text(f"Downloading: {percent} complete, Speed: {speed}, ETA: {eta}")
        try:
            progress = float(percent.strip('%')) / 100
            progress_bar.progress(min(progress, 1.0))
        except ValueError:
            pass
    elif d['status'] == 'finished':
        progress_bar.progress(1.0)
        status_placeholder.text("Download finished. Moving file...")

def main():
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
                status_placeholder = st.empty()
                result = {'success': False, 'error': None}
                
                # Start download in a separate thread
                download_thread = threading.Thread(target=download_video, args=(url, selected_format_id, progress_bar, result, status_placeholder))
                download_thread.start()
                
                # Wait for the download to complete or timeout
                timeout = 600  # 10 minutes
                start_time = time.time()
                while download_thread.is_alive():
                    if time.time() - start_time > timeout:
                        status_placeholder.text("Download timed out. Please try again or choose a different format.")
                        break
                    time.sleep(1)
                
                if result['success']:
                    st.success("Download completed!")
                elif result['error']:
                    st.error(f"Download failed: {result['error']}")
                else:
                    st.error("Download failed due to unknown reasons.")
        except Exception as e:
            logger.exception("An error occurred:")
            st.error(f"An error occurred: {str(e)}")
    else:
        st.info("Please enter a valid URL to start.")

if __name__ == "__main__":
    main()

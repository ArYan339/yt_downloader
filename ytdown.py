import streamlit as st
import subprocess
import tempfile
import os
import base64
import io

def download_video(url, progress_bar, status_area):
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')
            command = [
                'yt-dlp',
                '-f', 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '-o', output_template,
                '--newline',
                url
            ]
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            
            for line in process.stdout:
                if '[download]' in line and '%' in line:
                    try:
                        percent = float(line.split('%')[0].split()[-1])
                        progress_bar.progress(percent / 100)
                    except ValueError:
                        pass
            
            process.wait()
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command)
            
            downloaded_files = [f for f in os.listdir(temp_dir) if f.endswith(('.mp4', '.webm', '.mkv'))]
            
            if not downloaded_files:
                raise FileNotFoundError(f"No video files found in {temp_dir}")
            
            file_path = os.path.join(temp_dir, downloaded_files[0])
            with open(file_path, 'rb') as f:
                file_content = f.read()
            return io.BytesIO(file_content), downloaded_files[0]
        
        except subprocess.CalledProcessError as e:
            status_area.error(f"An error occurred during download: {str(e)}")
            return None, None
        except Exception as e:
            status_area.error(f"An unexpected error occurred: {str(e)}")
            return None, None

st.title("Video Downloader")

url = st.text_input("Enter the video URL:")

if st.button("Download"):
    if url:
        progress_bar = st.progress(0)
        status_area = st.empty()
        status_area.text("Downloading... Please wait.")
        
        file_content, file_name = download_video(url, progress_bar, status_area)
        
        if file_content and file_name:
            status_area.success("Download completed!")
            
            # Provide download button
            st.download_button(
                label="Download Video",
                data=file_content,
                file_name=file_name,
                mime="video/mp4"
            )
            
            # Clean up
            status_area.empty()
            progress_bar.empty()
    else:
        st.warning("Please enter a URL before downloading.")
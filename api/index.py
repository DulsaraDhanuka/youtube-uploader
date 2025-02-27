from flask import Flask, request, Response
import requests
from werkzeug.http import parse_options_header
from urllib.parse import urlparse
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
import io
import google_auth_oauthlib.flow
import googleapiclient.discovery
import json

load_dotenv(".env")

app = Flask(__name__)

UPLOAD_FOLDER = 'youtube-uploads'
scopes = ["https://www.googleapis.com/auth/youtubepartner", "https://www.googleapis.com/auth/youtube.force-ssl", "https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/youtube.upload"]
api_service_name = "youtube"
api_version = "v3"

def get_authenticated_service():
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_config(json.loads(os.environ["CLIENT_CONFIG"]), scopes)
    credentials = flow.run_local_server(port=0)
    return googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

@app.route('/')
def home():
    return 'Hello, World123!'

@app.route('/download_video', methods=['GET'])
def download_video():
    # Get the URL from the query parameters
    video_url = request.args.get('url')
    if not video_url:
        return 'Error: Missing URL parameter. Please provide a URL.', 400

    try:
        # Stream the request to handle large files efficiently
        video_file_response = requests.get(video_url, stream=True)
        video_file_response.raw.decode_content = True
        video_file_response.raise_for_status()  # Raise exception for HTTP errors
    except requests.exceptions.RequestException as e:
        return f'Error fetching the URL: {str(e)}', 500

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    youtube = get_authenticated_service()

    # Extract filename from Content-Disposition header or URL
    content_disposition = video_file_response.headers.get('Content-Disposition', '')
    _, params = parse_options_header(content_disposition)
    filename = params.get('filename', '')

    if not filename:
        # Fallback to extracting filename from URL
        path = urlparse(video_url).path
        filename = os.path.basename(path) or 'downloaded_file'

    youtube_request_body = {
        'snippet': {
            'title': filename, # Use filename as title
            'description': 'Uploaded via OpenHands'
        },
        'status': {
            'privacyStatus': 'private' # Or 'public', 'unlisted'
        }
    }

    media = googleapiclient.http.MediaIoBaseUpload(io.BytesIO(video_file_response.content), mimetype='video/*')

    try:
        youtube_request = youtube.videos().insert(
            part='snippet,status',
            body=youtube_request_body,
            media_body=media
        )
        youtube_response = youtube_request.execute()
        print(f"Video {filename} uploaded. Video ID: {youtube_response['id']}") # Log video ID
    except Exception as e:
        print(f"Error uploading {filename}: {e}") # Log errors

    headers = {
        'Content-Type': 'text/json',
    }

    return Response(
        response="true",
        headers=headers
    )

if __name__ == "__main__":
    app.run()

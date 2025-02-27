from flask import Flask, request, Response, url_for, session, redirect
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
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or os.urandom(24)

UPLOAD_FOLDER = 'youtube-uploads'
api_service_name = "youtube"
api_version = "v3"

# This sets up a configuration for the OAuth flow
oauth_flow = google_auth_oauthlib.flow.Flow.from_client_config(
    json.loads(os.environ["CLIENT_CONFIG"]),
    # scopes define what APIs you want to access on behave of the user once authenticated
    scopes=["https://www.googleapis.com/auth/youtubepartner", "https://www.googleapis.com/auth/youtube.force-ssl", "https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/youtube.upload"]
)

@app.route('/')
def home():
    return 'Hello, World123!'

# This is entrypoint of the login page. It will redirect to the Google login service located at the
# `authorization_url`. The `redirect_uri` is actually the URI which the Google login service will use to
# redirect back to this app.
@app.route('/signin')
def signin():
    # We rewrite the URL from http to https because inside the Replit App http is used,
    # but externally it's accessed via https, and the redirect_uri has to match that
    oauth_flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_url, state = oauth_flow.authorization_url()
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    if not session['state'] == request.args['state']:
        return Response("Invalid state parameter.", 401)
    oauth_flow.fetch_token(authorization_response=request.url.replace('http:', 'https:'))
    session['access_token'] = oauth_flow.credentials.token
    return redirect("/")

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
    youtube = googleapiclient.discovery.build(api_service_name, api_version, credentials=oauth_flow.credentials)

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
    app.run(port=5000)

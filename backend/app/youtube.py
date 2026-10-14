"""YouTube upload adapter. Uploads are always PRIVATE; public publishing is intentionally absent."""
import os
from pathlib import Path

YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def upload_video_private(file_path: str, title: str, description: str, tags: list[str] | None = None) -> dict[str, str]:
    client_id = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()
    if not all((client_id, client_secret, refresh_token)):
        raise RuntimeError("YouTube OAuth is not configured")
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError("Video file does not exist")
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[YOUTUBE_SCOPE],
    )
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": (tags or [])[:500],
                "categoryId": "27",
            },
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(str(path), mimetype="video/mp4", resumable=True),
    )
    result = request.execute()
    return {"video_id": str(result["id"]), "privacy_status": "private"}

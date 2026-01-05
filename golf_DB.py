# 파일명: golf_DB.py
from googleapiclient.discovery import build
import sqlite3
import datetime
import sys
import io
import os  # 👈 [필수] 경로 추적 탐정

# 한글 깨짐 방지
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# 👇 API 키 입력
API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    raise ValueError("🚨 API 키가 없습니다! 환경변수를 확인해주세요.")
youtube = build('youtube', 'v3', developerKey=API_KEY)

# ------------------------------------------------------------------
# 🧭 [절대 경로 마법] "나는 지금 어디에 있는가?"
# ------------------------------------------------------------------
# 1. 지금 이 파일(golf_DB.py)이 있는 폴더 위치를 알아냅니다.
current_folder = os.path.dirname(os.path.abspath(__file__))

# 2. 그 폴더 안에 있는 'golf.db'를 지목합니다.
db_path = os.path.join(current_folder, 'golf.db')

print(f"📂 [주방장] DB 저장 위치: {db_path}")
# ------------------------------------------------------------------

# DB 연결 (무조건 위에서 찾은 경로로 연결)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 초기화 (테이블 삭제 후 재생성)
cursor.execute("DROP TABLE IF EXISTS trending_videos")

cursor.execute('''
    CREATE TABLE trending_videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        channel TEXT,
        view_count INTEGER,
        like_count INTEGER,
        comment_count INTEGER,
        publish_date TEXT,
        tags TEXT,
        thumbnail_url TEXT,
        video_url TEXT,
        scrapped_date TEXT
    )
''')
conn.commit()

def save_trending_videos_to_db():
    print("🔥 데이터 수집 시작...")
    
    try:
        request = youtube.videos().list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode="KR",
            videoCategoryId="17", 
            maxResults=10
        )
        response = request.execute()

        today = datetime.datetime.now().strftime('%Y-%m-%d')
        count = 0

        for item in response['items']:
            snippet = item['snippet']
            stats = item['statistics']

            title = snippet['title']
            channel = snippet['channelTitle']
            vid_id = item['id']
            link = f"https://www.youtube.com/watch?v={vid_id}"
            thumbnail = snippet['thumbnails']['medium']['url']
            
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            comments = int(stats.get('commentCount', 0))
            pub_date = snippet.get('publishedAt', '')
            tags = ",".join(snippet.get('tags', []))

            cursor.execute('''
                INSERT INTO trending_videos 
                (title, channel, view_count, like_count, comment_count, publish_date, tags, thumbnail_url, video_url, scrapped_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, channel, views, likes, comments, pub_date, tags, thumbnail, link, today))
            count += 1

        conn.commit()
        print("-" * 50)
        print(f"✅ [주방장] 요리 끝! {count}개 영상 저장 완료.")
        print("-" * 50)

    except Exception as e:
        print("에러 발생:", e)
    finally:
        conn.close()

if __name__ == "__main__":

    save_trending_videos_to_db()

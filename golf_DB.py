import google.generativeai as genai
from googleapiclient.discovery import build
import sqlite3
import datetime
import sys
import io
import os
import time # 👈 AI 과부하 방지용 휴식

# 한글 깨짐 방지
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# ---------------------------------------------------------
# 🔑 비밀키 가져오기 (Youtube + Gemini)
# ---------------------------------------------------------

# 👇 [수정됨] 여기에 프로님의 진짜 키를 붙여넣으세요! (따옴표 필수)
# 🚨 주의: 이 상태로 깃허브에 올리면 안 됩니다! 로컬 실행 끝나면 꼭 되돌리세요!
# 👇 다시 이렇게 안전한 상태로 돌려놓고 저장하세요!
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 👇 원래 코드는 잠시 주석(#) 처리 해둡니다. (나중에 복구용)
# YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
# GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not YOUTUBE_API_KEY or YOUTUBE_API_KEY.startswith("여기에"):
    raise ValueError("🚨 유튜브 API 키를 입력해주세요!")
if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("여기에"):
    raise ValueError("🚨 제미나이 API 키를 입력해주세요!")

# 서비스 연결
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # 빠르고 똑똑한 모델

# ---------------------------------------------------------
# 🧭 경로 설정
# ---------------------------------------------------------
current_folder = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_folder, 'golf.db')

# DB 연결 및 초기화
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ⚠️ 테이블 싹 밀고 새로 만듭니다 (ai_summary 컬럼 추가됨!)
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
        scrapped_date TEXT,
        ai_summary TEXT  -- 👈 여기에 AI 요약이 들어갑니다
    )
''')
conn.commit()

def analyze_with_ai(title, channel, tags):
    """제미나이에게 분석을 요청하는 함수"""
    try:
        prompt = f"""
        너는 골프 전문 데이터 분석가야. 아래 유튜브 영상 정보를 보고 
        '이 영상이 왜 인기 있는지'를 분석해서 한국어로 3줄 요약해줘.
        
        [영상 정보]
        - 제목: {title}
        - 채널: {channel}
        - 태그: {tags}
        
        [답변 형식]
        💡 핵심 포인트: (내용)
        🎯 타겟 시청자: (내용)
        🔥 벤치마킹 팁: (내용)
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 분석 실패: {e}"

def save_trending_videos_to_db():
    print("🔥 데이터 수집 및 AI 분석 시작...")
    
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

            # 🧠 [AI 단계] 제미나이에게 물어보기
            print(f"🤖 AI가 '{title}' 분석 중...")
            ai_summary = analyze_with_ai(title, channel, tags)
            time.sleep(2) # AI도 숨 쉴 틈을 줍니다 (에러 방지)

            cursor.execute('''
                INSERT INTO trending_videos 
                (title, channel, view_count, like_count, comment_count, publish_date, tags, thumbnail_url, video_url, scrapped_date, ai_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, channel, views, likes, comments, pub_date, tags, thumbnail, link, today, ai_summary))
            count += 1

        conn.commit()
        print("-" * 50)
        print(f"✅ 수집 및 AI 분석 완료! {count}개 저장됨.")
        print("-" * 50)

    except Exception as e:
        print("에러 발생:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    save_trending_videos_to_db()
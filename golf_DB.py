import google.generativeai as genai
from googleapiclient.discovery import build
import sqlite3
import datetime
import sys
import io
import os
import time

# 한글 깨짐 방지
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# ---------------------------------------------------------
# 🔑 비밀키 가져오기
# ---------------------------------------------------------
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not YOUTUBE_API_KEY:
    raise ValueError("🚨 유튜브 API 키가 없습니다!")
if not GEMINI_API_KEY:
    raise ValueError("🚨 제미나이 API 키가 없습니다! Secrets를 확인하세요.")

# 서비스 연결
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# ---------------------------------------------------------
# 🤖 AI 모델 자동 선택 (여기가 핵심!)
# ---------------------------------------------------------
def get_working_model():
    """사용 가능한 모델을 자동으로 찾아서 반환합니다."""
    print("🤖 사용 가능한 AI 모델 탐색 중...")
    try:
        # 우선순위: 최신 플래시 -> 프로 -> 아무거나
        preferred_order = ['gemini-1.5-flash', 'gemini-pro']
        
        # API가 제공하는 모든 모델 리스트 가져오기
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # 모델 이름에서 'models/' 제거 (예: models/gemini-pro -> gemini-pro)
                clean_name = m.name.replace('models/', '')
                available_models.append(clean_name)
        
        # 1. 우리가 원하는 모델이 있는지 확인
        for pref in preferred_order:
            if pref in available_models:
                print(f"✅ 최적 모델 선택됨: {pref}")
                return genai.GenerativeModel(pref)
        
        # 2. 없으면 Gemini 들어간 아무거나 선택
        for m in available_models:
            if 'gemini' in m:
                print(f"⚠️ 대체 모델 선택됨: {m}")
                return genai.GenerativeModel(m)
                
        # 3. 진짜 아무것도 없으면 기본값 강제 시도
        return genai.GenerativeModel('gemini-pro')
        
    except Exception as e:
        print(f"⚠️ 모델 탐색 실패 ({e}), 기본값(gemini-pro)으로 시도합니다.")
        return genai.GenerativeModel('gemini-pro')

# 자동으로 찾은 모델 장착!
model = get_working_model()

# ---------------------------------------------------------
# 🧭 경로 및 DB 설정
# ---------------------------------------------------------
current_folder = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_folder, 'golf.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 테이블 초기화
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
        ai_summary TEXT
    )
''')
conn.commit()

def analyze_with_ai(title, channel, tags):
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
            
            # 데이터 추출
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

            # AI 분석
            print(f"🤖 AI가 '{title}' 분석 중...")
            ai_summary = analyze_with_ai(title, channel, tags)
            time.sleep(2)

            cursor.execute('''
                INSERT INTO trending_videos 
                (title, channel, view_count, like_count, comment_count, publish_date, tags, thumbnail_url, video_url, scrapped_date, ai_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, channel, views, likes, comments, pub_date, tags, thumbnail, link, today, ai_summary))
            count += 1

        conn.commit()
        print(f"✅ 완료! {count}개 저장됨.")

    except Exception as e:
        print("에러 발생:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    save_trending_videos_to_db()

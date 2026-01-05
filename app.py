import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime, timezone
from dateutil import parser

# ------------------------------------------------------------------
# 1. 🥇 페이지 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="Insight Golf Pro", page_icon="⛳", layout="wide")

# ------------------------------------------------------------------
# 2. 🧭 경로 설정
# ------------------------------------------------------------------
current_folder = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_folder, 'golf.db')

# ------------------------------------------------------------------
# 3. 🎨 디자인 (CSS)
# ------------------------------------------------------------------
def apply_custom_style():
    st.markdown("""
        <style>
        .stApp { background-color: #F5F7F9; }
        .video-card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        h1 { color: #1E1E1E; font-family: sans-serif; font-weight: 700; }
        [data-testid="stMetricValue"] { font-size: 1.5rem !important; color: #FF4B4B; }
        /* 비디오 플레이어 여백 조정 */
        .stVideo { margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

apply_custom_style()

# ------------------------------------------------------------------
# 4. 🧠 데이터 가공 (화력 계산)
# ------------------------------------------------------------------
def process_data(df):
    now = datetime.now(timezone.utc)
    def calc_firepower(row):
        try:
            pub = parser.parse(row['publish_date'])
            diff = (now - pub).total_seconds() / 3600
            if diff <= 0: return 0
            return int(row['view_count'] / diff)
        except: return 0

    df['firepower'] = df.apply(calc_firepower, axis=1)
    
    def calc_time_txt(row):
        try:
            pub = parser.parse(row['publish_date'])
            diff = (now - pub).total_seconds() / 3600
            if diff < 24: return f"{int(diff)}시간 전"
            else: return f"{int(diff/24)}일 전"
        except: return "-"
    df['time_txt'] = df.apply(calc_time_txt, axis=1)
    return df

# ------------------------------------------------------------------
# 5. 🖥️ 메인 로직
# ------------------------------------------------------------------
st.title("⛳ Insight Golf: 트렌드 대시보드")

# DB 읽기
if not os.path.exists(db_path):
    st.error("🚨 DB 파일이 없습니다! 'golf_DB.py'를 먼저 실행해주세요.")
    df = pd.DataFrame() # 빈 데이터프레임 생성 (에러 방지)
else:
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql("SELECT * FROM trending_videos ORDER BY view_count DESC", conn)
        df = process_data(df) # 화력 계산
    except Exception as e:
        st.error(f"DB 오류: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()

# ------------------------------------------------------------------
# 6. 👈 사이드바 (관리자 메뉴 + 화력 그래프)
# ------------------------------------------------------------------
with st.sidebar:
    st.header("관리자 메뉴")
    st.info(f"📂 DB 연결 중...")
    
    if st.button("🔄 데이터 새로고침"):
        st.rerun()
    
    st.divider()
    
    # 📊 [요청하신 기능] 사이드바에 화력 그래프 숨겨두기
    if not df.empty:
        st.subheader("📊 데이터 시각화")
        # 'expander'가 바로 "누르면 열리는 버튼"입니다!
        with st.expander("🔥 화력 랭킹 그래프 보기", expanded=False):
            st.caption("지금 가장 뜨거운 영상 TOP 10")
            chart_df = df.sort_values(by='firepower', ascending=False).head(10)
            st.bar_chart(chart_df.set_index('title')['firepower'], color="#FF4B4B")
    else:
        st.warning("데이터가 없어서 그래프를 못 그립니다.")

# ------------------------------------------------------------------
# 7. 📺 메인 화면 (영상 재생 + 정보)
# ------------------------------------------------------------------
if not df.empty:
    # 검색 기능
    col_search, _ = st.columns([1, 2])
    with col_search:
        search_keyword = st.text_input("🔍 영상 검색", placeholder="제목, 채널명...")

    if search_keyword:
        df = df[df['title'].str.contains(search_keyword, case=False) | 
                df['channel'].str.contains(search_keyword, case=False)]
    
    st.caption(f"총 {len(df)}개의 영상")
    
    # 연관 키워드
    all_tags = []
    for t in df['tags']:
        if t: all_tags.extend(t.split(','))
    
    if all_tags:
        from collections import Counter
        cols = st.columns(6)
        for i, (tag, cnt) in enumerate(Counter(all_tags).most_common(6)):
            cols[i].button(f"#{tag}", disabled=True, key=f"btn_{i}")

    st.write("") 

    # 🎬 [요청하신 기능] 리스트 출력 (바로 재생)
    for index, row in df.iterrows():
        st.markdown('<div class="video-card">', unsafe_allow_html=True)
        
        # 왼쪽: 비디오 플레이어 (썸네일 대신 들어감!)
        # 오른쪽: 정보
        c1, c2 = st.columns([1.2, 2]) # 영상 크기를 조금 더 키움 (1.2)
        
        with c1:
            # 유튜브 바로 재생 기능
            if row['video_url']:
                st.video(row['video_url'])
        
        with c2:
            st.subheader(row['title'])
            st.caption(f"{row['channel']} • {row['time_txt']}")
            
            # 지표 표시
            m1, m2, m3 = st.columns(3)
            m1.metric("👁️ 조회수", f"{row['view_count']:,}")
            m2.metric("❤️ 좋아요", f"{row['like_count']:,}")
            m3.metric("🔥 화력", f"{row['firepower']:,}")
            
            # (영상 보기 버튼은 이제 필요 없어서 삭제했습니다)
        
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("데이터가 없습니다. 'golf_DB.py'를 실행해주세요.")
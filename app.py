import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime, timezone
from dateutil import parser

st.set_page_config(page_title="Insight Golf Pro", page_icon="⛳", layout="wide")

current_folder = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_folder, 'golf.db')

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
        .ai-box {
            background-color: #E8F5E9; /* 연한 초록색 배경 */
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #2E7D32;
            margin-top: 10px;
            font-size: 0.95rem;
            color: #1B5E20;
        }
        h1 { color: #1E1E1E; font-family: sans-serif; font-weight: 700; }
        [data-testid="stMetricValue"] { font-size: 1.5rem !important; color: #FF4B4B; }
        .stVideo { margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

apply_custom_style()

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

st.title("⛳ Insight Golf: AI 트렌드 분석기")

if not os.path.exists(db_path):
    st.error("🚨 DB 파일이 없습니다! 데이터를 수집해주세요.")
    df = pd.DataFrame()
else:
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql("SELECT * FROM trending_videos ORDER BY view_count DESC", conn)
        # 데이터는 있는데 ai_summary 컬럼이 아직 없는 경우 에러 방지
        if 'ai_summary' not in df.columns:
             df['ai_summary'] = "🤖 다음 업데이트부터 AI 요약이 표시됩니다."
        df = process_data(df)
    except Exception as e:
        st.error(f"DB 오류: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()

with st.sidebar:
    st.header("관리자 메뉴")
    st.info("매일 아침 6시 자동 업데이트됨 🤖")
    
    # 깃허브 액션이 도니까 여기서 버튼은 이제 장식에 가깝지만 남겨둡니다.
    if st.button("🔄 데이터 새로고침"):
        st.rerun()
    
    st.divider()
    
    if not df.empty:
        st.subheader("📊 데이터 시각화")
        with st.expander("🔥 화력 랭킹 그래프", expanded=False):
            chart_df = df.sort_values(by='firepower', ascending=False).head(10)
            st.bar_chart(chart_df.set_index('title')['firepower'], color="#FF4B4B")

if not df.empty:
    col_search, _ = st.columns([1, 2])
    with col_search:
        search_keyword = st.text_input("🔍 영상 검색", placeholder="제목, 채널명...")

    if search_keyword:
        df = df[df['title'].str.contains(search_keyword, case=False) | 
                df['channel'].str.contains(search_keyword, case=False)]
    
    st.caption(f"총 {len(df)}개의 영상 분석 완료")
    
    all_tags = []
    for t in df['tags']:
        if t: all_tags.extend(t.split(','))
    
    if all_tags:
        from collections import Counter
        cols = st.columns(6)
        for i, (tag, cnt) in enumerate(Counter(all_tags).most_common(6)):
            cols[i].button(f"#{tag}", disabled=True, key=f"btn_{i}")

    st.write("") 

    for index, row in df.iterrows():
        st.markdown('<div class="video-card">', unsafe_allow_html=True)
        
        c1, c2 = st.columns([1.2, 2])
        
        with c1:
            if row['video_url']:
                st.video(row['video_url'])
        
        with c2:
            st.subheader(row['title'])
            st.caption(f"{row['channel']} • {row['time_txt']}")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("👁️ 조회수", f"{row['view_count']:,}")
            m2.metric("❤️ 좋아요", f"{row['like_count']:,}")
            m3.metric("🔥 화력", f"{row['firepower']:,}")
            
            # 👇 여기가 AI 요약 보여주는 부분!
            if row['ai_summary']:
                st.markdown(f"""
                <div class="ai-box">
                    <b>🤖 Gemini 분석 리포트</b><br>
                    {row['ai_summary'].replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("데이터가 없습니다.")

import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime
from google import genai
from google.genai import types
from supabase import create_client

# ----------------------------------------------------
# 1. Initial Configuration and Secret Loading
# ----------------------------------------------------
st.set_page_config(page_title="AI Latest News Collector", page_icon="📰", layout="wide")

# API & DB Connections (using st.secrets)
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Client Initialization
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📰 AI Latest News Search & Auto-Saver")
st.markdown("Enter a keyword, and Gemini will search Google for the latest 5 news articles, summarize them, and automatically save them to the database.")

# ----------------------------------------------------
# Tab Setup
# ----------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🔍 Search", "💾 Saved News", "📊 Statistical Analytics"])

# ==========================================
# Tab 1: Search & Save Logic
# ==========================================
with tab1:
    st.subheader("Search New Articles")
    
    with st.form("search_form"):
        keyword = st.text_input("Enter a keyword to search (e.g., Artificial Intelligence, Tesla, Economy, etc.):")
        submitted = st.form_submit_button("Search & Summarize 🚀")
        
    if submitted and keyword:
        with st.spinner(f"Searching and analyzing the latest news for '{keyword}'..."):
            try:
                # ----------------------------------------------------------------------------------
                # Prompt requesting exactly 5 articles with JSON formatting
                # ----------------------------------------------------------------------------------
                prompt = f"""
                Search Google for the top 5 latest news articles regarding '{keyword}'.
                Based on the search results, return ONLY a JSON array in the exact format below. Do NOT output markdown backticks (```) or any additional explanatory text.
                [
                    {{
                        "title": "Article Title",
                        "source": "News Publisher Name",
                        "news_date": "Publication Date (e.g., 2023-10-25)",
                        "url": "Original Article URL",
                        "summary": "3-line summary of the article"
                    }}
                ]
                Do NOT hallucinate or invent URLs.
                """
                # ----------------------------------------------------------------------------------
                
                # Gemini API Call (Temperature 0.0, Google Search Tool Enabled)
                response = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        tools=[{"google_search": {}}]
                    )
                )
                
                # JSON Text Extraction (handling potential markdown backticks)
                response_text = response.text
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                
                if json_match:
                    news_data = json.loads(json_match.group())
                    
                    # ----------------------------------------------------
                    # URL Anti-Hallucination Logic (Using Grounding Metadata)
                    # ----------------------------------------------------
                    real_links = {}
                    # Extract source information referenced by Google Search from grounding_metadata
                    if hasattr(response, 'candidates') and response.candidates:
                        grounding_metadata = response.candidates[0].grounding_metadata
                        if grounding_metadata and grounding_metadata.grounding_chunks:
                            for chunk in grounding_metadata.grounding_chunks:
                                if hasattr(chunk, 'web') and chunk.web:
                                    # Map article title and actual URL found in Google Search
                                    real_links[chunk.web.title] = chunk.web.uri
                    
                    # Verify and overwrite JSON URLs with confirmed real URLs
                    for item in news_data:
                        for real_title, real_url in real_links.items():
                            # Match titles flexibly in case LLM truncated the title
                            if item['title'].lower() in real_title.lower() or real_title.lower() in item['title'].lower():
                                # Overwrite only if it is a valid HTTP link and not an internal grounding redirect link
                                if real_url.startswith("http") and "grounding-api-redirect" not in real_url:
                                    item['url'] = real_url
                                break
                    # ----------------------------------------------------
                    
                    # Output to Screen and Save to Database
                    saved_count = 0
                    skipped_count = 0
                    
                    st.success("✨ Search completed successfully!")
                    
                    for idx, item in enumerate(news_data):
                        # Display Card UI
                        with st.container():
                            st.markdown(f"### {idx+1}. [{item['title']}]({item['url']})")
                            st.caption(f"Source: {item['source']} | Date: {item['news_date']}")
                            st.write(f"**Summary:** {item['summary']}")
                            st.divider()
                        
                        # Save to Supabase DB
                        try:
                            db_data = {
                                "keyword": keyword,
                                "title": item['title'],
                                "source": item['source'],
                                "news_date": item['news_date'],
                                "url": item['url'],
                                "summary": item['summary']
                            }
                            supabase.table("news_history").insert(db_data).execute()
                            saved_count += 1
                        except Exception as e:
                            # Postgres code 23505 indicates Unique Violation
                            if '23505' in str(e) or 'duplicate key' in str(e).lower():
                                skipped_count += 1
                            else:
                                st.error(f"Database insertion error: {e}")
                    
                    st.toast(f"✅ Saved {saved_count} new articles! (Duplicates skipped: {skipped_count})", icon="🎉")
                else:
                    st.error("Failed to parse the data structure. Please try again.")
                    
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# ==========================================
# Tab 2: Saved News History
# ==========================================
with tab2:
    st.subheader("💾 Saved News History")
    
    # Retrieve data from DB (Latest first)
    response = supabase.table("news_history").select("*").order("created_at", desc=True).execute()
    data = response.data
    
    if data:
        df = pd.DataFrame(data)
        
        # Format Timestamp
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Search / Filtering Feature
        filter_text = st.text_input("🔍 Search within results (by Title or Keyword)")
        if filter_text:
            df = df[df['title'].str.contains(filter_text, case=False, na=False) | 
                    df['keyword'].str.contains(filter_text, case=False, na=False)]
        
        # Display DataFrame
        st.dataframe(
            df[['keyword', 'title', 'source', 'news_date', 'url', 'created_at']],
            use_container_width=True,
            hide_index=True
        )
        
        # Download CSV Button
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download Current Data as CSV",
            data=csv,
            file_name=f"news_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No articles saved yet. Try searching for news in Tab 1!")

# ==========================================
# Tab 3: Statistical Analytics Dashboard
# ==========================================
with tab3:
    st.subheader("📊 News Collection Statistics")
    
    if data: # Reusing data retrieved in Tab 2
        stat_df = pd.DataFrame(data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 📌 Articles Collected per Keyword")
            keyword_counts = stat_df['keyword'].value_counts()
            st.bar_chart(keyword_counts)
            
        with col2:
            st.markdown("##### 📅 Saved Articles by Date")
            # Extract YYYY-MM-DD from created_at
            stat_df['date_only'] = pd.to_datetime(stat_df['created_at']).dt.strftime('%Y-%m-%d')
            date_counts = stat_df['date_only'].value_counts().sort_index()
            st.line_chart(date_counts)
    else:
        st.info("Not enough data to display statistics.")

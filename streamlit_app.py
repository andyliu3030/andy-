import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 配置页面样式 ---
st.set_page_config(page_title="影像科工作量助手", page_icon="📊")
st.title("🏥 影像科工作量上报系统")

# --- 2. 连接 Google Sheets ---
# 在 Streamlit 部署时，我们会设置这部分的安全连接
sheet_url = st.secrets["public_gsheet_url"]

@st.cache_data(ttl=600) # 每 10 分钟缓存一次，减少读取压力
def load_data(url):
    # 将 Google Sheets 链接转换为 CSV 下载链接
    csv_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    return pd.read_csv(csv_url, skiprows=1)

try:
    df = load_data(sheet_url)
    # 转换日期列
    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
    
    # --- 3. 核心统计逻辑 ---
    now = datetime.now()
    offset = (3 - now.weekday())
    end_week = (now + timedelta(days=offset)).replace(hour=23, minute=59, second=59)
    start_week = (end_week - timedelta(days=6)).replace(hour=0, minute=0, second=0)

    # 筛选本周数据
    mask = (df.iloc[:, 0] >= start_week) & (df.iloc[:, 0] <= end_week)
    week_data = df.loc[mask]

    # --- 4. 渲染网页内容 ---
    st.subheader(f"📅 本周统计范围")
    st.write(f"从 **{start_week.strftime('%Y-%m-%d')}** 到 **{end_week.strftime('%Y-%m-%d')}**")

    if not week_data.empty:
        # 这里的列索引根据你的表格结构调整 (B=1, C=2...)
        ct_p = int(week_data.iloc[:, 1].sum())
        ct_s = int(week_data.iloc[:, 2].sum())
        dr_p = int(week_data.iloc[:, 3].sum())
        dr_s = int(week_data.iloc[:, 4].sum())
        
        pe_ts = int(week_data.iloc[:, 7].sum())
        pe_dr = int(week_data.iloc[:, 6].sum())
        pe_ct = int(week_data.iloc[:, 5].sum())

        report_text = f"""{start_week.strftime('%Y年%m月%d日')}至{end_week.strftime('%Y年%m月%d日')}影像科工作量：
CT：{ct_p}人，{ct_s}部位
DR：{dr_p}人，{dr_s}部位

查体：
透视：{pe_ts}部位
拍片: {pe_dr}部位
CT: {pe_ct}部位"""

        st.text_area("📋 报表文字（直接复制）", value=report_text, height=250)
        
        if st.button("🚀 刷新数据"):
            st.cache_data.clear()
            st.rerun()
            
    else:
        st.warning("⚠️ 本周范围内暂无数据，请先去 Google Sheets 填报。")

except Exception as e:
    st.error(f"连接 Google Sheets 失败，请检查链接权限。错误详情: {e}")

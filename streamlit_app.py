import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="影像科管理系统", page_icon="🏥", layout="wide")

# --- 2. 配置信息 (请在此处修改) ---
BASE_URL = st.secrets.get("public_gsheet_url", "你的Google表格地址")
MANUAL_GID = "1955581250"
FORM_GID = "720850282"
form_url = "https://forms.gle/AzUyPeRgJnnAgEbj8?embedded=true"

# 安全设置：设置你的登录密码
SYSTEM_PASSWORD = "666" # 你可以改成你喜欢的数字或字母

# --- 3. 登录逻辑 ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🏥 影像科管理系统 - 身份验证")
    # 这里也去掉了“主任”字样，更简洁
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("进入系统"):
        if pwd == SYSTEM_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("密码错误，请联系管理员")
    st.stop()

# --- 4. 核心功能函数 ---

def fetch_sheet(gid):
    try:
        clean_url = BASE_URL.strip()
        base_id = clean_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{base_id}/export?format=csv&gid={gid}"
        return pd.read_csv(csv_url, on_bad_lines='skip')
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=30)
def get_merged_data():
    df_manual = fetch_sheet(MANUAL_GID)
    df_form = fetch_sheet(FORM_GID)
    
    columns = ['日期', '常规CT人', '常规CT部位', '常规DR人', '常规DR部位', '查体CT', '查体DR', '查体透视']
    
    if not df_form.empty:
        df_form.columns = ['提交时间'] + columns
        df_form['日期'] = pd.to_datetime(df_form['日期'], errors='coerce').dt.normalize()
        df_form = df_form.sort_values('提交时间')
        df_form = df_form[columns]
    
    if not df_manual.empty:
        df_manual.columns = columns
        df_manual['日期'] = pd.to_datetime(df_manual['日期'], errors='coerce').dt.normalize()
        
    combined = pd.concat([df_manual, df_form], ignore_index=True)
    combined = combined.sort_values('日期')
    combined = combined.drop_duplicates(subset=['日期'], keep='last')
    return combined.dropna(subset=['日期'])

# --- 5. 导航与侧边栏 ---
# 这里已经改成了您要求的：直接显示 andy
st.sidebar.title(f"👨‍⚕️ andy")
if st.sidebar.button("退出登录"):
    st.session_state["authenticated"] = False
    st.rerun()

menu = st.sidebar.radio("功能切换", ["📊 业务统计看板", "🔍 历史检查与修正", "📝 每日数据录入"])

df = get_merged_data()

# --- 6. 逻辑实现 ---

if menu == "📝 每日数据录入":
    st.header("📝 每日影像工作量上报")
    st.components.v1.iframe(form_url, height=850, scrolling=True)

elif menu == "🔍 历史检查与修正":
    st.header("🔍 历史记录检查")
    st.write("如需修改，直接在下方重新提交该日期的数据，系统会自动修正。")
    
    display_df = df.sort_values('日期', ascending=False).head(15)
    st.table(display_df)
    
    st.markdown("---")
    st.subheader("🛠️ 极速数据修正")
    st.components.v1.iframe(form_url, height=600, scrolling=True)

else:
    st.header("📊 影像业务多维度看板")
    tab_week, tab_month, tab_year = st.tabs(["📅 周报", "📆 月报", "🏆 年报"])
    
    today = pd.Timestamp.now().normalize()

    with tab_week:
        days_since_friday = (today.weekday() - 4 + 7) % 7
        start_w = today - pd.Timedelta(days=days_since_friday)
        end_w = start_w + pd.Timedelta(days=6)
        
        week_df = df[(df['日期'] >= start_w) & (df['日期'] <= end_w)]
        if not week_df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("本周 CT 部位", int(week_df['常规CT部位'].sum()))
            c2.metric("本周 DR 部位", int(week_df['常规DR部位'].sum()))
            c3.metric("总查体量", int(week_df['查体CT'].sum() + week_df['查体DR'].sum() + week_df['查体透视'].sum()))
            
            report = f"{start_w.date()}至{end_w.date()}工作量：\nCT：{int(week_df['常规CT人'].sum())}人，{int(week_df['常规CT部位'].sum())}部位\nDR：{int(week_df['常规DR人'].sum())}人，{int(week_df['常规DR部位'].sum())}部位\n查体：{int(week_df['查体CT'].sum() + week_df['查体DR'].sum() + week_df['查体透视'].sum())}部位"
            st.text_area("全选复制周报", report, height=150)
        else:
            st.warning("本周暂无数据")

    with tab_month:
        month_start = today.replace(day=1)
        month_df = df[(df['日期'] >= month_start) & (df['日期'] <= today)]
        if not month_df.empty:
            st.subheader(f"📅 {today.month} 月统计概览")
            st.bar_chart(month_df.set_index('日期')[['常规CT部位', '常规DR部位']])
            st.write(f"本月累计：{int(month_df[['常规CT部位', '常规DR部位', '查体CT', '查体DR', '查体透视']].sum().sum())} 部位")
        else:
            st.warning("本月暂无数据")

    with tab_year:
        year_start = today.replace(month=1, day=1)
        year_df = df[(df['日期'] >= year_start) & (df['日期'] <= today)]
        if not year_df.empty:
            st.subheader(f"🏆 {today.year} 年度汇总")
            st.info(f"年度累计完成：{int(year_df[['常规CT部位', '常规DR部位', '查体CT', '查体DR', '查体透视']].sum().sum())} 部位")
            year_df['月'] = year_df['日期'].dt.month
            monthly = year_df.groupby('月')[['常规CT部位', '常规DR部位']].sum()
            st.line_chart(monthly)

if st.sidebar.button("🔄 立即同步云端数据"):
    st.cache_data.clear()
    st.rerun()

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

def login():
    st.title("🏥 影像科管理系统 - 身份验证")
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("进入系统"):
        if pwd == SYSTEM_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("密码错误，请联系管理员")

if not st.session_state["authenticated"]:
    login()
    st.stop()

# --- 4. 核心功能函数 ---

def fetch_sheet(gid):
    try:
        clean_url = BASE_URL.strip()
        base_id = clean_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{base_id}/export?format=csv&gid={gid}"
        return pd.read_csv(csv_url, on_bad_lines='skip')
    except Exception as e:
        st.error(f"读取标签页 {gid} 失败。")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_merged_data():
    df_manual = fetch_sheet(MANUAL_GID)
    df_form = fetch_sheet(FORM_GID)
    
    columns = ['日期', '常规CT人', '常规CT部位', '常规DR人', '常规DR部位', '查体CT', '查体DR', '查体透视']
    
    if not df_form.empty:
        # 表单数据去重覆盖逻辑
        df_form.columns = ['提交时间'] + columns
        df_form['日期'] = pd.to_datetime(df_form['日期'], errors='coerce').dt.normalize()
        df_form = df_form.sort_values('提交时间')
        df_form = df_form[columns]
    
    if not df_manual.empty:
        df_manual.columns = columns
        df_manual['日期'] = pd.to_datetime(df_manual['日期'], errors='coerce').dt.normalize()
        
    combined = pd.concat([df_manual, df_form], ignore_index=True)
    combined = combined.sort_values('日期')
    # 唯一性去重：保留最后一次提交
    combined = combined.drop_duplicates(subset=['日期'], keep='last')
    return combined.dropna(subset=['日期'])

# --- 5. 界面逻辑 ---

st.sidebar.title(f"👨‍⚕️ Andy 主任")
if st.sidebar.button("退出登录"):
    st.session_state["authenticated"] = False
    st.rerun()

menu = st.sidebar.radio("请选择功能", ["📊 业务统计看板", "📝 每日数据录入", "🔍 历史记录检查"])

df = get_merged_data()

if menu == "📝 每日数据录入":
    st.header("📝 每日影像工作量上报")
    st.info("💡 纠错说明：如需修改某日数据，只需针对该日期重新提交，系统将自动覆盖旧记录。")
    st.components.v1.iframe(form_url, height=850, scrolling=True)

elif menu == "🔍 历史记录检查":
    st.header("🔍 数据历史记录 (已去重)")
    st.write("你可以通过此表检查是否有录入错误。如果有误，请记下日期去【数据录入】重新提交。")
    # 显示最近30条记录，按日期倒序
    st.dataframe(df.sort_values('日期', ascending=False).head(30), use_container_width=True)

else:
    st.header("📊 影像业务多维度看板")
    
    # 定义时间维度
    tab_week, tab_month, tab_year = st.tabs(["📅 周报统计", "📆 月报统计", "🏆 年报汇总"])
    
    today = pd.Timestamp.now().normalize()

    # --- 周报逻辑 ---
    with tab_week:
        days_since_friday = (today.weekday() - 4 + 7) % 7
        start_w = today - pd.Timedelta(days=days_since_friday)
        end_w = start_w + pd.Timedelta(days=6)
        
        week_df = df[(df['日期'] >= start_w) & (df['日期'] <= end_w)]
        
        if not week_df.empty:
            cols = st.columns(3)
            cols[0].metric("本周 CT 部位", int(week_df['常规CT部位'].sum()))
            cols[1].metric("本周 DR 部位", int(week_df['常规DR部位'].sum()))
            cols[2].metric("本周总查体", int(week_df['查体CT'].sum() + week_df['查体DR'].sum() + week_df['查体透视'].sum()))
            
            st.text_area("周报文字 (复制用)", f"{start_w.date()}至{end_w.date()}工作量：\nCT：{int(week_df['常规CT人'].sum())}人，{int(week_df['常规CT部位'].sum())}部位\nDR：{int(week_df['常规DR人'].sum())}人，{int(week_df['常规DR部位'].sum())}部位\n查体：{int(week_df['查体CT'].sum() + week_df['查体DR'].sum() + week_df['查体透视'].sum())}部位")
        else:
            st.warning("本周暂无数据")

    # --- 月报逻辑 ---
    with tab_month:
        month_start = today.replace(day=1)
        # 获取本月所有数据
        month_df = df[(df['日期'] >= month_start) & (df['日期'] <= today)]
        
        if not month_df.empty:
            st.subheader(f"✨ {today.month} 月实时汇总")
            m_ct_s = int(month_df['常规CT部位'].sum())
            m_dr_s = int(month_df['常规DR部位'].sum())
            m_pe = int(month_df['查体CT'].sum() + month_df['查体DR'].sum() + month_df['查体透视'].sum())
            
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("当月 CT 部位", m_ct_s)
            mc2.metric("当月 DR 部位", m_dr_s)
            mc3.metric("当月查体量", m_pe)
            
            st.bar_chart(month_df.set_index('日期')[['常规CT部位', '常规DR部位']])
        else:
            st.warning("本月暂无数据")

    # --- 年报逻辑 ---
    with tab_year:
        year_start = today.replace(month=1, day=1)
        year_df = df[(df['日期'] >= year_start) & (df['日期'] <= today)]
        
        if not year_df.empty:
            st.subheader(f"🏆 {today.year} 年度大盘")
            y_total = int(year_df[['常规CT部位', '常规DR部位', '查体CT', '查体DR', '查体透视']].values.sum())
            st.info(f"截止今日，{today.year} 年度全科室累计完成检查量：{y_total} 部位")
            
            # 按月汇总展示
            year_df['月份'] = year_df['日期'].dt.month
            monthly_trend = year_df.groupby('月份')[['常规CT部位', '常规DR部位']].sum()
            st.line_chart(monthly_trend)
        else:
            st.warning("本年暂无数据")

if st.sidebar.button("🔄 刷新云端数据"):
    st.cache_data.clear()
    st.rerun()

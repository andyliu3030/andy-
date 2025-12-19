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
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("进入系统"):
        if pwd == SYSTEM_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()

# --- 4. 辅助功能：通用复制按钮 (JavaScript) ---
def universal_copy_button(text, label="📋 点击一键复制"):
    # 利用 HTML/JS 实现跨版本兼容的复制功能
    html_code = f"""
    <button onclick="copyText()" style="
        background-color: #ff4b4b;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        cursor: pointer;
        font-weight: bold;
    ">{label}</button>
    <textarea id="copyTarget" style="position:absolute; left:-9999px;">{text}</textarea>
    <script>
    function copyText() {{
        var copyText = document.getElementById("copyTarget");
        copyText.select();
        copyText.setSelectionRange(0, 99999);
        document.execCommand("copy");
        alert("✅ 已成功复制到剪贴板！");
    }}
    </script>
    """
    components.html(html_code, height=60)

# --- 5. 核心数据获取 ---
def fetch_sheet(gid):
    try:
        clean_url = BASE_URL.strip()
        base_id = clean_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{base_id}/export?format=csv&gid={gid}"
        return pd.read_csv(csv_url, on_bad_lines='skip')
    except:
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
    combined = combined.sort_values('日期').drop_duplicates(subset=['日期'], keep='last')
    return combined.dropna(subset=['日期'])

# --- 6. 界面实现 ---
st.sidebar.title(f"👨‍⚕️ andy")
menu = st.sidebar.radio("功能切换", ["📊 业务统计看板", "🔍 历史检查与修正", "📝 每日数据录入"])
df = get_merged_data()

if menu == "📝 每日数据录入":
    st.components.v1.iframe(form_url, height=850, scrolling=True)

elif menu == "🔍 历史检查与修正":
    st.header("🔍 历史记录检查")
    st.table(df.sort_values('日期', ascending=False).head(15))
    st.markdown("---")
    st.subheader("🛠️ 极速数据修正")
    st.components.v1.iframe(form_url, height=600, scrolling=True)

else:
    st.header("📊 影像业务统计")
    tab_week, tab_month, tab_year = st.tabs(["📅 周报", "📆 月报", "🏆 年报"])
    today = pd.Timestamp.now().normalize()

    def gen_text(data, start, end):
        if data.empty: return "暂无数据"
        return f"{start.strftime('%Y年%m月%d日')}至{end.strftime('%Y年%m月%d日')}影像科工作量：\n" \
               f"CT：{int(data['常规CT人'].sum())}人，{int(data['常规CT部位'].sum())}部位\n" \
               f"DR：{int(data['常规DR人'].sum())}人，{int(data['常规DR部位'].sum())}部位\n\n" \
               f"查体：\n透视：{int(data['查体透视'].sum())}部位\n拍片: {int(data['查体DR'].sum())}部位\nCT: {int(data['查体CT'].sum())}部位"

    with tab_week:
        # 统计上一个完整周期（周五到周四）
        current_fri = today - pd.Timedelta(days=(today.weekday() - 4 + 7) % 7)
        start_w, end_w = current_fri - pd.Timedelta(days=7), current_fri - pd.Timedelta(days=1)
        week_df = df[(df['日期'] >= start_w) & (df['日期'] <= end_w)]
        if not week_df.empty:
            report = gen_text(week_df, start_w, end_w)
            st.text_area("周报预览", report, height=220)
            universal_copy_button(report, "📋 一键复制周报")
        else: st.warning("上周暂无数据")

    with tab_month:
        start_m = today.replace(day=1)
        month_df = df[(df['日期'] >= start_m) & (df['日期'] <= today)]
        if not month_df.empty:
            report = gen_text(month_df, start_m, today)
            st.text_area("月报预览", report, height=220)
            universal_copy_button(report, "📋 一键复制月报")
        else: st.warning("本月暂无数据")

    with tab_year:
        start_y = today.replace(month=1, day=1)
        year_df = df[(df['日期'] >= start_y) & (df['日期'] <= today)]
        if not year_df.empty:
            st.info(f"年度累计完成：{int(year_df[['常规CT部位', '常规DR部位', '查体CT', '查体DR', '查体透视']].sum().sum())} 部位")
            st.line_chart(year_df.groupby(year_df['日期'].dt.month)[['常规CT部位', '常规DR部位']].sum())

if st.sidebar.button("🔄 同步云端"):
    st.cache_data.clear()
    st.rerun()

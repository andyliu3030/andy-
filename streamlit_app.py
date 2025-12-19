import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="影像科管理系统", page_icon="🏥", layout="wide")

# --- 2. 配置信息 (请在此修改) ---
DATA_BRIDGE_URL = "https://data.huhu.de5.net" # 之前创建的 Cloudflare 数据中转站
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyPz6hr6H4fSlAXGkzHJeAX0oU-j5T8Sa7thHe6YJFxhAp0OgzO5HpV-9lQJxPopJDnpg/exec" # ⚠️ 填入刚才部署的 Web 应用 URL
BASE_URL = st.secrets.get("public_gsheet_url", "https://docs.google.com/spreadsheets/d/1RmSEy1RhqO69UadsYMATKoHDG0-ksO--ONu_jbiEuHU/edit?gid=1955581250#gid=1955581250")

MANUAL_GID = "1955581250"
FORM_GID = "720850282"
SYSTEM_PASSWORD = "666" 

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

# --- 4. 辅助功能：一键复制 ---
def universal_copy_button(text, label="📋 点击一键复制"):
    safe_text = text.replace('\n', '\\n').replace("'", "\\'")
    html_code = f"""
    <button onclick="copyToClipboard()" style="background-color:#ff4b4b;color:white;border:none;padding:12px 24px;border-radius:10px;cursor:pointer;font-weight:bold;">{label}</button>
    <script>
    function copyToClipboard() {{
        const textArea = document.createElement("textarea");
        textArea.value = '{safe_text}';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        alert('✅ 复制成功！');
        document.body.removeChild(textArea);
    }}
    </script>
    """
    components.html(html_code, height=70)

# --- 5. 数据处理 ---
def fetch_sheet(gid):
    try:
        base_id = BASE_URL.split("/d/")[1].split("/")[0]
        proxy_url = f"{DATA_BRIDGE_URL.rstrip('/')}/?id={base_id}&gid={gid}"
        return pd.read_csv(proxy_url, on_bad_lines='skip')
    except:
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def get_merged_data():
    df_manual = fetch_sheet(MANUAL_GID)
    df_form = fetch_sheet(FORM_GID)
    columns = ['日期', '常规CT人', '常规CT部位', '常规DR人', '常规DR部位', '查体CT', '查体DR', '查体透视']
    if not df_form.empty:
        df_form.columns = ['提交时间'] + columns
        df_form['日期'] = pd.to_datetime(df_form['日期'], errors='coerce').dt.normalize()
        df_form = df_form[columns]
    if not df_manual.empty:
        df_manual.columns = columns
        df_manual['日期'] = pd.to_datetime(df_manual['日期'], errors='coerce').dt.normalize()
    combined = pd.concat([df_manual, df_form], ignore_index=True)
    return combined.sort_values('日期').drop_duplicates(subset=['日期'], keep='last').dropna(subset=['日期'])

# --- 6. 主界面 ---
st.sidebar.title(f"👨‍⚕️ andy")
menu = st.sidebar.radio("功能切换", ["📊 业务统计看板", "📝 每日数据录入", "🔍 历史数据检查"])
df = get_merged_data()

if menu == "📝 每日数据录入":
    st.header("📝 影像业务数据极速上报")
    with st.form("data_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("选择业务日期", datetime.now())
            st.markdown("**常规 CT**")
            ct_p = st.number_input("常规 CT 人数", min_value=0, step=1)
            ct_s = st.number_input("常规 CT 部位", min_value=0, step=1)
        with col2:
            st.markdown("**常规 DR**")
            dr_p = st.number_input("常规 DR 人数", min_value=0, step=1)
            dr_s = st.number_input("常规 DR 部位", min_value=0, step=1)
        
        st.markdown("---")
        st.markdown("**查体业务 (单位：部位)**")
        c1, c2, c3 = st.columns(3)
        pe_ct = c1.number_input("查体 CT", min_value=0, step=1)
        pe_dr = c2.number_input("查体 拍片(DR)", min_value=0, step=1)
        pe_ts = c3.number_input("查体 透视", min_value=0, step=1)
        
        submitted = st.form_submit_button("🚀 提交数据到云端")
        
        if submitted:
            payload = {
                "date": str(date), "ct_p": ct_p, "ct_s": ct_s, 
                "dr_p": dr_p, "dr_s": dr_s, "pe_ct": pe_ct, "pe_dr": pe_dr, "pe_ts": pe_ts
            }
            try:
                res = requests.post(GOOGLE_SCRIPT_URL, json=payload)
                if res.status_code == 200:
                    st.success(f"✅ {date} 数据已成功录入！数据大约在 24 小时内更新，如需立即查看请点击左侧刷新。")
                else:
                    st.error("提交失败，请检查脚本 URL。")
            except:
                st.error("网络连接异常，请重试。")

elif menu == "🔍 历史数据检查":
    st.header("🔍 历史记录")
    st.table(df.sort_values('日期', ascending=False).head(15))

else:
    st.header("📊 影像业务统计")
    tab_week, tab_month, tab_year = st.tabs(["📅 周报", "📆 月报", "🏆 年报"])
    today = pd.Timestamp.now().normalize()
    
    def gen_text(data, start, end):
        if data.empty: return "该时段暂无数据。"
        return f"{start.strftime('%Y年%m月%d日')}至{end.strftime('%Y年%m月%d日')}影像科工作量：\\nCT：{int(data['常规CT人'].sum())}人，{int(data['常规CT部位'].sum())}部位\\nDR：{int(data['常规DR人'].sum())}人，{int(data['常规DR部位'].sum())}部位\\n\\n查体：\\n透视：{int(data['查体透视'].sum())}部位\\n拍片: {int(data['查体DR'].sum())}部位\\nCT: {int(data['查体CT'].sum())}部位"

    with tab_week:
        current_fri = today - pd.Timedelta(days=(today.weekday() - 4 + 7) % 7)
        sw, ew = current_fri - pd.Timedelta(days=7), current_fri - pd.Timedelta(days=1)
        w_df = df[(df['日期'] >= sw) & (df['日期'] <= ew)]
        if not w_df.empty:
            report = gen_text(w_df, sw, ew)
            st.text_area("内容预览", report.replace('\\n', '\n'), height=220)
            universal_copy_button(report, "📋 一键复制周报")
        else: st.warning("暂无数据")

    with tab_month:
        sm = today.replace(day=1)
        m_df = df[(df['日期'] >= sm) & (df['日期'] <= today)]
        if not m_df.empty:
            report = gen_text(m_df, sm, today)
            st.text_area("内容预览", report.replace('\\n', '\n'), height=220)
            universal_copy_button(report, "📋 一键复制月报")
        else: st.warning("暂无数据")

if st.sidebar.button("🔄 立即强制刷新"):
    st.cache_data.clear()
    st.rerun()

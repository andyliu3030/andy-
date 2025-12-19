import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="影像科管理系统", page_icon="🏥", layout="wide")

# --- 2. 配置信息 (请务必检查此处) ---
# ⚠️ 填写你在 Cloudflare 部署的数据中转站地址
DATA_BRIDGE_URL = "https://data.huhu.de5.net" 

# 原本的 Google 表格地址
BASE_URL = st.secrets.get("public_gsheet_url", "https://docs.google.com/spreadsheets/d/1RmSEy1RhqO69UadsYMATKoHDG0-ksO--ONu_jbiEuHU/edit?gid=1955581250#gid=1955581250")

MANUAL_GID = "1955581250"
FORM_GID = "720850282"
# ⚠️ 检查：表单地址必须是 viewform 结尾，且带有 ?embedded=true
form_url = "https://docs.google.com/forms/d/e/1FAIpQLSdwewwOi46gZDDH2Kt3Eu4Y94DAztLRTbOyYDOa7z8wjd1Dmg/viewform?usp=header?embedded=true"

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

# --- 4. 辅助功能：一键复制按钮 ---
def universal_copy_button(text, label="📋 点击一键复制"):
    safe_text = text.replace('\n', '\\n').replace("'", "\\'")
    html_code = f"""
    <div style="margin-bottom: 20px;">
        <button onclick="copyToClipboard()" style="
            background-color: #ff4b4b;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
        ">{label}</button>
    </div>
    <script>
    function copyToClipboard() {{
        const text = '{safe_text}';
        const textArea = document.createElement("textarea");
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        alert('✅ 报表已成功复制到剪贴板！');
        document.body.removeChild(textArea);
    }}
    </script>
    """
    components.html(html_code, height=70)

# --- 5. 数据读取 (免代理版) ---
def fetch_sheet(gid):
    try:
        clean_url = BASE_URL.strip()
        base_id = clean_url.split("/d/")[1].split("/")[0]
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
menu = st.sidebar.radio("功能切换", ["📊 业务统计看板", "📝 每日数据上报", "🔍 历史检查与修正"])
df = get_merged_data()

if menu == "📝 每日数据上报":
    st.header("📝 每日数据上报")
    
    # 🌟 新增：如果内网打不开表单，提供直接跳转按钮
    st.warning("💡 如果下方表单显示为黑色或无法加载，请点击下方按钮在独立窗口中打开。")
    st.link_button("🔗 点击此处直接打开填报表单", form_url.replace("?embedded=true", ""))
    
    st.markdown("---")
    # 尝试嵌入
    try:
        st.components.v1.iframe(form_url, height=900, scrolling=True)
    except:
        st.error("表单嵌入失败，请使用上方的直接跳转按钮。")

elif menu == "🔍 历史检查与修正":
    st.header("🔍 历史记录检查")
    st.table(df.sort_values('日期', ascending=False).head(15))
    st.markdown("---")
    st.subheader("🛠️ 快速修正")
    st.info("如需修改，请点击上方“📝 每日数据上报”重新提交正确日期的数据。")

else:
    st.header("📊 影像业务统计")
    tab_week, tab_month, tab_year = st.tabs(["📅 周报", "📆 月报", "🏆 年报"])
    today = pd.Timestamp.now().normalize()
    
    def gen_text(data, start, end):
        if data.empty: return "该时段暂无数据。"
        return f"{start.strftime('%Y年%m月%d日')}至{end.strftime('%Y年%m月%d日')}影像科工作量：\\n" \
               f"CT：{int(data['常规CT人'].sum())}人，{int(data['常规CT部位'].sum())}部位\\n" \
               f"DR：{int(data['常规DR人'].sum())}人，{int(data['常规DR部位'].sum())}部位\\n\\n" \
               f"查体：\\n透视：{int(data['查体透视'].sum())}部位\\n拍片: {int(data['查体DR'].sum())}部位\\nCT: {int(data['查体CT'].sum())}部位"

    with tab_week:
        current_fri = today - pd.Timedelta(days=(today.weekday() - 4 + 7) % 7)
        sw, ew = current_fri - pd.Timedelta(days=7), current_fri - pd.Timedelta(days=1)
        w_df = df[(df['日期'] >= sw) & (df['日期'] <= ew)]
        if not w_df.empty:
            report = gen_text(w_df, sw, ew)
            st.text_area("内容预览", report.replace('\\n', '\n'), height=220)
            universal_copy_button(report, "📋 一键复制周报")
        else: st.warning("上周暂无数据")

    with tab_month:
        sm = today.replace(day=1)
        m_df = df[(df['日期'] >= sm) & (df['日期'] <= today)]
        if not m_df.empty:
            report = gen_text(m_df, sm, today)
            st.text_area("内容预览", report.replace('\\n', '\n'), height=220)
            universal_copy_button(report, "📋 一键复制月报")
        else: st.warning("本月暂无数据")

    with tab_year:
        sy = today.replace(month=1, day=1)
        y_df = df[(df['日期'] >= sy) & (df['日期'] <= today)]
        if not y_df.empty:
            st.info(f"🏆 {today.year} 年度累计完成：{int(y_df[['常规CT部位', '常规DR部位', '查体CT', '查体DR', '查体透视']].sum().sum())} 部位")
            st.line_chart(y_df.groupby(y_df['日期'].dt.month)[['常规CT部位', '常规DR部位']].sum())

if st.sidebar.button("🔄 立即强制刷新"):
    st.cache_data.clear()
    st.rerun()

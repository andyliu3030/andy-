import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="影像科管理系统", page_icon="🏥", layout="wide")

# --- 2. 配置信息 (请在此处修改) ---
# ⚠️ 填写你刚刚在 Cloudflare 部署的数据中转站地址 (例如 https://data.huhu.de5.net)
DATA_BRIDGE_URL = "https://data.huhu.de5.net" 

# 原本的 Google 表格地址 (用于提取表格 ID)
BASE_URL = st.secrets.get("public_gsheet_url", "你的Google表格地址")

MANUAL_GID = "1955581250"
FORM_GID = "720850282"
form_url = "https://forms.gle/AzUyPeRgJnnAgEbj8?embedded=true"
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

# --- 4. 辅助功能：一键复制按钮 (JavaScript 方案) ---
def universal_copy_button(text, label="📋 点击一键复制"):
    # 清理文本中的换行符，防止 JS 报错
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
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        ">{label}</button>
    </div>
    <script>
    function copyToClipboard() {{
        const text = '{safe_text}';
        const textArea = document.createElement("textarea");
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {{
            document.execCommand('copy');
            alert('✅ 报表已成功复制到剪贴板！');
        }} catch (err) {{
            console.error('复制失败', err);
        }}
        document.body.removeChild(textArea);
    }}
    </script>
    """
    components.html(html_code, height=70)

# --- 5. 数据处理核心 (免代理中转版) ---
def fetch_sheet(gid):
    """
    通过 Cloudflare Worker 中转读取数据
    解决内网环境下无法直连 Google 的问题
    """
    try:
        clean_url = BASE_URL.strip()
        # 从 Google 链接中提取 Spreadsheet ID
        base_id = clean_url.split("/d/")[1].split("/")[0]
        
        # ⚠️ 构造中转请求：不再访问 google.com，而是访问你自己的 data.huhu.de5.net
        proxy_url = f"{DATA_BRIDGE_URL.rstrip('/')}/?id={base_id}&gid={gid}"
        
        # 读取 CSV 数据
        return pd.read_csv(proxy_url, on_bad_lines='skip')
    except Exception as e:
        st.sidebar.warning(f"⚠️ 标签页 {gid} 读取延迟，请手动刷新。")
        return pd.DataFrame()

# 设置 24 小时刷新频率 (86400秒)
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

# --- 6. 报表文字生成逻辑 ---
def generate_report_text(data, start, end):
    if data.empty: return "该时段暂无数据。"
    return f"{start.strftime('%Y年%m月%d日')}至{end.strftime('%Y年%m月%d日')}影像科工作量：\\n" \
           f"CT：{int(data['常规CT人'].sum())}人，{int(data['常规CT部位'].sum())}部位\\n" \
           f"DR：{int(data['常规DR人'].sum())}人，{int(data['常规DR部位'].sum())}部位\\n\\n" \
           f"查体：\\n透视：{int(data['查体透视'].sum())}部位\\n拍片: {int(data['查体DR'].sum())}部位\\nCT: {int(data['查体CT'].sum())}部位"

# --- 7. 主界面逻辑 ---
st.sidebar.title(f"👨‍⚕️ andy")
menu = st.sidebar.radio("功能切换", ["📊 业务统计看板", "🔍 历史检查与修正", "📝 每日数据录入"])
df = get_merged_data()

if menu == "📝 每日数据录入":
    st.header("📝 每日数据上报")
    # 注意：表单通常本身可以通过域名访问，无需特殊代理
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

    with tab_week:
        # 统计上一个完整周期 (上周五到本周四)
        current_fri = today - pd.Timedelta(days=(today.weekday() - 4 + 7) % 7)
        start_w = current_fri - pd.Timedelta(days=7)
        end_w = current_fri - pd.Timedelta(days=1)
        
        week_df = df[(df['日期'] >= start_w) & (df['日期'] <= end_w)]
        if not week_df.empty:
            st.subheader(f"📅 上周汇总 ({start_w.date()} ~ {end_w.date()})")
            report = generate_report_text(week_df, start_w, end_w)
            st.text_area("内容预览", report.replace('\\n', '\n'), height=220)
            universal_copy_button(report, "📋 一键复制周报")
        else:
            st.warning("上周完整周期内暂无数据")

    with tab_month:
        start_m = today.replace(day=1)
        month_df = df[(df['日期'] >= start_m) & (df['日期'] <= today)]
        if not month_df.empty:
            st.subheader(f"📆 {today.month} 月实时汇总")
            report = generate_report_text(month_df, start_m, today)
            st.text_area("内容预览", report.replace('\\n', '\n'), height=220)
            universal_copy_button(report, "📋 一键复制月报")
        else:
            st.warning("本月暂无数据")

    with tab_year:
        start_y = today.replace(month=1, day=1)
        year_df = df[(df['日期'] >= start_y) & (df['日期'] <= today)]
        if not year_df.empty:
            st.info(f"🏆 {today.year} 年度累计：{int(year_df[['常规CT部位', '常规DR部位', '查体CT', '查体DR', '查体透视']].sum().sum())} 部位")
            st.line_chart(year_df.groupby(year_df['日期'].dt.month)[['常规CT部位', '常规DR部位']].sum())

# 侧边栏按钮：强制刷新
if st.sidebar.button("🔄 立即强制刷新"):
    st.cache_data.clear()
    st.rerun()

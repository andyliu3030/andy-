import streamlit as st
import pandas as pd
import io
from datetime import datetime
from seatable_api import Base
import streamlit.components.v1 as components

# --- 1. 核心配置 (Token 已锁定) ---
SEATABLE_API_TOKEN = "18f698b812378e4d0a85de15f902fad1c205f393" 
SEATABLE_SERVER_URL = "https://cloud.seatable.cn"
TABLE_NAME = "业务数据录入" 

SYSTEM_PASSWORD = "666"

st.set_page_config(page_title="影像科管理", page_icon="🏥", layout="wide", initial_sidebar_state="collapsed")

# --- 2. UI 增强样式 ---
st.markdown("""
    <style>
    [data-testid="stWidgetLabel"] p { color: #1E3A8A !important; font-weight: bold !important; font-size: 1.05rem !important; }
    .stButton > button { width: 100%; height: 50px; border-radius: 12px; font-size: 18px !important; font-weight: bold; background-color: #ff4b4b; color: white; }
    .section-box { background-color: #f8fafc; padding: 15px; border-radius: 12px; border-left: 5px solid #1E3A8A; margin-bottom: 20px; }
    [data-testid="stMetric"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 12px; border-radius: 12px; }
    .stDownloadButton > button { background-color: #10B981 !important; height: 45px !important; } 
    
    .period-highlight {
        font-size: 22px !important;
        color: #ff4b4b !important;
        font-weight: 800 !important;
        padding: 8px 0;
        border-bottom: 2px solid #ff4b4b;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 身份验证 ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🏥 影像科管理系统")
    pwd = st.text_input("访问密码", type="password")
    if st.button("解锁进入"):
        if pwd == SYSTEM_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("密码错误")
    st.stop()

# --- 4. 数据处理核心 ---
@st.cache_data(ttl=86400)
def get_seatable_data():
    try:
        base = Base(SEATABLE_API_TOKEN, SEATABLE_SERVER_URL)
        base.auth()
        rows = base.list_rows(TABLE_NAME)
        df = pd.DataFrame(rows)
        if not df.empty:
            df['日期'] = pd.to_datetime(df['日期']).dt.tz_localize(None).dt.normalize()
            df = df.dropna(subset=['日期']).drop_duplicates(subset=['日期'], keep='last')
            if '查体DR' in df.columns and '查体拍片' not in df.columns:
                df.rename(columns={'查体DR': '查体拍片'}, inplace=True)
            return df.sort_values('日期', ascending=False)
        return pd.DataFrame()
    except: return pd.DataFrame()

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='影像业务台账')
    return output.getvalue()

# 🌟 调整：复制按钮宽度减半
def universal_copy_button(text, label="📋 一键复制内容"):
    safe_text = text.replace('\n', '\\n').replace("'", "\\'")
    html_code = f"""
    <button onclick="copyToClipboard()" style="
        background-color:#ff4b4b;color:white;border:none;width:50%;height:42px;
        border-radius:10px;cursor:pointer;font-weight:bold;font-size:16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">{label}</button>
    <script>
    function copyToClipboard() {{
        const textArea = document.createElement("textarea");
        textArea.value = '{safe_text}';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        alert('✅ 报表内容已成功复制！');
        document.body.removeChild(textArea);
    }}
    </script>
    """
    components.html(html_code, height=55)

# --- 5. 侧边栏 ---
menu = st.sidebar.radio("菜单导航", ["📊 统计看板", "📝 每日录入"])
df = get_seatable_data()

# --- 6. 功能实现 ---
if menu == "📝 每日录入":
    st.header("📝 业务数据录入")
    with st.form("mobile_form", clear_on_submit=True):
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        d = st.date_input("📅 选择业务日期 (必填)", value=None)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.subheader("🏥 常规业务统计")
        c1, c2 = st.columns(2)
        ct_p = c1.number_input("常规 CT 人数", min_value=0, value=None, step=1)
        ct_s = c1.number_input("常规 CT 部位", min_value=0, value=None, step=1)
        dr_p = c2.number_input("常规 DR 人数", min_value=0, value=None, step=1)
        dr_s = c2.number_input("常规 DR 部位", min_value=0, value=None, step=1)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.subheader("🩺 查体业务统计")
        p1, p2, p3 = st.columns(3)
        pe_ct = p1.number_input("查体 CT", min_value=0, value=None)
        pe_dr = p2.number_input("查体 拍片", min_value=0, value=None)
        pe_ts = p3.number_input("查体 透视", min_value=0, value=None)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.form_submit_button("🚀 提交业务记录"):
            if d is None:
                st.error("❌ 提交失败：请先选择日期！")
            else:
                try:
                    base = Base(SEATABLE_API_TOKEN, SEATABLE_SERVER_URL)
                    base.auth()
                    row_data = {
                        "日期": str(d), 
                        "常规CT人": ct_p if ct_p is not None else 0, 
                        "常规CT部位": ct_s if ct_s is not None else 0,
                        "常规DR人": dr_p if dr_p is not None else 0, 
                        "常规DR部位": dr_s if dr_s is not None else 0,
                        "查体CT": pe_ct if pe_ct is not None else 0, 
                        "查体拍片": pe_dr if pe_dr is not None else 0, 
                        "查体透视": pe_ts if pe_ts is not None else 0
                    }
                    base.append_row(TABLE_NAME, row_data)
                    st.success(f"✅ {d} 数据提交成功！")
                    st.cache_data.clear()
                    st.rerun()
                except: st.error("网络异常，请核对 SeaTable 设置")

else:
    st.header("📊 业务统计看板")
    if not df.empty:
        today = pd.Timestamp.now().normalize()
        current_fri = today - pd.Timedelta(days=(today.weekday() - 4 + 7) % 7)
        sw, ew = current_fri - pd.Timedelta(days=7), current_fri - pd.Timedelta(days=1)
        w_df = df[(df['日期'] >= sw) & (df['日期'] <= ew)]
        
        with st.expander("📑 原始数据管理"):
            excel_data = convert_df_to_excel(df)
            st.download_button("📥 导出完整 Excel 报表", data=excel_data, file_name=f"影像数据_{datetime.now().strftime('%Y%m%d')}.xlsx")

        if not w_df.empty:
            st.markdown(f'<div class="period-highlight">统计周期：{sw.date()} ~ {ew.date()}</div>', unsafe_allow_html=True)
            
            m1, m2 = st.columns(2)
            m1.metric("常规 CT 总部位", int(w_df['常规CT部位'].sum()))
            m2.metric("常规 DR 总部位", int(w_df['常规DR部位'].sum()) )
            
            report = f"{sw.strftime('%Y年%m月%d日')}至{ew.strftime('%Y年%m月%d日')}影像科工作量：\\n" \
                     f"CT：{int(w_df['常规CT人'].sum())}人，{int(w_df['常规CT部位'].sum())}部位\\n" \
                     f"DR：{int(w_df['常规DR人'].sum())}人，{int(w_df['常规DR部位'].sum())}部位\\n\\n" \
                     f"查体：\\n透视：{int(w_df['查体透视'].sum())}部位\\n拍片: {int(w_df['查体拍片'].sum())}部位\\nCT: {int(w_df['查体CT'].sum())}部位"
            
            # 🌟 调整：预览框高度翻倍
            with st.expander("📝 报表预览与复制", expanded=True):
                st.text_area("报表原文", report.replace('\\n', '\n'), height=360) 
                universal_copy_button(report)
        else:
            st.warning("当前统计周期内暂无录入记录")
        
        st.markdown("---")
        if st.checkbox("查看最新数据明细"):
            st.dataframe(df.head(7), use_container_width=True)
    else:
        st.warning("库内目前没有数据。")

if st.sidebar.button("🔄 立即强制刷新同步"):
    st.cache_data.clear()
    st.rerun()

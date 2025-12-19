import streamlit as st
import pandas as pd
from datetime import datetime
from seatable_api import Base
import streamlit.components.v1 as components

# --- 1. 核心配置 ---
SEATABLE_API_TOKEN = "18f698b812378e4d0a85de15f902fad1c205f393" 
SEATABLE_SERVER_URL = "https://cloud.seatable.cn"
TABLE_NAME = "业务数据录入" 

SYSTEM_PASSWORD = "666"

st.set_page_config(page_title="影像科管理", page_icon="🏥", layout="wide", initial_sidebar_state="collapsed")

# --- 2. 移动端 UI 增强 (CSS) ---
st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
        height: 50px;
        border-radius: 12px;
        font-size: 18px !important;
        font-weight: bold;
        background-color: #ff4b4b;
        color: white;
    }
    [data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    /* 优化输入框焦点颜色 */
    input:focus {
        border-color: #ff4b4b !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 身份验证 ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🏥 影像科管理系统")
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("解锁进入"):
        if pwd == SYSTEM_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("密码错误")
    st.stop()

# --- 4. 一键复制功能 ---
def universal_copy_button(text, label="📋 复制报表发微信"):
    safe_text = text.replace('\n', '\\n').replace("'", "\\'")
    html_code = f"""
    <button onclick="copyToClipboard()" style="
        background-color:#ff4b4b;color:white;border:none;width:100%;height:55px;
        border-radius:12px;cursor:pointer;font-weight:bold;font-size:18px;
    ">{label}</button>
    <script>
    function copyToClipboard() {{
        const textArea = document.createElement("textarea");
        textArea.value = '{safe_text}';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        alert('✅ 已复制！\\n快去微信群粘贴吧。');
        document.body.removeChild(textArea);
    }}
    </script>
    """
    components.html(html_code, height=80)

# --- 5. SeaTable 数据读写 ---
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
            return df.sort_values('日期')
        return pd.DataFrame()
    except: return pd.DataFrame()

# --- 6. 导航 ---
menu = st.sidebar.radio("功能切换", ["📊 统计看板", "📝 每日数据录入"])
df = get_seatable_data()

# --- 7. 功能实现 ---
if menu == "📝 每日数据录入":
    st.header("📝 业务数据极速录入")
    with st.form("mobile_form", clear_on_submit=True):
        d = st.date_input("业务日期", datetime.now())
        
        st.markdown("---")
        st.subheader("🏥 常规业务")
        c1, c2 = st.columns(2)
        # 🌟 这里的 value=None 实现了输入框默认为空
        ct_p = c1.number_input("CT人数", min_value=0, value=None, step=1)
        ct_s = c1.number_input("CT部位", min_value=0, value=None, step=1)
        dr_p = c2.number_input("DR人数", min_value=0, value=None, step=1)
        dr_s = c2.number_input("DR部位", min_value=0, value=None, step=1)
        
        st.subheader("🩺 查体业务")
        p1, p2, p3 = st.columns(3)
        pe_ct = p1.number_input("查体CT", min_value=0, value=None)
        pe_dr = p2.number_input("查体拍片", min_value=0, value=None)
        pe_ts = p3.number_input("查体透视", min_value=0, value=None)
        
        if st.form_submit_button("🚀 确认提交"):
            try:
                base = Base(SEATABLE_API_TOKEN, SEATABLE_SERVER_URL)
                base.auth()
                # 🌟 提交时：如果用户没填（None），自动转为 0 存入 SeaTable
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
                st.success("✅ 提交成功！")
                st.cache_data.clear()
                st.rerun()
            except: st.error("网络异常，请重试")

else:
    st.header("📊 影像业务周报看板")
    if not df.empty:
        today = pd.Timestamp.now().normalize()
        current_fri = today - pd.Timedelta(days=(today.weekday() - 4 + 7) % 7)
        sw, ew = current_fri - pd.Timedelta(days=7), current_fri - pd.Timedelta(days=1)
        w_df = df[(df['日期'] >= sw) & (df['日期'] <= ew)]
        
        if not w_df.empty:
            st.markdown(f"**统计周期：{sw.date()} ~ {ew.date()}**")
            m1, m2 = st.columns(2)
            m1.metric("常规 CT 总部位", int(w_df['常规CT部位'].sum()))
            m2.metric("常规 DR 总部位", int(w_df['常规DR部位'].sum()) )
            
            # 报表文本生成
            report = f"{sw.strftime('%Y年%m月%d日')}至{ew.strftime('%Y年%m月%d日')}影像科工作量：\\n" \
                     f"CT：{int(w_df['常规CT人'].sum())}人，{int(w_df['常规CT部位'].sum())}部位\\n" \
                     f"DR：{int(w_df['常规DR人'].sum())}人，{int(w_df['常规DR部位'].sum())}部位\\n\\n" \
                     f"查体：\\n透视：{int(w_df['查体透视'].sum())}部位\\n拍片: {int(w_df['查体拍片'].sum())}部位\\nCT: {int(w_df['查体CT'].sum())}部位"
            
            with st.expander("📝 点击预览报表并复制", expanded=True):
                st.text_area("报表预览", report.replace('\\n', '\n'), height=200)
                universal_copy_button(report)
        else:
            st.warning("本统计周期暂无数据记录")
        
        st.markdown("---")
        if st.checkbox("查看最近录入明细"):
            st.dataframe(df.tail(7), use_container_width=True)
    else:
        st.warning("暂无数据，请先录入")

if st.sidebar.button("🔄 立即强制刷新同步"):
    st.cache_data.clear()
    st.rerun()

import streamlit as st
import pandas as pd
from datetime import datetime
from seatable_api import Base
import streamlit.components.v1 as components

# --- 1. 核心配置 (请在此处核对) ---
SEATABLE_API_TOKEN = "18f698b812378e4d0a85de15f902fad1c205f393" 
SEATABLE_SERVER_URL = "https://cloud.seatable.cn"
TABLE_NAME = "业务数据录入" # ⚠️ 确保和网页端标签页名称一致

SYSTEM_PASSWORD = "666"

st.set_page_config(page_title="影像科管理系统", page_icon="🏥", layout="wide")

# --- 2. 身份验证 ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🏥 影像科管理系统")
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("进入系统"):
        if pwd == SYSTEM_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("密码错误")
    st.stop()

# --- 3. 辅助功能：一键复制 ---
def universal_copy_button(text, label="📋 点击一键复制报表"):
    safe_text = text.replace('\n', '\\n').replace("'", "\\'")
    html_code = f"""
    <button onclick="copyToClipboard()" style="background-color:#ff4b4b;color:white;border:none;padding:10px 20px;border-radius:10px;cursor:pointer;font-weight:bold;">{label}</button>
    <script>
    function copyToClipboard() {{
        const textArea = document.createElement("textarea");
        textArea.value = '{safe_text}';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        alert('✅ 报表已成功复制到剪贴板！');
        document.body.removeChild(textArea);
    }}
    </script>
    """
    components.html(html_code, height=60)

# --- 4. SeaTable 数据读写 (加入去重逻辑) ---
@st.cache_data(ttl=86400) # 24小时缓存
def get_seatable_data():
    try:
        base = Base(SEATABLE_API_TOKEN, SEATABLE_SERVER_URL)
        base.auth()
        rows = base.list_rows(TABLE_NAME)
        df = pd.DataFrame(rows)
        
        if not df.empty:
            # 1. 统一日期格式并去除时区
            df['日期'] = pd.to_datetime(df['日期']).dt.tz_localize(None).dt.normalize()
            
            # 2. 🌟 核心逻辑：同一日期保留最后一次录入
            # 由于 list_rows 返回的是按录入顺序排列的，keep='last' 会保留最新的那条记录
            # 这样即便同一天录了两次，统计时也不会累加，而是只取后面那次
            df = df.dropna(subset=['日期']).drop_duplicates(subset=['日期'], keep='last')
            
            # 3. 列名兼容性处理
            if '查体DR' in df.columns and '查体拍片' not in df.columns:
                df.rename(columns={'查体DR': '查体拍片'}, inplace=True)
            
            return df.sort_values('日期')
        return pd.DataFrame()
    except Exception as e:
        st.sidebar.error("数据刷新失败，请检查网络或 Token。")
        return pd.DataFrame()

# --- 5. 主界面逻辑 ---
st.sidebar.title(f"👨‍⚕️ andy")
menu = st.sidebar.radio("功能切换", ["📊 业务统计看板", "📝 每日数据录入"])
df = get_seatable_data()

if menu == "📝 每日数据录入":
    st.header("📝 业务数据录入 (SeaTable)")
    st.info("💡 如果录入错误，只需选择同一日期重新提交一份正确的数据，系统会自动覆盖旧记录。")
    with st.form("seatable_form", clear_on_submit=True):
        d = st.date_input("业务日期", datetime.now())
        c1, c2 = st.columns(2)
        ct_p = c1.number_input("常规 CT 人数", 0, step=1)
        ct_s = c1.number_input("常规 CT 部位", 0, step=1)
        dr_p = c2.number_input("常规 DR 人数", 0, step=1)
        dr_s = c2.number_input("常规 DR 部位", 0, step=1)
        
        st.markdown("---")
        st.markdown("##### 🩺 查体业务")
        pe1, pe2, pe3 = st.columns(3)
        p_ct = pe1.number_input("查体 CT", 0)
        p_dr = pe2.number_input("查体 拍片", 0)
        p_ts = pe3.number_input("查体 透视", 0)
        
        if st.form_submit_button("🚀 提交数据"):
            try:
                base = Base(SEATABLE_API_TOKEN, SEATABLE_SERVER_URL)
                base.auth()
                row_data = {
                    "日期": str(d), "常规CT人": ct_p, "常规CT部位": ct_s,
                    "常规DR人": dr_p, "常规DR部位": dr_s,
                    "查体CT": p_ct, "查体拍片": p_dr, "查体透视": p_ts
                }
                base.append_row(TABLE_NAME, row_data)
                st.success(f"✅ {d} 数据已录入成功！")
                st.cache_data.clear() # 提交成功立即强制刷新
                st.rerun()
            except Exception as e:
                st.error("录入失败，请确认 SeaTable 列名是否完全匹配。")

else:
    st.header("📊 影像业务统计看板")
    if not df.empty:
        today = pd.Timestamp.now().normalize()
        # 统计周期：显示上周五到本周四
        current_fri = today - pd.Timedelta(days=(today.weekday() - 4 + 7) % 7)
        sw, ew = current_fri - pd.Timedelta(days=7), current_fri - pd.Timedelta(days=1)
        
        w_df = df[(df['日期'] >= sw) & (df['日期'] <= ew)]
        
        tab_week, tab_month = st.tabs(["📅 周报生成", "📈 趋势概览"])
        
        with tab_week:
            if not w_df.empty:
                st.info(f"当前统计周期：{sw.date()} 至 {ew.date()}")
                
                # 安全获取数据，若缺失列则补0
                ct_s = int(w_df.get('常规CT部位', pd.Series([0])).sum())
                ct_p = int(w_df.get('常规CT人', pd.Series([0])).sum())
                dr_s = int(w_df.get('常规DR部位', pd.Series([0])).sum())
                dr_p = int(w_df.get('常规DR人', pd.Series([0])).sum())
                pe_ts = int(w_df.get('查体透视', pd.Series([0])).sum())
                pe_dr = int(w_df.get('查体拍片', pd.Series([0])).sum())
                pe_ct = int(w_df.get('查体CT', pd.Series([0])).sum())

                report = f"{sw.strftime('%Y年%m月%d日')}至{ew.strftime('%Y年%m月%d日')}影像科工作量：\\n" \
                         f"CT：{ct_p}人，{ct_s}部位\\n" \
                         f"DR：{dr_p}人，{dr_s}部位\\n\\n" \
                         f"查体：\\n透视：{pe_ts}部位\\n拍片: {pe_dr}部位\\nCT: {pe_ct}部位"

                st.text_area("报表文本预览", report.replace('\\n', '\n'), height=240)
                universal_copy_button(report, "📋 一键复制上周报表")
            else:
                st.warning(f"周期 {sw.date()} ~ {ew.date()} 暂无数据录入")
        
        with tab_month:
            # 显示本月业务趋势
            this_month = today.replace(day=1)
            m_df = df[df['日期'] >= this_month]
            if not m_df.empty:
                st.subheader(f"{today.month} 月数据趋势")
                st.line_chart(m_df.set_index('日期')[['常规CT部位', '常规DR部位']])
            else:
                st.warning("本月暂无录入记录")

        st.markdown("---")
        st.subheader("📊 最近 10 条有效数据 (去重后)")
        st.dataframe(df.tail(10), use_container_width=True)
    else:
        st.warning("SeaTable 库中为空，请先录入。")

if st.sidebar.button("🔄 立即强制刷新"):
    st.cache_data.clear()
    st.rerun()

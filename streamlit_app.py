import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
# ⚠️ 确保 requirements.txt 里有 seatable-api
from seatable_api import Base
import streamlit.components.v1 as components

# --- 1. 核心配置 (请在此处填入你的信息) ---
# ⚠️ 这里填入刚才生成的那个长长的 API Token
SEATABLE_API_TOKEN = "18f698b812378e4d0a85de15f902fad1c205f393" 
SEATABLE_SERVER_URL = "https://cloud.seatable.cn"
TABLE_NAME = "业务数据录入" # ⚠️ 请确保和 SeaTable 里的标签页名称完全一致

SYSTEM_PASSWORD = "666"

st.set_page_config(page_title="影像科管理系统", page_icon="🏥", layout="wide")

# --- 2. 身份验证 ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🏥 影像科管理系统 - SeaTable 版")
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
        alert('✅ 报表已成功复制！');
        document.body.removeChild(textArea);
    }}
    </script>
    """
    components.html(html_code, height=60)

# --- 4. SeaTable 数据读写核心 ---
@st.cache_data(ttl=86400) # 24小时刷新一次
def get_seatable_data():
    try:
        base = Base(SEATABLE_API_TOKEN, SEATABLE_SERVER_URL)
        base.auth() # 认证
        rows = base.list_rows(TABLE_NAME) # 读取数据
        df = pd.DataFrame(rows)
        if not df.empty:
            df['日期'] = pd.to_datetime(df['日期']).dt.normalize()
            # 排除掉可能存在的空行
            return df.dropna(subset=['日期']).sort_values('日期')
        return pd.DataFrame()
    except Exception as e:
        st.sidebar.error(f"连接 SeaTable 失败，请检查 Token。")
        return pd.DataFrame()

# --- 5. 主界面逻辑 ---
st.sidebar.title(f"👨‍⚕️ andy")
menu = st.sidebar.radio("功能切换", ["📊 业务统计看板", "📝 每日数据录入"])
df = get_seatable_data()

if menu == "📝 每日数据录入":
    st.header("📝 影像业务数据录入 (SeaTable 直连)")
    st.info("💡 此处录入不经过 Google，医院内网可秒速提交。")
    with st.form("seatable_form", clear_on_submit=True):
        d = st.date_input("业务日期", datetime.now())
        c1, c2 = st.columns(2)
        ct_p = c1.number_input("常规 CT 人数", 0, step=1)
        ct_s = c1.number_input("常规 CT 部位", 0, step=1)
        dr_p = c2.number_input("常规 DR 人数", 0, step=1)
        dr_s = c2.number_input("常规 DR 部位", 0, step=1)
        
        st.markdown("---")
        st.markdown("##### 🩺 查体件数")
        pe1, pe2, pe3 = st.columns(3)
        p_ct = pe1.number_input("查体 CT", 0)
        p_dr = pe2.number_input("查体 拍片", 0)
        p_ts = pe3.number_input("查体 透视", 0)
        
        if st.form_submit_button("🚀 提交数据到 SeaTable"):
            try:
                base = Base(SEATABLE_API_TOKEN, SEATABLE_SERVER_URL)
                base.auth()
                row_data = {
                    "日期": str(d), "常规CT人": ct_p, "常规CT部位": ct_s,
                    "常规DR人": dr_p, "常规DR部位": dr_s,
                    "查体CT": p_ct, "查体拍片": p_dr, "查体透视": p_ts
                }
                base.append_row(TABLE_NAME, row_data) # 写入数据
                st.success(f"✅ {d} 数据已存入库！")
                st.cache_data.clear() # 提交后立即清理缓存
                st.rerun()
            except Exception as e:
                st.error(f"录入失败，请确认表格字段名是否正确。")

else:
    st.header("📊 影像业务周/月统计")
    if not df.empty:
        tab_week, tab_month = st.tabs(["📅 周报", "📆 月报汇总"])
        today = pd.Timestamp.now().normalize()
        
        def gen_text(data, s, e):
            return f"{s.strftime('%Y年%m月%d日')}至{e.strftime('%Y年%m月%d日')}影像科工作量：\\n" \
                   f"CT：{int(data['常规CT人'].sum())}人，{int(data['常规CT部位'].sum())}部位\\n" \
                   f"DR：{int(data['常规DR人'].sum())}人，{int(data['常规DR部位'].sum())}部位\\n\\n" \
                   f"查体：\\n透视：{int(data['查体透视'].sum())}部位\\n拍片: {int(data['查体拍片'].sum())}部位\\nCT: {int(data['查体CT'].sum())}部位"

        with tab_week:
            # 统计逻辑：上周五到本周四
            current_fri = today - pd.Timedelta(days=(today.weekday() - 4 + 7) % 7)
            sw, ew = current_fri - pd.Timedelta(days=7), current_fri - pd.Timedelta(days=1)
            w_df = df[(df['日期'] >= sw) & (df['日期'] <= ew)]
            if not w_df.empty:
                report = gen_text(w_df, sw, ew)
                st.text_area("报表内容", report.replace('\\n', '\n'), height=220)
                universal_copy_button(report, "📋 一键复制周报")
            else: st.warning("当前统计周期内暂无数据")
        
        st.markdown("---")
        st.write("📈 最近 10 条录入记录")
        st.dataframe(df.tail(10), use_container_width=True)
    else:
        st.warning("SeaTable 库中暂无数据，请先录入。")

if st.sidebar.button("🔄 立即刷新同步"):
    st.cache_data.clear()
    st.rerun()

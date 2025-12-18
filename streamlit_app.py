import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 页面配置 ---
st.set_page_config(page_title="影像科管理系统", page_icon="🏥", layout="wide")

# 从 Secrets 获取配置
BASE_URL = st.secrets["public_gsheet_url"]
# 建议在 Secrets 里新增一个 FORM_GID，或者直接写在这里
MANUAL_GID = "0"          # 初始表格的 GID (通常是 0)
FORM_GID = "720850282" # <--- 请把刚才记下的数字填在这里

@st.cache_data(ttl=60) # 录入后刷新网页即可看到，缓存设为 60 秒
def get_merged_data():
    def fetch_sheet(gid):
    # 找到文件 ID 的核心部分
    # 原始链接类似 https://docs.google.com/spreadsheets/d/ABCDEFG/edit#gid=0
    base_id = BASE_URL.split("/d/")[1].split("/")[0]
    # 构造最标准的 CSV 导出链接
    csv_url = f"https://docs.google.com/spreadsheets/d/{base_id}/export?format=csv&gid={gid}"
    
    # 打印调试信息（你可以通过 Streamlit 云端的 Logs 查看这个链接对不对）
    # st.write(f"正在尝试读取: {csv_url}") 
    
    # 使用 on_bad_lines 容错处理
    return pd.read_csv(csv_url, on_bad_lines='skip')

    # 1. 读取手动填写的旧数据
    df_manual = fetch_sheet(MANUAL_GID)
    # 2. 读取表单产生的新数据
    df_form = fetch_sheet(FORM_GID)

    # --- 关键：数据清洗与合并 ---
    # 表单数据第一列通常是"时间戳"，我们要跳过它，取后面的列
    # 假设你的表单字段顺序和之前 Excel 顺序一致
    if len(df_form.columns) > 8: 
        # 去掉第一列时间戳，只保留后面的列
        df_form = df_form.iloc[:, 1:]
    
    # 统一列名，确保合并不会出错
    columns = ['日期', '常规_CT人', '常规_CT部位', '常规_DR人', '常规_DR部位', '查体_CT', '查体_DR', '查体_透视']
    df_manual.columns = columns
    df_form.columns = columns

    # 合并两个表格
    df_combined = pd.concat([df_manual, df_form], ignore_index=True)
    df_combined['日期'] = pd.to_datetime(df_combined['日期'], errors='coerce')
    return df_combined.dropna(subset=['日期'])

# --- 3. 侧边栏导航 ---
st.sidebar.title("🛠️ 管理菜单")
menu = st.sidebar.radio("请选择操作", ["📊 查看报表", "📝 数据录入"])

if menu == "📝 数据录入":
    st.header("📝 每日影像工作量上报")
    st.info("提示：请在下方表单中填写今日数据，提交后将自动汇总至云端。")
    # 替换成你创建的 Google 表单链接
    form_url = "你的Google表单链接?embedded=true"
    st.components.v1.iframe(form_url, height=900, scrolling=True)

else:
    st.header("📊 影像科业务周报/月报")
    try:
        df = get_merged_data()
        
        # 统计逻辑
        now = datetime.now()
        offset = (3 - now.weekday())
        end_week = (now + timedelta(days=offset)).replace(hour=23, minute=59, second=59)
        start_week = (end_week - timedelta(days=6)).replace(hour=0, minute=0, second=0)

        mask = (df['日期'] >= start_week) & (df['日期'] <= end_week)
        week_data = df.loc[mask]

        if not week_data.empty:
            ct_p = int(week_data['常规_CT人'].sum())
            ct_s = int(week_data['常规_CT部位'].sum())
            dr_p = int(week_data['常规_DR人'].sum())
            dr_s = int(week_data['常规_DR部位'].sum())
            pe_ct = int(week_data['查体_CT'].sum())
            pe_dr = int(week_data['查体_DR'].sum())
            pe_ts = int(week_data['查体_透视'].sum())

            report_text = f"""{start_week.strftime('%Y年%m月%d日')}至{end_week.strftime('%Y年%m月%d日')}影像科工作量：
CT：{ct_p}人，{ct_s}部位
DR：{dr_p}人，{dr_s}部位

查体：
透视：{pe_ts}部位
拍片: {pe_dr}部位
CT: {pe_ct}部位"""

            st.text_area("📋 报表文字（直接复制）", value=report_text, height=250)
            
            # 展示汇总的小卡片，看起来更专业
            c1, c2, c3 = st.columns(3)
            c1.metric("本周 CT 总部位", ct_s)
            c2.metric("本周 DR 总部位", dr_s)
            c3.metric("本周查体总量", pe_ct + pe_dr + pe_ts)
            
        else:
            st.warning("⚠️ 本周范围内暂无数据。")

    except Exception as e:
        st.error(f"数据处理出错，请检查表格列名是否一致。错误: {e}")

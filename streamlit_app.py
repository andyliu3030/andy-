import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="影像科管理系统", page_icon="🏥", layout="wide")

# --- 2. 配置信息（请根据你的实际情况修改这几项） ---
# 建议你在 Streamlit Secrets 里设置了 public_gsheet_url
BASE_URL = st.secrets.get("public_gsheet_url", "你的Google表格地址")

# 你的标签页 ID
MANUAL_GID = "1955581250"              # 手动填写的标签页 (通常是 0)
FORM_GID = "720850282"  # <--- 请在此处填入那串长数字

# 你的 Google 表单嵌入链接
# 注意：结尾一定要带 ?embedded=true
form_url = "https://forms.gle/AzUyPeRgJnnAgEbj8?embedded=true"

# --- 3. 数据读取函数 ---
def fetch_sheet(gid):
    """从 Google Sheets 读取特定标签页并返回 DataFrame"""
    try:
        # 提取 Spreadsheet ID 并构造 CSV 链接
        base_id = BASE_URL.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{base_id}/export?format=csv&gid={gid}"
        # 读取数据，跳过损坏行
        return pd.read_csv(csv_url, on_bad_lines='skip')
    except Exception as e:
        st.error(f"读取标签页 {gid} 出错，请检查权限。错误: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_merged_data():
    """合并手动数据和表单数据"""
    df_manual = fetch_sheet(MANUAL_GID)
    df_form = fetch_sheet(FORM_GID)
    
    # 定义标准列名
    columns = ['日期', '常规_CT人', '常规_CT部位', '常规_DR人', '常规_DR部位', '查体_CT', '查体_DR', '查体_透视']
    
    # 清洗表单数据 (去掉第一列时间戳)
    if not df_form.empty and len(df_form.columns) > 8:
        df_form = df_form.iloc[:, 1:]
    
    # 强制统一列名
    if not df_manual.empty:
        df_manual.columns = columns
    if not df_form.empty:
        df_form.columns = columns
        
    # 合并
    combined = pd.concat([df_manual, df_form], ignore_index=True)
    combined['日期'] = pd.to_datetime(combined['日期'], errors='coerce')
    return combined.dropna(subset=['日期'])

# --- 4. 侧边栏导航 ---
st.sidebar.title("👨‍⚕️ Andy 的管理后台")
menu = st.sidebar.radio("功能切换", ["📊 查看业务报表", "📝 每日数据录入"])

# --- 5. 逻辑实现 ---
if menu == "📝 每日数据录入":
    st.header("📝 每日影像工作量上报")
    st.markdown("---")
    # 嵌入 Google 表单
    st.components.v1.iframe(form_url, height=850, scrolling=True)

else:
    st.header("📊 影像业务汇总看板")
    st.markdown("---")
    
    try:
        df = get_merged_data()
        
        # 计算周统计范围（上周五到本周四）
        now = datetime.now()
        offset = (3 - now.weekday())
        end_week = (now + timedelta(days=offset)).replace(hour=23, minute=59, second=59)
        start_week = (end_week - timedelta(days=6)).replace(hour=0, minute=0, second=0)

        # 筛选数据
        mask = (df['日期'] >= start_week) & (df['日期'] <= end_week)
        week_data = df.loc[mask]

        if not week_data.empty:
            # 求和计算
            ct_p = int(week_data['常规_CT人'].sum())
            ct_s = int(week_data['常规_CT部位'].sum())
            dr_p = int(week_data['常规_DR人'].sum())
            dr_s = int(week_data['常规_DR部位'].sum())
            pe_ct = int(week_data['查体_CT'].sum())
            pe_dr = int(week_data['查体_DR'].sum())
            pe_ts = int(week_data['查体_透视'].sum())

            # 生成报表文本
            report_text = f"{start_week.strftime('%Y年%m月%d日')}至{end_week.strftime('%Y年%m月%d日')}影像科工作量：\n" \
                          f"CT：{ct_p}人，{ct_s}部位\n" \
                          f"DR：{dr_p}人，{dr_s}部位\n\n" \
                          f"查体：\n" \
                          f"透视：{pe_ts}部位\n" \
                          f"拍片: {pe_dr}部位\n" \
                          f"CT: {pe_ct}部位"

            # 界面展示
            col1, col2, col3 = st.columns(3)
            col1.metric("常规 CT 部位", ct_s)
            col2.metric("常规 DR 部位", dr_s)
            col3.metric("总查体量", pe_ct + pe_dr + pe_ts)

            st.subheader("📋 复制报表文字")
            st.text_area("直接全选复制即可发送至微信群：", value=report_text, height=220)
            
            if st.button("🔄 立即刷新云端数据"):
                st.cache_data.clear()
                st.rerun()
        else:
            st.warning("📅 本周统计范围内暂无数据，请确认员工是否已通过【数据录入】提交。")

    except Exception as e:
        st.error(f"⚠️ 统计失败，请确保表格和表单的字段顺序一致。详细错误: {e}")

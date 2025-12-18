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

# --- 3. 核心功能函数 ---

def fetch_sheet(gid):
    """从 Google Sheets 安全读取 CSV 数据"""
    try:
        # 清理并解析 URL 提取 Spreadsheet ID
        clean_url = BASE_URL.strip()
        base_id = clean_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{base_id}/export?format=csv&gid={gid}"
        return pd.read_csv(csv_url, on_bad_lines='skip')
    except Exception as e:
        st.error(f"读取标签页 {gid} 失败。请检查表格【分享】权限是否为【任何知道链接的人】。")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_merged_data():
    """合并手动数据和表单自动生成的数据"""
    df_manual = fetch_sheet(MANUAL_GID)
    df_form = fetch_sheet(FORM_GID)
    
    # 定义标准列名 (对应你表格的 8 个核心数据列)
    columns = ['日期', '常规CT人', '常规CT部位', '常规DR人', '常规DR部位', '查体CT', '查体DR', '查体透视']
    
    # 处理表单数据 (根据截屏：A列是时间戳记，B列才是日期)
    if not df_form.empty:
        # 丢弃第一列“时间戳记”，保留后面的列
        if len(df_form.columns) > 8:
            df_form = df_form.iloc[:, 1:]
        df_form.columns = columns
    
    # 处理手动数据
    if not df_manual.empty:
        df_manual.columns = columns
        
    # 合并两个数据源
    combined = pd.concat([df_manual, df_form], ignore_index=True)
    combined['日期'] = pd.to_datetime(combined['日期'], errors='coerce')
    return combined.dropna(subset=['日期'])

# --- 4. 界面展示逻辑 ---

st.sidebar.title("👨‍⚕️ Andy 的管理后台")
menu = st.sidebar.radio("请选择功能", ["📊 查看业务报表", "📝 每日数据录入"])

if menu == "📝 每日数据录入":
    st.header("📝 每日影像工作量上报")
    st.info("请在下方填写数据并提交。完成后，点击左侧【查看业务报表】即可看到汇总结果。")
    st.markdown("---")
    # 嵌入 Google 表单 (确保 form_url 正确)
    st.components.v1.iframe(form_url, height=900, scrolling=True)

else:
    st.header("📊 影像业务汇总看板")
    st.markdown("---")
    
    try:
        df = get_merged_data()
        
        # 统计逻辑：上周五到本周四
        now = datetime.now()
        day = now.getDay() if hasattr(now, 'getDay') else now.weekday()
        # 转换：Python weekday 0=周一, 6=周日
        # 目标：计算本周四
        offset = (3 - day) if day <= 3 else (3 - day + 7)
        end_week = (now + timedelta(days=offset)).replace(hour=23, minute=59, second=59)
        start_week = (end_week - timedelta(days=6)).replace(hour=0, minute=0, second=0)

        # 筛选本周数据
        mask = (df['日期'] >= start_week) & (df['日期'] <= end_week)
        week_data = df.loc[mask]

        if not week_data.empty:
            # 汇总计算
            ct_p = int(week_data['常规CT人'].sum())
            ct_s = int(week_data['常规CT部位'].sum())
            dr_p = int(week_data['常规DR人'].sum())
            dr_s = int(week_data['常规DR部位'].sum())
            pe_ct = int(week_data['查体CT'].sum())
            pe_dr = int(week_data['查体DR'].sum())
            pe_ts = int(week_data['查体透视'].sum())

            # 顶部核心指标卡片
            c1, c2, c3 = st.columns(3)
            c1.metric("本周常规 CT 部位", f"{ct_s} 部位")
            c2.metric("本周常规 DR 部位", f"{dr_s} 部位")
            c3.metric("总查体量", f"{pe_ct + pe_dr + pe_ts} 部位")

            # 报表文字区域
            st.subheader("📋 报表文字 (直接复制)")
            report_text = f"{start_week.strftime('%Y年%m月%d日')}至{end_week.strftime('%Y年%m月%d日')}影像科工作量：\n" \
                          f"CT：{ct_p}人，{ct_s}部位\n" \
                          f"DR：{dr_p}人，{dr_s}部位\n\n" \
                          f"查体：\n" \
                          f"透视：{pe_ts}部位\n" \
                          f"拍片: {pe_dr}部位\n" \
                          f"CT: {pe_ct}部位"
            
            st.text_area("复制下方文字发至微信群：", value=report_text, height=220)
            
            if st.button("🔄 强制刷新同步云端"):
                st.cache_data.clear()
                st.rerun()
        else:
            st.warning("📅 本周统计范围内暂无数据。请检查数据录入日期是否正确。")

    except Exception as e:
        st.error(f"⚠️ 数据处理出错。请检查表格标签页 ID (GID) 是否填错。错误详情: {e}")

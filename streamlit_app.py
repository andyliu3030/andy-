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
    try:
        clean_url = BASE_URL.strip()
        base_id = clean_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{base_id}/export?format=csv&gid={gid}"
        return pd.read_csv(csv_url, on_bad_lines='skip')
    except Exception as e:
        st.error(f"读取标签页 {gid} 失败。错误: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_merged_data():
    """合并数据并实现：同日期自动覆盖（保留最后一次提交）"""
    df_manual = fetch_sheet(MANUAL_GID)
    df_form = fetch_sheet(FORM_GID)
    
    columns = ['日期', '常规CT人', '常规CT部位', '常规DR人', '常规DR部位', '查体CT', '查体DR', '查体透视']
    
    # 1. 处理表单数据 (含时间戳)
    if not df_form.empty:
        # 表单数据通常第一列是系统自动生成的“时间戳记”
        # 我们利用这个时间戳来判断哪一个是“最新提交的”
        df_form.columns = ['提交时间'] + columns
        # 转换日期格式
        df_form['日期'] = pd.to_datetime(df_form['日期'], errors='coerce').dt.normalize()
        # 按照“提交时间”排序，确保最新的在最后
        df_form = df_form.sort_values('提交时间')
        # 只保留核心数据列，去掉时间戳
        df_form = df_form[columns]
    
    # 2. 处理手动数据
    if not df_manual.empty:
        df_manual.columns = columns
        df_manual['日期'] = pd.to_datetime(df_manual['日期'], errors='coerce').dt.normalize()
        
    # 3. 合并数据源
    # 注意：我们将 df_form 放在后面，这样在去重时，表单数据会优先覆盖手动数据
    combined = pd.concat([df_manual, df_form], ignore_index=True)
    
    # --- 核心逻辑：去重覆盖 ---
    # 根据“日期”列去重，keep='last' 表示如果有重复日期，保留列表中的最后一个（即最新的）
    combined = combined.sort_values('日期') # 先按业务日期排序
    combined = combined.drop_duplicates(subset=['日期'], keep='last')
    
    return combined.dropna(subset=['日期'])

# --- 4. 界面逻辑 ---

st.sidebar.title("👨‍⚕️ Andy 的管理后台")
menu = st.sidebar.radio("请选择功能", ["📊 查看业务报表", "📝 每日数据录入"])

if menu == "📝 每日数据录入":
    st.header("📝 每日影像工作量上报")
    st.info("💡 填错了吗？没关系，只需针对同一日期重新提交一份正确的数据，系统将自动覆盖旧数据。")
    st.components.v1.iframe(form_url, height=900, scrolling=True)

else:
    st.header("📊 影像业务汇总看板")
    st.markdown("---")
    
    try:
        df = get_merged_data()
        
        # 日期计算逻辑：上周五到本周四
        today = pd.Timestamp.now().normalize() 
        day_of_week = today.weekday()
        
        if day_of_week == 4: # 今天是周五
            start_week = today
            end_week = today + pd.Timedelta(days=6)
        else: # 今天是周六至下周四
            days_since_friday = (today.weekday() - 4 + 7) % 7
            start_week = today - pd.Timedelta(days=days_since_friday)
            end_week = start_week + pd.Timedelta(days=6)

        mask = (df['日期'] >= start_week) & (df['日期'] <= end_week)
        week_data = df.loc[mask]

        if not week_data.empty:
            ct_p = int(week_data['常规CT人'].sum())
            ct_s = int(week_data['常规CT部位'].sum())
            dr_p = int(week_data['常规DR人'].sum())
            dr_s = int(week_data['常规DR部位'].sum())
            pe_ct = int(week_data['查体CT'].sum())
            pe_dr = int(week_data['查体DR'].sum())
            pe_ts = int(week_data['查体透视'].sum())

            # 核心卡片展示
            col1, col2, col3 = st.columns(3)
            col1.metric("常规 CT 部位", f"{ct_s}")
            col2.metric("常规 DR 部位", f"{dr_s}")
            col3.metric("总查体量", f"{pe_ct + pe_dr + pe_ts}")

            st.subheader("📋 报表文字 (已启用唯一性覆盖)")
            report_text = f"{start_week.strftime('%Y年%m月%d日')}至{end_week.strftime('%Y年%m月%d日')}影像科工作量：\n" \
                          f"CT：{ct_p}人，{ct_s}部位\n" \
                          f"DR：{dr_p}人，{dr_s}部位\n\n" \
                          f"查体：\n" \
                          f"透视：{pe_ts}部位\n" \
                          f"拍片: {pe_dr}部位\n" \
                          f"CT: {pe_ct}部位"
            
            st.text_area("复制发至微信群：", value=report_text, height=220)
            st.caption(f"统计范围：{start_week.date()} 到 {end_week.date()} | 💡 如有重复日期，仅统计最新提交的一笔数据。")
        else:
            st.warning(f"📅 周期 {start_week.date()} 至 {end_week.date()} 暂无数据。")

    except Exception as e:
        st.error(f"数据处理异常: {e}")

if st.sidebar.button("🔄 立即强制刷新"):
    st.cache_data.clear()
    st.rerun()

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
    df_manual = fetch_sheet(MANUAL_GID)
    df_form = fetch_sheet(FORM_GID)
    
    columns = ['日期', '常规CT人', '常规CT部位', '常规DR人', '常规DR部位', '查体CT', '查体DR', '查体透视']
    
    if not df_form.empty:
        # 截屏显示：表单表第一列是时间戳，需要切掉
        if len(df_form.columns) > 8:
            df_form = df_form.iloc[:, 1:]
        df_form.columns = columns
    
    if not df_manual.empty:
        df_manual.columns = columns
        
    combined = pd.concat([df_manual, df_form], ignore_index=True)
    
    # 关键点：强制转换为日期，并抹去具体时间，只保留年月日
    combined['日期'] = pd.to_datetime(combined['日期'], errors='coerce').dt.normalize()
    return combined.dropna(subset=['日期'])

# --- 4. 界面逻辑 ---

st.sidebar.title("👨‍⚕️ Andy 的管理后台")
menu = st.sidebar.radio("请选择功能", ["📊 查看业务报表", "📝 每日数据录入"])

if menu == "📝 每日数据录入":
    st.header("📝 每日影像工作量上报")
    st.components.v1.iframe(form_url, height=900, scrolling=True)

else:
    st.header("📊 影像业务汇总看板")
    st.markdown("---")
    
    try:
        df = get_merged_data()
        
        # --- 修正后的日期计算逻辑 ---
        # 设定今天为基准，抹去时间
        today = pd.Timestamp.now().normalize() 
        # 找到最近的周四 (weekday: 0=Mon, 3=Thu, 6=Sun)
        # 如果今天是周五(4)、周六(5)、周日(6)，周四在未来；如果今天是周一至周四，周四在今天或过去
        days_to_thursday = (3 - today.weekday() + 7) % 7
        if today.weekday() > 3: # 如果过了周四，则取本周四
             end_week = today + pd.Timedelta(days=days_to_thursday)
        else: # 如果在周四之前或当天，计算逻辑一致
             end_week = today + pd.Timedelta(days=days_to_thursday)
        
        # 修正：Andy 的逻辑是统计【当前周期】。
        # 如果今天是周四，end_week 就是今天；start_week 是上周五（6天前）
        # 如果今天是周五，end_week 是下周四；start_week 是今天
        day_of_week = today.weekday()
        if day_of_week == 4: # 今天是周五
            start_week = today
            end_week = today + pd.Timedelta(days=6)
        else: # 今天是周六至下周四
            # 找到之前的那个周五
            days_since_friday = (today.weekday() - 4 + 7) % 7
            start_week = today - pd.Timedelta(days=days_since_friday)
            end_week = start_week + pd.Timedelta(days=6)

        # 再次确保范围边界是纯日期
        start_week = start_week.normalize()
        end_week = end_week.normalize()

        # 筛选：使用强制包含边界的方法
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

            # 核心卡片
            c1, c2, c3 = st.columns(3)
            c1.metric("常规 CT 部位", f"{ct_s}")
            c2.metric("常规 DR 部位", f"{dr_s}")
            c3.metric("总查体量", f"{pe_ct + pe_dr + pe_ts}")

            st.subheader("📋 报表文字 (已包含上周五数据)")
            report_text = f"{start_week.strftime('%Y年%m月%d日')}至{end_week.strftime('%Y年%m月%d日')}影像科工作量：\n" \
                          f"CT：{ct_p}人，{ct_s}部位\n" \
                          f"DR：{dr_p}人，{dr_s}部位\n\n" \
                          f"查体：\n" \
                          f"透视：{pe_ts}部位\n" \
                          f"拍片: {pe_dr}部位\n" \
                          f"CT: {pe_ct}部位"
            
            st.text_area("复制发至微信群：", value=report_text, height=220)
            st.caption(f"当前统计周期：{start_week.date()} (周五) 00:00 到 {end_week.date()} (周四) 23:59")
        else:
            st.warning(f"📅 周期 {start_week.date()} 至 {end_week.date()} 暂无数据。")

    except Exception as e:
        st.error(f"数据处理异常: {e}")

if st.sidebar.button("🔄 立即强制刷新"):
    st.cache_data.clear()
    st.rerun()

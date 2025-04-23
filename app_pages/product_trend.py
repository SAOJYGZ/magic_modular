import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from api import get_trade_data

def render():
    st.header("客户产品趋势分析")
    data = get_trade_data()
    if not data:
        st.write("无法获取交易数据，无法进行趋势分析。")
        return
    df = pd.DataFrame(data)

    # 统一日期字段为 Python date
    df['startDate_dt'] = pd.to_datetime(
        df.get('tradeStartDate', df.get('startDate')),
        errors='coerce'
    ).dt.date
    df['tradeTerminationDate_dt'] = pd.to_datetime(
        df['tradeTerminationDate'],
        errors='coerce'
    ).dt.date

    # —— 参数选择区 —— #
    st.subheader("请选择分析参数")
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_type = st.radio(
            "指标类型",
            ["当期新增", "累计新增", "当期了结", "累计了结", "期末存续"],
            horizontal=True
        )
    with col2:
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=365)
        trend_range = st.date_input(
            "选择分析日期范围",
            [default_start, today]
        )
        if len(trend_range) != 2:
            st.error("请选择起始和结束日期")
            return
        trend_start, trend_end = trend_range
    with col3:
        freq = st.radio("聚合周期", ["周", "月"], horizontal=True)

    # —— 侧边栏筛选区 —— #
    types = df['tradeType'].dropna().unique().tolist() if 'tradeType' in df.columns else []
    products = df['productType'].dropna().unique().tolist() if 'productType' in df.columns else []
    cptys = df['counterparty'].dropna().unique().tolist() if 'counterparty' in df.columns else []
    selected_types = st.sidebar.multiselect("交易类型", options=types, default=types)
    all_cptys = st.sidebar.checkbox("全选交易对手方", value=True)
    default_cptys = cptys if all_cptys else []
    selected_cptys = st.sidebar.multiselect("交易对手方", options=cptys, default=default_cptys)
    selected_product = st.sidebar.selectbox("产品类型(单选)", options=products)
    indicator = st.sidebar.selectbox("选择绘图指标", ["名义本金", "保证金"] )

    # 数据过滤
    df_f = df[
        df['tradeType'].isin(selected_types) &
        df['counterparty'].isin(selected_cptys) &
        (df['productType'] == selected_product)
    ].copy()
    if df_f.empty:
        st.warning("无符合条件的数据。")
        return

    freq_str = 'W' if freq == '周' else 'M'

    # 非期末存续逻辑
    if metric_type != '期末存续':
        date_field = 'startDate_dt' if '新增' in metric_type else 'tradeTerminationDate_dt'
        if '当期' in metric_type:
            df_m = df_f[(df_f[date_field] >= trend_start) & (df_f[date_field] <= trend_end)]
        else:
            df_m = df_f[df_f[date_field] <= trend_end]

        df_m['名义本金'] = df_m['notionalPrincipal'].astype(float).fillna(0)
        df_m['保证金'] = df_m['名义本金'] * df_m['marginRatio'].astype(float).fillna(0)
        df_m['日期'] = pd.to_datetime(df_m[date_field])
        df_m['周期'] = df_m['日期'].dt.to_period(freq_str).dt.to_timestamp()
        agg = df_m.groupby(['周期', 'counterparty'], as_index=False)[[indicator]].sum()
    else:
        # 期末存续逻辑
        df_o = df_f[df_f['startDate_dt'] <= trend_end].copy()
        df_o['名义本金'] = df_o['notionalPrincipal'].astype(float).fillna(0)
        df_o['保证金'] = df_o['名义本金'] * df_o['marginRatio'].astype(float).fillna(0)
        points = pd.date_range(trend_start, trend_end, freq=freq_str)
        frames = []
        for t in points:
            t_date = t.date()
            sel = df_o[
                (df_o['startDate_dt'] <= t_date) &
                ((df_o['tradeTerminationDate_dt'].isna()) | (df_o['tradeTerminationDate_dt'] >= t_date))
            ]
            if sel.empty:
                continue
            grp = sel.groupby('counterparty', as_index=False)[[indicator]].sum()
            grp['周期'] = pd.to_datetime(t_date)
            frames.append(grp)
        if not frames:
            st.write("在所选时间区间内未找到期末存续数据。")
            return
        agg = pd.concat(frames, ignore_index=True)

    # 绘图：堆叠直方图
    st.subheader(f"{selected_product} {metric_type}（按{freq}）—{indicator}堆叠直方图")
    fig_stack = px.bar(
        agg,
        x='周期', y=indicator,
        color='counterparty',
        barmode='stack',
        labels={'counterparty': '交易对手方', indicator: indicator},
        title=f"{selected_product} {metric_type} {indicator} 各交易对手方堆叠图"
    )
    fig_stack.update_layout(legend_title_text='交易对手方')
    st.plotly_chart(fig_stack, use_container_width=True)

    # 绘图：分组直方图（汇总）
    st.subheader(f"{selected_product} {metric_type}（按{freq}）—{indicator}汇总直方图")
    # 按周期汇总所有交易对手方
    sum_df = agg.groupby('周期', as_index=False)[indicator].sum()
    fig_group = px.bar(
        sum_df,
        x='周期', y=indicator,
        labels={indicator: indicator},
        title=f"{selected_product} {metric_type} {indicator} 汇总"
    )
    st.plotly_chart(fig_group, use_container_width=True)
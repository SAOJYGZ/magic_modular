import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from api import get_trade_data
from classification import apply_classification, classification_options

def format_product_title(products: list[str]) -> str:
    """将产品列表格式化为 a、b 和 c 的形式"""
    if not products:
        return ""
    if len(products) == 1:
        return products[0]
    if len(products) == 2:
        return products[0] + '和' + products[1]
    return '、'.join(products[:-1]) + '和' + products[-1]


def render():
    st.header("客户产品趋势分析")
    data = get_trade_data()
    if not data:
        st.write("无法获取交易数据，无法进行趋势分析。")
        return
    df = pd.DataFrame(data)

    # counterparty classification
    df = apply_classification(df)
    class_opts = classification_options()
    all_class = st.checkbox("全选对手方分类", value=True)
    default_classes = class_opts if all_class else []
    selected_classes = st.multiselect(
        "对手方分类", options=class_opts, default=default_classes
    )
    df = df[df['分类'].isin(selected_classes)]
    if df.empty:
        st.warning("选择的分类下没有数据。")
        return

    # parameter selection
    st.subheader("请选择分析参数")
    col1, col2, col3, col4 = st.columns(4)
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
    with col4:
        indicator = st.selectbox(
            "选择绘图指标",
            ["名义本金", "保证金"]
        )

    # sidbar filters
    types = df['tradeType'].dropna().unique().tolist() if 'tradeType' in df.columns else []
    products = df['productType'].dropna().unique().tolist() if 'productType' in df.columns else []
    cptys = df['counterparty'].dropna().unique().tolist() if 'counterparty' in df.columns else []
    selected_types = st.sidebar.multiselect("交易类型", options=types, default=types)
    selected_cptys = st.sidebar.multiselect("交易对手方", options=cptys, default=cptys)
    selected_products = st.sidebar.multiselect("产品类型(多选)", options=products, default=products)

    if not selected_products:
        st.warning("请至少选择一个产品类型！")
        return

    product_title = format_product_title(selected_products)

    # data cleaning
    df_f = df[
        df['tradeType'].isin(selected_types) &
        df['counterparty'].isin(selected_cptys) &
        df['productType'].isin(selected_products)
    ].copy()
    if df_f.empty:
        st.warning("无符合侧边栏筛选条件的数据。")
        return

    freq_str = 'W' if freq == '周' else 'M'

    # data preprocessing
    if metric_type != '期末存续':
        date_field = 'startDate_dt' if '新增' in metric_type else 'tradeTerminationDate_dt'
        df_f['startDate_dt'] = pd.to_datetime(df_f.get('tradeStartDate', df_f.get('startDate')), errors='coerce').dt.date
        df_f['tradeTerminationDate_dt'] = pd.to_datetime(df_f['tradeTerminationDate'], errors='coerce').dt.date
        if '当期' in metric_type:
            df_sel = df_f[(df_f[date_field] >= trend_start) & (df_f[date_field] <= trend_end)]
        else:
            df_sel = df_f[df_f[date_field] <= trend_end]
        df_sel['名义本金'] = df_sel['notionalPrincipal'].astype(float).fillna(0)
        df_sel['保证金'] = df_sel['名义本金'] * df_sel['marginRatio'].astype(float).fillna(0)
        df_sel['日期'] = pd.to_datetime(df_sel[date_field])
        df_sel['周期'] = df_sel['日期'].dt.to_period(freq_str).dt.to_timestamp()
        agg = df_sel.groupby(['周期', 'counterparty'], as_index=False)[['名义本金', '保证金']].sum()
        agg = agg[['周期', 'counterparty', indicator]]
    else:
        df_f['startDate_dt'] = pd.to_datetime(df_f.get('tradeStartDate', df_f.get('startDate')), errors='coerce').dt.date
        df_f['tradeTerminationDate_dt'] = pd.to_datetime(df_f['tradeTerminationDate'], errors='coerce').dt.date
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
            grp = sel.groupby('counterparty', as_index=False)[['名义本金', '保证金']].sum()
            grp = grp[['counterparty', indicator]]
            grp['周期'] = pd.to_datetime(t_date)
            frames.append(grp)
        if not frames:
            st.write("在所选时间区间内未找到期末存续数据。")
            return
        agg = pd.concat(frames, ignore_index=True)

    # plot
    st.subheader(f"{product_title} {metric_type}（按{freq}）—{indicator}堆叠直方图")
    fig_stack = px.bar(
        agg,
        x='周期', y=indicator,
        color='counterparty',
        barmode='stack',
        labels={'counterparty': '交易对手方', indicator: indicator},
        title=f"{product_title} {metric_type} {indicator} 各交易对手方堆叠图"
    )
    fig_stack.update_layout(legend_title_text='交易对手方')
    st.plotly_chart(fig_stack, use_container_width=True)

    st.subheader(f"{product_title} {metric_type}（按{freq}）—{indicator}汇总直方图")
    sum_df = agg.groupby('周期', as_index=False)[indicator].sum()
    fig_sum = px.bar(
        sum_df,
        x='周期', y=indicator,
        labels={indicator: indicator},
        title=f"{product_title} {metric_type} {indicator} 汇总"
    )
    st.plotly_chart(fig_sum, use_container_width=True)

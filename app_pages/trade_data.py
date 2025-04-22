import streamlit as st
import pandas as pd
from collections import defaultdict
import plotly.express as px
from api import get_trade_data


def render():
    st.header("交易数据分析")
    data = get_trade_data()
    if not data:
        st.write("无法获取交易数据，或暂无数据。")
        return
    df = pd.DataFrame(data)

    status_options = df['tradeStatus'].dropna().unique().tolist() if 'tradeStatus' in df.columns else []
    type_options   = df['tradeType'].dropna().unique().tolist()   if 'tradeType' in df.columns else []
    prod_options   = df['productType'].dropna().unique().tolist() if 'productType' in df.columns else []
    cpty_options   = df['counterparty'].dropna().unique().tolist() if 'counterparty' in df.columns else []
    for opts in [status_options, type_options, prod_options, cpty_options]:
        opts.sort()

    selected_status = st.sidebar.multiselect("交易状态", options=status_options, default=status_options)
    selected_types  = st.sidebar.multiselect("交易类型", options=type_options, default=type_options)
    selected_prods  = st.sidebar.multiselect("产品类型", options=prod_options, default=prod_options)
    selected_cptys  = st.sidebar.multiselect("交易对手方", options=cpty_options, default=cpty_options)

    df_filtered = df.copy()
    if selected_status:
        df_filtered = df_filtered[df_filtered['tradeStatus'].isin(selected_status)]
    if selected_types:
        df_filtered = df_filtered[df_filtered['tradeType'].isin(selected_types)]
    if selected_prods:
        df_filtered = df_filtered[df_filtered['productType'].isin(selected_prods)]
    if selected_cptys:
        df_filtered = df_filtered[df_filtered['counterparty'].isin(selected_cptys)]

    if df_filtered.empty:
        st.warning("没有满足筛选条件的交易数据。")
        return

    res = defaultdict(lambda: defaultdict(int))
    for trade in df_filtered.to_dict(orient='records'):
        if trade['productType'] != 'Phoenix':
            res[trade['counterparty']][f"{trade['productType']} TradeTerminationPayoff"] += trade.get('tradeTerminationPayoff', 0)
            res[trade['counterparty']][f"{trade['productType']} NotionalPrincipal"] += trade.get('notionalPrincipal', 0)
            res[trade['counterparty']]['Total TradeTerminationPayoff'] += trade.get('tradeTerminationPayoff', 0)
        else:
            coupons = trade.get('couponsPaid', [])
            res[trade['counterparty']]['Phoenix TradeTerminationPayoff'] += sum(coupons)
            res[trade['counterparty']][f"{trade['productType']} NotionalPrincipal"] += trade.get('notionalPrincipal', 0)
            res[trade['counterparty']]['Total TradeTerminationPayoff'] += sum(coupons)
        res[trade['counterparty']]['Total NotionalPrincipal'] += trade.get('notionalPrincipal', 0)

    def translate_column(col):
        mapping = {
            'Trinary Snowball TradeTerminationPayoff': '三元雪球了结收益',
            'Trinary Snowball NotionalPrincipal': '三元雪球名义本金',
            'Autocallable Airbag TradeTerminationPayoff': '锁盈缓冲了结收益',
            'Autocallable Airbag NotionalPrincipal': '锁盈缓冲名义本金',
            'Autocall Binary TradeTerminationPayoff': '自动赎回二元了结收益',
            'Autocall Binary NotionalPrincipal': '自动赎回二元名义本金',
            'Phoenix TradeTerminationPayoff': '凤凰了结收益',
            'Phoenix NotionalPrincipal': '凤凰名义本金',
            'Total TradeTerminationPayoff': '总了结收益',
            'Total NotionalPrincipal': '总名义本金',
            'Snowball TradeTerminationPayoff': '雪球了结收益',
            'Snowball NotionalPrincipal': '雪球名义本金',
            'Binary TradeTerminationPayoff': '二元了结收益',
            'Binary NotionalPrincipal': '二元名义本金',
            'Vanilla TradeTerminationPayoff': '香草了结收益',
            'Vanilla NotionalPrincipal': '香草名义本金',
            'Shark Fin TradeTerminationPayoff': '鲨鱼鳍了结收益',
            'Shark Fin NotionalPrincipal': '鲨鱼鳍名义本金'
        }
        for key in sorted(mapping.keys(), key=lambda k: len(k), reverse=True):
            col = col.replace(key, mapping[key])
        return col

    df_res = pd.DataFrame(res).T.fillna(0)
    df_res.columns = [translate_column(col) for col in df_res.columns]
    priority_cols = ['总了结收益','总名义本金']
    other_cols = [c for c in df_res.columns if c not in priority_cols]
    df_res = df_res[priority_cols + other_cols]

    st.subheader("交易数据展示")
    df_copy = df_res.reset_index()
    df_copy.insert(0, "序号", range(1, len(df_copy)+1))
    df_copy.rename(columns={"index": "交易对手方"}, inplace=True)
    st.data_editor(df_copy, num_rows="dynamic")

    df_reset = df_res.reset_index().rename(columns={df_res.reset_index().columns[0]: 'counterparty'})
    melted_df = df_reset.melt(id_vars=['counterparty'], var_name='product', value_name='value')
    melted_df.rename(columns={'counterparty':'交易对手方', 'product':'产品', 'value':'数值'}, inplace=True)
    selected_metric = st.sidebar.radio("选择指标", options=["了结收益","名义本金"], index=0)
    melted_df = melted_df[melted_df['产品'].str.contains(selected_metric)]

    st.subheader("皇家堆叠直方图")
    fig_stack = px.bar(
        melted_df,
        x='数值', y='交易对手方', color='产品', barmode='stack',
        labels={'交易对手方':'交易对手方','数值':'已了结收益/本金','产品':'产品'},
        title="各交易对手方在不同产品下的堆叠直方图"
    )
    df_sort = melted_df.groupby('交易对手方', as_index=False)['数值'].sum()
    sorted_order = df_sort.sort_values('数值')['交易对手方'].tolist()
    fig_stack.update_yaxes(categoryorder='array', categoryarray=sorted_order)
    st.plotly_chart(fig_stack, use_container_width=True)

    st.subheader("皇家饼图")
    pie_df = melted_df.groupby('交易对手方', as_index=False)['数值'].sum()
    fig_pie = px.pie(pie_df, names='交易对手方', values='数值', title="各交易对手方在所有产品下的占比")
    st.plotly_chart(fig_pie, use_container_width=True)

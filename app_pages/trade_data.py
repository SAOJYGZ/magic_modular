import streamlit as st
import pandas as pd
from collections import defaultdict
import plotly.express as px
from api import get_trade_data
from classification import apply_classification, classification_options

def render():
    st.header("交易数据分析")

    # 1) 获取原始交易数据
    data = get_trade_data()
    if not data:
        st.write("无法获取交易数据，或暂无数据。")
        return
    df = pd.DataFrame(data)

    # 2) 应用对手方分类
    df = apply_classification(df)
    class_opts = classification_options()
    # 全选分类按钮
    all_class = st.checkbox("全选对手方分类", value=True)
    default_classes = class_opts if all_class else []
    selected_classes = st.multiselect(
        "对手方分类", options=class_opts, default=default_classes
    )
    df = df[df['分类'].isin(selected_classes)]

    # 3) 侧边栏：状态、类型、产品、对手方 筛选
    status_opts = df['tradeStatus'].dropna().unique().tolist() if 'tradeStatus' in df.columns else []
    type_opts   = df['tradeType'].dropna().unique().tolist()   if 'tradeType' in df.columns else []
    prod_opts   = df['productType'].dropna().unique().tolist() if 'productType' in df.columns else []
    cpty_opts   = df['counterparty'].dropna().unique().tolist() if 'counterparty' in df.columns else []
    for opts in [status_opts, type_opts, prod_opts, cpty_opts]:
        opts.sort()

    st.sidebar.header("其他筛选")
    selected_status = st.sidebar.multiselect("交易状态", options=status_opts, default=status_opts)
    selected_types  = st.sidebar.multiselect("交易类型", options=type_opts, default=type_opts)
    selected_prods  = st.sidebar.multiselect("产品类型", options=prod_opts, default=prod_opts)
    selected_cptys  = st.sidebar.multiselect("交易对手方", options=cpty_opts, default=cpty_opts)

    # 4) 应用侧边栏筛选
    df_f = df.copy()
    if selected_status:
        df_f = df_f[df_f['tradeStatus'].isin(selected_status)]
    if selected_types:
        df_f = df_f[df_f['tradeType'].isin(selected_types)]
    if selected_prods:
        df_f = df_f[df_f['productType'].isin(selected_prods)]
    if selected_cptys:
        df_f = df_f[df_f['counterparty'].isin(selected_cptys)]

    if df_f.empty:
        st.warning("没有满足筛选条件的交易数据。")
        return

    # 5) 聚合计算
    res = defaultdict(lambda: defaultdict(int))
    for trade in df_f.to_dict(orient='records'):
        pt = trade.get('productType','')
        cp = trade.get('counterparty','')
        payoff = trade.get('tradeTerminationPayoff',0)
        notional = trade.get('notionalPrincipal',0)
        if pt != 'Phoenix':
            res[cp][f"{pt} TradeTerminationPayoff"]   += payoff
            res[cp][f"{pt} NotionalPrincipal"]         += notional
            res[cp]['Total TradeTerminationPayoff']     += payoff
        else:
            coupons = trade.get('couponsPaid',[])
            res[cp]['Phoenix TradeTerminationPayoff']  += sum(coupons)
            res[cp][f"{pt} NotionalPrincipal"]         += notional
            res[cp]['Total TradeTerminationPayoff']     += sum(coupons)
        res[cp]['Total NotionalPrincipal']            += notional

    # 6) 列名翻译
    def translate_column(col: str) -> str:
        mapping = {
            'Trinary Snowball TradeTerminationPayoff': '三元雪球了结收益',
            'Trinary Snowball NotionalPrincipal':     '三元雪球名义本金',
            'Autocallable Airbag TradeTerminationPayoff': '锁盈缓冲了结收益',
            'Autocallable Airbag NotionalPrincipal':     '锁盈缓冲名义本金',
            'Autocall Binary TradeTerminationPayoff':    '自动赎回二元了结收益',
            'Autocall Binary NotionalPrincipal':         '自动赎回二元名义本金',
            'Phoenix TradeTerminationPayoff':            '凤凰了结收益',
            'Phoenix NotionalPrincipal':                 '凤凰名义本金',
            'Total TradeTerminationPayoff':              '总了结收益',
            'Total NotionalPrincipal':                   '总名义本金',
            'Snowball TradeTerminationPayoff':           '雪球了结收益',
            'Snowball NotionalPrincipal':                '雪球名义本金',
            'Binary TradeTerminationPayoff':             '二元了结收益',
            'Binary NotionalPrincipal':                  '二元名义本金',
            'Vanilla TradeTerminationPayoff':            '香草了结收益',
            'Vanilla NotionalPrincipal':                 '香草名义本金',
            'Shark Fin TradeTerminationPayoff':          '鲨鱼鳍了结收益',
            'Shark Fin NotionalPrincipal':               '鲨鱼鳍名义本金'
        }
        for k in sorted(mapping.keys(), key=len, reverse=True):
            col = col.replace(k, mapping[k])
        return col

    df_res = pd.DataFrame(res).T.fillna(0)
    df_res.columns = [translate_column(c) for c in df_res.columns]
    priority = ['总了结收益','总名义本金']
    others   = [c for c in df_res.columns if c not in priority]
    df_res = df_res[priority + others]

    # 7) 展示表格
    st.subheader("交易数据展示")
    df_copy = df_res.reset_index()
    df_copy.insert(0, "序号", range(1, len(df_copy)+1))
    df_copy.rename(columns={"index":"交易对手方"}, inplace=True)
    st.data_editor(df_copy, num_rows="dynamic")

    # 8) 主区指标选择
    selected_metric = st.radio("选择指标", options=["名义本金","了结收益"], index=0)

    # 9) 准备并绘图
    df_plot = df_res.reset_index().rename(columns={"index":"交易对手方"})
    melted = df_plot.melt(
        id_vars=["交易对手方"],
        var_name="产品",
        value_name="数值"
    )
    melted = melted[melted["产品"].str.contains(selected_metric)]

    st.subheader("皇家堆叠直方图")
    fig_stack = px.bar(
        melted,
        x="数值", y="交易对手方",
        color="产品", barmode="stack",
        labels={"交易对手方":"交易对手方","数值":"数值","产品":"产品"},
        title="各交易对手方在不同产品下的堆叠直方图"
    )
    order = (
        melted.groupby("交易对手方", as_index=False)["数值"]
        .sum().sort_values("数值")["交易对手方"].tolist()
    )
    fig_stack.update_yaxes(categoryorder="array", categoryarray=order)
    st.plotly_chart(fig_stack, use_container_width=True)

    st.subheader("皇家饼图")
    pie_df = melted.groupby("交易对手方", as_index=False)["数值"].sum()
    fig_pie = px.pie(
        pie_df, names="交易对手方", values="数值",
        title="各交易对手方在所有产品下的占比"
    )
    st.plotly_chart(fig_pie, use_container_width=True)

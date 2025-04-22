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
    if 'tradeStartDate' in df.columns:
        df['start_date'] = pd.to_datetime(df['tradeStartDate'].fillna(df.get('startDate')),errors='coerce').dt.date
    else:
        df['start_date'] = pd.to_datetime(df['startDate'],errors='coerce').dt.date
    df['startDate_dt'] = pd.to_datetime(df['startDate'],errors='coerce').dt.date
    df['tradeTerminationDate_dt'] = pd.to_datetime(df['tradeTerminationDate'],errors='coerce').dt.date

    st.subheader("请选择分析参数")
    col1,col2,col3 = st.columns(3)
    with col1:
        metric_type = st.radio("指标类型",["当期新增","累计新增","当期了结","累计了结","期末存续"],horizontal=True)
    with col2:
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=365)
        trend_range = st.date_input("选择分析日期范围",[default_start,today])
        if len(trend_range)!=2:
            st.error("请选择起始和结束日期")
            return
        trend_start, trend_end = trend_range
    with col3:
        freq = st.radio("聚合周期",["周","月"],horizontal=True)

    # 侧边栏筛选
    type_opts = df['tradeType'].dropna().unique().tolist() if 'tradeType' in df.columns else []
    prod_opts = df['productType'].dropna().unique().tolist() if 'productType' in df.columns else []
    cpty_opts = df['counterparty'].dropna().unique().tolist() if 'counterparty' in df.columns else []
    selected_types = st.sidebar.multiselect("交易类型",options=type_opts,default=type_opts)
    all_prod = st.sidebar.checkbox("全选产品类型",value=True)
    selected_prods = prod_opts if all_prod else []
    selected_prods = st.sidebar.multiselect("产品类型",options=prod_opts,default=selected_prods)
    all_cpty = st.sidebar.checkbox("全选交易对手方",value=True)
    default_cptys = cpty_opts if all_cpty else []
    selected_cptys = st.sidebar.multiselect("交易对手方",options=cpty_opts,default=default_cptys)

    df_filtered = df.copy()
    if selected_types:
        df_filtered = df_filtered[df_filtered['tradeType'].isin(selected_types)]
    if selected_prods:
        df_filtered = df_filtered[df_filtered['productType'].isin(selected_prods)]
    if selected_cptys:
        df_filtered = df_filtered[df_filtered['counterparty'].isin(selected_cptys)]

    freq_str = 'W' if freq=='周' else 'M'

    # 根据不同指标处理
    if metric_type!='期末存续':
        field = 'startDate_dt' if '新增' in metric_type else 'tradeTerminationDate_dt'
        if '当期' in metric_type:
            df_m = df_filtered[(df_filtered[field]>=trend_start)&(df_filtered[field]<=trend_end)]
        else:
            df_m = df_filtered[df_filtered[field]<=trend_end]
        df_m['名义本金'] = df_m['notionalPrincipal'].astype(float).fillna(0)
        df_m['保证金'] = df_m['名义本金']*df_m['marginRatio'].astype(float).fillna(0)
        df_m['日期'] = pd.to_datetime(df_m[field])
        df_m['周期'] = df_m['日期'].dt.to_period(freq_str).dt.to_timestamp()
        agg = df_m.groupby(['周期','productType'],as_index=False)[['名义本金','保证金']].sum()
        if '累计' in metric_type:
            agg['累计名义本金'] = agg.groupby('productType')['名义本金'].cumsum()
            agg['累计保证金'] = agg.groupby('productType')['保证金'].cumsum()
            value_cols = ['累计名义本金','累计保证金']
        else:
            value_cols = ['名义本金','保证金']
        long = agg.melt(id_vars=['周期','productType'],value_vars=value_cols,var_name='指标',value_name='值')
        long['产品指标'] = long['productType']+' - '+long['指标']
        st.subheader(f"{metric_type}指标趋势（按{freq}）")
        fig = px.bar(long,x='周期',y='值',color='产品指标',barmode='group',title="各产品类型指标趋势")
        st.plotly_chart(fig,use_container_width=True)
        st.subheader("指标趋势数据表")
        st.dataframe(long.pivot(index='周期',columns='产品指标',values='值').reset_index().fillna(0))
    else:
        df_o = df_filtered[df_filtered['startDate_dt']<=trend_end].copy()
        df_o['名义本金'] = df_o['notionalPrincipal'].astype(float).fillna(0)
        df_o['保证金'] = df_o['名义本金']*df_o['marginRatio'].astype(float).fillna(0)
        points = pd.date_range(trend_start,trend_end,freq=freq_str)
        results=[]
        for t in points:
            active = df_o[(df_o['startDate_dt']<=t)&((df_o['tradeTerminationDate_dt'].isna())|(df_o['tradeTerminationDate_dt']>=t))]
            if active.empty: continue
            grp = active.groupby('productType',as_index=False)[['名义本金','保证金']].sum()
            grp['周期']=t
            results.append(grp)
        if results:
            df_dyn=pd.concat(results,ignore_index=True)
            long=df_dyn.melt(id_vars=['周期','productType'],value_vars=['名义本金','保证金'],var_name='指标',value_name='值')
            long['产品指标']=long['productType']+' - '+long['指标']
            st.subheader(f"期末存续动态趋势（按{freq}）")
            fig=px.bar(long,x='周期',y='值',color='产品指标',barmode='group',title="各产品类型期末存续指标动态趋势")
            st.plotly_chart(fig,use_container_width=True)
            st.subheader("期末存续动态趋势数据表")
            st.dataframe(long.pivot(index='周期',columns='产品指标',values='值').reset_index().fillna(0))
        else:
            st.write("在所选时间区间内未找到期末存续数据。")
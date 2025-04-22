import streamlit as st
import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from api import get_bs_params, get_price_data


def render():
    st.header("对冲参数分析")
    underlying_codes = ['000016.SH','000300.SH','000905.SH','000852.SH']
    underlying_code = st.selectbox("标的代码", options=underlying_codes, index=3)
    today = datetime.date.today()
    default_start = today - datetime.timedelta(days=90)
    date_range = st.date_input("调整日期范围", [default_start, today])
    if len(date_range) != 2:
        st.error("请选择起始和结束日期")
        return
    start_date, end_date = date_range
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    params_data = get_bs_params(underlying_code, start_str, end_str)
    if not params_data:
        st.write("未获取到任何对冲参数数据。")
        return

    # DataFrame
    params_data.sort(key=lambda x: x['adjustment_date'])
    df_params = pd.DataFrame({
        '日期': pd.to_datetime([item['adjustment_date'] for item in params_data]),
        '波动率': [item.get('vol', 0) for item in params_data],
        'b值': [item.get('b', 0) for item in params_data],
        '-b值': [-(item.get('b', 0)) for item in params_data]
    })

    # Get price data
    price_result = get_price_data(underlying_codes, start_str, end_str)
    price_list = price_result.get(underlying_code, [])
    if not price_list:
        st.write(f"未获取到标的 {underlying_code} 的历史价格数据。")
        return
    df_price = pd.DataFrame(price_list)
    df_price['日期'] = pd.to_datetime(df_price['date'])
    df_price = df_price[['日期', 'close']].rename(columns={'close': '标的收盘'})

    # 合并并绘图
    df_merged = pd.merge(df_params, df_price, on='日期', how='inner')
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        specs=[[{}], [{'secondary_y': True}]],
        subplot_titles=[
            f"{underlying_code} 标的收盘价格（折线图）", 
            "对冲参数：-b值 与 波动率"
        ]
    )
    fig.add_trace(
        go.Scatter(x=df_merged['日期'], y=df_merged['标的收盘'], mode='lines+markers', name='标的收盘'),
        row=1, col=1
    )
    fig.update_yaxes(title_text='标的收盘', row=1, col=1)
    fig.add_trace(
        go.Scatter(x=df_merged['日期'], y=df_merged['-b值'], mode='lines+markers', name='-b值'),
        row=2, col=1, secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=df_merged['日期'], y=df_merged['波动率'], mode='lines+markers', name='波动率'),
        row=2, col=1, secondary_y=True
    )
    fig.update_yaxes(title_text='-b值', row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text='波动率', row=2, col=1, secondary_y=True)
    fig.update_layout(title=f"{underlying_code} 对冲参数与标的收盘价格时间序列", legend_title='图例')
    st.plotly_chart(fig, use_container_width=True)

    # Show data
    st.subheader("对冲参数数据明细")
    st.dataframe(df_merged)
import streamlit as st
from app_pages.trade_data import render as render_trade_data
from app_pages.hedge_params import render as render_hedge_params
from app_pages.product_trend import render as render_product_trend
from app_pages.acknowledgements import render as render_acknowledgements

st.set_page_config(page_title="交易分析仪表板",layout="wide")
st.sidebar.title("功能导航")
page=st.sidebar.radio("选择页面：",["交易数据分析","对冲参数分析","客户产品趋势分析","特别鸣谢"])

if page=="交易数据分析":
    render_trade_data()
elif page=="对冲参数分析":
    render_hedge_params()
elif page=="客户产品趋势分析":
    render_product_trend()
elif page=="特别鸣谢":
    render_acknowledgements()
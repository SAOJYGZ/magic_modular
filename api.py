import requests
import streamlit as st

@st.cache_data
def get_trade_data(expr: str = ""):
    """从交易数据接口获取交易数据列表"""
    url = "http://192.168.1.103:60000/api/query-trades"
    params = {"repo_name": "all", "expr": expr}
    try:
        resp = requests.post(url, json=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("result", [])
    except Exception as e:
        st.error(f"交易数据获取失败: {e}")
        return []

@st.cache_data
def get_bs_params(underlying_code: str, start_date: str, end_date: str):
    """从对冲参数接口获取BS参数"""
    url = "http://192.168.1.103:60000/api/datahub/query-bs-params?date-in-iso=1"
    params = {
        "underlyingCode": [underlying_code],
        "parameterGroup": ["hedge"],
        "adjustmentDateStart": start_date,
        "adjustmentDateEnd": end_date
    }
    try:
        resp = requests.post(url, json=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("result", [])
    except Exception as e:
        st.error(f"对冲参数数据获取失败: {e}")
        return []

@st.cache_data
def get_price_data(codes: list, start_date: str, end_date: str):
    """获取标的历史价格数据"""
    url = "http://192.168.1.103:60000/api/mkt-accessor-v2/get-price"
    payload = {"codes": codes, "startDate": start_date, "endDate": end_date}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json().get("result", {})
    except Exception as e:
        st.error(f"价格数据获取失败: {e}")
        return {}

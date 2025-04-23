import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def render():
    st.header("产品情景分析")
    st.subheader("开发中...请勿使用！")

    # 1) 产品类型选择（后续可扩充更多）
    product = st.selectbox("选择产品类型", ["Snowball"], index=0)
    st.subheader(f"{product} 参数输入模板")

    # 2) 参数输入表单
    with st.form(key="params_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            term = st.text_input("期限", value="24M")
            ko_barrier = st.number_input("敲出障碍价格 (%)", min_value=0.0, max_value=200.0, value=105.0)
            ki_barrier = st.number_input("敲入障碍价格 (%)", min_value=0.0, max_value=200.0, value=70.0)
            obs_style = st.selectbox("观察方式", ["每日观察", "每月观察", "到期观察"])
        with col2:
            participation = st.number_input("参与率 (%)", min_value=0.0, max_value=500.0, value=100.0)
            coupon_rate = st.number_input("固定票息率 (%)", min_value=0.0, max_value=100.0, value=5.0)
            margin_ratio = st.number_input("保证金比例 (%)", min_value=0.0, max_value=100.0, value=100.0)
        with col3:
            max_loss = st.number_input("最大亏损比例 (%)", min_value=0.0, max_value=100.0, value=100.0)
            st.write("")  # 占位
            st.write("")
        submitted = st.form_submit_button("生成分析图表")

    if submitted:
        # 参数汇总表
        params = {
            "期限": term,
            "敲出障碍价格": f"{ko_barrier:.2f}%",
            "敲入障碍价格": f"{ki_barrier:.2f}%",
            "观察方式": obs_style,
            "参与率": f"{participation:.2f}%",
            "票息率": f"{coupon_rate:.2f}%",
            "保证金比例": f"{margin_ratio:.2f}%",
            "最大亏损比例": f"{max_loss:.2f}%"
        }
        df_params = (
            pd.DataFrame.from_dict(params, orient="index", columns=["值"])  
              .reset_index().rename(columns={"index": "参数"})
        )
        st.table(df_params)

        # 收益情景模拟
        prices = np.linspace(0, 200, 201)
        # Snowball 到期回报示意：
        # price <= 敲入障碍：按标的跌幅承担损失；否则兑付本金+票息
        payoff = np.where(
            prices <= ki_barrier,
            prices,  # 按底价兑付
            100 + coupon_rate  # 本金 + 固定票息%
        )

        fig = go.Figure()
        # 回报曲线
        fig.add_trace(go.Scatter(
            x=prices, y=payoff,
            mode='lines', name='到期回报', line=dict(color='firebrick', width=2)
        ))
        # 本金+票息水平
        level = 100 + coupon_rate
        fig.add_shape(type='line', x0=0, x1=200, y0=level, y1=level,
            line=dict(color='gray', width=1, dash='dash'))
        fig.add_annotation(x=200, y=level, text='本金+票息', showarrow=False,
            xanchor='right', font=dict(color='gray'))
        # 敲入障碍线
        fig.add_shape(type='line', x0=ki_barrier, x1=ki_barrier, y0=min(payoff), y1=max(payoff),
            line=dict(color='blue', width=2, dash='dot'))
        fig.add_annotation(x=ki_barrier, y=max(payoff), text='敲入障碍', showarrow=False,
            yanchor='bottom', font=dict(color='blue'))
        # 敲出障碍线
        fig.add_shape(type='line', x0=ko_barrier, x1=ko_barrier, y0=min(payoff), y1=max(payoff),
            line=dict(color='green', width=2, dash='dash'))
        fig.add_annotation(x=ko_barrier, y=max(payoff), text='敲出障碍', showarrow=False,
            yanchor='bottom', font=dict(color='green'))

        fig.update_layout(
            title='Snowball 产品到期回报示意图',
            xaxis_title='标的到期价格 (%)',
            yaxis_title='到期兑付 (%)',
            xaxis=dict(range=[0, 200]), yaxis=dict(range=[0, level*1.1]),
            legend=dict(orientation='h', y=1.02, x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("请在上方输入参数，然后点击'生成分析图表'")

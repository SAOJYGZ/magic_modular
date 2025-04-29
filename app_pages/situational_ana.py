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

        # 解析期限（月数）
        try:
            months = int(term.rstrip("M"))
        except:
            months = 24

        # 时间序列：0 到 months
        time = np.arange(0, months + 1)

        # 模拟标的价格路径（GBM）
        dt = 1/12
        mu = 0.0
        vol = 0.2
        prices = [100]
        for _ in range(months):
            shock = np.random.normal((mu - 0.5 * vol**2) * dt, vol * np.sqrt(dt))
            prices.append(prices[-1] * np.exp(shock))
        prices = np.array(prices)

        # 检测敲入/敲出事件
        ki_events = np.where(prices <= ki_barrier)[0]
        ko_events = np.where(prices >= ko_barrier)[0]
        ki_date = int(ki_events[0]) if ki_events.size > 0 else None
        ko_date = int(ko_events[0]) if ko_events.size > 0 else None

        # 计算回报
        principal = 100
        coupon = coupon_rate
        if ko_date is not None and ko_date > 0:
            payoff = principal + coupon
            end_msg = f"第{ko_date}月敲出，产品提前结束，回报 {payoff:.2f}%"
        else:
            if ki_date is not None:
                payoff = prices[-1]
                end_msg = f"到期未敲出，已发生敲入（第{ki_date}月），按标的价格({payoff:.2f}%)兑付"
            else:
                payoff = principal + coupon
                end_msg = f"到期未敲出且未敲入，按本金+票息({payoff:.2f}%)兑付"

        # 绘制路径与事件
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=time, y=prices,
            mode='lines', name='标的价格', line=dict(width=2)
        ))
        # 障碍线
        fig.add_shape(type='line', x0=0, x1=months, y0=ki_barrier, y1=ki_barrier,
                      line=dict(color='blue', width=1, dash='dash'))
        fig.add_shape(type='line', x0=0, x1=months, y0=ko_barrier, y1=ko_barrier,
                      line=dict(color='green', width=1, dash='dash'))
        # 事件标记
        if ki_date is not None:
            fig.add_trace(go.Scatter(
                x=[ki_date], y=[prices[ki_date]],
                mode='markers', name='敲入',
                marker=dict(symbol='x', size=10, color='blue')
            ))
        if ko_date is not None:
            fig.add_trace(go.Scatter(
                x=[ko_date], y=[prices[ko_date]],
                mode='markers', name='敲出',
                marker=dict(symbol='star', size=12, color='green')
            ))

        fig.update_layout(
            title='标的价格路径与敲入/敲出事件',
            xaxis_title='时间（月）',
            yaxis_title='标的价格 (%)',
            xaxis=dict(range=[0, months]),
            yaxis=dict(range=[prices.min() * 0.9, prices.max() * 1.1]),
            legend=dict(orientation='h', y=1.05, x=0.5, xanchor='center')
        )
        st.plotly_chart(fig, use_container_width=True)

        # 模拟结果
        st.write(end_msg)

    else:
        st.info("请在上方输入参数，然后点击'生成分析图表'")


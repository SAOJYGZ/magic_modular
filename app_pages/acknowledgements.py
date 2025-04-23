import streamlit as st

def render():
    st.header("特别鸣谢")
    # 地址修改为本地路径 切勿上传个人照片至GitHub
    st.image("D:/Github/magic_modular/指导员.jpg",caption="指导员 -- 宋博",width=300)

    if "step" not in st.session_state:
        st.session_state.step = 0

    if st.button("不要点我", key="btn1"):
        st.session_state.step = 1

    if st.session_state.step >= 1:
        st.balloons()
        st.warning("????")

        if st.button("真别点了", key="btn2"):
            st.session_state.step = 2

    if st.session_state.step >= 2:
        st.balloons()
        st.warning("叛逆")

        if st.button("有本事再点一下", key="btn3"):
            st.session_state.step = 3

    if st.session_state.step >= 3:
        st.balloons()
        st.success("没得点了")
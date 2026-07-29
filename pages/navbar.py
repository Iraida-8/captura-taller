import streamlit as st


def render_navbar():

    st.markdown(
        """
        <style>

        .omega-navbar{
            position:sticky;
            top:0;
            z-index:999999;

            background:#151F6D;

            padding:14px 28px;

            border-radius:0px;

            display:flex;
            justify-content:space-between;
            align-items:center;

            color:white;

            margin-bottom:25px;
        }

        .omega-title{

            font-size:28px;
            font-weight:800;

            letter-spacing:1px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="omega-navbar">

            <div class="omega-title">
                OMEGA
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )
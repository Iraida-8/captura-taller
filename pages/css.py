import streamlit as st


def load_css():

    st.markdown(
        """
        <style>

        /* Hide sidebar */
        [data-testid="stSidebar"]{
            display:none;
        }

        /* App background */
        .stApp{
            background-color:#FFFFFF;
        }

        /* Give page breathing room */
        .block-container{
            padding-top:2rem;
            padding-bottom:3rem;
        }

        /* =========================
           HEADER STYLE
           ========================= */

        h1{
            font-size:1.9rem;
            margin-bottom:.2rem;
            color:#151F6D;
        }

        h2,
        h3{
            margin-top:.5rem;
            color:#BFA75F;
        }

        /* =========================
           DIVIDERS
           ========================= */

        hr{
            border:none !important;
            border-top:1px solid #B8B8B8 !important;
            opacity:1 !important;
        }

        /* =========================
           MODULE BUTTONS
           ========================= */

        div.stButton > button{
            height:95px;
            border-radius:16px;
            padding:1.2rem;
            background:#151F6D !important;
            color:white !important;
            border:none;
            box-shadow:0 4px 14px rgba(0,0,0,.12);
            transition:all .2s ease;
        }

        div.stButton > button p,
        div.stButton > button span{
            color:white !important;
            font-size:1.4rem !important;
            font-weight:700 !important;
        }

        div.stButton > button:hover{
            background:#BFA75F !important;
            color:white !important;
            transform:translateY(-2px);
        }

        div.stButton > button:hover p,
        div.stButton > button:hover span{
            color:white !important;
        }

        /* =========================
           LOGOUT BUTTON
           ========================= */

        button[kind="secondary"]{
            display:block;
            margin-left:auto;
            margin-right:auto;
            border-radius:12px;
            background-color:transparent;
            color:#BFA75F;
            border:1px solid #BFA75F;
            font-weight:600;
        }

        button[kind="secondary"]:hover{
            background-color:#BFA75F;
            color:#151F6D;
        }

        /* General Text */

        p,
        label,
        span{
            color:#222222;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
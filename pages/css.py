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

        /* =========================
        INPUTS / SELECTS
        ========================= */

        /* Enabled inputs */
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div {
            background-color:#1B267A !important;
            border:1px solid rgba(191,167,95,.25) !important;
            border-radius:10px !important;
            color:white !important;
            transition:.2s;
        }

        /* Enabled textareas */
        textarea{
            background:#3D56C8 !important;
            border:1px solid rgba(191,167,95,.25) !important;
            border-radius:10px !important;
            color:white !important;
            transition:.2s;
        }

        /* Disabled text inputs */
        input:disabled{
            background:#DCDCDC !important;
            color:#555555 !important;
            cursor:not-allowed;
        }

        /* Disabled input containers */
        div[data-baseweb="input"] div:has(input:disabled){
            background:#E8E8E8 !important;
            border:1px solid #CFCFCF !important;
        }

        /* Disabled selectboxes */
        div[data-baseweb="select"] div:has(div[aria-disabled="true"]){
            background:#E8E8E8 !important;
            border:1px solid #CFCFCF !important;
        }

        /* Disabled textarea */
        textarea:disabled{
            background:#D8E6FF !important;
            color:#555555 !important;
        }

        /* Enabled textarea */
        textarea:not(:disabled){
            background:#1B267A !important;
            color:white !important;
        }

        /* Text */
        /* Enabled text */
        input:not(:disabled),
        textarea:not(:disabled){
            color:white !important;
        }

        /* Disabled text */
        input:disabled,
        textarea:disabled{
            color:#333333 !important;
            -webkit-text-fill-color:#333333 !important;
            opacity:1 !important;
        }

        /* Placeholder */
        input::placeholder,
        textarea::placeholder{
            color:#D0D0D0 !important;
        }

        /* Selectbox text */
        /* Enabled selectbox text */
        div[data-baseweb="select"] div[role="combobox"]{
            color:white !important;
        }

        /* Disabled selectbox text */
        div[data-baseweb="select"] div[aria-disabled="true"]{
            color:#333333 !important;
            -webkit-text-fill-color:#333333 !important;
        }

        /* Radio */
        div[role="radiogroup"] label{
            color:white !important;
        }

        /* Checkbox */
        .stCheckbox label{
            color:white !important;
        }

        /* Placeholder */
        input::placeholder,
        textarea::placeholder {
            color: #d0d0d0 !important;
        }

        /* Selectbox dropdown */
        div[data-baseweb="select"] * {
            color: white !important;
        }

        /* Radio buttons */
        div[role="radiogroup"] label {
            color: white !important;
        }

        /* Checkbox */
        .stCheckbox label {
            color: white !important;
        }

        /* Notification boxes */
        div[data-baseweb="notification"] {
            border-radius: 12px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
import streamlit as st


def load_css():

    st.markdown(
        """
        <style>

        /* =========================
           HIDE SIDEBAR
        ========================= */

        [data-testid="stSidebar"]{
            display:none;
        }

        /* =========================
           PAGE SPACING
        ========================= */

        .block-container{
            padding-top:2rem;
            padding-bottom:3rem;
        }

        /* =========================
           HEADERS
        ========================= */

        h1{
            font-size:1.9rem;
            margin-bottom:.2rem;
        }

        h2,
        h3{
            margin-top:.5rem;
        }

        /* =========================
           CONTAINER BORDERS
        ========================= */

        div[data-testid="stVerticalBlockBorderWrapper"]{
            border:1px solid #000000 !important;
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
           PRIMARY BUTTONS
        ========================= */

        div.stButton button{

            border-radius:10px;

            background:#151F6D !important;

            color:#FFFFFF !important;

            border:none !important;

            font-weight:600;

            transition:.2s;
        }

        div.stButton button *{

            color:inherit !important;
        }

        div.stButton button:hover{

            background:#BFA75F !important;

            color:#FFFFFF !important;

            transform:translateY(-2px);
        }

        /* =========================
           LOGOUT BUTTON
        ========================= */

        button[kind="secondary"]{

            display:block;

            margin-left:auto;

            margin-right:auto;

            border-radius:12px;

            background:transparent !important;

            border:1px solid #BFA75F !important;

            color:#BFA75F !important;

            font-weight:600;
        }

        button[kind="secondary"]:hover{

            background:#BFA75F !important;

            color:#151F6D !important;
        }
        /* =========================
           INPUTS / SELECTS
        ========================= */

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div{

            border:1px solid rgba(191,167,95,.25) !important;

            border-radius:10px !important;

            transition:.2s;
        }

        textarea{

            border:1px solid rgba(191,167,95,.25) !important;

            border-radius:10px !important;

            transition:.2s;
        }

        /* =========================
           DISABLED INPUTS
        ========================= */

        input:disabled{

            background:#DCDCDC !important;

            color:#555555 !important;

            cursor:not-allowed;
        }

        div[data-baseweb="input"] div:has(input:disabled){

            background:#E8E8E8 !important;

            border:1px solid #CFCFCF !important;
        }

        div[data-baseweb="select"] div:has(div[aria-disabled="true"]){

            background:#E8E8E8 !important;

            border:1px solid #CFCFCF !important;
        }

        textarea:disabled{

            background:#D8E6FF !important;

            color:#555555 !important;
        }

        input:disabled,
        textarea:disabled{

            -webkit-text-fill-color:#333333 !important;

            opacity:1 !important;
        }

        /* =========================
           PLACEHOLDERS
        ========================= */

        input::placeholder,
        textarea::placeholder{

            color:#D0D0D0 !important;
        }

        /* =========================
           NOTIFICATIONS
        ========================= */

        div[data-baseweb="notification"]{

            border-radius:12px;
        }
        /* =========================
           EXPANDERS
        ========================= */

        [data-testid="stExpander"]{

            border:1px solid rgba(191,167,95,.20);

            border-radius:14px;
        }

        /* =========================
           FILE UPLOADER
        ========================= */

        [data-testid="stFileUploader"]{

            border:1px solid rgba(191,167,95,.25) !important;

            border-radius:12px !important;
        }

        /* =========================
           DOWNLOAD BUTTONS
        ========================= */

        div[data-testid="stDownloadButton"] button{

            border-radius:12px;

            box-shadow:0 4px 12px rgba(191,167,95,.20);

            font-weight:600;

            transition:all .2s ease;
        }

        div[data-testid="stDownloadButton"] button:hover{

            transform:translateY(-1px);
        }

        /* =========================
           DATAFRAME / DATA EDITOR
        ========================= */

        [data-testid="stDataFrame"],
        [data-testid="stDataEditor"]{

            border:1px solid rgba(191,167,95,.20);

            border-radius:12px;

            overflow:hidden;
        }

        /* =========================
           METRIC CARDS
        ========================= */

        [data-testid="metric-container"]{

            border:1px solid rgba(191,167,95,.20);

            border-radius:14px;

            padding:1rem;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
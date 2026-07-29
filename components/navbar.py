import streamlit as st

def render_navbar():

    st.divider()

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        st.button("🏠 Home", use_container_width=True)

    with c2:
        st.button("🏭 Solicitudes", use_container_width=True)

    with c3:
        st.button("📋 Gestión", use_container_width=True)

    with c4:
        st.button("🔍 Consultas", use_container_width=True)

    with c5:
        st.button("⚙ Extras", use_container_width=True)

    with c6:
        st.button("🗄 Administración", use_container_width=True)

    st.divider()
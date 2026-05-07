import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date, timezone
from auth import require_login, require_access
import json

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Solicitud de Viaticos y Reembolsos",
    layout="wide"
)

# Security gates
require_login()
require_access("solicitud_viaticos")

if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

tab_solicitud, tab_comprobacion = st.tabs([
    "🧳 SOLICITUD GTOS DE VIAJE",
    "🧾 COMPROBACION GTOS VIAJE"
])

with tab_solicitud:
    st.subheader("🧳 Solicitud de Fondo para Gastos de Viaje")

    # PART 1: DATOS GENERALES
    col1, col2 = st.columns([1, 2])
    with col1:
        fecha_solicitud = st.date_input("Fecha de Solicitud")
    with col2:
        empresa_servicio = st.text_input("Nombre de la Empresa que Brinda el Servicio")

    empleado = st.text_input("Nombre del Empleado que lo Solicita")
    motivo_viaje = st.text_area("Motivo del Viaje", height=90)

    col_l, col_p = st.columns(2)
    with col_l:
        lugar_viaje = st.text_input("Lugar a Donde se Realiza el Viaje")
    with col_p:
        periodo_viaje = st.text_input("Periodo del Viaje")

    st.divider()

    # Selectboxes
    st.markdown("### Empresa a Cargo")
    empresa_cargo = st.selectbox("Empresa", ["Seleccione...", "SET FREIGHT", "LINCOLN", "PICUS", "IGLOO", "SET LOGIS PLUS"], label_visibility="collapsed")
    
    st.markdown("### Unidad de Negocio")
    unidad_negocio = st.selectbox("Unidad", ["Seleccione...", "CARRIER", "LOGISTICA", "PLUS"], label_visibility="collapsed")

    st.markdown("### Sucursal")
    sucursal = st.radio("", ["NUEVO LAREDO", "DALLAS", "CHICAGO", "GUADALAJARA", "MONTERREY", "QUERETARO", "LEON", "TLAXCALA", "OTRO"], horizontal=True, label_visibility="collapsed")
    
    sucursal_final = st.text_input("Especificar Sucursal") if sucursal == "OTRO" else sucursal

    st.divider()

    # ========================================================
    # PART 2: THE TABLE (FIXED HTML & COLORS)
    # ========================================================
    expenses = [
        ("transporte", "TRANSPORTACION TERRESTRE"),
        ("hospedaje", "HOSPEDAJE"),
        ("alimentos", "ALIMENTOS"),
        ("propinas", "PROPINAS"),
        ("taxis", "TAXIS"),
    ]

    # Build rows correctly
    expense_rows = ""
    for id_raw, label in expenses:
        expense_rows += f"""
        <tr>
            <td class="expense-label">{label}</td>
            <td class="cur-cell">$</td>
            <td class="input-cell"><input type="number" id="{id_raw}" oninput="calcTotal()" value="0"></td>
        </tr>
        """

    other_rows = ""
    for i in range(1, 4):
        other_rows += f"""
        <tr>
            <td class="expense-label">Descripción {i}</td>
            <td class="cur-cell">$</td>
            <td class="input-cell"><input type="number" id="others_{i}" oninput="calcTotal()" value="0"></td>
        </tr>
        """

    # Final HTML Construction
    chart_html = f"""
    <div class="custom-expense-wrapper">
        <h2 style="color: #BFA75F; text-decoration: underline;">ESTIMACION DE GASTOS DE VIAJE A INCURRIR</h2>
        <table class="expense-table">
            <thead>
                <tr>
                    <th style="text-align: left; color: #FFFFFF; width: 60%;">CONCEPTO</th>
                    <th colspan="2" style="text-align: right; color: #BFA75F;">TOTAL ESTIMADO</th>
                </tr>
            </thead>
            <tbody>
                {expense_rows}
                <tr><td class="expense-others-subtitle" colspan="3">OTROS (Describir)</td></tr>
                {other_rows}
                <tr class="sum-row">
                    <td class="expense-sum-text">SUMA GASTOS ESPECÍFICOS</td>
                    <td class="cur-cell">$</td>
                    <td class="total-output" id="calculated_sum_cell">0.00</td>
                </tr>
                <tr class="final-row">
                    <td class="expense-bold-label">Importe estimado de gastos de viaje</td>
                    <td class="cur-cell">$</td>
                    <td class="total-output" id="table_final_total">0.00</td>
                </tr>
            </tbody>
        </table>
    </div>
    """

    with st.form("form_solicitud_gastos"):
        st.markdown(chart_html, unsafe_allow_html=True)
        
        st.divider()
        col_a, col_m = st.columns(2)
        with col_a:
            anticipo = st.number_input("(-) Anticipo para Gastos de Viaje Entregado", min_value=0.0)
        with col_m:
            total_est_placeholder = st.empty()
            diferencia_placeholder = st.empty()

        observaciones = st.text_area("Observaciones")
        hidden_total_input = st.text_input("calculated_total_field", value="0", label_visibility="hidden")
        
        if st.form_submit_button("💳 Enviar Solicitud", use_container_width=True):
            try:
                total_val = float(hidden_total_input)
            except:
                total_val = 0.0
            
            total_est_placeholder.metric("Total Estimado", f"${total_val:,.2f}")
            diferencia_placeholder.metric("Diferencia", f"${total_val - anticipo:,.2f}")
            st.success("Solicitud Enviada.")

# =================================
# CSS & JAVASCRIPT
# =================================

javascript_code = f"""
<script>
    function calcTotal() {{
        const fixedIds = ["transporte", "hospedaje", "alimentos", "propinas", "taxis"];
        let specificSum = 0;
        let totalSum = 0;

        fixedIds.forEach(id => {{
            specificSum += parseFloat(document.getElementById(id).value) || 0;
        }});

        document.getElementById('calculated_sum_cell').innerText = specificSum.toFixed(2);

        totalSum = specificSum;
        for(let i=1; i<=3; i++) {{
            totalSum += parseFloat(document.getElementById('others_' + i).value) || 0;
        }}

        document.getElementById('table_final_total').innerText = totalSum.toFixed(2);

        const hiddenInput = document.querySelector('input[aria-label="calculated_total_field"]');
        if (hiddenInput) {{
            hiddenInput.value = totalSum;
            hiddenInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
    }}
</script>
"""

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    .stApp { background-color: #151F6D; }
    
    /* Force text visibility */
    label, p, span, .stMarkdown { color: #FFFFFF !important; }
    h1, h2, h3 { color: #BFA75F !important; }

    .expense-table { width: 100%; border-collapse: collapse; color: white; margin-bottom: 20px;}
    .expense-table td { padding: 12px; border-bottom: 1px dotted rgba(255, 255, 255, 0.2); }
    
    .expense-label { color: #FFFFFF; font-size: 1rem; }
    .expense-others-subtitle { color: #BFA75F; font-weight: bold; padding-top: 25px; border-bottom: 2px solid #BFA75F; }
    
    /* Clean Input Styling */
    .input-cell input {
        width: 100%;
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: #BFA75F !important;
        border: 1px solid rgba(191, 167, 95, 0.4);
        border-radius: 5px;
        text-align: right;
        padding: 5px;
        font-weight: bold;
    }

    .total-output { text-align: right; font-weight: bold; color: #BFA75F; font-size: 1.2rem; }
    .cur-cell { text-align: right; color: #FFFFFF; width: 30px; }

    .sum-row { background-color: rgba(191, 167, 95, 0.1); }
    .final-row { border: 2px solid #BFA75F; background-color: rgba(191, 167, 95, 0.2); }
    
    /* Forms */
    div[data-testid="stForm"] { border: 1px solid rgba(191, 167, 95, 0.3); border-radius: 10px; padding: 20px; }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(javascript_code, unsafe_allow_html=True)
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

# =================================
# Security gates
# =================================
require_login()
require_access("solicitud_viaticos")

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# TABS
# =================================
tab_solicitud, tab_comprobacion = st.tabs([
    "🧳 SOLICITUD GTOS DE VIAJE",
    "🧾 COMPROBACION GTOS VIAJE"
])

# =================================
# TAB 1 — SOLICITUD
# =================================
with tab_solicitud:

    st.subheader("🧳 Solicitud de Fondo para Gastos de Viaje")

    # =========================
    # PART 1: DATOS GENERALES
    # =========================
    col1, col2 = st.columns([1, 2])

    with col1:
        fecha_solicitud = st.date_input("Fecha de Solicitud")

    with col2:
        empresa_servicio = st.text_input("Nombre de la Empresa que Brinda el Servicio")

    empleado = st.text_input("Nombre del Empleado que lo Solicita")

    motivo_viaje = st.text_area("Motivo del Viaje", height=90)

    col1, col2 = st.columns(2)
    with col1:
        lugar_viaje = st.text_input("Lugar a Donde se Realiza el Viaje")
    with col2:
        periodo_viaje = st.text_input("Periodo del Viaje")

    st.divider()

    st.markdown("### Empresa a Cargo para Gastos de este Viaje")
    empresa_cargo = st.selectbox(
        "Empresa a Cargo", 
        ["Seleccione una opción...", "SET FREIGHT", "LINCOLN", "PICUS", "IGLOO", "SET LOGIS PLUS"],
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("### Unidad de Negocio")
    unidad_negocio = st.selectbox(
        "Unidad de Negocio", 
        ["Seleccione una opción...", "CARRIER", "LOGISTICA", "PLUS"],
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("### Sucursal")
    sucursal = st.radio(
        "",
        ["NUEVO LAREDO", "DALLAS", "CHICAGO", "GUADALAJARA", "MONTERREY", "QUERETARO", "LEON", "TLAXCALA", "OTRO"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if sucursal == "OTRO":
        suc_otro_texto = st.text_input("Especificar")
        sucursal_final = suc_otro_texto if suc_otro_texto else ""
    else:
        st.text_input("Especificar", value="", disabled=True)
        sucursal_final = sucursal

    st.divider()

    # ========================================================
    # PART 2: THE CHART (RESTORED CONTRAST & FIXING HTML)
    # ========================================================
    
    # Define variables for JS
    expenses = [
        ("transporte", "TRANSPORTACION TERRESTRE"),
        ("hospedaje", "HOSPEDAJE"),
        ("alimentos", "ALIMENTOS"),
        ("propinas", "PROPINAS"),
        ("taxis", "TAXIS"),
    ]
    num_other_inputs = 3

    # We build the HTML outside the form to avoid the "code leakage" shown in your screenshot
    expense_rows = ""
    for id_raw, label in expenses:
        expense_rows += f"""
        <tr>
            <td class="expense-label">{label}</td>
            <td class="cur-cell">$</td>
            <td class="input-cell"><input type="number" id="{id_raw}" oninput="calcTotal()" value="0"></td>
        </tr>"""

    other_rows = ""
    for i in range(num_other_inputs):
        other_rows += f"""
        <tr>
            <td class="expense-label"></td>
            <td class="cur-cell">$</td>
            <td class="input-cell"><input type="number" id="others_{i+1}" oninput="calcTotal()" value="0"></td>
        </tr>"""

    chart_html = f"""
    <div class="custom-expense-wrapper">
        <h2 class="chart-header">ESTIMACION DE GASTOS DE VIAJE A INCURRIR</h2>
        <table class="expense-table">
            <thead>
                <tr>
                    <th style="width: 60%;"></th>
                    <th colspan="2" style="text-align: center; color: #BFA75F;">TOTAL ESTIMADO</th>
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
        # Render the chart inside the form
        st.markdown(chart_html, unsafe_allow_html=True)
        
        st.divider()
        
        col_calc1, col_calc2 = st.columns(2)
        with col_calc1:
            anticipo = st.number_input("(-) Anticipo para Gastos de Viaje Entregado", min_value=0.0, step=100.0)
        
        with col_calc2:
            st.markdown("### Resumen Final")
            total_est_placeholder = st.empty()
            diferencia_placeholder = st.empty()

        observaciones = st.text_area("Observaciones", height=100)
        
        # This hidden input bridges Javascript values back to Python
        hidden_total_input = st.text_input("calculated_total_field", value="0", label_visibility="hidden")

        submitted = st.form_submit_button("💳 Enviar Solicitud", use_container_width=True)

        if submitted:
            try:
                total_val = float(hidden_total_input)
            except:
                total_val = 0.0
            
            diff = total_val - anticipo
            total_est_placeholder.metric("Total Estimado", f"${total_val:,.2f}")
            diferencia_placeholder.metric("Diferencia", f"${diff:,.2f}")

            if empresa_cargo == "Seleccione una opción..." or unidad_negocio == "Seleccione una opción...":
                st.error("⚠️ Falta seleccionar Empresa o Unidad.")
            else:
                st.success(f"Solicitud procesada por ${total_val:,.2f}")

# =================================
# JS & CSS (FIXED COLORS & VISIBILITY)
# =================================

javascript_code = f"""
<script>
    function calcTotal() {{
        const fixedIds = {json.dumps([id_raw for id_raw, label in expenses])};
        let specificSum = 0;
        let totalSum = 0;

        fixedIds.forEach(id => {{
            specificSum += parseFloat(document.getElementById(id).value) || 0;
        }});

        document.getElementById('calculated_sum_cell').innerText = specificSum.toFixed(2);

        totalSum = specificSum;
        for(let i=1; i<={num_other_inputs}; i++) {{
            totalSum += parseFloat(document.getElementById('others_' + i).value) || 0;
        }}

        document.getElementById('table_final_total').innerText = totalSum.toFixed(2);

        // Sync with Streamlit
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
    /* Global Styles */
    [data-testid="stSidebar"] { display: none; }
    .stApp { background-color: #151F6D; }
    
    /* Text Contrast Fix: Force labels and headers to white/gold */
    label, p, span, .stMarkdown { color: #FFFFFF !important; }
    h1, h2, h3 { color: #BFA75F !important; }

    /* Chart Container */
    .custom-expense-wrapper {
        background-color: transparent;
        padding: 10px;
        border-radius: 8px;
    }
    
    .chart-header {
        font-size: 1.2rem;
        text-decoration: underline;
        margin-bottom: 15px;
    }

    /* Table Styling */
    .expense-table {
        width: 100%;
        border-collapse: collapse;
        color: white;
    }

    .expense-table th { border-bottom: 2px solid #BFA75F; padding-bottom: 5px; }
    
    .expense-table td {
        padding: 8px;
        border-bottom: 1px dotted rgba(255, 255, 255, 0.2);
    }

    .expense-label { font-weight: normal; }
    .expense-others-subtitle { color: #BFA75F; font-weight: bold; padding-top: 20px; }
    .cur-cell { text-align: right; color: #FFFFFF; font-weight: bold; }
    
    /* Input Styling: White background, black text for readability */
    .input-cell input {
        width: 100%;
        background-color: white !important;
        color: black !important;
        border: 1px solid #BFA75F;
        border-radius: 4px;
        text-align: right;
        padding: 4px;
        font-size: 1rem;
    }

    .total-output {
        text-align: right;
        font-weight: bold;
        color: #BFA75F;
        font-size: 1.1rem;
    }

    .sum-row { background-color: rgba(255, 255, 255, 0.05); }
    .expense-sum-text { text-align: right; padding-right: 20px; font-weight: bold; color: #BFA75F; }
    
    .final-row { border-top: 2px solid #BFA75F; }
    .expense-bold-label { font-weight: bold; }

    /* Button Styling */
    div.stButton > button {
        height: 60px; background-color: #1B267A; color: white;
        border: 1px solid #BFA75F; border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(javascript_code, unsafe_allow_html=True)
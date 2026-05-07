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
# Security & Navigation
# =================================
require_login()
require_access("solicitud_viaticos")

if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# Global CSS & JavaScript Injection
# =================================
# This handles the background, text colors, and the table styling
st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    .stApp { background-color: #151F6D; }
    
    /* Global Text Contrast */
    label, p, span, .stMarkdown { color: #FFFFFF !important; }
    h1, h2, h3 { color: #BFA75F !important; }

    /* Table Layout based on image_cf2cf2.png */
    .expense-table { width: 100%; border-collapse: collapse; color: white; margin-top: 10px; }
    .expense-table td { padding: 10px; border-bottom: 1px dotted rgba(255, 255, 255, 0.3); }
    .expense-label { color: #FFFFFF; font-size: 1rem; width: 60%; }
    .cur-cell { text-align: right; color: #FFFFFF; width: 5%; font-weight: bold; }
    
    /* Input High Contrast Fix */
    .input-cell { width: 35%; }
    .input-cell input {
        width: 100%;
        background-color: #FFFFFF !important; /* White background for visibility */
        color: #000000 !important;          /* Black text */
        border: 2px solid #BFA75F;
        border-radius: 4px;
        padding: 5px;
        text-align: right;
        font-weight: bold;
    }

    .expense-others-subtitle { color: #BFA75F; font-weight: bold; padding-top: 20px; font-size: 1.1rem; }
    .total-output { text-align: right; font-weight: bold; color: #BFA75F; font-size: 1.2rem; }
    .sum-row { background-color: rgba(255, 255, 255, 0.05); }
    .final-row { border: 2px solid #BFA75F; background-color: rgba(191, 167, 95, 0.1); }
    
    /* Form Box Styling */
    div[data-testid="stForm"] { border: 1px solid rgba(191, 167, 95, 0.3); border-radius: 12px; }
    </style>

    <script>
    function calcTotal() {
        const fixedIds = ["transporte", "hospedaje", "alimentos", "propinas", "taxis"];
        let specificSum = 0;
        let totalSum = 0;

        fixedIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) specificSum += parseFloat(el.value) || 0;
        });

        const sumCell = document.getElementById('calculated_sum_cell');
        if (sumCell) sumCell.innerText = '$ ' + specificSum.toLocaleString('en-US', {minimumFractionDigits: 2});

        totalSum = specificSum;
        for (let i = 1; i <= 3; i++) {
            const otherEl = document.getElementById('others_' + i);
            if (otherEl) totalSum += parseFloat(otherEl.value) || 0;
        }

        const finalCell = document.getElementById('table_final_total');
        if (finalCell) finalCell.innerText = '$ ' + totalSum.toLocaleString('en-US', {minimumFractionDigits: 2});

        // Bridge JS value to Streamlit hidden input
        const hiddenInput = document.querySelector('input[aria-label="calculated_total_field"]');
        if (hiddenInput) {
            hiddenInput.value = totalSum;
            hiddenInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }
    </script>
""", unsafe_allow_html=True)

# =================================
# Main UI
# =================================
tab_solicitud, tab_comprobacion = st.tabs(["🧳 SOLICITUD", "🧾 COMPROBACION"])

with tab_solicitud:
    st.subheader("🧳 Solicitud de Fondo para Gastos de Viaje")

    # PART 1: DATOS GENERALES
    col1, col2 = st.columns(2)
    with col1:
        fecha_solicitud = st.date_input("Fecha de Solicitud")
        empleado = st.text_input("Nombre del Empleado")
    with col2:
        empresa_servicio = st.text_input("Nombre de la Empresa que Brinda el Servicio")
        periodo_viaje = st.text_input("Periodo del Viaje")

    motivo_viaje = st.text_area("Motivo del Viaje")

    st.divider()

    # Dropdowns
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### Empresa a Cargo")
        empresa_cargo = st.selectbox("E", ["SET FREIGHT", "LINCOLN", "PICUS", "IGLOO", "SET LOGIS PLUS"], label_visibility="collapsed")
    with c2:
        st.markdown("### Unidad de Negocio")
        unidad_negocio = st.selectbox("U", ["CARRIER", "LOGISTICA", "PLUS"], label_visibility="collapsed")
    with c3:
        st.markdown("### Sucursal")
        sucursal = st.selectbox("S", ["NUEVO LAREDO", "DALLAS", "CHICAGO", "GUADALAJARA", "MONTERREY", "QUERETARO", "LEON", "TLAXCALA", "OTRO"], label_visibility="collapsed")

    st.divider()

    # PART 2: THE FORM & CHART
    with st.form("form_solicitud_gastos"):
        
        # Use a simple string for HTML to prevent leaking code through f-string errors
        chart_html = """
        <div class="custom-expense-wrapper">
            <h2 style="text-decoration: underline;">ESTIMACION DE GASTOS DE VIAJE A INCURRIR</h2>
            <table class="expense-table">
                <tbody>
                    <tr><td class="expense-label">TRANSPORTACION TERRESTRE</td><td class="cur-cell">$</td><td class="input-cell"><input type="number" id="transporte" oninput="calcTotal()" value="0"></td></tr>
                    <tr><td class="expense-label">HOSPEDAJE</td><td class="cur-cell">$</td><td class="input-cell"><input type="number" id="hospedaje" oninput="calcTotal()" value="0"></td></tr>
                    <tr><td class="expense-label">ALIMENTOS</td><td class="cur-cell">$</td><td class="input-cell"><input type="number" id="alimentos" oninput="calcTotal()" value="0"></td></tr>
                    <tr><td class="expense-label">PROPINAS</td><td class="cur-cell">$</td><td class="input-cell"><input type="number" id="propinas" oninput="calcTotal()" value="0"></td></tr>
                    <tr><td class="expense-label">TAXIS</td><td class="cur-cell">$</td><td class="input-cell"><input type="number" id="taxis" oninput="calcTotal()" value="0"></td></tr>
                    
                    <tr><td class="expense-others-subtitle" colspan="3">OTROS (Describir)</td></tr>
                    
                    <tr><td class="expense-label">Descripción 1</td><td class="cur-cell">$</td><td class="input-cell"><input type="number" id="others_1" oninput="calcTotal()" value="0"></td></tr>
                    <tr><td class="expense-label">Descripción 2</td><td class="cur-cell">$</td><td class="input-cell"><input type="number" id="others_2" oninput="calcTotal()" value="0"></td></tr>
                    <tr><td class="expense-label">Descripción 3</td><td class="cur-cell">$</td><td class="input-cell"><input type="number" id="others_3" oninput="calcTotal()" value="0"></td></tr>
                    
                    <tr class="sum-row">
                        <td class="expense-label" style="text-align:right; font-weight:bold;">SUMA GASTOS ESPECÍFICOS</td>
                        <td colspan="2" class="total-output" id="calculated_sum_cell">$ 0.00</td>
                    </tr>
                    <tr class="final-row">
                        <td class="expense-label" style="font-weight:bold;">Importe estimado de gastos de viaje</td>
                        <td colspan="2" class="total-output" id="table_final_total">$ 0.00</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """
        st.markdown(chart_html, unsafe_allow_html=True)
        
        # Hidden input for Python to receive the JS total
        hidden_total = st.text_input("calculated_total_field", value="0", label_visibility="hidden")
        
        st.divider()
        
        col_metrics_a, col_metrics_b = st.columns(2)
        with col_metrics_a:
            anticipo = st.number_input("(-) Anticipo para Gastos de Viaje Entregado", min_value=0.0)
        
        observaciones = st.text_area("Observaciones")

        if st.form_submit_button("💳 Enviar Solicitud", use_container_width=True):
            try:
                final_val = float(hidden_total)
            except:
                final_val = 0.0
            
            st.success(f"Solicitud procesada: Total ${final_val:,.2f} | Diferencia Cargo ${final_val - anticipo:,.2f}")

with tab_comprobacion:
    st.info("Sección de comprobación de gastos.")
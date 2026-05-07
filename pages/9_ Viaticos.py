import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date, timezone
from auth import require_login, require_access

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
    # Using a container instead of a form here so the radio button can trigger the UI update
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

    # EMPRESA A CARGO
    st.markdown("### Empresa a Cargo para Gastos de este Viaje")
    empresa_cargo = st.selectbox(
        "Empresa a Cargo", 
        ["Seleccione una opción...", "SET FREIGHT", "LINCOLN", "PICUS", "IGLOO", "SET LOGIS PLUS"],
        index=0,
        label_visibility="collapsed"
    )

    # UNIDAD DE NEGOCIO
    st.markdown("### Unidad de Negocio")
    unidad_negocio = st.selectbox(
        "Unidad de Negocio", 
        ["Seleccione una opción...", "CARRIER", "LOGISTICA", "PLUS"],
        index=0,
        label_visibility="collapsed"
    )

    # =========================
    # SUCURSAL (REACTIVE SECTION)
    # =========================
    st.markdown("### Sucursal")
    sucursal = st.radio(
        "",
        ["NUEVO LAREDO", "DALLAS", "CHICAGO", "GUADALAJARA", "MONTERREY", "QUERETARO", "LEON", "TLAXCALA", "OTRO"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if sucursal == "OTRO":
        suc_otro_texto = st.text_input("Especificar")
        sucursales_final = [suc_otro_texto] if suc_otro_texto else []
    else:
        st.text_input("Especificar", value="", disabled=True)
        sucursales_final = [sucursal]

    st.divider()

    # ========================================================
    # PART 2: THE FORM (CALCULATIONS & SUBMIT) with NEW TABLE
    # ========================================================
    with st.form("form_solicitud_gastos"):
        # We replace the old grid with the custom tabular structure.
        # We use a 3-part layout to help with centering.
        spacer1, table_container, spacer2 = st.columns([1, 4, 1])

        with table_container:
            st.markdown("## ESTIMACION DE GASTOS DE VIAJE A INCURRIR")

            # Definitions for the specific fixed categories
            expenses = [
                ("transporte", "TRANSPORTACION TERRESTRE"),
                ("hospedaje", "HOSPEDAJE"),
                ("alimentos", "ALIMENTOS"),
                ("propinas", "PROPINAS"),
                ("taxis", "TAXIS"),
            ]

            # Generate HTML for the fixed rows
            expense_rows = ""
            for id_raw, label in expenses:
                expense_rows += f"""
                <tr>
                    <td class="expense-label expense-fixed-text">{label}</td>
                    <td class="cur-cell">$</td>
                    <td class="input-cell"><input type="number" id="{id_raw}" oninput="calcTotal()" value="0"></td>
                </tr>
                """

            # Definitions for 'Otros' - matching image_0.png with label, blanks, and sum line
            num_other_inputs = 3
            num_blank_rows = 3
            other_rows = ""
            
            # Subtitle line
            other_rows += f"""
                <tr>
                    <td class="expense-label expense-others-subtitle" colspan="3">OTROS (Describir)</td>
                </tr>
            """

            # Lines with inputs and blanks
            for i in range(num_other_inputs):
                other_rows += f"""
                    <tr>
                        <td class="expense-label"> </td>
                        <td class="cur-cell">$</td>
                        <td class="input-cell"><input type="number" id="others_{i+1}" oninput="calcTotal()" value="0"></td>
                    </tr>
                """
            for _ in range(num_blank_rows):
                other_rows += f"""<tr><td class="expense-label expense-blank-label"> </td><td> </td><td> </td></tr>"""
            
            # The summary row
            sum_row = f"""
                <tr>
                    <td class="expense-label expense-sum-text">SUMA GASTOS ESPECÍFICOS</td>
                    <td colspan="2" class="total-output" id="calculated_sum_cell">$0.00</td>
                </tr>
            """

            # The final row
            final_line_label = "Importe estimado de gastos de viaje"
            total_estimated_row = f"""
                <tr>
                    <td colspan="2" class="expense-label expense-bold-label">{final_line_label}</td>
                    <td class="total-output input-bold-border" id="table_final_total">$0.00</td>
                </tr>
            """

            # Final assembly of the HTML structure
            expense_form_html = f"""
                <div class="custom-expense-wrapper">
                    <table class="expense-table">
                        <tbody>
                            {expense_rows}
                            {other_rows}
                            {sum_row}
                            {total_estimated_row}
                        </tbody>
                    </table>
                </div>
            """

            # Render the HTML component
            st.markdown(expense_form_html, unsafe_allow_html=True)

            st.divider()
            
            # Metrics section
            col_calc1, col_calc2 = st.columns(2)
            
            with col_calc1:
                anticipo = st.number_input("(-) Anticipo para Gastos de Viaje Entregado", min_value=0.0, step=100.0)
                
            with col_calc2:
                # Placeholders updated by JavaScript
                total_est_placeholder = st.empty()
                diff_label_placeholder = st.empty()
                diferencia_placeholder = st.empty()

        st.divider()
        observaciones = st.text_area("Observaciones", height=150)
        st.divider()
        
        # We use a hidden input field to capture the JS total so Python can read it.
        # The key is crucial for access in st.session_state.
        hidden_total_input = st.text_input("calculated_total_field", value="0", label_visibility="hidden")

        submitted = st.form_submit_button("💳 Enviar Solicitud", use_container_width=True)

        if submitted:
            # Re-read the hidden field to get the JS-calculated total
            # Need to handle potential empty/string/float conversion
            try:
                total_estimado_value = float(hidden_total_input)
            except ValueError:
                total_estimado_value = 0.0
                
            diferencia_value = total_estimado_value - anticipo

            # Re-render placeholders with metrics for display upon submission
            total_est_placeholder.metric("Importe estimado de gastos de viaje", f"${total_estimado_value:,.2f}")
            diferencia_placeholder.metric("Diferencia a Cargo (Favor)", f"${diferencia_value:,.2f}")

            # VALIDATION (UNCHANGED)
            if empresa_cargo == "Seleccione una opción..." or unidad_negocio == "Seleccione una opción...":
                st.error("⚠️ Por favor seleccione una Empresa y una Unidad de Negocio válidas.")
            elif sucursal == "OTRO" and not sucursal_final:
                st.error("⚠️ Por favor especifique la sucursal.")
            elif total_estimado_value <= 0:
                st.error("⚠️ Por favor ingrese una estimación de gastos válida.")
            else:
                # Access all variables (from outside, hidden JS total, and inside form) to send to Supabase
                st.success(f"Solicitud enviada correctamente por ${total_estimado_value:,.2f}")

# =================================
# TAB 2 — COMPROBACION (UNCHANGED)
# =================================
with tab_comprobacion:
    st.subheader("🧾 Comprobación de Gastos de Viaje")
    with st.form("form_comprobacion_viaticos"):
        col1, col2 = st.columns(2)
        with col1:
            folio = st.text_input("Folio")
            empleado_comp = st.text_input("Empleado")
            fecha_comprobacion = st.date_input("Fecha de Comprobación", value=date.today())
        with col2:
            total_comprobado = st.number_input("Total Comprobado", min_value=0.0, step=100.0)
            obs_comp = st.text_area("Observaciones")

        submitted_comprobacion = st.form_submit_button("🧾 Guardar Comprobación", use_container_width=True)
        if submitted_comprobacion:
            st.success("Comprobación guardada correctamente.")

# =================================
# SUPABASE CONFIGURATION
# =================================
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

supabase = get_supabase()

# -------------------------------
# CSS & JAVASCRIPT
# -------------------------------

# Define Javascript functionality to link table outputs to standard inputs
javascript_code = f"""
<script>
    function calcTotal() {{
        const fixedIds = {json.dumps([id_raw for id_raw, label in expenses])};
        const numOthers = {num_other_inputs};
        const anticipoInput = document.querySelector('div[data-testid="stForm"] input[type="number"]'); // First numeric input in form (anticipo)

        let expenseSum = 0;
        let totalSum = 0;

        // Sum fixed expenses
        fixedIds.forEach(id => {{
            const val = parseFloat(document.getElementById(id).value) || 0;
            expenseSum += val;
        }});

        // Update specific expense sum display in table
        document.getElementById('calculated_sum_cell').innerText = '$' + expenseSum.toFixed(2);

        // Calculate final total (specific expenses + 'Otros' inputs)
        totalSum = expenseSum;
        for(let i=1; i<=numOthers; i++){{
            const val = parseFloat(document.getElementById('others_' + i).value) || 0;
            totalSum += val;
        }}

        // Format currency helper
        const formatter = new Intl.NumberFormat('en-US', {{
            style: 'currency',
            currency: 'USD',
        }});

        // Update the two final output cells
        document.getElementById('table_final_total').innerText = formatter.format(totalSum);

        // Find standard Streamlit metric displays at the bottom and update them visually
        // Selector finds the text inside the standard metric box
        const metricValueNodes = document.querySelectorAll('div[data-testid="stMetricValue"]');
        
        // Find standard hidden input for total estimation and set value
        const hiddenTotalInput = document.querySelector('div[data-testid="stForm"] input[key="calculated_total_field"]');
        
        // Update values and UI
        if (hiddenTotalInput) {{
            hiddenTotalInput.value = totalSum; // Set JS total back to Python form variable
        }}

        if (metricValueNodes.length >= 2) {{
            // Metric Value 1 = "Total Estimado"
            metricValueNodes[0].innerText = formatter.format(totalSum);
            
            // Re-read anticipo for difference calc
            let currentAnticipo = anticipoInput ? (parseFloat(anticipoInput.value) || 0) : 0;
            let diferenciaValue = totalSum - currentAnticipo;
            
            // Metric Value 2 = "Diferencia"
            metricValueNodes[1].innerText = formatter.format(diferenciaValue);
        }}
    }}
</script>
"""

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    .stApp { background-color: #151F6D; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    h1 { font-size: 1.9rem; margin-bottom: 0.2rem; color: #FFFFFF; }
    h2, h3 { margin-top: 0.5rem; color: #BFA75F; }
    div.stButton > button {
        height: 95px; font-size: 1.05rem; font-weight: 600; border-radius: 16px;
        background-color: #1B267A; color: #FFFFFF; border: 1px solid rgba(191, 167, 95, 0.25);
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover { background-color: #24338C; border-color: #BFA75F; color: #BFA75F; }
    .stTabs [data-baseweb="tab-list"] { gap: 0; width: 100%; }
    .stTabs [data-baseweb="tab"] {
        flex: 1; justify-content: center; height: 70px; font-size: 1.05rem; font-weight: 700;
        background-color: #1B267A; color: #FFFFFF; border-radius: 14px 14px 0 0;
        border: 1px solid rgba(191, 167, 95, 0.25); margin-right: 4px;
    }
    .stTabs [aria-selected="true"] { background-color: #24338C; color: #BFA75F; border-color: #BFA75F; }
    p, label, span { color: #F5F5F5; }

    /* ========================================================
       NEW TABULAR GASTOS TABLE CSS
       Match image_0.png structure
       ======================================================== */
    .custom-expense-wrapper {
        color: black;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }

    .custom-expense-wrapper h2 {
        color: black;
        text-transform: none;
        text-decoration: underline;
        font-weight: 600;
        border: none;
        font-size: 1.25rem;
    }

    .expense-table {
        width: 100%;
        border-collapse: collapse;
        color: black;
        font-family: sans-serif;
    }

    .expense-table tbody tr {
        border-bottom: 1px dotted rgba(0, 0, 0, 0.3); /* Dotted lines as in image */
    }

    /* Fixed first column text style from image */
    .expense-label {
        width: 60%;
        color: black;
        padding-left: 5px;
        font-size: 0.9rem;
    }

    .expense-fixed-text {
        text-transform: none; /* Fixed categories in image are normal text, 'OTROS' subtitle is bold */
    }

    /* Subtitle 'Otros' bold text style from image */
    .expense-others-subtitle {
        color: black;
        font-weight: 600;
        padding-top: 10px;
    }

    .cur-cell {
        color: black;
        width: 5%;
        text-align: right;
    }

    /* Input field text style from image */
    .input-cell {
        width: 35%;
        color: black;
        padding: 2px 5px;
    }

    .expense-table input {
        width: 100%;
        border: none; /* No border for input cells in image */
        padding: 5px;
        color: black;
        text-align: right;
    }

    /* Input boxes should be transparent within the Streamlit dark bg */
    .expense-table input {
        background-color: white;
        border-bottom: 1px dotted rgba(0, 0, 0, 0.2);
    }

    .expense-sum-text {
        color: black;
        text-align: right;
        font-weight: 600;
        padding-right: 15px;
    }

    .total-output {
        color: black;
        text-align: right;
        padding: 5px;
        font-weight: 600;
    }

    .input-bold-border {
        border: 2px solid black;
    }

    /* Final line 'Importe estimado' bold style from image */
    .expense-bold-label {
        font-weight: 600;
        color: black;
    }

    /* Correcting visual dotted line overflow */
    .expense-table tr:last-child {
        border-bottom: none;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# Inject the necessary JS to handle calculations and form links
st.markdown(javascript_code, unsafe_allow_html=True)
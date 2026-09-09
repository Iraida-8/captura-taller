import json
import re

import streamlit as st
from auth import require_login, require_access
from pages.css import load_css
from supabase import create_client
import urllib.error
import urllib.request


# =================================
# RELEASE CHANNEL
# =================================
APP_CHANNEL = "BETA"
# APP_CHANNEL = "RELEASE"

DASHBOARD_PAGE = (
    "pages/dashboard_beta.py"
    if APP_CHANNEL == "BETA"
    else "pages/dashboard.py"
)


# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title=(
        "Agente IA OMEGA BETA"
        if APP_CHANNEL.upper() == "BETA"
        else "Agente IA OMEGA"
    ),
    layout="wide"
)


# =================================
# PAGE STYLE
# =================================
load_css()


# =================================
# Navigation
# =================================
st.write("")

if st.button("⬅ Volver al Dashboard"):
    st.switch_page(DASHBOARD_PAGE)

st.divider()


# =================================
# Security gates
# =================================
require_login()

user = st.session_state.user

require_access("ai_testing")


# =================================
# ROLE
# =================================
user_role = str(
    user.get("role", "")
).strip().lower()

if user_role not in ("admin", "manager"):
    st.info("Comming soon")
    st.stop()


# =================================
# SUPABASE
# =================================
@st.cache_resource
def get_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )


supabase = get_supabase()


# =================================
# OLLAMA
# =================================
OLLAMA_HOST = "https://highways-dimension-revelation-bend.trycloudflare.com"
OLLAMA_MODEL = "qwen3:14b"


def ollama_chat(messages, tools=None):

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    if tools:
        payload["tools"] = tools

    request = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.URLError as e:
        raise RuntimeError(
            "No se pudo conectar con Ollama. "
            "Asegúrate de que Ollama esté ejecutándose en "
            f"{OLLAMA_HOST} y que el modelo '{OLLAMA_MODEL}' esté instalado. "
            f"Detalle: {e}"
        ) from e


# =================================
# ACTIVITY LOG
# =================================
def log_activity(action, page):

    try:

        supabase.table("user_activity_log").insert({

            "user_id": user.get("id"),
            "user_name": user.get("name"),
            "login_counter": st.session_state.get("login_counter"),
            "action": action,
            "page": page,

        }).execute()

    except Exception as e:
        print(e)


# =================================
# PAGE ACTIVITY
# =================================
log_activity(
    "Abrió módulo AI Tester",
    "AI Tester"
)


# =================================
# HEADER
# =================================
st.title("🤖 Agente AI PG")

st.caption(
    "Consulta información de ShopPass utilizando lenguaje natural."
)


# =================================
# APPROVED DATABASE TABLES
# =================================
ALLOWED_TABLES = {
    "vehicle_units",
    "tc_mensual",
    "gps_vehicle_history",
    "gps_landmarks",
    "gps_sync_log",
}


# =================================
# DATABASE SCHEMA
# =================================
DATABASE_SCHEMA = """
ShopPass database.

Approved tables:

1. public.vehicle_units
   Fleet vehicle/unit information.

   Columns:
   - id: unique UUID for the record.
   - empresa: company code. This is the field used to identify
     which company owns/operates the unit.
   - unidad: unit number/identifier.
   - marca: vehicle/equipment brand or manufacturer.
   - modelo: model or model year.
   - vin: VIN/chassis identification number.
   - tipo_unidad: unit type, such as TRACTOR, CAJA SECA,
     CAJA REFRIGERADA, etc.
   - sucursal: branch/location assigned to the unit.
   - estado: current unit status, such as ACTIVA or other statuses.
   - created_at: record creation timestamp.

    IMPORTANT COMPANY MAPPING:
    - LIN = Lincoln
    - LF = Lincoln
    - IGT = Igloo
    - PIC = Picus
    - SLP = SLPlus
    - SET = SET

    IMPORTANT:
    - When the user asks for units belonging to a company,
    filter by empresa, NOT marca.
    - "empresa" identifies the company.
    - "marca" identifies the manufacturer/brand of the unit.

2. public.tc_mensual
   Monthly exchange rates.
   - YEAR + MONTH identify the month the TC applies to.
   - TC is the exchange rate.
   - DATE is the date the record was entered/registered.
   - DATE does NOT represent the applicable month.

3. public.gps_vehicle_history
   GPS vehicle history records.

4. public.gps_landmarks
   GPS landmark records.

5. public.gps_sync_log
   GPS synchronization log records.

Only these tables may be queried.
"""


# =================================
# SQL SAFETY
# =================================
def validate_sql(sql):

    sql = sql.strip()

    if not sql:
        raise ValueError("La consulta SQL está vacía.")

    # Remove markdown fences if the model accidentally returns them.
    sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"^```\s*", "", sql)
    sql = re.sub(r"\s*```$", "", sql)

    sql = sql.strip()

    # Only SELECT statements.
    if not re.match(r"^select\b", sql, flags=re.IGNORECASE):
        raise ValueError(
            "Solo se permiten consultas SELECT."
        )

    # No multiple statements.
    if ";" in sql.rstrip(";"):
        raise ValueError(
            "No se permiten múltiples consultas SQL."
        )

    # Block dangerous SQL operations.
    forbidden = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "create",
        "grant",
        "revoke",
        "execute",
        "call",
        "merge",
        "upsert",
        "pg_sleep",
    ]

    lowered = sql.lower()

    for keyword in forbidden:

        if re.search(
            rf"\b{re.escape(keyword)}\b",
            lowered
        ):
            raise ValueError(
                f"La consulta contiene una operación no permitida: {keyword}"
            )

    # Make sure only approved tables are referenced.
    tables = re.findall(
        r"(?:from|join)\s+"
        r'(?:(?:public)\.)?["`]?([a-zA-Z_][a-zA-Z0-9_]*)["`]?',
        sql,
        flags=re.IGNORECASE
    )

    for table in tables:

        if table.lower() not in ALLOWED_TABLES:

            raise ValueError(
                f"La tabla '{table}' no está autorizada para consultas de AI."
            )

    # Do not impose an automatic LIMIT.
    # The AI decides whether a LIMIT is appropriate based on the user's request.
    sql = sql.rstrip(";")

    return sql


# =================================
# DATABASE QUERY TOOL
# =================================
def query_shop_pass(sql):

    safe_sql = validate_sql(sql)

    try:

        result = supabase.rpc(
            "execute_readonly_query",
            {
                "query_text": safe_sql
            }
        ).execute()

        return result.data

    except Exception:

        # Fallback for direct SQL if the RPC is not available.
        # This is intentionally disabled so the AI cannot bypass
        # the SQL safety validation.
        raise


# =================================
# OLLAMA TOOL DEFINITION
# =================================
DATABASE_TOOL = {
    "type": "function",
    "function": {
        "name": "query_shop_pass",
        "description": (
            "Execute a READ-ONLY SQL SELECT query against the approved "
            "ShopPass database tables. Use this whenever the user asks "
            "for factual information contained in the database. "
            "Never use this tool to modify data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": (
                        "A single PostgreSQL SELECT statement using only "
                        "the approved ShopPass tables."
                    ),
                }
            },
            "required": ["sql"],
            "additionalProperties": False,
        },
    },
}

# =================================
# AI INSTRUCTIONS
# =================================
AI_INSTRUCTIONS = f"""
You are AI OMEGA, an internal database assistant for ShopPass.

Your job is to answer questions using the ShopPass database.

{DATABASE_SCHEMA}

RULES:

1. If the user's question requires database information,
   ALWAYS call the query_shop_pass tool. Do not answer from memory
   or assume database values.

2. Do not guess database values.

3. Do not invent records, counts, totals, dates, or exchange rates.

4. You may only query the approved tables.

5. Only use SELECT queries.

6. Never attempt INSERT, UPDATE, DELETE, DROP, ALTER,
   TRUNCATE, CREATE, GRANT, REVOKE, or any other modification.

7. Keep database queries efficient.

8. Prefer aggregate SQL when the user asks for counts,
   sums, averages, minimums, maximums, comparisons, etc.

9. Do not retrieve thousands of individual rows when an
   aggregate query can answer the question.

10. When the user asks for a complete list, all units, all records,
    or similar wording:
    - Query ALL matching records.
    - Do NOT add an arbitrary LIMIT.
    - Do NOT return only a sample and describe it as the complete result.

11. Only use LIMIT when the user explicitly requests a limited
    number of records.

12. If the user asks "how many", "total", "count", etc., use
    COUNT(*) or another appropriate aggregate instead of retrieving
    individual records.

13. If the user asks for a list of units, return the complete
    matching list unless the user specifies a limit.

14. Never assume that a subset of returned rows represents the
    complete database.

15. When the user refers to a company by its name or abbreviation,
    use the empresa column in vehicle_units.

16. Company mappings:
    - LIN = Lincoln
    - LF = Lincoln
    - IGT = Igloo
    - PIC = Picus
    - SLP = SLPlus
    - SET = SET

17. Never use the marca column to determine the company.

18. If the user asks "cuántas unidades", use COUNT(*).

19. If the user asks for units belonging to a company,
    filter empresa using the appropriate company code.

20. If multiple company codes represent the same company,
    include all applicable codes. For Lincoln, use:
    empresa IN ('LIN', 'LF').

21. When the user asks for a list of units or the names/numbers
    of units, ALWAYS query the database for the actual unidad
    column.

22. Do not generate, infer, reconstruct, or invent unit names/numbers.

23. Every unit name/number presented to the user must come directly
    from the results returned by query_shop_pass.

24. If the user asks for information that exists in vehicle_units,
    you MUST query vehicle_units before answering.

25. Do not answer a database question using information from the
    previous conversation unless the current database query confirms it.

26. If a database query returns multiple records, do not replace
    those records with an example, sample, fabricated list, or
    description.
"""


# =================================
# SESSION STATE
# =================================
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []


# =================================
# DISPLAY PREVIOUS CHAT
# =================================
for message in st.session_state.ai_messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# =================================
# DATABASE QUERY EXECUTION LOOP
# =================================
def ask_ai(user_question):

    # Add user message to the visible conversation.
    st.session_state.ai_messages.append({
        "role": "user",
        "content": user_question,
    })

    # Build the Ollama conversation.
    # The system instructions are kept separate from the visible chat.
    model_messages = [
        {
            "role": "system",
            "content": AI_INSTRUCTIONS,
        }
    ]

    for message in st.session_state.ai_messages:

        model_messages.append({
            "role": message["role"],
            "content": message["content"],
        })

    # ---------------------------------
    # AI request / tool execution loop
    # ---------------------------------
    while True:

        response = ollama_chat(
            messages=model_messages,
            tools=[DATABASE_TOOL],
        )

        assistant_message = response.get("message", {})

        # If the model requested database tools, execute them and
        # send the results back to the local model.
        tool_calls = assistant_message.get("tool_calls", [])

        if not tool_calls:
            break

        # Preserve the assistant tool-call message exactly as returned
        # by Ollama so the next request has the required tool-call context.
        model_messages.append(assistant_message)

        for tool_call in tool_calls:

            function = tool_call.get("function", {})
            tool_name = function.get("name")

            if tool_name != "query_shop_pass":

                model_messages.append({
                    "role": "tool",
                    "content": json.dumps({
                        "error": "Unknown tool."
                    }),
                })

                continue

            try:

                arguments = function.get("arguments", {})
                sql = arguments.get("sql")

                if not sql:
                    raise ValueError(
                        "La herramienta no proporcionó una consulta SQL."
                    )

                data = query_shop_pass(sql)

                model_messages.append({
                    "role": "tool",
                    "content": json.dumps(
                        data,
                        default=str
                    ),
                })

            except Exception as e:

                model_messages.append({
                    "role": "tool",
                    "content": json.dumps({
                        "error": str(e)
                    }),
                })

    # ---------------------------------
    # Final answer
    # ---------------------------------
    answer = assistant_message.get("content", "").strip()

    if not answer:
        answer = (
            "No pude generar una respuesta a partir de la información "
            "disponible en ShopPass."
        )

    st.session_state.ai_messages.append({
        "role": "assistant",
        "content": answer,
    })

    return answer


# =================================
# CHAT INPUT
# =================================
question = st.chat_input(
    "Pregunta algo sobre ShopPass..."
)


if question:

    with st.chat_message("user"):

        st.markdown(question)

    with st.chat_message("assistant"):

        with st.spinner("Consultando ShopPass..."):

            try:

                answer = ask_ai(question)

                st.markdown(answer)

                log_activity(
                    f"AI Tester: {question}",
                    "AI Tester"
                )

            except Exception as e:

                error_message = (
                    "No pude consultar la información "
                    f"de ShopPass.\n\n`{str(e)}`"
                )

                st.error(error_message)

                log_activity(
                    "AI Tester: error en consulta",
                    "AI Tester"
                )


# =================================
# CLEAR CHAT
# =================================
if st.session_state.ai_messages:

    st.divider()

    if st.button(
        "🗑️ Limpiar conversación",
        key="clear_ai_chat"
    ):

        st.session_state.ai_messages = []

        st.rerun()
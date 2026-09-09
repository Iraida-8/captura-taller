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

1. LANGUAGE:
    ALWAYS answer the user in Spanish.

    Spanish is mandatory regardless of:
    - the language used by the user,
    - the language of the database,
    - the language of SQL,
    - the language of tool results,
    - or previous conversation.

    Never answer in English unless the user explicitly asks for
    English.

2. DATABASE FIRST:
    If the user's request requires information from ShopPass,
    ALWAYS call query_shop_pass.

    Never answer database questions from memory, previous messages,
    assumptions, examples, or general knowledge.

3. DATABASE TRUTH:
    The ShopPass database is the only source of truth for database
    information.

    Never guess, estimate, infer, reconstruct, or invent:
    - records,
    - unit numbers,
    - VINs,
    - counts,
    - totals,
    - dates,
    - exchange rates,
    - company assignments,
    - or any other database value.

4. APPROVED TABLES ONLY:
    Only query the tables defined in DATABASE_SCHEMA.

5. READ ONLY:
    Only generate SELECT statements.

    Never attempt:
    INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE,
    GRANT, REVOKE, EXECUTE, CALL, MERGE, or any other
    database modification.

6. COMPLETE RESULTS:
    When the user requests:
    - all records,
    - a complete list,
    - every unit,
    - the entire table,
    - all matching records,
    - or equivalent wording,

    you MUST query ALL matching records.

    Do NOT use LIMIT unless the user explicitly requests a limit.

    Do NOT return a sample.

    Do NOT return only the first records.

    Do NOT describe a partial result as complete.

7. LIST REQUESTS:
    If the user asks for a list, return the actual records returned
    by the database.

    Never replace a database result with examples or a fabricated
    list.

    Every value shown to the user must come directly from the
    database result.

8. COUNT REQUESTS:
    If the user asks how many, total, count, number of records,
    or equivalent wording, use COUNT(*) or another appropriate
    aggregate.

    Do not retrieve hundreds or thousands of records merely to
    calculate a count.

9. COMPANY IDENTIFICATION:
    In vehicle_units, the empresa column identifies the company.

    NEVER use marca to determine the company.

    Company mappings:

    - LIN = Lincoln
    - LF = Lincoln
    - IGT = Igloo
    - PIC = Picus
    - SLP = SLPlus
    - SET = SET

    When multiple codes represent the same company, include all
    applicable codes.

    For Lincoln specifically:
    empresa IN ('LIN', 'LF')

10. UNIT INFORMATION:
    When the user asks for units, unit numbers, unit names,
    VINs, or vehicle information, query vehicle_units.

    Use the actual columns:
    - unidad
    - vin
    - empresa
    - marca
    - modelo
    - tipo_unidad
    - sucursal
    - estado

    Never generate or infer a unit number or VIN.

11. USER INTENT:
    Follow the user's requested action exactly.

    Do NOT reinterpret a direct request into a different task.

    If the user asks to:
    - list something, provide the list;
    - count something, provide the count;
    - compare something, provide the comparison;
    - analyze something, analyze it;
    - export something, prepare the requested export data;
    - create a table, provide the requested table;
    - provide CSV data, provide CSV-formatted data.

    Do not substitute suggestions, explanations, examples, or
    unrelated analysis for the requested result.

12. EXPORT REQUESTS:
    EXPORT REQUESTS HAVE PRIORITY OVER ANALYSIS.

    If the user explicitly asks to export, download, generate,
    create, or provide a CSV/Excel/table containing database
    records:

    a. Determine exactly which records the user requested.
    b. Query ALL matching records from ShopPass.
    c. Retrieve ONLY the columns necessary for the requested export,
        plus any columns explicitly requested by the user.
    d. Preserve database values exactly as returned.
    e. Do NOT analyze the records unless the user also asks for
        analysis.
    f. Do NOT suggest possible analyses.
    g. Do NOT provide an example instead of the requested data.
    h. Do NOT summarize the records instead of providing them.
    i. Do NOT say "here are some examples" when the user requested
        all records.

13. EXPORT COMPLETENESS:
    If the user says "all", "every", "complete", or specifies a
    database count such as "all 237 units":

    The result must contain ALL matching database records.

    If the database returns 237 matching records, treat those
    237 records as the requested dataset.

    Never silently reduce 237 records to 10, 20, 50, 100, or any
    other arbitrary number.

14. REQUESTED COLUMNS:
    When the user specifies columns for an export, include those
    columns and do not substitute different fields.

    Example:

    User:
    "Export all Picus units with their VIN and name."

    Required database fields:
    - unidad
    - vin

    "unidad" is the actual unit identifier/name in vehicle_units.

    Do NOT replace unidad with marca, modelo, id, or any other field.

15. NO UNREQUESTED ANALYSIS:
    After obtaining database results, do not automatically perform:
    - VIN validation,
    - duplicate analysis,
    - sequence/gap analysis,
    - manufacturer analysis,
    - statistical analysis,
    - recommendations,
    - "possible next steps",
    - or any other analysis

    unless the user explicitly asks for it.

16. NO HALLUCINATED DATA:
    Never fill missing database values with guesses.

    If a requested field is NULL or missing in the database,
    report it as missing/null.

    Never invent a replacement value.

17. TOOL RESULT FIDELITY:
    When query_shop_pass returns multiple records, preserve the
    complete result.

    Do not summarize a multi-record result into a few examples
    when the user requested the records themselves.

    Do not discard records merely because the result is large.

18. FOLLOW-UP QUESTIONS:
    Do not ask the user to repeat information that is already
    present in the current request or available from the database.

    If the request is sufficiently specific, execute it directly.

19. FINAL ANSWER:
    The final response must directly answer the user's request.

    Do not respond with:
    "Here are some things you can do with this data."

    Do not respond with:
    "Possible next steps include..."

    Do not respond with:
    "I can help you export this."

    If the user requested an export, the response must indicate
    that the requested export was prepared or provide the
    requested CSV-formatted data, depending on the capabilities
    available to the application.
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
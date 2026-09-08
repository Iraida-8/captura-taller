import json
import re

import streamlit as st
from auth import require_login, require_access
from pages.css import load_css
from supabase import create_client
from openai import OpenAI # type: ignore


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
        "AI STOOF BETA"
        if APP_CHANNEL.upper() == "BETA"
        else "AI STOOF"
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
# OPENAI
# =================================
@st.cache_resource
def get_openai():

    return OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )


openai_client = get_openai()


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
st.title("🤖 AI STOOF")

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

2. public.tc_mensual
   Monthly exchange rates.
   Important:
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

    # Protect against accidentally returning enormous datasets.
    if not re.search(
        r"\blimit\s+\d+",
        lowered
    ):

        sql = sql.rstrip(";")

        sql += "\nLIMIT 1000"

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
# OPENAI TOOL DEFINITION
# =================================
DATABASE_TOOL = {
    "type": "function",
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
    "strict": True,
}


# =================================
# AI INSTRUCTIONS
# =================================
AI_INSTRUCTIONS = f"""
You are AI STOOF, an internal database assistant for ShopPass.

Your job is to answer questions using the ShopPass database.

{DATABASE_SCHEMA}

RULES:

1. If the user's question requires database information,
   use the query_shop_pass tool.

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

10. If the user asks about monthly exchange rates:
    YEAR + MONTH identify the applicable period.
    DATE is only the record-registration date.

11. Answer in the same language used by the user.

12. When presenting database results, be clear about what
    the numbers represent.

13. If the database does not contain enough information
    to answer the question, say so rather than guessing.

14. You are a database assistant, not a general-purpose
    internet search assistant. Do not use external web
    information to answer ShopPass database questions.
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

    # Add user message to conversation.
    st.session_state.ai_messages.append({
        "role": "user",
        "content": user_question,
    })

    # Convert conversation into Responses API input.
    input_messages = []

    for message in st.session_state.ai_messages:

        input_messages.append({
            "role": message["role"],
            "content": message["content"],
        })


    # ---------------------------------
    # First AI request
    # ---------------------------------
    response = openai_client.responses.create(

        model="gpt-5.6-luna",

        instructions=AI_INSTRUCTIONS,

        input=input_messages,

        tools=[
            DATABASE_TOOL
        ],

        tool_choice="auto",

    )


    # ---------------------------------
    # Process tool calls
    # ---------------------------------
    while True:

        tool_calls = [
            item
            for item in response.output
            if getattr(item, "type", None) == "function_call"
        ]

        if not tool_calls:
            break


        tool_outputs = []


        for tool_call in tool_calls:

            if tool_call.name != "query_shop_pass":

                tool_outputs.append({

                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps({
                        "error": "Unknown tool."
                    }),
                })

                continue


            try:

                arguments = json.loads(
                    tool_call.arguments
                )

                sql = arguments["sql"]

                data = query_shop_pass(sql)

                tool_outputs.append({

                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps(
                        data,
                        default=str
                    ),
                })


            except Exception as e:

                tool_outputs.append({

                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps({
                        "error": str(e)
                    }),
                })


        # ---------------------------------
        # Continue the response with tool
        # results
        # ---------------------------------
        response = openai_client.responses.create(

            model="gpt-5.6-luna",

            instructions=AI_INSTRUCTIONS,

            previous_response_id=response.id,

            input=tool_outputs,

            tools=[
                DATABASE_TOOL
            ],

            tool_choice="auto",

        )


    # ---------------------------------
    # Final answer
    # ---------------------------------
    answer = response.output_text

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
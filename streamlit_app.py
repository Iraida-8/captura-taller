import streamlit as st
from supabase import create_client
import hashlib

# ✅ Verificación de sesión y rol
if "usuario" not in st.session_state:
    st.error("⚠️ No has iniciado sesión.")
    st.stop()

rol = st.session_state.usuario.get("Rol", "").lower()
if rol != "admin":
    st.error("🚫 No tienes permiso para acceder a este módulo.")
    st.stop()

# Conexión a Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("👤 Registro de Nuevo Usuario")

# 🔐 Función para hashear contraseña
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 📋 Formulario de registro
with st.form("form_registro"):
    id_usuario = st.text_input("ID Usuario (correo o nombre corto)")
    nombre = st.text_input("Nombre completo")
    password = st.text_input("Contraseña", type="password")
    rol = st.selectbox("Rol", ["Admin", "Gerente", "Ejecutivo", "Visitante"])

    submitted = st.form_submit_button("Registrar Usuario")

    if submitted:
        if not id_usuario or not password or not nombre:
            st.error("⚠️ Todos los campos son obligatorios.")
        else:
            datos = {
                "ID_Usuario": id_usuario,
                "Nombre": nombre,
                "Password": password,  # Solo para referencia visible
                "Rol": rol,
                "Password_Hash": hash_password(password)  # Para login
            }
            try:
                supabase.table("Usuarios").insert(datos).execute()
                st.success(f"✅ Usuario {nombre} registrado correctamente.")
            except Exception as e:
                st.error(f"❌ Error al registrar usuario: {e}")
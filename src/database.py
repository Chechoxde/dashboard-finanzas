import streamlit as st
from supabase import create_client, Client

# 1. Inicializar la conexión
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# Instancia global del cliente de Supabase
supabase = init_connection()

# 2. Funciones para traer los datos maestros
def get_medios_pago():
    """Obtiene todos los medios de pago de la base de datos."""
    response = supabase.table("medios_pago").select("*").execute()
    return response.data

def get_categorias():
    """Obtiene todas las categorías de la base de datos."""
    response = supabase.table("categorias").select("*").execute()
    return response.data

def get_subcategorias():
    """Obtiene todas las subcategorías de la base de datos."""
    response = supabase.table("subcategorias").select("*").execute()
    return response.data

def insert_transaccion(datos):
    """Inserta una nueva transacción en la base de datos."""
    response = supabase.table("transacciones").insert(datos).execute()
    return response.data
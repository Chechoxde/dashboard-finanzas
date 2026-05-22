import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Dashboard Sergio Ruiz", page_icon="📊", layout="wide")

# --- 1. CAPA DE SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acceso Restringido")
    st.markdown("Por favor, ingresa tu credencial para acceder a las finanzas.")
    
    password = st.text_input("Contraseña del Dashboard:", type="password")
    
    if st.button("Ingresar", type="primary"):
        if password == st.secrets["dashboard_password"]:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta. Intento bloqueado.")
    st.stop() # Detiene la ejecución aquí si no hay autenticación

# --- 2. CONEXIÓN Y EXTRACCIÓN DE DATOS ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase: Client = init_connection()

@st.cache_data(ttl=60) # Guarda los datos en caché por 60 segundos para no saturar Supabase
def cargar_datos():
    # Descargar tablas
    trans = supabase.table("transacciones").select("*").execute().data
    cats = supabase.table("categorias").select("*").execute().data
    subcats = supabase.table("subcategorias").select("*").execute().data
    
    df_trans = pd.DataFrame(trans)
    if df_trans.empty:
        return pd.DataFrame()
        
    df_cats = pd.DataFrame(cats)
    df_subcats = pd.DataFrame(subcats)
    
    # Cruzar datos (Joins) para tener nombres legibles en vez de IDs
    df_completo = pd.merge(df_trans, df_subcats, left_on="subcategoria_id", right_on="id", suffixes=("", "_sub"))
    df_completo = pd.merge(df_completo, df_cats, left_on="categoria_id", right_on="id", suffixes=("", "_cat"))
    
    # Limpiar y renombrar para el análisis
    df_completo.rename(columns={
        "nombre": "Subcategoría", 
        "nombre_cat": "Categoría", 
        "fecha_transaccion": "Fecha",
        "monto": "Monto"
    }, inplace=True)
    
    df_completo['Fecha'] = pd.to_datetime(df_completo['Fecha'])
    return df_completo

# --- 3. INTERFAZ DEL DASHBOARD ---
st.title("📊 Panel Financiero - Sergio Ruiz")
st.markdown("---")

df = cargar_datos()

if df.empty:
    st.info("Aún no hay transacciones en la base de datos. Usa tu App Web para registrar el primer movimiento.")
else:
    # Calcular KPIs
    ingresos_totales = df[df['tipo_movimiento'] == 'Ingreso']['Monto'].sum()
    gastos_totales = df[df['tipo_movimiento'] == 'Gasto']['Monto'].sum()
    balance = ingresos_totales - gastos_totales

    # Tarjetas de Resumen
    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos Históricos", f"${ingresos_totales:,.0f}".replace(",", "."))
    col2.metric("Gastos Históricos", f"${gastos_totales:,.0f}".replace(",", "."))
    col3.metric("Liquidez Disponible", f"${balance:,.0f}".replace(",", "."), 
                delta="Cuidado con los flujos" if balance < 0 else "Flujo positivo")

    st.markdown("---")

    # Fila de Gráficos
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Distribución de Gastos")
        df_gastos = df[df['tipo_movimiento'] == 'Gasto']
        if not df_gastos.empty:
            gastos_agrupados = df_gastos.groupby("Categoría")["Monto"].sum().reset_index()
            fig_pie = px.pie(gastos_agrupados, values='Monto', names='Categoría', 
                             hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("No hay datos de gastos para graficar.")

    with chart_col2:
        st.subheader("Flujo de Caja en el Tiempo")
        df_tiempo = df.groupby(['Fecha', 'tipo_movimiento'])['Monto'].sum().reset_index()
        fig_line = px.line(df_tiempo, x='Fecha', y='Monto', color='tipo_movimiento', 
                           markers=True, color_discrete_map={"Ingreso": "#20c997", "Gasto": "#ff6b6b"})
        st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")
    
    # Tabla de últimos movimientos
    st.subheader("Últimos Movimientos Registrados")
    columnas_mostrar = ['Fecha', 'tipo_movimiento', 'Categoría', 'Subcategoría', 'Monto', 'descripcion']
    df_vista = df[columnas_mostrar].sort_values(by='Fecha', ascending=False).head(15)
    
    # Formatear la fecha para que se vea solo el día en la tabla
    df_vista['Fecha'] = df_vista['Fecha'].dt.strftime('%Y-%m-%d')
    st.dataframe(df_vista, use_container_width=True, hide_index=True)
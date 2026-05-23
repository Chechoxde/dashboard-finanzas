import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
from datetime import datetime, timedelta

# Configuración de la página (Modo Wide para aprovechar la pantalla completa)
st.set_page_config(page_title="Finanzas Personales", page_icon="💰", layout="wide")

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
    st.stop()

# --- 2. CONEXIÓN Y EXTRACCIÓN DE DATOS ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase: Client = init_connection()

@st.cache_data(ttl=60)
def cargar_datos():
    trans = supabase.table("transacciones").select("*").execute().data
    cats = supabase.table("categorias").select("*").execute().data
    subcats = supabase.table("subcategorias").select("*").execute().data
    
    df_trans = pd.DataFrame(trans)
    if df_trans.empty:
        return pd.DataFrame()
        
    df_cats = pd.DataFrame(cats)
    df_subcats = pd.DataFrame(subcats)
    
    df_completo = pd.merge(df_trans, df_subcats, left_on="subcategoria_id", right_on="id", how="left", suffixes=("", "_sub"))
    df_completo = pd.merge(df_completo, df_cats, left_on="categoria_id", right_on="id", how="left", suffixes=("", "_cat"))
    
    if 'nombre' in df_completo.columns:
        df_completo['nombre'] = df_completo['nombre'].fillna('Sin Subcategoría')
    else:
        df_completo['nombre'] = 'Sin Subcategoría'
        
    if 'nombre_cat' in df_completo.columns:
        df_completo['nombre_cat'] = df_completo['nombre_cat'].fillna('Sin Categoría')
    else:
        df_completo['nombre_cat'] = 'Sin Categoría'
    
    df_completo.rename(columns={
        "nombre": "Subcategoría", 
        "nombre_cat": "Categoría", 
        "fecha_transaccion": "Fecha",
        "monto": "Monto"
    }, inplace=True)
    
    df_completo['Fecha'] = pd.to_datetime(df_completo['Fecha'])
    return df_completo

df_crudo = cargar_datos()

if df_crudo.empty:
    st.title("📊 Control de Gastos e Ingresos")
    st.info("Aún no hay transacciones en la base de datos. ¡Registra algo en tu web primero!")
else:
    # --- 3. DISEÑO DE FILTROS EN LA BARRA LATERAL (SIDEBAR) ---
    st.sidebar.header("🔍 Filtros de Análisis")
    st.sidebar.markdown("Ajusta los parámetros para segmentar la información.")
    
    # Filtro 1: Rango de Fechas Dinámico
    fecha_min = df_crudo['Fecha'].min().date()
    fecha_max = df_crudo['Fecha'].max().date()
    
    st.sidebar.subheader("Calendario")
    rango_fechas = st.sidebar.date_input(
        "Selecciona el período:",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max
    )
    
    # Filtro 2: Selector de Categorías Multi-selección
    st.sidebar.subheader("Segmentación")
    categorias_disponibles = sorted(df_crudo['Categoría'].unique())
    categorias_seleccionadas = st.sidebar.multiselect(
        "Filtrar por categorías:",
        options=categorias_disponibles,
        default=categorias_disponibles # Por defecto vienen todas marcadas
    )
    
    # --- APLICACIÓN DE FILTROS ---
    # Filtrar por rango de fecha (evita errores si el usuario solo marca una fecha en el calendario)
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        inicio, fin = rango_fechas
        df_filtrado = df_crudo[(df_crudo['Fecha'].dt.date >= inicio) & (df_crudo['Fecha'].dt.date <= fin)]
    else:
        df_filtrado = df_crudo.copy()
        
    # Filtrar por categorías
    df_filtrado = df_filtrado[df_filtrado['Categoría'].isin(categorias_seleccionadas)]

    # --- 4. INTERFAZ VISUAL DEL DASHBOARD ---
    st.title("📊 Mi Centro de Mando Financiero")
    st.markdown("Un análisis detallado de dónde se va cada peso en tiempo real.")
    st.markdown("---")

    if df_filtrado.empty:
        st.warning("No hay transacciones que coincidan con los filtros seleccionados en la barra lateral.")
    else:
        # Cálculos de KPIs basados en el filtro
        ingresos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Ingreso']['Monto'].sum()
        gastos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Gasto']['Monto'].sum()
        balance = ingresos - gastos

        # Tarjetas de Resumen Estilizadas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.container(border=True)
            st.metric("Total Ingresos", f"${ingresos:,.0f}".replace(",", "."), delta=None)
        with col2:
            st.container(border=True)
            st.metric("Total Gastos", f"${gastos:,.0f}".replace(",", "."), delta=None, delta_color="inverse")
        with col3:
            st.container(border=True)
            # Cambia de color dinámicamente si el balance es positivo o negativo
            st.metric(
                "Saldo Neto (Liquidez)", 
                f"${balance:,.0f}".replace(",", "."), 
                delta="Superávit" if balance >= 0 else "Déficit en el período",
                delta_color="normal" if balance >= 0 else "inverse"
            )

        st.markdown("##") # Espaciador

        # --- 5. BLOQUE DE GRÁFICOS OPTIMIZADOS (PLOTLY PREMIUM) ---
        chart_col1, chart_col2 = st.columns([4, 6]) # Distribución de tamaño (40% y 60%)

        with chart_col1:
            st.subheader("🍕 Distribución del Gasto")
            df_gastos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Gasto']
            
            if not df_gastos.empty:
                gastos_agrupados = df_gastos.groupby("Categoría")["Monto"].sum().reset_index()
                
                fig_pie = px.pie(
                    gastos_agrupados, 
                    values='Monto', 
                    names='Categoría', 
                    hole=0.5, # Efecto Donut ultra moderno
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                # Embellecer layout: quitar márgenes innecesarios y poner leyenda abajo
                fig_pie.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No hay gastos registrados en este período.")

        with chart_col2:
            st.subheader("📈 Tendencia del Flujo de Caja")
            # Agrupar por fecha y tipo para ver la línea de tiempo limpia
            df_tiempo = df_filtrado.groupby(['Fecha', 'tipo_movimiento'])['Monto'].sum().reset_index()
            
            fig_line = px.line(
                df_tiempo, 
                x='Fecha', 
                y='Monto', 
                color='tipo_movimiento', 
                markers=True,
                color_discrete_map={"Ingreso": "#20c997", "Gasto": "#ff6b6b"},
                template="plotly_white" # Fondo limpio y estilizado
            )
            # Hacer las líneas curvas y suaves, ajustar grillas
            fig_line.update_traces(line_shape="spline", width=3)
            fig_line.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                xaxis=dict(showgrid=True, gridcolor="#f1f3f5"),
                yaxis=dict(showgrid=True, gridcolor="#f1f3f5"),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, title_text="")
            )
            st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("---")
        
        # --- 6. TABLA DE CONTROL INTERACTIVA ---
        st.subheader("📋 Historial Detallado de Movimientos")
        st.markdown("Puedes hacer clic en los encabezados de la tabla para ordenar los datos instantáneamente.")
        
        columnas_ideales = ['Fecha', 'tipo_movimiento', 'Categoría', 'Subcategoría', 'Monto', 'descripcion']
        columnas_mostrar = [col for col in columnas_ideales if col in df_filtrado.columns]
        
        df_vista = df_filtrado[columnas_mostrar].sort_values(by='Fecha', ascending=False)
        df_vista['Fecha'] = df_vista['Fecha'].dt.strftime('%Y-%m-%d')
        
        # Usar st.dataframe con contenedor expandido para una lectura óptima
        st.dataframe(
            df_vista, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Monto": st.column_config.NumberColumn("Monto", format="$%d"),
                "tipo_movimiento": "Tipo",
                "descripcion": "Descripción u Observación"
            }
        )
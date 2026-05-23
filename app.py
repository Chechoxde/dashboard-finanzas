import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Control Financiero Personal", page_icon="💸", layout="wide")

# --- 1. CAPA DE SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acceso Restringido")
    st.markdown("Por favor, ingresa tu credencial para acceder a tus finanzas.")
    
    password = st.text_input("Contraseña:", type="password")
    
    if st.button("Ingresar", type="primary"):
        if password == st.secrets["dashboard_password"]:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()

# --- 2. EXTRACCIÓN Y LIMPIEZA DE DATOS ---
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
    
    # Cruces seguros
    df_completo = pd.merge(df_trans, df_subcats, left_on="subcategoria_id", right_on="id", how="left", suffixes=("", "_sub"))
    df_completo = pd.merge(df_completo, df_cats, left_on="categoria_id", right_on="id", how="left", suffixes=("", "_cat"))
    
    # Limpieza de nulos
    df_completo['nombre'] = df_completo.get('nombre', 'Sin Subcategoría').fillna('Sin Subcategoría')
    df_completo['nombre_cat'] = df_completo.get('nombre_cat', 'Sin Categoría').fillna('Sin Categoría')
    
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
    st.title("💸 Mi Tablero Financiero")
    st.info("Aún no hay transacciones en la base de datos.")
else:
    # --- 3. BARRA LATERAL: FILTROS AVANZADOS ---
    st.sidebar.title("🎯 Panel de Control")
    st.sidebar.markdown("Filtra para encontrar fugas de dinero.")
    
    # Filtro de Fechas
    fecha_min = df_crudo['Fecha'].min().date()
    fecha_max = df_crudo['Fecha'].max().date()
    
    st.sidebar.subheader("📅 Rango de Tiempo")
    rango_fechas = st.sidebar.date_input(
        "Selecciona el período:",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max
    )
    
    # Filtro de Categorías
    st.sidebar.subheader("🏷️ Categorías")
    categorias_disponibles = sorted(df_crudo['Categoría'].unique())
    categorias_seleccionadas = st.sidebar.multiselect(
        "¿Qué gastos quieres ver?",
        options=categorias_disponibles,
        default=categorias_disponibles
    )

    # Aplicar filtros
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        inicio, fin = rango_fechas
        df_filtrado = df_crudo[(df_crudo['Fecha'].dt.date >= inicio) & (df_crudo['Fecha'].dt.date <= fin)]
    else:
        df_filtrado = df_crudo.copy()
        
    df_filtrado = df_filtrado[df_filtrado['Categoría'].isin(categorias_seleccionadas)]

    # --- 4. DASHBOARD PRINCIPAL ---
    st.title("💸 Mi Tablero Financiero")
    st.markdown("---")

    if df_filtrado.empty:
        st.warning("No hay movimientos con los filtros actuales.")
    else:
        # KPIs Financieros
        ingresos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Ingreso']['Monto'].sum()
        gastos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Gasto']['Monto'].sum()
        balance = ingresos - gastos
        
        # Calcular tasa de consumo (evitar división por cero)
        tasa_consumo = (gastos / ingresos * 100) if ingresos > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ingresos", f"${ingresos:,.0f}".replace(",", "."))
        col2.metric("Gastos", f"${gastos:,.0f}".replace(",", "."), delta=None, delta_color="inverse")
        col3.metric(
            "Liquidez", 
            f"${balance:,.0f}".replace(",", "."), 
            delta="Ahorro" if balance >= 0 else "Pérdida",
            delta_color="normal" if balance >= 0 else "inverse"
        )
        col4.metric(
            "Tasa de Consumo", 
            f"{tasa_consumo:.1f}%", 
            help="Qué porcentaje de tus ingresos te estás gastando. Ideal mantenerlo bajo el 80%."
        )

        st.markdown("##")

        # --- 5. VISUALIZACIONES ESTRATÉGICAS ---
        tab1, tab2 = st.tabs(["📊 Análisis de Gastos", "📈 Tendencia de Flujo"])
        
        with tab1:
            col_chart1, col_chart2 = st.columns(2)
            df_gastos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Gasto']
            
            with col_chart1:
                st.subheader("Distribución General")
                if not df_gastos.empty:
                    fig_pie = px.pie(
                        df_gastos, values='Monto', names='Categoría', hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20), legend=dict(orientation="h", y=-0.1))
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("Sin gastos para graficar.")
            
            with col_chart2:
                st.subheader("Top Fugas de Dinero (Subcategorías)")
                if not df_gastos.empty:
                    # Agrupar por subcategoría para ver el detalle fino
                    top_gastos = df_gastos.groupby("Subcategoría")["Monto"].sum().reset_index()
                    top_gastos = top_gastos.sort_values(by="Monto", ascending=True).tail(5) # Top 5
                    
                    fig_bar = px.bar(
                        top_gastos, x='Monto', y='Subcategoría', orientation='h',
                        color_discrete_sequence=['#ff6b6b'], text_auto='.2s'
                    )
                    fig_bar.update_layout(margin=dict(t=20, b=20, l=20, r=20), xaxis_title="Monto ($)", yaxis_title="")
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("Sin gastos para graficar.")

        with tab2:
            st.subheader("Línea de Tiempo")
            df_tiempo = df_filtrado.groupby(['Fecha', 'tipo_movimiento'])['Monto'].sum().reset_index()
            
            if not df_tiempo.empty:
                fig_line = px.line(
                    df_tiempo, x='Fecha', y='Monto', color='tipo_movimiento', markers=True,
                    color_discrete_map={"Ingreso": "#20c997", "Gasto": "#ff6b6b"}
                )
                # SOLUCIÓN DEL ERROR PLOTLY AQUÍ:
                fig_line.update_traces(line=dict(shape="spline", width=3))
                
                fig_line.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, title_text="")
                )
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Sin datos en el tiempo.")

        st.markdown("---")
        
        # --- 6. TABLA MAESTRA ---
        st.subheader("📋 Registro Detallado")
        
        columnas_mostrar = [col for col in ['Fecha', 'tipo_movimiento', 'Categoría', 'Subcategoría', 'Monto', 'descripcion'] if col in df_filtrado.columns]
        df_vista = df_filtrado[columnas_mostrar].sort_values(by='Fecha', ascending=False)
        df_vista['Fecha'] = df_vista['Fecha'].dt.strftime('%Y-%m-%d')
        
        st.dataframe(
            df_vista, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Monto": st.column_config.NumberColumn("Monto", format="$%d"),
                "tipo_movimiento": "Tipo",
                "descripcion": "Descripción"
            }
        )
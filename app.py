import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go

# Configuración premium de la página
st.set_page_config(page_title="Terminal Financiera", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# --- 1. CAPA DE SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔒 Acceso Seguro</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Ingresa tu credencial maestra para desencriptar los datos.</p>", unsafe_allow_html=True)
        password = st.text_input("", type="password", placeholder="Contraseña de acceso...")
        
        if st.button("Desbloquear Terminal", type="primary", use_container_width=True):
            if password == st.secrets["dashboard_password"]:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Acceso denegado. Contraseña incorrecta.")
    st.stop()

# --- 2. MOTOR DE DATOS ---
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
    st.title("📈 Terminal Financiera Activa")
    st.info("Esperando telemetría... Registra tu primera transacción en la aplicación web.")
else:
    # --- 3. SIDEBAR: FILTROS TÁCTICOS ---
    with st.sidebar:
        st.header("⚙️ Parámetros")
        
        # Calendario Inteligente
        fecha_min = df_crudo['Fecha'].min().date()
        fecha_max = df_crudo['Fecha'].max().date()
        rango_fechas = st.date_input("Rango de Análisis:", value=(fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max)
        
        # Filtros de Multiselección
        categorias_disponibles = sorted(df_crudo['Categoría'].unique())
        categorias_seleccionadas = st.multiselect("Categorías Visibles:", options=categorias_disponibles, default=categorias_disponibles)
        
        st.markdown("---")
        st.markdown("💡 *Tip: Haz clic en los anillos del gráfico Sunburst para aislar una categoría.*")

    # Aplicación estricta de filtros
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        inicio, fin = rango_fechas
        df_filtrado = df_crudo[(df_crudo['Fecha'].dt.date >= inicio) & (df_crudo['Fecha'].dt.date <= fin)]
    else:
        df_filtrado = df_crudo.copy()
        inicio, fin = fecha_min, fecha_max
        
    df_filtrado = df_filtrado[df_filtrado['Categoría'].isin(categorias_seleccionadas)]

    # --- 4. CÁLCULO DE KPIs INTELIGENTES ---
    ingresos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Ingreso']['Monto'].sum()
    gastos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Gasto']['Monto'].sum()
    balance = ingresos - gastos
    
    dias_periodo = (fin - inicio).days + 1
    gasto_diario = gastos / dias_periodo if dias_periodo > 0 else gastos
    tasa_consumo = (gastos / ingresos * 100) if ingresos > 0 else 0

    # --- 5. CABECERA Y MÉTRICAS ---
    st.title("📊 Análisis de Liquidez Personal")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.container(border=True)
        st.metric("Ingresos Totales", f"${ingresos:,.0f}".replace(",", "."), help="Suma de todas las entradas en el período.")
    with col2:
        st.container(border=True)
        st.metric("Gastos Totales", f"${gastos:,.0f}".replace(",", "."), delta=f"~${gasto_diario:,.0f}/día".replace(",", "."), delta_color="inverse")
    with col3:
        st.container(border=True)
        st.metric("Saldo Neto", f"${balance:,.0f}".replace(",", "."), delta="Superávit" if balance >= 0 else "Déficit", delta_color="normal" if balance >= 0 else "inverse")
    with col4:
        st.container(border=True)
        st.metric("Tasa de Consumo", f"{tasa_consumo:.1f}%", help="Porcentaje de tus ingresos que has gastado.")
        # Barra de progreso visual para el estrés financiero
        if tasa_consumo > 100:
            st.progress(1.0, text="¡Peligro! Gastando más de lo que entra.")
        elif tasa_consumo > 80:
            st.warning("Precaución: Consumo alto.")
        else:
            st.progress(tasa_consumo / 100)

    st.markdown("##")

    # --- 6. PANTALLAS DE VISUALIZACIÓN (TABS) ---
    tab_graficos, tab_datos = st.tabs(["👁️ Visualización Avanzada", "🗄️ Bóveda de Registros"])

    with tab_graficos:
        row1_col1, row1_col2 = st.columns([1, 1])
        
        with row1_col1:
            st.subheader("🧬 Ecosistema de Gastos (Sunburst)")
            df_gastos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Gasto']
            
            if not df_gastos.empty:
                # Gráfico interactivo jerárquico
                fig_sun = px.sunburst(
                    df_gastos, 
                    path=['Categoría', 'Subcategoría'], 
                    values='Monto',
                    color='Categoría',
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_sun.update_traces(textinfo="label+percent parent")
                fig_sun.update_layout(margin=dict(t=10, l=10, r=10, b=10))
                st.plotly_chart(fig_sun, use_container_width=True)
            else:
                st.info("No hay datos de salidas para graficar.")

        with row1_col2:
            st.subheader("🎯 Top Fugas de Dinero")
            if not df_gastos.empty:
                top_gastos = df_gastos.groupby("Subcategoría")["Monto"].sum().reset_index()
                top_gastos = top_gastos.sort_values(by="Monto", ascending=True).tail(7) # Mostramos el Top 7
                
                fig_bar = px.bar(
                    top_gastos, 
                    x='Monto', 
                    y='Subcategoría', 
                    orientation='h',
                    text_auto='.2s',
                    color='Monto',
                    color_continuous_scale="Reds" # Mapa de calor para enfatizar gastos altos
                )
                fig_bar.update_layout(margin=dict(t=10, l=10, r=10, b=10), showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No hay datos de salidas para graficar.")

        st.markdown("---")
        st.subheader("📈 Velocidad de Flujo (Línea de Tiempo)")
        df_tiempo = df_filtrado.groupby(['Fecha', 'tipo_movimiento'])['Monto'].sum().reset_index()
        
        if not df_tiempo.empty:
            fig_line = px.line(
                df_tiempo, x='Fecha', y='Monto', color='tipo_movimiento', markers=True,
                color_discrete_map={"Ingreso": "#20c997", "Gasto": "#ff6b6b"}
            )
            fig_line.update_traces(line=dict(shape="spline", width=3), marker=dict(size=8))
            fig_line.update_layout(
                hovermode="x unified", # Tooltip avanzado al pasar el mouse
                margin=dict(t=10, l=10, r=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, title_text=""),
                xaxis_title="", yaxis_title="Monto ($)"
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Sin datos para trazar la línea de tiempo.")

    with tab_datos:
        col_down1, col_down2 = st.columns([8, 2])
        with col_down1:
            st.subheader("📋 Auditoría de Movimientos")
        with col_down2:
            # Botón nativo para exportar a CSV
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"finanzas_{inicio}_al_{fin}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        columnas_mostrar = [col for col in ['Fecha', 'tipo_movimiento', 'Categoría', 'Subcategoría', 'Monto', 'descripcion'] if col in df_filtrado.columns]
        df_vista = df_filtrado[columnas_mostrar].sort_values(by='Fecha', ascending=False)
        df_vista['Fecha'] = df_vista['Fecha'].dt.strftime('%Y-%m-%d')
        
        st.dataframe(
            df_vista, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Monto": st.column_config.NumberColumn("Monto", format="$%d"),
                "tipo_movimiento": st.column_config.TextColumn("Tipo"),
                "descripcion": st.column_config.TextColumn("Nota")
            }
        )
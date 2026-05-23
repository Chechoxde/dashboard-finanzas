import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# --- CONFIGURACIÓN PREMIUM DE LA PÁGINA ---
st.set_page_config(
    page_title="Control Financiero S&F", 
    page_icon="💎", 
    layout="wide", # Clave para el look dashboard
    initial_sidebar_state="expanded"
)

# --- INYECCIÓN DE CSS PERSONALIZADO (MÁGIA VISUAL) ---
# Esto replica las tarjetas redondeadas, sombras y colores de tu imagen de referencia.
st.markdown("""
<style>
    /* Fondo principal más claro */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Tipografía moderna */
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }

    /* Ocultar barra superior nativa de Streamlit para limpieza */
    header {visibility: hidden;}
    .reportview-container .main .footer {visibility: hidden;}
    
    /* Estilo para los títulos principales */
    .main-title {
        color: #1e293b;
        font-weight: 800;
        letter-spacing: -1px;
        margin-bottom: 0px;
    }
    
    /* Contenedor de métricas (replicando image_9.png) */
    [data-testid="stHorizontalBlock"] {
        gap: 1rem;
    }
    
    /* Estilo de Tarjeta Métricas (KPIs) con sombra y bordes redondeados */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border-bottom: 4px solid transparent;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-3px);
    }
    
    /* Colores específicos para las tarjetas (como en tu referencia) */
    .blue-card { border-bottom-color: #339af0; } /* Ingresos */
    .red-card { border-bottom-color: #ff6b6b; }  /* Gastos */
    .green-card { border-bottom-color: #20c997; } /* Saldo Positivo */
    .orange-card { border-bottom-color: #fcc419; } /* Saldo Negativo */
    .purple-card { border-bottom-color: #845ef7; } /* Burn Rate */

    .metric-title {
        color: #868e96;
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 5px;
    }
    
    .metric-value {
        color: #1e293b;
        font-size: 32px;
        font-weight: 800;
    }
    
    .metric-delta {
        font-size: 14px;
        font-weight: 500;
    }
    
    /* Estilo para las secciones/gráficos (cards blancas) */
    .chart-container {
        background-color: white;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    
    .chart-title {
        color: #1e293b;
        font-weight: 700;
        font-size: 18px;
        margin-bottom: 15px;
    }

</style>
""", unsafe_allow_html=True)

# --- 1. CAPA DE SEGURIDAD (ESTILIZADA) ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>🔒 Terminal Segura</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Ingresa tu credencial para desencriptar el panel.</p>", unsafe_allow_html=True)
        password = st.text_input("", type="password", placeholder="Contraseña Maestra...")
        
        if st.button("Desbloquear Sistema", type="primary", use_container_width=True):
            if password == st.secrets["dashboard_password"]:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Credencial incorrecta.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 2. MOTOR DE DATOS (CONEXIÓN Y CARGA) ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase: Client = init_connection()

@st.cache_data(ttl=60)
def cargar_datos():
    # Descargar tablas base
    trans = supabase.table("transacciones").select("*").execute().data
    cats = supabase.table("categorias").select("*").execute().data
    subcats = supabase.table("subcategorias").select("*").execute().data
    
    df_trans = pd.DataFrame(trans)
    if df_trans.empty: return pd.DataFrame()
        
    df_cats = pd.DataFrame(cats)
    df_subcats = pd.DataFrame(subcats)
    
    # Cruces seguros
    df_completo = pd.merge(df_trans, df_subcats, left_on="subcategoria_id", right_on="id", how="left", suffixes=("", "_sub"))
    df_completo = pd.merge(df_completo, df_cats, left_on="categoria_id", right_on="id", how="left", suffixes=("", "_cat"))
    
    # Relleno de Nulos por seguridad
    df_completo['nombre'] = df_completo.get('nombre', 'Sin Subcategoría').fillna('Sin Subcategoría')
    df_completo['nombre_cat'] = df_completo.get('nombre_cat', 'Sin Categoría').fillna('Sin Categoría')
    
    # Renombrado de columnas gerenciales
    df_completo.rename(columns={
        "nombre": "Subcategoría", 
        "nombre_cat": "Categoría", 
        "fecha_transaccion": "Fecha",
        "monto": "Monto",
        "tipo_movimiento": "Tipo"
    }, inplace=True)
    
    df_completo['Fecha'] = pd.to_datetime(df_completo['Fecha'])
    return df_completo

df_crudo = cargar_datos()

if df_crudo.empty:
    st.markdown("<h1 class='main-title'>💎 Terminal de Control Financiero</h1>", unsafe_allow_html=True)
    st.info("Conexión activa pero sin telemetría. Registra movimientos en la Web App.")
else:
    # --- 3. BARRA LATERAL (FILTROS GERENCIALES) ---
    with st.sidebar:
        st.image("https://supabase.com/dashboard/img/supabase-logo.svg", width=50) # O el logo de S&F si tienes url
        st.markdown("<h2 style='color: white;'>Panel de Control</h2>", unsafe_allow_html=True)
        
        # Filtro de Fechas
        fecha_min = df_crudo['Fecha'].min().date()
        fecha_max = df_crudo['Fecha'].max().date()
        
        st.markdown("---")
        st.subheader("📅 Ventana de Tiempo")
        rango_fechas = st.date_input("Selecciona Período:", value=(fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max)
        
        # Filtro de Categorías
        st.markdown("---")
        st.subheader("🏷️ Segmentación")
        categorias_disponibles = sorted(df_crudo['Categoría'].unique())
        categorias_seleccionadas = st.multiselect("Categorías a Visualizar:", options=categorias_disponibles, default=categorias_disponibles)
        
        st.markdown("---")
        st.markdown("<small style='color: gray;'>S&F Atelier Finance Tool v4.0</small>", unsafe_allow_html=True)

    # Aplicar filtros estrictos
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        inicio, fin = rango_fechas
        df_filtrado = df_crudo[(df_crudo['Fecha'].dt.date >= inicio) & (df_crudo['Fecha'].dt.date <= fin)]
        dias_periodo = (fin - inicio).days + 1
    else:
        df_filtrado = df_crudo.copy()
        inicio, fin = fecha_min, fecha_max
        dias_periodo = (fecha_max - fecha_min).days + 1
        
    df_filtrado = df_filtrado[df_filtrado['Categoría'].isin(categorias_seleccionadas)]

    # --- 4. CÁLCULO DE KPIs ---
    ingresos = df_filtrado[df_filtrado['Tipo'] == 'Ingreso']['Monto'].sum()
    gastos = df_filtrado[df_filtrado['Tipo'] == 'Gasto']['Monto'].sum()
    balance = ingresos - gastos
    gasto_promedio_diario = gastos / dias_periodo if dias_periodo > 0 else gastos

    # --- 5. CUERPO PRINCIPAL (DISEÑO PREMIUM) ---
    st.markdown("<h1 class='main-title'>💎 Terminal de Control Financiero</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #64748b; margin-top: -5px;'>Análisis del {inicio} al {fin} ({dias_periodo} días)</p>", unsafe_allow_html=True)
    st.markdown("---")

    if df_filtrado.empty:
        st.warning("No hay telemetría para los filtros seleccionados.")
    else:
        # Fila 1: Tarjetas Métricas (Replicando estética de image_9.png)
        col1, col2, col3, col4 = st.columns(4)
        
        # Tarjeta 1: Ingresos (Azul)
        with col1:
            st.markdown(f"""
                <div class="metric-card blue-card">
                    <div class="metric-title">Ingresos Totales</div>
                    <div class="metric-value">${ingresos:,.0f}</div>
                    <div class="metric-delta" style="color: #20c997;">↑ Entradas de efectivo</div>
                </div>
            """, unsafe_allow_html=True)
            
        # Tarjeta 2: Gastos (Rojo)
        with col2:
            st.markdown(f"""
                <div class="metric-card red-card">
                    <div class="metric-title">Gastos Totales</div>
                    <div class="metric-value">${gastos:,.0f}</div>
                    <div class="metric-delta" style="color: #ff6b6b;">↓ Salidas de efectivo</div>
                </div>
            """, unsafe_allow_html=True)

        # Tarjeta 3: Saldo Neto (Dinámica Verde/Naranja)
        color_saldo = "#20c997" if balance >= 0 else "#fcc419"
        card_saldo = "green-card" if balance >= 0 else "orange-card"
        texto_saldo = "↑ Superávit" if balance >= 0 else "↓ Déficit"
        with col3:
            st.markdown(f"""
                <div class="metric-card {card_saldo}">
                    <div class="metric-title">Saldo Neto (Liquidez)</div>
                    <div class="metric-value" style="color: {color_saldo};">${balance:,.0f}</div>
                    <div class="metric-delta" style="color: {color_saldo};">{texto_saldo}</div>
                </div>
            """, unsafe_allow_html=True)
            
        # Tarjeta 4: Burn Rate (Morado)
        with col4:
            st.markdown(f"""
                <div class="metric-card purple-card">
                    <div class="metric-title">Gasto Promedio Diario</div>
                    <div class="metric-value">${gasto_promedio_diario:,.0f}</div>
                    <div class="metric-delta" style="color: gray;">Ritmo de consumo</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Fila 2: Gráficos Principales en Secciones Redondeadas
        row2_col1, row2_col2 = st.columns([6, 4]) # 60% Tendencia, 40% Distribución

        with row2_col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title">📈 Evolución del Flujo de Caja (Tendencia)</div>', unsafe_allow_html=True)
            df_tiempo = df_filtrado.groupby(['Fecha', 'Tipo'])['Monto'].sum().reset_index()
            if not df_tiempo.empty:
                fig_line = px.line(
                    df_tiempo, x='Fecha', y='Monto', color='Tipo', markers=True,
                    color_discrete_map={"Ingreso": "#20c997", "Gasto": "#ff6b6b"},
                    template="plotly_white" # Fondo limpio
                )
                # Solución error plotly anterior: líneas curvas (spline) y grosor
                fig_line.update_traces(line=dict(shape="spline", width=3))
                fig_line.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#f1f3f5"),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, title_text="")
                )
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Sin datos para trazar tendencia.")
            st.markdown('</div>', unsafe_allow_html=True)

        with row2_col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title">🍕 Distribución del Gasto</div>', unsafe_allow_html=True)
            df_gastos = df_filtrado[df_filtrado['Tipo'] == 'Gasto']
            if not df_gastos.empty:
                # Sunburst jerárquico (Categoría > Subcategoría) - Mucho más premium que pie normal
                fig_sun = px.sunburst(
                    df_gastos, path=['Categoría', 'Subcategoría'], values='Monto',
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_sun.update_traces(textinfo="label+percent parent")
                fig_sun.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_sun, use_container_width=True)
            else:
                st.info("Sin gastos para distribuir.")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Fila 3: Tabla de Control y Exportación
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        col_tabla1, col_tabla2 = st.columns([8, 2])
        with col_tabla1:
            st.markdown('<div class="chart-title">📋 Bóveda de Registros (Auditoría Detallada)</div>', unsafe_allow_html=True)
        with col_tabla2:
            # Botón de exportación compacto
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Exportar CSV", data=csv, file_name=f"finanzas_{inicio}_{fin}.csv", mime="text/csv", use_container_width=True)
        
        columnas_mostrar = [col for col in ['Fecha', 'Tipo', 'Categoría', 'Subcategoría', 'Monto', 'descripcion'] if col in df_filtrado.columns]
        df_vista = df_filtrado[columnas_mostrar].sort_values(by='Fecha', ascending=False)
        df_vista['Fecha'] = df_vista['Fecha'].dt.strftime('%Y-%m-%d')
        
        # Estilizar tabla nativa
        st.dataframe(
            df_vista, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Monto": st.column_config.NumberColumn("Monto", format="$%d"),
                "Tipo": st.column_config.TextColumn("Tipo"),
                "descripcion": st.column_config.TextColumn("Descripción")
            }
        )
        st.markdown('</div>', unsafe_allow_html=True)
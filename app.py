import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN PREMIUM ---
st.set_page_config(page_title="Finanzas Sergio Ruiz", page_icon="💎", layout="wide", initial_sidebar_state="expanded")

# --- CSS SEGURO Y MINIMALISTA ---
# Le da un efecto de elevación suave a los contenedores nativos sin romper la responsividad
st.markdown("""
<style>
    /* Efecto hover suave en los contenedores nativos */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        background-color: #ffffff;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.08);
    }
    /* Centrar y agrandar el valor de la métrica */
    div[data-testid="stMetricValue"] { 
        font-size: 2.2rem; 
        font-weight: 800; 
        color: #1e293b;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 1rem;
        font-weight: 600;
        color: #64748b;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. CAPA DE SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center; color: #1e293b;'>🔐 Acceso Encriptado</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 2rem;'>Sistema de Análisis Financiero Sergio Ruiz</p>", unsafe_allow_html=True)
        password = st.text_input("Credencial de acceso:", type="password", placeholder="Ingresa tu clave maestra...")
        
        if st.button("Desbloquear Terminal", type="primary", use_container_width=True):
            if password == st.secrets["dashboard_password"]:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Acceso denegado. Credencial incorrecta.")
    st.stop()

# --- 2. EXTRACCIÓN DE DATOS ---
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
    if df_trans.empty: return pd.DataFrame()
        
    df_cats = pd.DataFrame(cats)
    df_subcats = pd.DataFrame(subcats)
    
    df_completo = pd.merge(df_trans, df_subcats, left_on="subcategoria_id", right_on="id", how="left", suffixes=("", "_sub"))
    df_completo = pd.merge(df_completo, df_cats, left_on="categoria_id", right_on="id", how="left", suffixes=("", "_cat"))
    
    df_completo['nombre'] = df_completo.get('nombre', 'Sin Subcategoría').fillna('Sin Subcategoría')
    df_completo['nombre_cat'] = df_completo.get('nombre_cat', 'Sin Categoría').fillna('Sin Categoría')
    
    df_completo.rename(columns={"nombre": "Subcategoría", "nombre_cat": "Categoría", "fecha_transaccion": "Fecha", "monto": "Monto"}, inplace=True)
    df_completo['Fecha'] = pd.to_datetime(df_completo['Fecha'])
    return df_completo

df_crudo = cargar_datos()

if df_crudo.empty:
    st.title("💎 Terminal Financiera Sergio Ruiz")
    st.info("Base de datos en blanco. Registra tu primer movimiento en la Web App.")
else:
    # --- 3. BARRA LATERAL (FILTROS Y PRESUPUESTO) ---
    with st.sidebar:
        st.header("⚙️ Parámetros de Análisis")
        
        fecha_min = df_crudo['Fecha'].min().date()
        fecha_max = df_crudo['Fecha'].max().date()
        rango_fechas = st.date_input("Rango de Análisis:", value=(fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max)
        
        categorias_disponibles = sorted(df_crudo['Categoría'].unique())
        categorias_seleccionadas = st.multiselect("Filtrar Categorías:", options=categorias_disponibles, default=categorias_disponibles)
        
        st.markdown("---")
        st.subheader("🎯 Meta de Control")
        presupuesto_max = st.number_input("Presupuesto Máximo de Gastos ($)", min_value=0, value=200000, step=10000)

    # Filtrado del DataFrame
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        inicio, fin = rango_fechas
        df_filtrado = df_crudo[(df_crudo['Fecha'].dt.date >= inicio) & (df_crudo['Fecha'].dt.date <= fin)]
    else:
        df_filtrado = df_crudo.copy()
        
    df_filtrado = df_filtrado[df_filtrado['Categoría'].isin(categorias_seleccionadas)]

    # --- 4. CÁLCULO DE KPIs ---
    ingresos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Ingreso']['Monto'].sum()
    gastos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Gasto']['Monto'].sum()
    balance = ingresos - gastos
    
    # --- 5. CABECERA Y MÉTRICAS ---
    st.title("📊 Análisis de Liquidez Personal")
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True): 
            st.metric("Ingresos Totales", f"${ingresos:,.0f}".replace(",", "."), delta="↑ Entradas", delta_color="normal")
    with col2:
        with st.container(border=True):
            st.metric("Gastos Totales", f"${gastos:,.0f}".replace(",", "."), delta="↓ Salidas", delta_color="inverse")
    with col3:
        with st.container(border=True):
            st.metric("Saldo Neto", f"${balance:,.0f}".replace(",", "."), delta="Superávit" if balance >= 0 else "Déficit", delta_color="normal" if balance >= 0 else "inverse")
    with col4:
        with st.container(border=True):
            pct_presupuesto = (gastos / presupuesto_max * 100) if presupuesto_max > 0 else 0
            st.metric("Uso de Presupuesto", f"{pct_presupuesto:.1f}%", delta=f"Meta: ${presupuesto_max:,.0f}".replace(",", "."), delta_color="off")
            if pct_presupuesto >= 100:
                st.progress(1.0)
            else:
                st.progress(pct_presupuesto / 100)

    st.markdown("##")

    # --- 6. TABS DE VISUALIZACIÓN ---
    tab1, tab2, tab3 = st.tabs(["💧 Flujo de Caja (Cascada)", "👁️ Análisis Profundo", "🗄️ Bóveda Buscador"])

    with tab1:
        st.subheader("📉 Cómo se distribuyó tu dinero")
        df_gastos = df_filtrado[df_filtrado['tipo_movimiento'] == 'Gasto']
        gastos_por_cat = df_gastos.groupby('Categoría')['Monto'].sum().reset_index()
        
        nombres = ["Ingresos Totales"] + gastos_por_cat['Categoría'].tolist() + ["Saldo Final"]
        valores = [ingresos] + [-val for val in gastos_por_cat['Monto'].tolist()] + [balance]
        medidas = ["relative"] + ["relative"] * len(gastos_por_cat) + ["total"]
        
        fig_waterfall = go.Figure(go.Waterfall(
            name="Flujo", orientation="v",
            measure=medidas,
            x=nombres, textposition="outside",
            text=[f"${v:,.0f}".replace(",", ".") for v in valores],
            y=valores,
            decreasing={"marker":{"color":"#ef4444"}}, # Rojo moderno
            increasing={"marker":{"color":"#10b981"}}, # Verde moderno
            totals={"marker":{"color":"#3b82f6"}}      # Azul moderno
        ))
        fig_waterfall.update_layout(
            margin=dict(t=30, b=20, l=10, r=10), 
            waterfallgap=0.3,
            template="plotly_white",
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9")
        )
        st.plotly_chart(fig_waterfall, use_container_width=True)

        if not df_gastos.empty:
            gasto_max = df_gastos.loc[df_gastos['Monto'].idxmax()]
            dia_max = df_gastos.groupby('Fecha')['Monto'].sum().idxmax()
            
            st.success(f"""
            **🤖 Insight Financiero Automático:**
            * Tu mayor fuga individual de dinero fue en **{gasto_max['Subcategoría']}** por **${gasto_max['Monto']:,.0f}**.
            * El día que más gastaste fue el **{dia_max.strftime('%Y-%m-%d')}**.
            """)

    with tab2:
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.subheader("🧬 Ecosistema (Sunburst)")
            if not df_gastos.empty:
                fig_sun = px.sunburst(
                    df_gastos, path=['Categoría', 'Subcategoría'], values='Monto', 
                    color='Categoría', color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_sun.update_traces(textinfo="label+percent parent")
                fig_sun.update_layout(margin=dict(t=20, l=10, r=10, b=10), template="plotly_white")
                st.plotly_chart(fig_sun, use_container_width=True)
            else:
                st.info("Sin salidas registradas.")

        with col_chart2:
            st.subheader("🎯 Top Fugas de Dinero")
            if not df_gastos.empty:
                top_gastos = df_gastos.groupby("Subcategoría")["Monto"].sum().reset_index().sort_values(by="Monto", ascending=True).tail(7)
                fig_bar = px.bar(
                    top_gastos, x='Monto', y='Subcategoría', orientation='h', 
                    text_auto='.2s', color='Monto', color_continuous_scale="Reds"
                )
                fig_bar.update_layout(
                    margin=dict(t=20, l=10, r=10, b=10), showlegend=False, 
                    coloraxis_showscale=False, yaxis_title="", template="plotly_white"
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Sin salidas registradas.")

    with tab3:
        col_search1, col_search2 = st.columns([3, 1])
        with col_search1:
            busqueda = st.text_input("🔍 Buscar por descripción o detalle:", placeholder="Ej: insumos, filamento, herramientas...")
        
        if busqueda:
            df_tabla = df_filtrado[df_filtrado['descripcion'].str.contains(busqueda, case=False, na=False)]
        else:
            df_tabla = df_filtrado.copy()

        with col_search2:
            st.markdown("<br>", unsafe_allow_html=True)
            csv = df_tabla.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Descargar Vista", data=csv, file_name="registros_filtrados.csv", mime="text/csv", use_container_width=True)
            
        columnas_mostrar = [col for col in ['Fecha', 'tipo_movimiento', 'Categoría', 'Subcategoría', 'Monto', 'descripcion'] if col in df_tabla.columns]
        df_vista = df_tabla[columnas_mostrar].sort_values(by='Fecha', ascending=False)
        df_vista['Fecha'] = df_vista['Fecha'].dt.strftime('%Y-%m-%d')
        
        st.dataframe(
            df_vista, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Monto": st.column_config.NumberColumn("Monto", format="$%d"),
                "tipo_movimiento": st.column_config.TextColumn("Tipo"),
                "descripcion": st.column_config.TextColumn("Detalle")
            }
        )
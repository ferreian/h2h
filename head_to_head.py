import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode



st.set_page_config(layout="wide")
st.title("⚔️ Análise Head to Head via Excel")
st.markdown("Carregue um arquivo Excel com as colunas **Local**, **Material**, **Produtividade** (sc/ha).")

uploaded_file = st.file_uploader("📁 Faça upload do arquivo Excel", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    df.rename(columns={
        "Material": "Cultivar",
        "Produtividade": "prod_sc_ha"
    }, inplace=True)

    df["prod_sc_ha"] = pd.to_numeric(df["prod_sc_ha"], errors="coerce")
    df = df[["Local", "Cultivar", "prod_sc_ha"]].dropna()
    df = df[df["prod_sc_ha"] > 0]

    df["Pop_Final"] = None
    df["Umidade (%)"] = None

    st.success("✅ Dados carregados e formatados!")

    if st.button("🔁 Rodar Análise Head to Head"):
        resultados_h2h = []

        for local, grupo in df.groupby("Local"):
            cultivares = grupo["Cultivar"].unique()

            for head in cultivares:
                prod_head = grupo.loc[grupo["Cultivar"] == head, "prod_sc_ha"].values[0]

                for check in cultivares:
                    if head == check:
                        continue
                    prod_check = grupo.loc[grupo["Cultivar"] == check, "prod_sc_ha"].values[0]
                    diff = prod_head - prod_check
                    win = int(diff > 1)
                    draw = int(-1 <= diff <= 1)

                    resultados_h2h.append({
                        "Local": local,
                        "Head": head,
                        "Check": check,
                        "Head_Mean": round(prod_head, 1),
                        "Check_Mean": round(prod_check, 1),
                        "Difference": round(diff, 1),
                        "Number_of_Win": win,
                        "Is_Draw": draw,
                        "Percentage_of_Win": 100.0 if win else 0.0
                    })

        df_resultado = pd.DataFrame(resultados_h2h)
        st.session_state["df_resultado_h2h"] = df_resultado
        st.success("✅ Análise concluída!")

if "df_resultado_h2h" in st.session_state:
    df_resultado = st.session_state["df_resultado_h2h"]

        # 🎯 Filtro por Local
    locais_disponiveis = sorted(df_resultado["Local"].unique())
    local_selecionado = st.multiselect("📍 Filtrar por Local", options=locais_disponiveis, default=locais_disponiveis)

    # Aplica filtro no DataFrame
    df_resultado_filtrado = df_resultado[df_resultado["Local"].isin(local_selecionado)]


    st.markdown("### 🔹 Selecione os cultivares para comparação Head to Head")
    cultivares_unicos = sorted(df_resultado_filtrado["Head"].unique())

    col1, col2, col3 = st.columns([0.3, 0.4, 0.3])

    with col1:
        head_select = st.selectbox("Selecionar Cultivar Head", options=cultivares_unicos, key="head_select")
    with col2:
        st.markdown("<h1 style='text-align: center;'>X</h1>", unsafe_allow_html=True)
    with col3:
        check_select = st.selectbox("Selecionar Cultivar Check", options=cultivares_unicos, key="check_select")

    if head_select and check_select and head_select != check_select:
        df_selecionado = df_resultado_filtrado[
            (df_resultado_filtrado["Head"] == head_select) & (df_resultado_filtrado["Check"] == check_select)
        ]


        st.markdown(f"### 📋 Tabela Head to Head: <b>{head_select} x {check_select}</b>", unsafe_allow_html=True)

        if not df_selecionado.empty:
            df_h2h_fmt = df_selecionado.copy()

            cell_style_js = JsCode("""
            function(params) {
                let value = params.value;
                let min = 0;
                let max = 100;
                let ratio = (value - min) / (max - min);

                let r, g, b;
                if (ratio < 0.5) {
                    r = 253;
                    g = 98 + ratio * 2 * (200 - 98);
                    b = 94 + ratio * 2 * (15 - 94);
                } else {
                    r = 242 - (ratio - 0.5) * 2 * (242 - 1);
                    g = 200 - (ratio - 0.5) * 2 * (200 - 184);
                    b = 15 + (ratio - 0.5) * 2 * (170 - 15);
                }

                return {
                    'backgroundColor': 'rgb(' + r + ',' + g + ',' + b + ')',
                    'color': 'black',
                    'fontWeight': 'bold',
                    'fontSize': '16px'
                }
            }
            """)

            gb = GridOptionsBuilder.from_dataframe(df_h2h_fmt)

            for col in df_h2h_fmt.select_dtypes(include=["float"]).columns:
                if col in ["Head_Mean", "Check_Mean"]:
                    gb.configure_column(col, type=["numericColumn"], valueFormatter="x.toFixed(1)", cellStyle=cell_style_js)
                else:
                    gb.configure_column(col, type=["numericColumn"], valueFormatter="x.toFixed(1)")

            gb.configure_default_column(cellStyle={'fontSize': '14px'})
            gb.configure_grid_options(headerHeight=30)

            custom_css = {
                ".ag-header-cell-label": {
                    "font-weight": "bold",
                    "font-size": "15px",
                    "color": "black"
                }
            }

            AgGrid(
                df_h2h_fmt,
                gridOptions=gb.build(),
                height=500,
                custom_css=custom_css,
                allow_unsafe_jscode=True
            )

            # 📊 Estatísticas
            num_locais = df_selecionado["Local"].nunique()
            vitorias = df_selecionado[df_selecionado["Difference"] > 1].shape[0]
            derrotas = df_selecionado[df_selecionado["Difference"] < -1].shape[0]
            empates = df_selecionado[df_selecionado["Difference"].between(-1, 1)].shape[0]

            max_diff = df_selecionado["Difference"].max() if not df_selecionado.empty else 0
            min_diff = df_selecionado["Difference"].min() if not df_selecionado.empty else 0
            media_diff_vitorias = df_selecionado[df_selecionado["Difference"] > 1]["Difference"].mean() or 0
            media_diff_derrotas = df_selecionado[df_selecionado["Difference"] < -1]["Difference"].mean() or 0

            # 🔹 Cards de Resumo
            col4, col5, col6, col7 = st.columns(4)

            with col4:
                st.markdown(f"""
                    <div style="background-color:#f2f2f2; padding:15px; border-radius:10px; text-align:center;">
                        <h5 style="font-weight:bold; color:#333;">📍 Número de Locais</h5>
                        <div style="font-size: 20px; font-weight:bold; color:#f2f2f2;">&nbsp;</div>
                        <h2 style="margin: 10px 0; color:#333; font-weight:bold; font-size: 4em;">{num_locais}</h2>
                        <div style="font-size: 20px; font-weight:bold; color:#f2f2f2;">&nbsp;</div>
                    </div>
                """, unsafe_allow_html=True)

            with col5:
                st.markdown(f"""
                    <div style="background-color:#01B8AA80; padding:15px; border-radius:10px; text-align:center;">
                        <h5 style="font-weight:bold; color:#004d47;">✅ Vitórias</h5>
                        <div style="font-size: 20px; font-weight:bold; color:#004d47;">Max: {max_diff:.1f} sc/ha</div>
                        <h2 style="margin: 10px 0; color:#004d47; font-weight:bold; font-size: 4em;">{vitorias}</h2>
                        <div style="font-size: 20px; font-weight:bold; color:#004d47;">Média: {media_diff_vitorias:.1f} sc/ha</div>
                    </div>
                """, unsafe_allow_html=True)

            with col6:
                st.markdown(f"""
                    <div style="background-color:#F2C80F80; padding:15px; border-radius:10px; text-align:center;">
                        <h5 style="font-weight:bold; color:#8a7600;">➖ Empates</h5>
                        <div style="font-size: 20px; font-weight:bold; color:#8a7600;">Entre -1 e 1 sc/ha</div>
                        <h2 style="margin: 10px 0; color:#8a7600; font-weight:bold; font-size: 4em;">{empates}</h2>
                        <div style="font-size: 20px; font-weight:bold; color:#F2C80F80;">&nbsp;</div>
                    </div>
                """, unsafe_allow_html=True)

            with col7:
                st.markdown(f"""
                    <div style="background-color:#FD625E80; padding:15px; border-radius:10px; text-align:center;">
                        <h5 style="font-weight:bold; color:#7c1f1c;">❌ Derrotas</h5>
                        <div style="font-size: 20px; font-weight:bold; color:#7c1f1c;">Min: {min_diff:.1f} sc/ha</div>
                        <h2 style="margin: 10px 0; color:#7c1f1c; font-weight:bold; font-size: 4em;">{derrotas}</h2>
                        <div style="font-size: 20px; font-weight:bold; color:#7c1f1c;">Média: {media_diff_derrotas:.1f} sc/ha</div>
                    </div>
                """, unsafe_allow_html=True)

            # 🎯 Gráfico de Pizza
            col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
            with col_p2:
                st.markdown("""
                    <div style="background-color: #f9f9f9; padding: 10px; border-radius: 12px; 
                                box-shadow: 0px 2px 5px rgba(0,0,0,0.1); text-align: center;">
                        <h4 style="margin-bottom: 0.5rem;">Resultado Geral do Head</h4>
                """, unsafe_allow_html=True)

                fig_pizza = go.Figure(data=[go.Pie(
                    labels=["Vitórias", "Empates", "Derrotas"],
                    values=[vitorias, empates, derrotas],
                    marker=dict(colors=["#01B8AA", "#F2C80F", "#FD625E"]),
                    hole=0.6,
                    textinfo='label+percent',
                    textposition='outside',
                    textfont=dict(size=20, color="black", family="Arial Black"),
                )])

                fig_pizza.update_layout(
                    margin=dict(t=10, b=60, l=10, r=10),
                    height=330,
                    showlegend=False
                )

                st.plotly_chart(fig_pizza, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # 📊 Gráfico Diferença por Local
            st.markdown(f"### <b>📊 Diferença de Produtividade por Local - {head_select} X {check_select}</b>", unsafe_allow_html=True)
            st.markdown("### 📌 Dica: para melhor visualização dos rótulos, filtre para um número menor de locais.")

            df_validos = df_selecionado[(df_selecionado["Head_Mean"] > 0) & (df_selecionado["Check_Mean"] > 0)]
            df_validos = df_validos.sort_values("Difference")

            cores_local = df_validos["Difference"].apply(
                lambda x: "#01B8AA" if x > 1 else "#FD625E" if x < -1 else "#F2C80F"
            )

            fig_diff_local = go.Figure()
            fig_diff_local.add_trace(go.Bar(
                y=df_validos["Local"],
                x=df_validos["Difference"],
                orientation='h',
                text=df_validos["Difference"].round(1),
                textposition="outside",
                textfont=dict(size=20, family="Arial Black", color="black"),
                marker_color=cores_local
            ))

            fig_diff_local.update_layout(
                title=dict(text=f"<b>📍 Diferença de Produtividade por Local — {head_select} X {check_select}</b>", font=dict(size=20, family="Arial Black")),
                xaxis=dict(title=dict(text="<b>Diferença (sc/ha)</b>", font=dict(size=20)), tickfont=dict(size=20)),
                yaxis=dict(title=dict(text="<b>Local</b>", font=dict(size=20)), tickfont=dict(size=20)),
                margin=dict(t=40, b=40, l=100, r=40),
                height=600,
                showlegend=False
            )

            st.plotly_chart(fig_diff_local, use_container_width=True)

            # 🔀 Comparação Multichecks
            st.markdown("### 🔹 Comparação Head x Múltiplos Checks")
            st.markdown("""
            <small>
            Essa análise permite comparar um cultivar (Head) com vários outros (Checks) ao mesmo tempo. 
            Ela apresenta o percentual de vitórias, produtividade média e a diferença média de performance 
            em relação aos demais cultivares selecionados.
            </small>
            """, unsafe_allow_html=True)

            head_unico = st.selectbox("Cultivar Head", options=cultivares_unicos, key="multi_head")
            opcoes_checks = [c for c in cultivares_unicos if c != head_unico]
            checks_selecionados = st.multiselect("Cultivares Check", options=opcoes_checks, key="multi_checks")

            if head_unico and checks_selecionados:
                df_multi = df_resultado[
                    (df_resultado["Head"] == head_unico) &
                    (df_resultado["Check"].isin(checks_selecionados))
                ]

                if not df_multi.empty:
                    prod_head_media = df_multi["Head_Mean"].mean().round(1)

                    st.markdown(f"#### 🎯 Cultivar Head: **{head_unico}** | Produtividade Média: **{prod_head_media} sc/ha**")

                    resumo = df_multi.groupby("Check").agg({
                        "Number_of_Win": "sum",
                        "Is_Draw": "sum",
                        "Check_Mean": "mean",
                        "Head_Mean": "mean"  # 👈 Adicionado aqui
                    }).reset_index()

                    resumo.rename(columns={
                        "Check": "Cultivar Check",
                        "Number_of_Win": "Vitórias",
                        "Is_Draw": "Empates",
                        "Check_Mean": "Prod_sc_ha_media",
                        "Head_Mean": "Head_sc_ha_media"  # 👈 Renomeado corretamente
                    }, inplace=True)


                    resumo["Num_Locais"] = df_multi.groupby("Check").size().values
                    resumo["% Vitórias"] = (resumo["Vitórias"] / resumo["Num_Locais"] * 100).round(1)
                    resumo["Prod_sc_ha_media"] = resumo["Prod_sc_ha_media"].round(1)
                    resumo["Head_sc_ha_media"] = resumo["Head_sc_ha_media"].round(1)

                    # ✅ Aqui está a diferença real de produtividade entre Head e Check
                    resumo["Diferença Média"] = (resumo["Head_sc_ha_media"] - resumo["Prod_sc_ha_media"]).round(1)

                    # Define colunas que vão para a tabela
                    resumo = resumo[[
                        "Cultivar Check",
                        "Num_Locais",
                        "Prod_sc_ha_media",
                        "Head_sc_ha_media",
                        "Diferença Média",
                        "% Vitórias"
                    ]]


                    col_tabela, col_grafico = st.columns([1.4, 1.6])
                    with col_tabela:
                        st.markdown("### 📊 Tabela Comparativa")
                        gb = GridOptionsBuilder.from_dataframe(resumo)
                        gb.configure_default_column(cellStyle={'fontSize': '14px'})
                        gb.configure_grid_options(headerHeight=30)
                        custom_css = {".ag-header-cell-label": {"font-weight": "bold", "font-size": "15px", "color": "black"}}
                        AgGrid(resumo, gridOptions=gb.build(), height=400, custom_css=custom_css)

                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                            resumo.to_excel(writer, sheet_name="comparacao_multi_check", index=False)

                        st.download_button(
                            label="📅 Baixar Comparação (Excel)",
                            data=buffer.getvalue(),
                            file_name=f"comparacao_{head_unico}_vs_checks.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    with col_grafico:
                        fig_diff = go.Figure()
                        cores_personalizadas = resumo["Diferença Média"].apply(
                            lambda x: "#01B8AA" if x > 1 else "#FD625E" if x < -1 else "#F2C80F"
                        )

                        fig_diff.add_trace(go.Bar(
                            y=resumo["Cultivar Check"],
                            x=resumo["Diferença Média"],
                            orientation='h',
                            text=resumo["Diferença Média"].round(1),
                            textposition="outside",
                            textfont=dict(size=16, family="Arial Black", color="black"),
                            marker_color=cores_personalizadas
                        ))

                        fig_diff.update_layout(
                            title=dict(text="📊 Diferença Média de Produtividade", font=dict(size=20, family="Arial Black")),
                            xaxis=dict(title=dict(text="Diferença Média (sc/ha)", font=dict(size=16)), tickfont=dict(size=14)),
                            yaxis=dict(title=dict(text="Check"), tickfont=dict(size=14)),
                            margin=dict(t=30, b=40, l=60, r=30),
                            height=400,
                            showlegend=False
                        )

                        st.plotly_chart(fig_diff, use_container_width=True)
                else:
                    st.info("❓ Nenhuma comparação disponível com os Checks selecionados.")



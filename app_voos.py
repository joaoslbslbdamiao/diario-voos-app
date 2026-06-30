import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Diário de Voos e Operações", page_icon="✈️", layout="wide")
st.title("✈️ Voos & 📏 Inspeções")

# --- LIGAÇÃO AO GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. Ler dados dos Voos (Aba Página1)
colunas_ordem = ["Data", "Início", "Fim", "Horas", "Minutos", "Motivo", "Piloto", "Colega", "Conta_Premio", "Troca"]
try:
    df = conn.read(worksheet="Página1", ttl=0)
    df = df.dropna(how="all")
    for col in colunas_ordem:
        if col not in df.columns:
            if col == "Conta_Premio": df[col] = "Sim"
            elif col == "Troca": df[col] = "Não"
            else: df[col] = "-"
except Exception:
    df = pd.DataFrame(columns=colunas_ordem)

# 2. Ler dados dos KMs Inspecionados (Aba KMs)
colunas_kms = ["Data", "KMs"]
try:
    df_kms = conn.read(worksheet="KMs", ttl=0)
    df_kms = df_kms.dropna(how="all")
    for col in colunas_kms:
        if col not in df_kms.columns:
            df_kms[col] = 0.0
except Exception:
    df_kms = pd.DataFrame(columns=colunas_kms)

# 3. Ler dados das Colheitas (Aba Colheitas - NOVA)
colunas_colheitas = ["Data", "Colheita", "Início", "Fim"]
try:
    df_col = conn.read(worksheet="Colheitas", ttl=0)
    df_col = df_col.dropna(how="all")
    for col in colunas_colheitas:
        if col not in df_col.columns:
            df_col[col] = "-"
except Exception:
    df_col = pd.DataFrame(columns=colunas_colheitas)

# 4. Ler Configurações
try:
    df_config = conn.read(worksheet="Config", ttl=0)
    p1_mem = float(df_config["Premio1"].iloc[0])
    p2_mem = float(df_config["Premio2"].iloc[0])
    p3_mem = float(df_config["Premio3"].iloc[0])
    data_lim_mem = datetime.date.fromisoformat(str(df_config["DataLimite"].iloc[0]))
    meses_pagos_str = str(df_config["Meses_Pagos"].iloc[0]) if "Meses_Pagos" in df_config.columns else ""
except:
    p1_mem, p2_mem, p3_mem = 21.02, 42.04, 63.06
    data_lim_mem = datetime.date(2024, 1, 1)
    meses_pagos_str = ""

lista_pagos = [m.strip() for m in meses_pagos_str.split(",") if m.strip()]

def ler_hora_escrita(texto):
    t = str(texto).strip().lower().replace(".", ":").replace("h", ":")
    if t.isdigit():
        if len(t) == 4: t = f"{t[:2]}:{t[2:]}"
        elif len(t) == 3: t = f"0{t[:1]}:{t[1:]}"
        elif len(t) == 2: t = f"00:{t}"
        elif len(t) == 1: t = f"00:0{t}"
    try: return datetime.datetime.strptime(t, "%H:%M").time()
    except: return None

# --- MENU LATERAL (CONFIGURAÇÃO) ---
st.sidebar.header("⚙️ Configuração")
with st.sidebar.form("form_premios"):
    st.write("### Prémios de Voo")
    premio1_val = st.number_input("Prémio 1", value=p1_mem, step=0.50)
    premio2_val = st.number_input("Prémio 2", value=p2_mem, step=0.50)
    premio3_val = st.number_input("Prémio 3", value=p3_mem, step=0.50)
    st.write("---")
    data_limite = st.date_input("Ativos desde:", value=data_lim_mem)
    if st.form_submit_button("Gravar Configuração", use_container_width=True):
        nova_cfg = pd.DataFrame([{
            "Premio1": premio1_val, "Premio2": premio2_val, "Premio3": premio3_val, 
            "DataLimite": data_limite.isoformat(), "Meses_Pagos": meses_pagos_str
        }])
        conn.update(worksheet="Config", data=nova_cfg)
        st.success("✅ Configuração Guardada!")
        st.rerun()

# --- SEPARADORES (TABS) - AGORA SÃO 4 ---
tab_voos, tab_kms, tab_colheitas, tab_apagar = st.tabs([
    "✈️ Voos e Prémios", 
    "📏 KMs Inspecionados", 
    "⏱️ Tempos Colheita",
    "🗑️ Apagar Registos"
])

# ==========================================
# ABA 1: VOOS E PRÉMIOS
# ==========================================
with tab_voos:
    if "voo_pendente" in st.session_state:
        st.warning("⚠️ **Atenção:** Voo com duração de 00h 00m.")
        st.write("Este registo conta para prémio (Prémio 1)?")
        col_sim, col_nao = st.columns(2)
        if col_sim.button("✅ Sim, conta para Prémio", use_container_width=True):
            st.session_state.voo_pendente["Conta_Premio"] = "Sim"
            df = pd.concat([df, pd.DataFrame([st.session_state.voo_pendente])], ignore_index=True)[colunas_ordem]
            conn.update(worksheet="Página1", data=df)
            del st.session_state["voo_pendente"]
            st.rerun()
        if col_nao.button("❌ Não, apenas registo", use_container_width=True):
            st.session_state.voo_pendente["Conta_Premio"] = "Não"
            df = pd.concat([df, pd.DataFrame([st.session_state.voo_pendente])], ignore_index=True)[colunas_ordem]
            conn.update(worksheet="Página1", data=df)
            del st.session_state["voo_pendente"]
            st.rerun()
    else:
        with st.expander("➕ Registar Novo Voo"):
            with st.form("form_registo", clear_on_submit=True):
                data_voo = st.date_input("Data do Voo", value=datetime.date.today())
                c1, c2 = st.columns(2)
                str_inicio = c1.text_input("Início (ex: 830)")
                str_fim = c2.text_input("Fim (ex: 1700)")
                c3, c4 = st.columns(2)
                piloto = c3.text_input("👨‍✈️ Piloto")
                colega = c4.text_input("👥 Colega")
                motivo = st.text_input("📍 Motivo")
                troca = st.checkbox("🔄 É uma Troca de serviço?")
                
                if st.form_submit_button("Guardar no Diário💾", use_container_width=True):
                    hora_inicio = ler_hora_escrita(str_inicio)
                    hora_fim = ler_hora_escrita(str_fim)
                    if not hora_inicio or not hora_fim or not motivo.strip():
                        st.error("⚠️ Verifica as horas e o motivo!")
                    else:
                        dt_i = datetime.datetime.combine(data_voo, hora_inicio)
                        dt_f = datetime.datetime.combine(data_voo, hora_fim)
                        if dt_f < dt_i: dt_f += datetime.timedelta(days=1)
                        total_m = int((dt_f - dt_i).total_seconds() / 60)
                        
                        dados_voo = {
                            "Data": data_voo.strftime("%d/%m/%Y"), "Início": hora_inicio.strftime("%H:%M"), "Fim": hora_fim.strftime("%H:%M"),
                            "Horas": total_m // 60, "Minutos": total_m % 60, "Motivo": motivo.strip(),
                            "Piloto": piloto.strip() or "-", "Colega": colega.strip() or "-",
                            "Conta_Premio": "Sim", "Troca": "Sim" if troca else "Não"
                        }
                        if total_m == 0:
                            st.session_state["voo_pendente"] = dados_voo
                            st.rerun()
                        else:
                            df = pd.concat([df, pd.DataFrame([dados_voo])], ignore_index=True)[colunas_ordem]
                            conn.update(worksheet="Página1", data=df)
                            st.success(f"✅ Guardado!")
                            st.rerun()

    if not df.empty:
        st.divider()
        df["DT"] = pd.to_datetime(df["Data"], format="%d/%m/%Y")
        df["Mes_Ano"] = df["DT"].dt.strftime("%m/%Y")
        mes_sel = st.selectbox("Filtrar Mês (Voos):", ["Todos"] + sorted(list(df["Mes_Ano"].unique()), reverse=True))
        df_f = df[df["Mes_Ano"] == mes_sel].copy() if mes_sel != "Todos" else df.copy()
        
        df_f["Horas"] = pd.to_numeric(df_f["Horas"], errors='coerce').fillna(0).astype(int)
        df_f["Minutos"] = pd.to_numeric(df_f["Minutos"], errors='coerce').fillna(0).astype(int)
        df_f["Mins"] = (df_f["Horas"] * 60) + df_f["Minutos"]
        df_f["Mins_Premio"] = df_f.apply(lambda r: r["Mins"] if str(r["Conta_Premio"]).strip().lower() != "não" else 0, axis=1)
        df_f["Voo_Valido"] = df_f.apply(lambda r: 1 if str(r["Conta_Premio"]).strip().lower() != "não" else 0, axis=1)
        
        df_dia = df_f.groupby("Data").agg({"Mins": "sum", "Mins_Premio": "sum", "Voo_Valido": "sum"}).reset_index()
        df_dia["DT"] = pd.to_datetime(df_dia["Data"], format="%d/%m/%Y")

        def calcular_premio_diario(row):
            if row["Voo_Valido"] == 0: return 0.0
            m = row["Mins_Premio"]
            p = (p1_mem, p2_mem, p3_mem) if row["DT"].date() >= data_lim_mem else (21.02, 42.04, 63.06)
            if m < 215: return p[0]   
            elif m < 285: return p[1] 
            else: return p[2]         

        df_dia["Valor"] = df_dia.apply(calcular_premio_diario, axis=1)
        total_eur = df_dia["Valor"].sum()
        total_hrs = int(df_f["Mins"].sum())
        pago = mes_sel in lista_pagos
        t_mes_formatado = f"{total_hrs//60:02d}h {total_hrs%60:02d}m"
        
        st.success(f"### 💰 {':green[' if pago else ''}Total Prémios: {total_eur:.2f} € | ⏱️ {t_mes_formatado}{' - PAGO ✅]' if pago else ''}")

        st.write("---")
        for _, r in df_dia.sort_values("DT", ascending=False).iterrows():
            v_dia = df_f[df_f["Data"] == r["Data"]].fillna("-")
            p_t = v_dia["Piloto"].iloc[0]; c_t = v_dia["Colega"].iloc[0]
            t_d = f"{int(r['Mins']//60):02d}h {int(r['Mins']%60):02d}m"
            e_troca = "Sim" in v_dia["Troca"].values
            tag_pago = " :green[[PAGO ✅]]" if r["DT"].strftime("%m/%Y") in lista_pagos else ""
            
            if e_troca: 
                titulo_final = f":orange-background[➕ {r['Data']} | ⏱️ {t_d} | 💰 {r['Valor']}€ | 👨‍✈️ {p_t} | 👥 {c_t} [TROCA 🔄]]{tag_pago}"
            else: 
                titulo_final = f"➕ {r['Data']} | ⏱️ {t_d} | 💰 {r['Valor']}€ | 👨‍✈️ {p_t} | 👥 {c_t}{tag_pago}"
            
            with st.expander(titulo_final):
                v_dia["Duração"] = v_dia.apply(lambda r: f"{int(r['Horas']):02d}:{int(r['Minutos']):02d}", axis=1)
                st.dataframe(v_dia[["Início", "Fim", "Duração", "Piloto", "Colega", "Motivo", "Conta_Premio", "Troca"]].reset_index(drop=True), use_container_width=True)

# ==========================================
# ABA 2: KMs INSPECIONADOS
# ==========================================
with tab_kms:
    with st.expander("➕ Registar Inspeção"):
        with st.form("form_kms", clear_on_submit=True):
            data_km = st.date_input("Data da Inspeção", value=datetime.date.today(), key="data_k")
            dist_km = st.number_input("📏 Total KMs Inspecionados", min_value=0.0, step=0.1, format="%.1f")
            
            if st.form_submit_button("Guardar Inspeção", use_container_width=True):
                if dist_km <= 0:
                    st.error("⚠️ Insere um valor de KMs superior a 0!")
                else:
                    novo_km = pd.DataFrame([{
                        "Data": data_km.strftime("%d/%m/%Y"),
                        "KMs": dist_km
                    }])
                    df_kms = pd.concat([df_kms, novo_km], ignore_index=True)[colunas_kms]
                    conn.update(worksheet="KMs", data=df_kms)
                    st.success("✅ Inspeção guardada no registo!")
                    st.rerun()

    if not df_kms.empty:
        st.divider()
        df_kms["DT"] = pd.to_datetime(df_kms["Data"], format="%d/%m/%Y")
        df_kms["Mes_Ano"] = df_kms["DT"].dt.strftime("%m/%Y")
        
        st.subheader("📅 Histórico Mensal")
        meses_kms = ["Todos"] + sorted(list(df_kms["Mes_Ano"].unique()), reverse=True)
        mes_sel_km = st.selectbox("Filtrar Mês:", meses_kms, key="mes_filter_km")
        
        df_k_filt = df_kms[df_kms["Mes_Ano"] == mes_sel_km].copy() if mes_sel_km != "Todos" else df_kms.copy()
        df_k_filt["KMs"] = pd.to_numeric(df_k_filt["KMs"], errors='coerce').fillna(0)
        
        df_k_agrupado = df_k_filt.groupby("Data").agg({"KMs": "sum"}).reset_index()
        df_k_agrupado["DT"] = pd.to_datetime(df_k_agrupado["Data"], format="%d/%m/%Y")
        df_k_agrupado = df_k_agrupado.sort_values("DT", ascending=False).reset_index(drop=True)
        
        st.info(f"### 📏 Total Inspecionado: {df_k_filt['KMs'].sum():.1f} KMs")
        st.dataframe(df_k_agrupado[["Data", "KMs"]], use_container_width=True, hide_index=True)

# ==========================================
# ABA 3: TEMPOS PARA POWERAPP
# ==========================================
with tab_colheitas:
    with st.expander("➕ Registar Tempo de Colheita"):
        with st.form("form_colheita", clear_on_submit=True):
            data_col = st.date_input("Data", value=datetime.date.today(), key="data_col")
            
            c1, c2, c3 = st.columns(3)
            num_colheita = c1.text_input("🏷️ Nº Colheita")
            inicio_col = c2.text_input("Início (ex: 830)", key="ini_col")
            fim_col = c3.text_input("Fim (ex: 1045)", key="fim_col")
            
            if st.form_submit_button("Guardar Registo", use_container_width=True):
                h_i = ler_hora_escrita(inicio_col)
                h_f = ler_hora_escrita(fim_col)
                
                if not h_i or not h_f or not num_colheita.strip():
                    st.error("⚠️ Verifica as horas e o Nº da Colheita!")
                else:
                    novo_registo = pd.DataFrame([{
                        "Data": data_col.strftime("%d/%m/%Y"),
                        "Colheita": num_colheita.strip(),
                        "Início": h_i.strftime("%H:%M"),
                        "Fim": h_f.strftime("%H:%M")
                    }])
                    df_col = pd.concat([df_col, novo_registo], ignore_index=True)[colunas_colheitas]
                    conn.update(worksheet="Colheitas", data=df_col)
                    st.success("✅ Tempo gravado com sucesso!")
                    st.rerun()

    if not df_col.empty:
        st.divider()
        st.subheader("📋 Últimos Registos")
        
        # Inverte a tabela para os últimos ficarem em cima
        st.dataframe(
            df_col.iloc[::-1].reset_index(drop=True), 
            use_container_width=True
        )

# ==========================================
# ABA 4: APAGAR REGISTOS (NOVA)
# ==========================================
with tab_apagar:
    st.subheader("🗑️ Apagar Registos")
    st.write("Enganaste-te a registar algo? Usa esta área para apagar registos. **Atenção:** A eliminação é definitiva.")
    
    # 1. Escolher a categoria
    tipo_apagar = st.selectbox("1️⃣ O que pretendes apagar?", ["Voos e Prémios", "KMs Inspecionados", "Tempos Colheita"])
    
    if tipo_apagar == "Voos e Prémios":
        df_target = df.copy()
        ws_name = "Página1"
    elif tipo_apagar == "KMs Inspecionados":
        df_target = df_kms.copy()
        ws_name = "KMs"
    else:
        df_target = df_col.copy()
        ws_name = "Colheitas"
        
    if df_target.empty:
        st.info(f"Não tens registos guardados em {tipo_apagar}.")
    else:
        # Inverter para que os registos mais recentes (os últimos inseridos) apareçam primeiro na lista
        df_target_rev = df_target.iloc[::-1]
        
        opcoes = []
        indices_originais = []
        
        # 2. Criar a lista de opções fácil de ler
        for i, row in df_target_rev.iterrows():
            indices_originais.append(i) # Guardar a linha real onde está no Excel
            if tipo_apagar == "Voos e Prémios":
                texto = f"Data: {row['Data']} | {row['Início']}-{row['Fim']} | Piloto: {row.get('Piloto', '-')} | Motivo: {row.get('Motivo', '-')}"
            elif tipo_apagar == "KMs Inspecionados":
                texto = f"Data: {row['Data']} | {row['KMs']} KMs"
            else:
                texto = f"Data: {row['Data']} | Colheita: {row.get('Colheita', '-')} | {row['Início']}-{row['Fim']}"
            opcoes.append(texto)
            
        mapa_opcoes = dict(zip(opcoes, indices_originais))
        
        # 3. Selecionar
        st.write("---")
        registo_sel = st.selectbox("2️⃣ Seleciona o registo que queres apagar:", opcoes)
        idx_apagar = mapa_opcoes[registo_sel]
        
        # 4. Confirmar e Apagar
        st.warning(f"Vais apagar permanentemente:\n**{registo_sel}**")
        certeza = st.checkbox("⚠️ Tenho a certeza absoluta que quero apagar este registo")
        
        if st.button("🗑️ Confirmar e Apagar Registo", type="primary", use_container_width=True):
            if certeza:
                # Remove a linha usando o índice original do DataFrame
                df_target = df_target.drop(idx_apagar).reset_index(drop=True)
                
                # Envia o DataFrame atualizado de volta para o Google Sheets
                conn.update(worksheet=ws_name, data=df_target)
                
                st.success("✅ Registo apagado com sucesso!")
                st.rerun()
            else:
                st.error("⚠️ Tens de marcar a caixa de confirmação antes de clicar no botão.")

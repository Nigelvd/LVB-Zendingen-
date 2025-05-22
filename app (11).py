import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="LVB Advies Tool", layout="wide")

st.title("📦 LVB Tool met Hermeting Controle")

tab1, tab2, tab3 = st.tabs(["📦 LVB Advies", "📏 Hermeting Controle", "📊 GAP Analyse"])

with tab1:
    wachtwoord = st.text_input("Voer wachtwoord in om verder te gaan:", type="password")
    if wachtwoord != "bhg2k25":
        st.stop()

    buffer_percentage = st.slider("Instelbare buffer (% van verkopen):", min_value=10, max_value=100, value=30, step=5)

    bol_file = st.file_uploader("📤 Upload Bol-export (.xlsx)", type=["xlsx"])
    fulfilment_file = st.file_uploader("🏬 Upload Fulfilment-export (.xlsx)", type=["xlsx"])
    vorige_zending_file = st.file_uploader("📂 Upload vorige zending (.xlsx) – optioneel", type=["xlsx"])
    filter_oude_producten = st.checkbox("🧹 Filter producten die al aangemeld zijn", value=True)

    df_uitgefilterd = pd.DataFrame()

    if bol_file and fulfilment_file:
        df_bol = pd.read_excel(bol_file)
        df_fulfilment = pd.read_excel(fulfilment_file)

        df_bol["EAN"] = df_bol["EAN"].astype(str)
        df_fulfilment["EAN"] = df_fulfilment["EAN"].astype(str)
        df_bol["Verkopen (Totaal)"] = pd.to_numeric(df_bol["Verkopen (Totaal)"], errors="coerce").fillna(0).astype(int)
        df_bol["Vrije voorraad"] = pd.to_numeric(df_bol["Vrije voorraad"], errors="coerce").fillna(0)
        df_bol["Verzendtype"] = df_bol.iloc[:, 4].astype(str)

        if vorige_zending_file and filter_oude_producten:
            try:
                df_vorige = pd.read_excel(vorige_zending_file)
                df_vorige["EAN"] = df_vorige["EAN"].astype(str)
                oude_eans = set(df_vorige["EAN"])
                df_uitgefilterd = df_bol[df_bol["EAN"].isin(oude_eans)].copy()
                df_bol = df_bol[~df_bol["EAN"].isin(oude_eans)]
                st.info(f"🔍 {len(df_uitgefilterd)} producten uit vorige zending gefilterd.")

                if not df_uitgefilterd.empty:
                    with st.expander("📋 Bekijk gefilterde producten", expanded=True):
                        st.dataframe(df_uitgefilterd, use_container_width=True)

                        buffer_filter = io.BytesIO()
                        df_uitgefilterd.to_excel(buffer_filter, index=False, engine='openpyxl')
                        st.download_button("📥 Download gefilterde producten als Excel", data=buffer_filter.getvalue(), file_name="Uitgefilterde_Producten.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                        csv_filter = df_uitgefilterd.to_csv(index=False).encode('utf-8')
                        st.download_button("📄 Download gefilterde producten als CSV", data=csv_filter, file_name="Uitgefilterde_Producten.csv", mime="text/csv")
            except Exception as e:
                st.warning(f"⚠️ Bestand vorige zending kon niet verwerkt worden: {e}")

        def match_fulfilment(ean, voorraad_df):
            for _, row in voorraad_df.iterrows():
                ean_list = str(row["EAN"]).split(",")
                if ean in [e.strip() for e in ean_list]:
                    return row["Vrije voorraad"], row.get("Verwachte voorraad", 0)
            return 0, 0

        resultaten = []
        for _, row in df_bol.iterrows():
            ean = row["EAN"]
            titel = row.get("Titel", "")
            bol_voorraad = row["Vrije voorraad"]
            verkopen = row["Verkopen (Totaal)"]
            verzendtype = row["Verzendtype"]

            fulfilment_vrij, fulfilment_verwacht = match_fulfilment(ean, df_fulfilment)
            if fulfilment_vrij <= 0 and fulfilment_verwacht <= 0:
                continue

            buffer_grens = verkopen * (buffer_percentage / 100)
            verschil = bol_voorraad - verkopen

            if verschil >= buffer_grens:
                benchmark = "Voldoende"
            elif 0 < verschil < buffer_grens:
                benchmark = "Twijfel"
            else:
                benchmark = "Onvoldoende"

            advies = ""
            aanbevolen = 0
            tekort = max(0, verkopen - bol_voorraad)

            if verzendtype.strip().upper() != "LVB" or benchmark != "Voldoende":
                if benchmark == "Twijfel":
                    if fulfilment_vrij > 0:
                        advies = "Voorraad krap – versturen aanbevolen"
                        aanbevolen = min(fulfilment_vrij, round(tekort * 1.3))
                    elif fulfilment_verwacht > 0:
                        advies = "Nog niet versturen – voorraad verwacht"
                        aanbevolen = 0
                    else:
                        continue
                elif benchmark == "Onvoldoende":
                    if fulfilment_vrij > 0:
                        advies = f"Verstuur minimaal {tekort} stuks"
                        aanbevolen = min(fulfilment_vrij, round(tekort * 1.3))
                    elif fulfilment_verwacht > 0:
                        advies = "Nog niet versturen – voorraad verwacht"
                        aanbevolen = 0
                    else:
                        continue
                elif benchmark == "Voldoende":
                    if verzendtype.strip().upper() != "LVB":
                        if fulfilment_vrij > 0:
                            advies = "Niet op LVB – voorraad beschikbaar – overweeg naar LVB te sturen"
                            aanbevolen = min(fulfilment_vrij, round(verkopen * 1.3))
                        elif fulfilment_verwacht > 0:
                            advies = "Nog niet versturen – voorraad verwacht (niet LVB)"
                            aanbevolen = 0
                        else:
                            continue
                    else:
                        continue

                resultaten.append({
                    "EAN": ean,
                    "Titel": titel,
                    "Benchmarkscore": benchmark,
                    "Verzendtype": verzendtype,
                    "Bol voorraad": bol_voorraad,
                    "Verkopen (Totaal)": verkopen,
                    "Fulfilment vrije voorraad": fulfilment_vrij,
                    "Fulfilment verwachte voorraad": fulfilment_verwacht,
                    "Advies": advies,
                    "Aanbevolen aantal mee te sturen (x1.3 buffer)": aanbevolen
                })

        if resultaten:
            df_resultaat = pd.DataFrame(resultaten)

            benchmark_order = {"Onvoldoende": 0, "Twijfel": 1, "Voldoende": 2}
            df_resultaat["Benchmarkscore_sort"] = df_resultaat["Benchmarkscore"].map(benchmark_order)
            df_resultaat.sort_values(by=["Benchmarkscore_sort", "Verzendtype"], inplace=True)
            df_resultaat.drop(columns=["Benchmarkscore_sort"], inplace=True)

            def kleur_op_benchmark(row):
                if row["Benchmarkscore"] == "Onvoldoende":
                    return ["background-color: #ff3333; color: white"] * len(row)
                elif row["Benchmarkscore"] == "Twijfel":
                    return ["background-color: #ffaa00; color: black"] * len(row)
                elif row["Benchmarkscore"] == "Voldoende":
                    return ["background-color: #33cc33; color: white"] * len(row)
                else:
                    return [""] * len(row)

            st.success("✅ Adviesoverzicht gegenereerd!")
            st.dataframe(df_resultaat.style.apply(kleur_op_benchmark, axis=1), use_container_width=True)

            buffer = io.BytesIO()
            df_resultaat.to_excel(buffer, index=False, engine='openpyxl')
            st.download_button("📥 Download als Excel", data=buffer.getvalue(), file_name="LVB_Advies_Overzicht.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            csv = df_resultaat.to_csv(index=False).encode('utf-8')
            st.download_button("📄 Download als CSV", data=csv, file_name="LVB_Advies_Overzicht.csv", mime="text/csv")
        else:
            st.info("✅ Geen nieuwe producten waarvoor advies nodig is.")

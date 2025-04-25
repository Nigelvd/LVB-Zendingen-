import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="LVB Advies Tool", layout="wide")  # ✅ MOET HIERBOVENSTAAN
st.warning("✅ [DEBUG] Gecombineerde versie met tabs is succesvol geladen.")  # ✔️ Debug erna

st.title("📦 LVB Tool met Hermeting Controle")

# Tabs: Advies + Hermeting
tab1, tab2 = st.tabs(["📦 LVB Advies", "📏 Hermeting Controle"])

with tab1:
    wachtwoord = st.text_input("Voer wachtwoord in om verder te gaan:", type="password")
    if wachtwoord != "bhg2k25":
        st.stop()

    buffer_percentage = st.slider("Instelbare buffer (% van verkopen):", min_value=10, max_value=100, value=30, step=5)

    bol_file = st.file_uploader("📤 Upload Bol-export (.xlsx)", type=["xlsx"])
    fulfilment_file = st.file_uploader("🏬 Upload Fulfilment-export (.xlsx)", type=["xlsx"])

    if bol_file and fulfilment_file:
        df_bol = pd.read_excel(bol_file)
        df_fulfilment = pd.read_excel(fulfilment_file)

        df_bol["EAN"] = df_bol["EAN"].astype(str)
        df_fulfilment["EAN"] = df_fulfilment["EAN"].astype(str)
        df_bol["Verkopen (Totaal)"] = pd.to_numeric(df_bol["Verkopen (Totaal)"], errors="coerce").fillna(0).astype(int)
        df_bol["Vrije voorraad"] = pd.to_numeric(df_bol["Vrije voorraad"], errors="coerce").fillna(0)
        df_bol["Verzendtype"] = df_bol.iloc[:, 4].astype(str)

        def match_fulfilment(ean, voorraad_df):
            for _, row in voorraad_df.iterrows():
                ean_list = str(row["EAN"]).split(",")
                if ean in [e.strip() for e in ean_list]:
                    return row["Vrije voorraad"], row["Verwachte voorraad"]
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

with tab2:
    st.subheader("📏 Hermeting Controle")

    col1, col2 = st.columns(2)
    with col1:
        hermeting_bestand = st.file_uploader("Upload je hermeting sheet (EAN, Naam, Gewenst formaat)", type=["xlsx"], key="hermeting")
    with col2:
        bol_verzendingen = st.file_uploader("Upload Bol verzendexport (EAN, Order, Verzonden formaat)", type=["xlsx"], key="verzending")

    if hermeting_bestand and bol_verzendingen:
        df_hermeting = pd.read_excel(hermeting_bestand)
        df_verzonden = pd.read_excel(bol_verzendingen)

        df_hermeting.iloc[:, 0] = df_hermeting.iloc[:, 0].astype(str)
        df_verzonden.iloc[:, 2] = df_verzonden.iloc[:, 2].astype(str)

        df_hermeting.rename(columns={'Gewenst formaat klasse van verpakking': 'Gewenst formaat'}, inplace=True)
        df_verzonden.columns.values[2] = 'EAN'
        df_verzonden.columns.values[5] = 'Ordernummer'
        df_verzonden.columns.values[7] = 'Verzonden formaat'

        df_vergelijk = pd.merge(df_verzonden, df_hermeting, on='EAN', how='left')
        df_afwijkend = df_vergelijk[df_vergelijk['Verzonden formaat'].str.lower() != df_vergelijk['Gewenst formaat'].str.lower()]

        if not df_afwijkend.empty:
            df_afwijkend['Afwijking'] = "✅ Ja"
            st.success(f"🔎 {len(df_afwijkend)} afwijkende formaten gevonden")
            st.dataframe(df_afwijkend[['EAN', 'Productnaam', 'Ordernummer', 'Gewenst formaat', 'Verzonden formaat', 'Afwijking']], use_container_width=True)

            buffer = io.BytesIO()
            df_afwijkend.to_excel(buffer, index=False, engine='openpyxl')
            st.download_button("📥 Download afwijkingen als Excel", data=buffer.getvalue(), file_name="hermeting_afwijkingen.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            csv = df_afwijkend.to_csv(index=False).encode('utf-8')
            st.download_button("📄 Download als CSV", data=csv, file_name="hermeting_afwijkingen.csv", mime="text/csv")

        else:
            st.info("✅ Geen afwijkingen gevonden. Alles komt overeen met je verwachte formaten.")

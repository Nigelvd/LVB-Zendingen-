
import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="LVB Advies Tool", layout="centered")
st.title("🔐 LVB Advies Tool met Verzendtypefilter")
st.markdown("Upload je Bol-export en fulfilment-export. Producten met verzendtype ≠ LVB worden altijd meegenomen.")

# Wachtwoordcontrole
wachtwoord = st.text_input("Voer wachtwoord in om verder te gaan:", type="password")
if wachtwoord != "bhg2k25":
    st.stop()

# Uploadsectie
bol_file = st.file_uploader("📦 Upload Bol-export (.xlsx)", type=["xlsx"])
fulfilment_file = st.file_uploader("🏬 Upload Fulfilment-export (.xlsx)", type=["xlsx"])

if bol_file and fulfilment_file:
    df_bol = pd.read_excel(bol_file)
    df_fulfilment = pd.read_excel(fulfilment_file)

    df_bol["EAN"] = df_bol["EAN"].astype(str)
    df_fulfilment["EAN"] = df_fulfilment["EAN"].astype(str)

    df_bol["Verkopen (Totaal)"] = pd.to_numeric(df_bol["Verkopen (Totaal)"], errors="coerce").fillna(0)
    df_bol["Vrije voorraad"] = pd.to_numeric(df_bol["Vrije voorraad"], errors="coerce").fillna(0)
    df_bol["Verzendtype"] = df_bol.iloc[:, 4].astype(str)  # Kolom E (5e kolom)

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

        verschil = bol_voorraad - verkopen
        if verschil >= 20:
            benchmark = "Voldoende"
        elif 0 < verschil < 20:
            benchmark = "Twijfel"
        else:
            benchmark = "Onvoldoende"

        advies = ""
        aanbevolen = 0

        if verzendtype.strip().upper() != "LVB":
            benchmark = "Niet LVB – verplicht opnemen"
            advies = "Wordt niet via LVB verzonden – altijd meenemen"
            tekort = max(1, verkopen - bol_voorraad)
            aanbevolen = min(fulfilment_vrij, round(tekort * 1.3)) if fulfilment_vrij > 0 else 0
        else:
            if benchmark == "Voldoende":
                continue
            elif benchmark == "Twijfel":
                if fulfilment_vrij > 0:
                    advies = "Wel versturen – twijfel, voorraad beschikbaar"
                elif fulfilment_verwacht > 0:
                    advies = "Nog niet versturen – voorraad verwacht"
                else:
                    continue
                tekort = max(0, verkopen - bol_voorraad)
                aanbevolen = min(fulfilment_vrij, round(tekort * 1.3)) if fulfilment_vrij > 0 else 0
            elif benchmark == "Onvoldoende":
                if fulfilment_vrij > 0:
                    advies = "Wel versturen – onvoldoende op Bol, voorraad beschikbaar"
                elif fulfilment_verwacht > 0:
                    advies = "Nog niet versturen – voorraad verwacht"
                else:
                    continue
                tekort = max(0, verkopen - bol_voorraad)
                aanbevolen = min(fulfilment_vrij, round(tekort * 1.3)) if fulfilment_vrij > 0 else 0

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
    st.success("✅ Adviesoverzicht gegenereerd!")
    st.dataframe(df_resultaat, use_container_width=True)

    buffer = io.BytesIO()
    df_resultaat.to_excel(buffer, index=False, engine='openpyxl')
    st.download_button("📥 Download als Excel", data=buffer.getvalue(), file_name="LVB_Advies_Overzicht.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    csv = df_resultaat.to_csv(index=False).encode('utf-8')
    st.download_button("📄 Download als CSV", data=csv, file_name="LVB_Advies_Overzicht.csv", mime="text/csv")

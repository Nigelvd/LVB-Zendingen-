
import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="LVB Advies Tool", layout="centered")
st.title("📦 Hermeting Controle")

col1, col2 = st.columns(2)
with col1:
    hermeting_bestand = st.file_uploader("Upload je hermeting sheet (EAN, Naam, Gewenst formaat)", type=["xlsx"], key="hermeting")
with col2:
    bol_verzendingen = st.file_uploader("Upload Bol verzendexport (EAN, Order, Verzonden formaat)", type=["xlsx"], key="verzending")

if hermeting_bestand and bol_verzendingen:
    df_hermeting = pd.read_excel(hermeting_bestand)
    df_verzonden = pd.read_excel(bol_verzendingen)

    # Zorg dat EANs strings zijn
    df_hermeting.iloc[:, 0] = df_hermeting.iloc[:, 0].astype(str)
    df_verzonden.iloc[:, 2] = df_verzonden.iloc[:, 2].astype(str)

    # Benoem kolommen voor duidelijkheid
    df_hermeting.columns = ['EAN', 'Productnaam', 'Gewenst formaat']
    df_verzonden.columns.values[2] = 'EAN'
    df_verzonden.columns.values[5] = 'Ordernummer'
    df_verzonden.columns.values[7] = 'Verzonden formaat'

    # Merge op EAN
    df_vergelijk = pd.merge(df_verzonden, df_hermeting, on='EAN', how='left')

    # Alleen afwijkende formaten tonen
    df_afwijkend = df_vergelijk[df_vergelijk['Verzonden formaat'].str.lower() != df_vergelijk['Gewenst formaat'].str.lower()]

    if not df_afwijkend.empty:
        df_afwijkend['Afwijking'] = "✅ Ja"
        st.success(f"🔎 {len(df_afwijkend)} afwijkende formaten gevonden")
        st.dataframe(df_afwijkend[['EAN', 'Productnaam', 'Ordernummer', 'Gewenst formaat', 'Verzonden formaat', 'Afwijking']], use_container_width=True)

        # Download als Excel
        buffer = io.BytesIO()
        df_afwijkend.to_excel(buffer, index=False, engine='openpyxl')
        st.download_button("📥 Download afwijkingen als Excel", data=buffer.getvalue(), file_name="hermeting_afwijkingen.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Download als CSV
        csv = df_afwijkend.to_csv(index=False).encode('utf-8')
        st.download_button("📄 Download als CSV", data=csv, file_name="hermeting_afwijkingen.csv", mime="text/csv")

    else:
        st.info("✅ Geen afwijkingen gevonden. Alles komt overeen met je verwachte formaten.")

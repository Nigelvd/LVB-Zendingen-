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

    bol_file = st.file_uploader("📤 Upload huidige Bol-export (.xlsx)", type=["xlsx"])
    vorige_file = st.file_uploader("📂 Upload vorige zending (.xlsx)", type=["xlsx"])
    filter_aan = st.checkbox("🧹 Filter producten die al aangemeld zijn", value=True)

    if bol_file:
        df_bol = pd.read_excel(bol_file)
        df_bol["EAN"] = df_bol["EAN"].astype(str)

        df_uitgefilterd = pd.DataFrame()

        if vorige_file and filter_aan:
            df_vorige = pd.read_excel(vorige_file)
            df_vorige["EAN"] = df_vorige["EAN"].astype(str)

            oude_eans = set(df_vorige["EAN"])
            df_uitgefilterd = df_bol[df_bol["EAN"].isin(oude_eans)].copy()
            df_bol = df_bol[~df_bol["EAN"].isin(oude_eans)]

            st.info(f"🔍 {len(df_uitgefilterd)} producten uit vorige zending gefilterd.")

            if not df_uitgefilterd.empty:
                st.subheader("📋 Uitgefilterde EAN's")
                st.dataframe(df_uitgefilterd[['EAN']], use_container_width=True)

                buffer = io.BytesIO()
                df_uitgefilterd[['EAN']].to_excel(buffer, index=False, engine='openpyxl')
                st.download_button("📥 Download EAN's als Excel", data=buffer.getvalue(), file_name="uitgefilterde_eans.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                csv = df_uitgefilterd[['EAN']].to_csv(index=False).encode('utf-8')
                st.download_button("📄 Download EAN's als CSV", data=csv, file_name="uitgefilterde_eans.csv", mime="text/csv")

with tab2:
    st.subheader("📏 Hermeting Controle")

    col1, col2 = st.columns(2)
    with col1:
        hermeting_bestand = st.file_uploader("Upload je hermeting sheet (EAN, Naam, Gewenst formaat)", type=["xlsx"], key="hermeting")
    with col2:
        bol_verzendingen = st.file_uploader("Upload Bol verzendexport (EAN, Verzonden formaat)", type=["xlsx"], key="verzending")

    if hermeting_bestand and bol_verzendingen:
        df_hermeting_raw = pd.read_excel(hermeting_bestand, dtype=str)
        df_hermeting = df_hermeting_raw.iloc[:, [0, 1, 2]].copy()
        df_hermeting.columns = ['EAN', 'Productnaam', 'Gewenst formaat']
        df_hermeting['EAN'] = df_hermeting['EAN'].astype(str)

        df_verzonden_raw = pd.read_excel(bol_verzendingen, header=None, dtype=str)
        df_verzonden = pd.DataFrame()
        df_verzonden['EAN'] = df_verzonden_raw.iloc[:, 2]
        df_verzonden['Verzonden formaat'] = df_verzonden_raw.iloc[:, 7]
        df_verzonden.dropna(subset=['EAN', 'Verzonden formaat'], inplace=True)
        df_verzonden['EAN'] = df_verzonden['EAN'].astype(str)

        df_vergelijk = pd.merge(df_verzonden, df_hermeting, on='EAN', how='left')
        df_vergelijk.dropna(subset=['Gewenst formaat', 'Verzonden formaat'], inplace=True)

        df_afwijkend = df_vergelijk[
            df_vergelijk['Verzonden formaat'].str.lower() != df_vergelijk['Gewenst formaat'].str.lower()
        ].drop_duplicates(subset=['EAN'])

        if not df_afwijkend.empty:
            df_afwijkend['Afwijking'] = "✅ Ja"
            st.success(f"🔎 {len(df_afwijkend)} afwijkende formaten gevonden")
            st.dataframe(df_afwijkend[['EAN', 'Productnaam', 'Gewenst formaat', 'Verzonden formaat', 'Afwijking']], use_container_width=True)

            buffer = io.BytesIO()
            df_afwijkend.to_excel(buffer, index=False, engine='openpyxl')
            st.download_button("📥 Download afwijkingen als Excel", data=buffer.getvalue(), file_name="hermeting_afwijkingen.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            csv = df_afwijkend.to_csv(index=False).encode('utf-8')
            st.download_button("📄 Download als CSV", data=csv, file_name="hermeting_afwijkingen.csv", mime="text/csv")
        else:
            st.info("✅ Geen afwijkingen gevonden. Alles komt overeen met je verwachte formaten.")

with tab3:
    st.header("📊 GAP Analyse Tool")
    st.markdown("Voer hieronder de links in van je eigen Bol.com listing en drie concurrenten om een vergelijking te maken.")

    eigen_link = st.text_input("🔗 Link naar jouw product")
    concurrent_links = [st.text_input(f"🔗 Link naar concurrent {i}") for i in range(1, 4)]

    if st.button("📈 Vergelijk Listings"):
        if not eigen_link or any(not link for link in concurrent_links):
            st.warning("Vul alle links in voordat je vergelijkt.")
        else:
            st.success("Links succesvol ontvangen! (De vergelijking volgt in de volgende versie.)")
            st.write("Jouw productlink:", eigen_link)
            for idx, link in enumerate(concurrent_links, start=1):
                st.write(f"Concurrent {idx}:", link)

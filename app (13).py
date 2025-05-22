import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="EAN Filter Tool", layout="centered")
st.title("📦 Uitgefilterde EAN's uit vorige zending")

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

import streamlit as st
import pandas as pd
import altair as alt
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets Authorization
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets.connections)
client = gspread.authorize(creds)

# Konfigurasi halaman agar memenuhi seluruh lebar (full width)
st.set_page_config(page_title="Dashboard Lab Fisika", layout="wide")

# Function to load data from Google Sheets
@st.cache_data(ttl=60)
def load_data(sheet_name):
    sheet = client.open("Keuangan Lab Fisika").worksheet(sheet_name)
    df = sheet.get_all_records()
    df = pd.DataFrame(df)
    return df

# Muat data
df = load_data("Sheet1")
df["Tanggal"] = pd.to_datetime(df["Tanggal"], format="%d/%m/%Y", dayfirst=True)
df.sort_values(by="Tanggal", inplace=True)

st.title("Dashboard Keuangan Lab Fisika UNJ")

# --- Filter tanggal di atas halaman ---
st.markdown("#### Pilih Rentang Tanggal")
col_filter = st.columns(2)
min_date = df["Tanggal"].min().date()
max_date = df["Tanggal"].max().date()
start_date = col_filter[0].date_input("Tanggal Awal", min_date, min_value=min_date, max_value=max_date)
end_date = col_filter[1].date_input("Tanggal Akhir", max_date, min_value=min_date, max_value=max_date)

if start_date > end_date:
    st.error("Tanggal akhir harus lebih besar atau sama dengan tanggal mulai.")
    st.stop()

# Filter data sesuai rentang tanggal
mask = (df["Tanggal"].dt.date >= start_date) & (df["Tanggal"].dt.date <= end_date)
df_filtered = df.loc[mask].copy()

# --- Styling untuk Tab Menu (CSS) ---
st.markdown("""
    <style>
        .stTabs>div>div>button {
            border: 2px solid #ccc;
            padding: 10px 20px;
            margin: 0 10px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 5px;
            cursor: pointer;
            transition: 0.3s;
        }
        .stTabs>div>div>button:hover {
            background-color: #f1f1f1;
            border-color: #bbb;
        }
        .stTabs>div>div>button:focus {
            outline: none;
            background-color: #ddd;
        }
        .tab-title {
            font-weight: bold;
            font-size: 18px;
        }
    </style>
""", unsafe_allow_html=True)

# Buat tab menu: Dashboard, Dataframe Rinci, dan Tambah Data
tabs = st.tabs(["Dashboard", "Tabel Rincian", "Tambah Data", "Dana Tertahan"])

with tabs[0]:
    # --- Hitung Metrics ---
    total_pemasukan = df_filtered.loc[df_filtered["Kategori"] == "Pemasukan", "Jumlah"].sum()
    total_pengeluaran = df_filtered.loc[df_filtered["Kategori"] == "Pengeluaran", "Jumlah"].sum()
    saldo_terakhir = df_filtered["Saldo"].iloc[-1] if not df_filtered.empty else 0

    # Buat rentang tanggal lengkap berdasarkan filter
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')

    # --- Grafik Pemasukan Harian ---
    daily_income = (
        df_filtered[df_filtered["Kategori"] == "Pemasukan"]
        .groupby(df_filtered["Tanggal"].dt.date)["Jumlah"]
        .sum()
        .reindex(all_dates.date, fill_value=0)
        .reset_index()
        .rename(columns={"index": "Tanggal", "Jumlah": "Pemasukan"})
    )
    daily_income["Tanggal"] = pd.to_datetime(daily_income["Tanggal"])

    # --- Grafik Pengeluaran Harian ---
    daily_expense = (
        df_filtered[df_filtered["Kategori"] == "Pengeluaran"]
        .groupby(df_filtered["Tanggal"].dt.date)["Jumlah"]
        .sum()
        .reindex(all_dates.date, fill_value=0)
        .reset_index()
        .rename(columns={"index": "Tanggal", "Jumlah": "Pengeluaran"})
    )
    daily_expense["Tanggal"] = pd.to_datetime(daily_expense["Tanggal"])

    # --- Grafik Batang Pengeluaran Berdasarkan Tipe ---
    df_pengeluaran = df_filtered[df_filtered["Kategori"] == "Pengeluaran"]
    expense_by_type = df_pengeluaran.groupby("Tipe")["Jumlah"].sum().reset_index() if not df_pengeluaran.empty else pd.DataFrame({"Tipe": [], "Jumlah": []})

    # --- Layout 2 x 2 ---
    # Baris pertama: kolom pertama berisi metrics (vertikal) dan kolom kedua berisi grafik batang pengeluaran berdasarkan tipe.
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Kondisi Keuangan")
        st.metric("Saldo Saat Ini", f"Rp {saldo_terakhir:,.0f}")
        st.metric("Pemasukan (sesuai rentang waktu)", f"Rp {total_pemasukan:,.0f}")
        st.metric("Pengeluaran (sesuai rentang waktu)", f"Rp {total_pengeluaran:,.0f}")

    with col2:
        st.markdown("#### Pengeluaran Berdasarkan Tipe")
        if not expense_by_type.empty:
            bar_chart = alt.Chart(expense_by_type).mark_bar().encode(
                x=alt.X("Tipe:N", sort="-y", title="Tipe"),
                y=alt.Y("Jumlah:Q", title="Total Pengeluaran (Rp)"),
                tooltip=["Tipe", "Jumlah"]
            ).properties(width="container", height=300)
            st.altair_chart(bar_chart, use_container_width=True)
        else:
            st.write("Tidak ada data pengeluaran pada rentang tanggal ini.")

    # Baris kedua: kolom pertama berisi grafik pemasukan harian dan kolom kedua berisi grafik pengeluaran harian.
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("#### Grafik Pemasukan Harian")
        if daily_income["Pemasukan"].sum() > 0:
            income_chart = alt.Chart(daily_income).mark_line(point=True).encode(
                x=alt.X("Tanggal:T", title="Tanggal"),
                y=alt.Y("Pemasukan:Q", title="Jumlah (Rp)"),
                tooltip=["Tanggal", "Pemasukan"]
            ).properties(width="container", height=300)
            st.altair_chart(income_chart, use_container_width=True)
        else:
            st.write("Tidak ada data pemasukan pada rentang tanggal ini.")
    
    with col4:
        st.markdown("#### Grafik Pengeluaran Harian")
        if daily_expense["Pengeluaran"].sum() > 0:
            expense_chart = alt.Chart(daily_expense).mark_line(point=True).encode(
                x=alt.X("Tanggal:T", title="Tanggal"),
                y=alt.Y("Pengeluaran:Q", title="Jumlah (Rp)"),
                tooltip=["Tanggal", "Pengeluaran"]
            ).properties(width="container", height=300)
            st.altair_chart(expense_chart, use_container_width=True)
        else:
            st.write("Tidak ada data pengeluaran pada rentang tanggal ini.")

with tabs[1]:
    st.markdown("### Dataframe Rinci")
    st.dataframe(df_filtered, use_container_width=True)

# --- Tab untuk Menambah Data ---
with tabs[2]:
    st.markdown("### Tambah Data Keuangan")

    # Form untuk input data
    with st.form(key="data_form"):
        tanggal = st.date_input("Tanggal")
        str_tanggal = tanggal.strftime("%d/%m/%Y")
        kategori = st.selectbox("Kategori", ["Pemasukan", "Pengeluaran"])
        tipe = st.selectbox("Tipe", ["Internal", "Bahan Persediaan", "Dana Taktis", "OB", "Konsumsi", "Honor", "Lainnya"])
        jumlah = st.number_input("Jumlah (Rp)", min_value=0)
        jumlah = float(jumlah)
        deskripsi = st.text_area("Deskripsi")


        # Tombol submit
        submit_button = st.form_submit_button("Tambah Data")

        if submit_button:
            saldo = df["Saldo"].iloc[-1] + jumlah if kategori == "Pemasukan" else df["Saldo"].iloc[-1] - jumlah
            sheet = client.open("Keuangan Lab Fisika").worksheet("Sheet1")
            new_row = [str_tanggal, deskripsi, kategori, tipe, jumlah, saldo]
            sheet.append_row(new_row)
            
            st.success("Data berhasil ditambahkan!")

with tabs[3]:
    st.markdown("### Dana Tertahan")
    df_tahan = load_data("Sheet2")
    st.dataframe(df_tahan, use_container_width=True)
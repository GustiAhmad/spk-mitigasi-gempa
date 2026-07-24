import pandas as pd

def periksa_katalog_sensor():
    print("==================================================")
    print("🔍 INSPEKSI BERKAS KATALOG_SENSOR.TSV")
    print("==================================================")
    
    try:
        # Membaca file katalog_sensor.tsv menggunakan pandas
        df_sensor = pd.read_csv('katalog_sensor.tsv', sep='\t', low_memory=False)
        
        # 1. Menampilkan nama-nama kolom yang tersedia
        print(f"✔️ Kolom yang tersedia ({len(df_sensor.columns)} kolom):")
        print(list(df_sensor.columns))
        
        print("\n" + "-"*50)
        
        # 2. Menampilkan informasi tipe data dan jumlah data non-null
        print("📊 Informasi Dataset:")
        print(df_sensor.info())
        
        print("\n" + "-"*50)
        
        # 3. Menampilkan 5 baris sampel data teratas
        print("👉 Sampel 5 Baris Data Awal:")
        print(df_sensor.head().to_string())
        
    except FileNotFoundError:
        print("❌ File 'katalog_sensor.tsv' tidak ditemukan di folder ini.")
        print("Pastikan nama filenya sudah benar dan berada di direktori yang sama dengan skrip ini.")
    except Exception as e:
        print(f"❌ Terjadi kesalahan saat membaca file: {e}")

if __name__ == '__main__':
    periksa_katalog_sensor()
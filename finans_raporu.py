import smtplib
import yfinance as yf
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
import re # Regular Expression modülünü ekledik

# --- AYARLAR ---
GMAIL_KULLANICI_ADI = "furkanbalkac@gmail.com"
GMAIL_UYGULAMA_SIFRESI = "jfjbmpmqusmdxehj"
ALICI_EMAILLERI = ["furkanbalkac@gmail.com"]
TICKERS = {
    "Altın (Ons/USD)": "GC=F",
    "Nasdaq 100 ETF (QQQ)": "QQQ",
    "S&P 500 ETF (IVV)": "IVV",
    "Dolar/TL": "USDTRY=X",
    "Bitcoin (BTC/USD)": "BTC-USD",
    "Ethereum (ETH/USD)": "ETH-USD",
    "Solana (SOL/USD)": "SOL-USD",
    "BIST 30 Endeksi": "XU030.IS"
}
SABLON_DOSYASI = "sablon.html"

# --- FONKSİYONLAR ---

def veri_cek():
    """Finansal verileri, günlük değişimleri ve para birimini dinamik olarak çeker."""
    print("Finansal veriler çekiliyor...")
    cekilen_veriler = {}
    for isim, ticker in TICKERS.items():
        try:
            data = yf.Ticker(ticker)
            gunluk_veri = data.history(period="7d", auto_adjust=True)
            if not gunluk_veri.empty and len(gunluk_veri) >= 2:
                son_fiyat = gunluk_veri['Close'].iloc[-1]
                onceki_fiyat = gunluk_veri['Close'].iloc[-2]
                degisim = son_fiyat - onceki_fiyat
                yuzde_degisim = (degisim / onceki_fiyat) * 100
                yon = 'up' if degisim > 0 else 'down' if degisim < 0 else 'flat'
                birim = data.info.get('currency', '')
                cekilen_veriler[isim] = {
                    'fiyat': f"{son_fiyat:,.2f}", 
                    'degisim': f"{degisim:+.2f}", 
                    'yuzde_degisim': f"{yuzde_degisim:+.2f}%", 
                    'yon': yon,
                    'birim': birim
                }
            elif not gunluk_veri.empty:
                son_fiyat = gunluk_veri['Close'].iloc[-1]
                birim = data.info.get('currency', '')
                cekilen_veriler[isim] = {
                    'fiyat': f"{son_fiyat:,.2f}", 
                    'yon': 'flat', 
                    'degisim': 'N/A', 
                    'yuzde_degisim': '',
                    'birim': birim
                }
            else:
                 cekilen_veriler[isim] = None
        except Exception as e:
            cekilen_veriler[isim] = None
            print(f"Hata: '{isim}' ({ticker}) verisi çekilirken bir sorun oluştu: {e}")
    print("✓ Veri çekme işlemi tamamlandı.")
    return {k: v for k, v in cekilen_veriler.items() if v is not None}

def email_html_olustur(veriler):
    """HTML şablonunu okur, satır şablonunu kullanarak verileri işler ve nihai HTML'i oluşturur."""
    print("HTML e-posta içeriği oluşturuluyor...")
    try:
        with open(SABLON_DOSYASI, 'r', encoding='utf-8') as f:
            sablon_icerigi = f.read()
    except FileNotFoundError:
        print(f"HATA: '{SABLON_DOSYASI}' bulunamadı! Lütfen dosyanın doğru yerde olduğundan emin olun.")
        return None

    # 1. Satır şablonunu HTML'den çıkar
    match = re.search(r'<!-- SATIR_SABLONU_BASLANGIC -->(.*?)<!-- SATIR_SABLONU_BITIS -->', sablon_icerigi, re.DOTALL)
    if not match:
        print(f"HATA: '{SABLON_DOSYASI}' içinde satır şablonu bulunamadı. Lütfen <!-- SATIR_SABLONU_BASLANGIC --> yorumlarını kontrol edin.")
        return None
    row_template = match.group(1).strip()

    # 2. Verileri kullanarak satırları oluştur
    data_rows = ""
    for isim, veri in veriler.items():
        renk = '#475569'
        if veri['yon'] == 'up': renk = '#16a34a'
        if veri['yon'] == 'down': renk = '#dc2626'
        ikon = '&#9650;' if veri['yon'] == 'up' else '&#9660;' if veri['yon'] == 'down' else ''
        birim = veri.get('birim', '')
        
        # Satır şablonunu doldur
        new_row = row_template
        new_row = new_row.replace('{{ISIM}}', isim)
        new_row = new_row.replace('{{FIYAT}}', veri['fiyat'])
        new_row = new_row.replace('{{BIRIM}}', birim)
        new_row = new_row.replace('{{RENK}}', renk)
        new_row = new_row.replace('{{IKON}}', ikon)
        new_row = new_row.replace('{{DEGISIM}}', veri['degisim'])
        new_row = new_row.replace('{{YUZDE_DEGISIM}}', veri['yuzde_degisim'])
        
        data_rows += new_row

    # 3. Ana şablondaki dummy verileri gerçek verilerle değiştir
    final_html = re.sub(
        r'<!-- VERI_SATIRLARI_BASLANGIC -->(.|\n)*?<!-- VERI_SATIRLARI_BITIS -->',
        data_rows,
        sablon_icerigi
    )

    # 4. Ana şablondaki tarih yer tutucusunu değiştir
    final_html = final_html.replace('{{TARIH}}', date.today().strftime('%d %B %Y'))
    
    # 5. Şablon bloğunu nihai HTML'den temizle
    final_html = re.sub(
        r'<!-- SABLON_ALANI_BASLANGIC -->(.|\n)*?<!-- SABLON_ALANI_BITIS -->',
        '',
        final_html
    )

    print("✓ HTML içeriği oluşturuldu.")
    return final_html

def email_gonder(html_icerik):
    """Hazırlanan HTML içeriğini e-posta olarak gönderir."""
    if not html_icerik:
        print("HTML içerik boş, gönderme işlemi iptal edildi.")
        return

    print("E-posta gönderme işlemi başlatılıyor...")
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Günlük Finans Piyasası Raporu - {date.today().strftime('%d.%m.%Y')}"
        msg['From'] = GMAIL_KULLANICI_ADI
        msg['To'] = ", ".join(ALICI_EMAILLERI)
        part2 = MIMEText(html_icerik, 'html', 'utf-8')
        msg.attach(part2)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_KULLANICI_ADI, GMAIL_UYGULAMA_SIFRESI)
            server.sendmail(GMAIL_KULLANICI_ADI, ALICI_EMAILLERI, msg.as_string())
        print(f"✓ E-posta başarıyla gönderildi: {', '.join(ALICI_EMAILLERI)}")
    except Exception as e:
        print(f"✗ E-posta gönderilirken bir hata oluştu: {e}")

# --- ANA ÇALIŞMA BLOKU ---
if __name__ == '__main__':
    print("--- Günlük Rapor Servisi Başlatıldı ---")
    finansal_veriler = veri_cek()
    if finansal_veriler:
        html_icerik = email_html_olustur(veriler=finansal_veriler)
        email_gonder(html_icerik)
    else:
        print("✗ Gönderilecek veri bulunamadı. İşlem durduruluyor.")
    print("--- Rapor Servisi İşlemini Tamamladı ---")

import os
import re
from datetime import date
import yfinance as yf
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# --- AYARLAR ---
# Bu değerler artık GitHub Actions ortam değişkenlerinden ve Secrets'tan okunuyor
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
GONDERICI_EMAIL = os.environ.get('GMAIL_KULLANICI_ADI') # Bu, SendGrid'de doğruladığınız adres olmalı
ALICI_EMAILLERI = ["furkanbalkac@gmail.com"] # Raporu alacak e-posta adresleri
TICKERS = {
    "Altın Vadeli (Ons/USD)": "GC=F",
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
    """HTML şablonunu okur ve verilerle doldurur."""
    print("HTML e-posta içeriği oluşturuluyor...")
    try:
        with open(SABLON_DOSYASI, 'r', encoding='utf-8') as f:
            sablon_icerigi = f.read()
    except FileNotFoundError:
        print(f"HATA: '{SABLON_DOSYASI}' bulunamadı!")
        return None

    match = re.search(r'(.*?)', sablon_icerigi, re.DOTALL)
    if not match:
        print(f"HATA: '{SABLON_DOSYASI}' içinde satır şablonu bulunamadı.")
        return None
    row_template = match.group(1).strip()

    data_rows = ""
    for isim, veri in veriler.items():
        renk = '#475569'
        if veri['yon'] == 'up': renk = '#16a34a'
        if veri['yon'] == 'down': renk = '#dc2626'
        ikon = '&#9650;' if veri['yon'] == 'up' else '&#9660;' if veri['yon'] == 'down' else ''
        birim = veri.get('birim', '')
        
        new_row = row_template.replace('{{ISIM}}', isim).replace('{{FIYAT}}', veri['fiyat']).replace('{{BIRIM}}', birim).replace('{{RENK}}', renk).replace('{{IKON}}', ikon).replace('{{DEGISIM}}', veri['degisim']).replace('{{YUZDE_DEGISIM}}', veri['yuzde_degisim'])
        data_rows += new_row

    final_html = re.sub(r'(.|\n)*?', data_rows, sablon_icerigi)
    final_html = final_html.replace('{{TARIH}}', date.today().strftime('%d %B %Y'))
    final_html = re.sub(r'(.|\n)*?', '', final_html)
    
    print("✓ HTML içeriği oluşturuldu.")
    return final_html

def email_gonder(html_icerik):
    """Hazırlanan HTML içeriğini SendGrid kullanarak e-posta olarak gönderir."""
    if not html_icerik:
        print("HTML içerik boş, gönderme işlemi iptal edildi.")
        return
    if not SENDGRID_API_KEY or not GONDERICI_EMAIL:
        print("HATA: SENDGRID_API_KEY veya GONDERICI_EMAIL ortam değişkenleri ayarlanmamış.")
        return

    print("E-posta gönderme işlemi SendGrid ile başlatılıyor...")
    message = Mail(
        from_email=GONDERICI_EMAIL,
        to_emails=ALICI_EMAILLERI,
        subject=f"Günlük Finans Piyasası Raporu - {date.today().strftime('%d.%m.%Y')}",
        html_content=html_icerik
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"✓ E-posta başarıyla gönderildi! Durum Kodu: {response.status_code}")
    except Exception as e:
        print(f"✗ SendGrid ile e-posta gönderilirken bir hata oluştu: {e}")

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

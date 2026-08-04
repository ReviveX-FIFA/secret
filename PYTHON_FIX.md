# Discord Botu Kurulum Talimatları
## Python 3.13 Uyumluluk Sorunu
Mevcut Python sürümünüzün (3.13) Discord kütüphaneleriyle uyumluluk sorunları var. İşte iki çözüm:
## Çözüm 1: Python 3.11 Yükleyin (Önerilen)
 1. **Python 3.11'i İndirin**: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
 2. **Python 3.11'i Kurun** (Python 3.13 kurulu kalsın)
 3. **Botu Python 3.11 ile çalıştırın**:
   ```bash
   py -3.11 discord_bot.py
   
   ```
## Çözüm 2: Sanal Ortam (Virtual Environment) Kullanın
 1. **Python 3.11 ile sanal ortam oluşturun**:
   ```bash
   py -3.11 -m venv discord_bot_env
   
   ```
 2. **Ortamı aktifleştirin**:
   ```bash
   discord_bot_env\Scripts\activate
   
   ```
 3. **Gereksinimleri yükleyin**:
   ```bash
   pip install -r requirements.txt
   
   ```
 4. **Botu çalıştırın**:
   ```bash
   python discord_bot.py
   
   ```
## Hızlı Çözüm
Python 3.11'i otomatik olarak indirmek için oluşturduğum install_python311.bat dosyasını çalıştırın.
## Bu Neden Oluyor?
Python 3.13 çok yeni ve Discord kütüphaneleri bunu destekleyecek şekilde henüz güncellenmedi. Python 3.11, Discord geliştirmeleri için en kararlı (stable) sürümdür.
## Python 3.11'i Kurduktan Sonra
Botunuz şunlarla sorunsuz çalışacaktır:
 * ✅ Tüm slash komutları
 * ✅ Rol izinleri
 * ✅ Bekleme süreleri (Cooldowns)
 * ✅ Sunucu/kanal kısıtlamaları
 * ✅ Tüm Twitch bot entegrasyonları

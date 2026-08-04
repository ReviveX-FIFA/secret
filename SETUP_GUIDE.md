# Discord Botu Kurulum Talimatları
## Hızlı Başlangıç (En Kolay Yöntem)
### Adım 1: Python 3.11'i Yükleyin
Python 3.11'i otomatik olarak indirip kurmak için install_python311_auto.bat dosyasına **çift tıklayın**
### Adım 2: Botu Çalıştırın
Discord botunu başlatmak için run_bot.bat dosyasına **çift tıklayın**
## Manuel Kurulum
Eğer otomatik yükleyici çalışmazsa:
 1. **Python 3.11'i İndirin**: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
 2. **Python 3.11'i Kurun** ("Add Python to PATH" seçeneğini işaretlediğinizden emin olun)
 3. **Botu çalıştırın**: Komut istemini (CMD) açın ve şunu yazın:
   ```
   py -3.11 discord_bot.py
   
   ```
## Komut Dosyaları (Scriptler) Ne İşe Yarıyor
 * install_python311_auto.bat: Python 3.11 yükleyicisini indirir ve çalıştırır
 * run_bot.bat: Python 3.11'i kontrol eder ve botu başlatır
 * PYTHON_FIX.md: Detaylı sorun giderme rehberi
## Kurulumdan Sonra
Botunuz şunlarla çalışacaktır:
 * ✅ Tüm slash komutları (/tfollow, /traid, /tview, /tlike, /tchat)
 * ✅ Rol izinleri (Op access, twitch free, Exclusive)
 * ✅ Bekleme süreleri (5dk, 8dk, 2dk)
 * ✅ Sunucu/kanal kısıtlamaları
 * ✅ Zaten ayarlanmış olan Discord token'ınız
## Sorun Giderme
Eğer "Python 3.11 not found" (Python 3.11 bulunamadı) hatası alırsanız:
 1. Yükleyiciyi kullanarak Python 3.11'i kurduğunuzdan emin olun
 2. Kurulumdan sonra bilgisayarınızı yeniden başlatın
 3. Mevcut Python sürümlerini görmek için py --list komutunu çalıştırmayı deneyin

# Discord Twitch Bot
Twitch otomasyon işlevleri için slash komutları sağlayan bir Discord botu.
## Setup (Kurulum)
 1. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt

```
 2. Discord bot token'ınızı discord_token.txt dosyasına ekleyin VEYA DISCORD_BOT_TOKEN ortam değişkenini (environment variable) ayarlayın.
 3. (İsteğe bağlı) role_permissions.py dosyasından rol izinlerini ayarlayın.
 4. Botu çalıştırın:
```bash
python discord_bot.py

```
## Commands (Komutlar)
### Owner Commands (Sahip Komutları - User IDs: 1389712262532431882, 1361768357044682994)
Sahip olarak, tüm komutlara sınırsız erişiminiz vardır:
 * /tfollow username:amount - Bir Twitch kanalını takip eder
 * /traid raid_id:amount - Bir Twitch raid'ine katılır
 * /tview username:amount - Bir yayına izleyici ekler
 * /tlike vod_url:amount - VOD'ları/klipleri beğenir
 * /tchat username:message:amount - Chat'e spam mesaj gönderir
 * /tbot_status - Botun durumunu kontrol eder
### Role-Based Commands (Role Dayalı Komutlar)
role_permissions.py dosyasını düzenleyerek Discord rollerine izinler atayabilirsiniz:
```python
ROLE_PERMISSIONS = {
    "Op access": {
        "tfollow": 250, "traid": 0, "tview": 10, 
        "tlike": 10, "tchat": 50, "cooldown": 5
    },
    "twitch free": {
        "tfollow": 100, "traid": 0, "tview": 0, 
        "tlike": 10, "tchat": 5, "cooldown": 8
    },
    "Exclusive": {
        "tfollow": 1500, "traid": 50, "tview": 200, 
        "tlike": 50, "tchat": 5000, "cooldown": 2
    },
}

```
## Role Permissions (Rol İzinleri)
### Op access (Role ID: 1484781614893629480)
 * **Follow**: Maksimum 250
 * **View**: Maksimum 10
 * **Like**: Maksimum 10
 * **Chat**: Maksimum 50
 * **Raid**: Erişim yok
 * **Cooldown (Bekleme süresi)**: 5 dakika
### twitch free (Role ID: 1486157280482299904)
 * **Follow**: Maksimum 100
 * **Like**: Maksimum 10
 * **Chat**: Maksimum 5
 * **View**: Erişim yok
 * **Raid**: Erişim yok
 * **Cooldown**: 8 dakika
### Exclusive (Role ID: 1486159828673106000)
 * **Follow**: Maksimum 1500
 * **Raid**: Maksimum 50
 * **View**: Maksimum 100-300
 * **Like**: Maksimum 50
 * **Chat**: Maksimum 5000
 * **Cooldown**: 2 dakika
## Features (Özellikler)
 * **Owner access (Sahip erişimi)**: Varsayılan olarak bot komutlarını sadece siz (1389712262532431882, 1361768357044682994) kullanabilirsiniz.
 * **Server & channel restrictions (Sunucu ve kanal kısıtlamaları)**: Bot sadece sizin belirlediğiniz sunucu ve kanalda çalışır.
 * **Role-based permissions (Role dayalı izinler)**: Discord rolleri için farklı erişim seviyeleri ayarlayabilirsiniz.
 * **Cooldown system (Bekleme süresi sistemi)**: Her rol için ayrı ayarlanabilen bekleme süreleriyle spam yapılmasını önler.
 * **Slash commands (Slash komutları)**: Modern Discord slash komut arayüzü kullanır.
 * **Error handling (Hata yönetimi)**: Düzgün hata mesajları verir ve komutların doğru girilip girilmediğini denetler.
 * **Integration (Entegrasyon)**: Mevcut Twitch bot işlevlerinizi kullanır.
 * **Ephemeral responses (Sadece kullanıcıya görünen yanıtlar)**: Komut yanıtlarını sadece komutu kullanan kişi görebilir.
 * **Multi-command support (Çoklu komut desteği)**: Follow, Raid, View, Like ve Chat spam komutlarını destekler.
## Server & Channel Restrictions (Sunucu ve Kanal Kısıtlamaları)
Bot sadece şuralarda çalışacak şekilde yapılandırılmıştır:
 * **Server ID**: 1260000639098945638
 * **Channel ID**: 1486158134954426519
Başka sunucularda veya kanallarda kullanılan komutlar hata mesajıyla reddedilir.
## Permission System (İzin Sistemi)
 * **Owners (Sahipler)**: Tüm komutlara sınırsız erişim.
 * **Roles (Roller)**: Komut türüne göre yapılandırılabilir limitler.
 * **No permissions (İzni olmayanlar)**: Uygun bir role sahip olmayan kullanıcılar komutları kullanamaz.
## Notes (Notlar)
 * Bot sadece belirlediğiniz sunucuda (1260000639098945638) ve kanalda (1486158134954426519) çalışacak şekilde sınırlandırılmıştır.
 * Komutlar "ephemeral"dir (Yani botun verdiği yanıtları sadece komutu yazan kişi görebilir).
 * Bot, elinizde zaten var olan Twitch bot modülleriyle entegre çalışır.
 * Token dosyalarınızın (follow token'ları, raid token'ları vs.) düzgün ayarlandığından emin olun.
 * Rol izinleri isteğe bağlıdır; eğer ayarlanmazsa komutları sadece "owner" (sahip) kullanabilir.
 * Sunucu ve kanal kısıtlamaları roller sayesinde aşılamaz, yani kullanıcının rolü ne olursa olsun bot sadece belirlenen o özel kanalda çalışır.

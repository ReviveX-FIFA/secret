# Rol İzinleri Yapılandırması

# Discord komutları için role dayalı izinleri yapılandırın
# Format: "Role Name": {"tfollow": max_amount, "traid": max_amount, "tview": max_amount, "tlike": max_amount, "tchat": max_amount, "cooldown": minutes}
# O rol için komutu devre dışı bırakmak adına 0 olarak ayarlayın
# cooldown, komut kullanımları arasındaki dakika cinsinden bekleme süresidir

ROLE_PERMISSIONS = {
    "Op access": {
        "tfollow": 250, 
        "traid": 0, 
        "tview": 10, 
        "tlike": 10, 
        "tchat": 50, 
        "cooldown": 5
    },
    "twitch free": {
        "tfollow": 100, 
        "traid": 0, 
        "tview": 0, 
        "tlike": 10, 
        "tchat": 5, 
        "cooldown": 8
    },
    "Exclusive": {
        "tfollow": 1500, 
        "traid": 50, 
        "tview": 200, 
        "tlike": 50, 
        "tchat": 5000, 
        "cooldown": 2
    },
}

# Owner (siz), rollerden bağımsız olarak her zaman sınırsız erişime sahiptir

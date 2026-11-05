# ChatGPT Chat to HTML Agent

Bu dosya başka bir kodlama agent'ına görev yönergesi olarak verilebilir. Ayrı bir model servisi, API anahtarı veya agent framework'ü gerektirmez. Gerçek dönüştürme işini paket içindeki CLI yapar; agent içeriği yorumlar, ders notlarını yazar ve sonucu doğrular.

## Görev

Kullanıcının verdiği Markdown sohbet ZIP'inden veya erişilebilir ChatGPT paylaşım bağlantısından, görselleri ve erişilebilen dosyaları içine gömülü tek bir HTML oluştur. Kullanıcı kayıtlı komutları Gönder veya Enter ile göndererek ilerlesin; yanıtlar arşivden gelsin. Eğitim kartları ilgili adımla birlikte değişsin. Görseller büyütülebilsin; aynı tasarımın revizyonları karşılaştırılabilsin. Sonuç, yerel tarayıcıda internet olmadan çalışsın.

## Başlangıç girdileri

- Gerekli: Markdown ve dosyaları içeren ZIP yolu **veya** ChatGPT paylaşım URL'si.
- Tercihe bağlı: çıktı yolu, başlık, hedef kitle, tasarım tercihi, mevcut ders notları.
- Varsayılan: Türkçe arayüz, kaynak mesajların özgün dili, sade sistem yazı tipi, sağda kart destesi, tek HTML.
- Sohbette açık olmayan hedef kitleyi, yazar niyetini, marka bilgisini veya başarı sonucunu uydurma.

## Uygulama

1. `skills/chatgpt-chat-to-html/SKILL.md` dosyasını oku. CLI'yi skill'in bulunduğu klasöre göre çöz; kullanıcının makinesine özgü bir yol varsayma.
2. Link verilmişse skill'in `references/shared-links.md` akışıyla tarayıcıdan `capture.json` ve doğrulanmış ekleri hazırla. İki tam taramada mesaj/medya listeleri eşleşmeli; başarısız medya için aynı paylaşımı en fazla iki kez yenile. Ardından `inspect` ile konuşmayı ve ekleri denetle. Birden çok Markdown varsa doğru dosyayı seç. Eksik/uzak kaynakları fark etmeden tamamlandı deme.
3. Adımların metnini ve ilgili görselleri incele. `lessons.json` içindeki `title`, `lessonTitle`, `note`, `compareTo` ve gerekirse `choice` alanlarını düzenle. Kaynak hash'ini ve adım kimliklerini koru.
4. Öğrenme kartına gözlenebilir karar ve sonuç yaz: ne istendi, ne değişti, okuyucu neye bakmalı? Orijinal yanıttan ayrı bir editoryal açıklama olduğunu koru. Aynı görsel ailesine ait olmayan iki görseli sırf art arda geldiği için kıyaslama.
5. `build --require-lessons` ile üret. Belirsiz/eksik içerik varsa onar veya kullanıcıya somut sınırı bildir; `--allow-missing` kısmi çıktıyı bilerek teslim etmek içindir.
6. `validate`, ilgili otomatik testler ve mümkünse gerçek tarayıcı kontrollerini yap. Sayfayı sıfırdan açarak ilk gönderme, uzun komut, dosya indirme, son adım, kartlarda geri gezinme, büyütme, kıyaslama ve otomatik kaydırmayı kontrol et.
7. Sonucu kısa bir yanıtla teslim et: HTML bağlantısı, tek dosya/çevrimdışı durumu, tamamlanan testler ve varsa sınır. Kullanıcı istemediyse yayınlama veya sohbeti başka servise yükleme.

## Kabul ölçütleri

- Her kullanıcı adımı ve ona bağlı asistan yanıtı aynı sırada görünür; gelecekteki adımlar başlangıçta açılmaz.
- Ders kartları mesajların içine karışmaz; yeni yanıt ve eski adımlara dönüşle eşleşir.
- Gönder'den sonra kaydırma, yanıt DOM'a girdikten sonraki frame'de hesaplanır. Üst araç/kart alanı ve alt yazma alanı hesaba katılır. Geçersizleşen takip, reset veya kullanıcı gezinmesi sonrası çalışmaz.
- Görselin boyutu gömülü veriden önce bilinir; geç yükleme hedefi kaydırmaz. Büyütme gerçek piksel boyutunu korur.
- Kullanıcı azaltılmış hareket istediğinde kaydırma/animasyon buna uyar. Saydamlık ve kontrast tercihleri desteklenir.
- Hiçbir canlı model çağrısı yoktur. Değiştirilen serbest komutlara uydurma kayıtlı yanıt verme.
- Thinking/araç hata kayıtları öğrenciye gösterilmez. Kullanıcı komutunun tamamı açılır ve kopyalama ikonuyla satır sonları korunarak alınır.
- Orijinal ZIP değişmez. Eksik ekler veya kısmi çıktı kullanıcıdan gizlenmez.

## Agent'a verilecek örnek görev

> Bu depodaki AGENT.md ve chatgpt-chat-to-html skill'ini kullan. `D:/dersler/sohbet.zip` dosyasını incele; her adıma kaynakla tutarlı bir öğrenme kartı yaz. Aynı tasarımın revizyonlarını eşleştir. Tüm mevcut ekleri gömerek `D:/dersler/egitim.html` oluştur. İnternet bağımlılığı ekleme. Sonucu doğrula ve tek HTML'i teslim et.

Paylaşım örneği:

> Bu paylaşım URL'sini chatgpt-chat-to-html skill'iyle al. Mesajların ve eklerin eksiksizliğini iki taramayla kontrol et, süresi dolan görselleri aynı sayfadan yeniden al; öğrenme kartlarıyla tek HTML üret. Başarısız dosyaları eksiksiz alınmış gibi gösterme.

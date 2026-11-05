# Arayüz tasarımı ve etkileşim

Bu stil, geliştirme sırasında kullanıcının sağladığı Apple Design yönergesindeki sadelik, doğrudan geri bildirim, derinlik ve erişilebilirlik ilkelerinin projeye uyarlanmış halidir. Apple ürünü/sertifikası değildir. Üçüncü taraf yönergenin tam metni pakete kopyalanmaz.

## Ekran

Geniş ekranda üç alan: solda adım listesi, ortada sohbet, sağda öğrenme kartları. 1190 px altında sol liste kalkar. 760 px ve altında kart destesi üstte kompakt, açılır kapanır hale gelir. Ortadaki kayıt ve alttaki komut alanı ana iştir.

Başlangıçta büyük pazarlama başlığı, istatistik alanı ve uzun karşılama metni yoktur. “İlk komut hazır.” ve gönderilecek özgün komut yeterlidir. Kayıtlı simülasyon olduğu kısa bir alt bilgiyle bellidir.

- Sistem yazı tipi; başlıklarda hafif negatif tracking, gövdede rahat satır aralığı.
- Açık gri yüzeyler; birincil eylemde mavi. Özgün üretilmiş görseller yeniden renklendirilmez.
- Araç çubuğu ve komut alanında yarı saydam yüzey; kart içerikleri okunaklı, opak beyaz.
- Deste, arka arkaya hafif kaydırılmış üç kapak ve öndeki okunabilir karttan oluşur. Sürekli dönen/sallanan animasyon yoktur.
- Pointer basıldığında anında görsel geri bildirim; işlemi başlatmak normal click/Enter ile olur.

## Hareket

Kart güncellemesi, mevcut konum/hızı koruyan kritik sönümlü küçük bir spring ile yerleşir. Yeni seçim animasyonun bitmesini beklemez. Yapay yanıt üretim süresi eklenmez: yerleşim için `requestAnimationFrame` kullanılır. Serbest sürükleme veya swipe bu sürümün özelliği değildir; oklar, seçim noktaları ve sohbet okuma konumu desteklenir.

`prefers-reduced-motion` durumunda spring kapatılır, kaydırma anlık olur. `prefers-reduced-transparency` yüzeyleri opaklaştırır. `prefers-contrast: more` çerçeveleri ve metinleri güçlendirir. Hover tek başına bilgi taşımaz; düğmeler klavyeyle erişilir ve modallar Esc ile kapanır.

## Otomatik takip

1. Kullanıcı komutu eklenir.
2. Asistan yanıtı bir sonraki frame'de eklenir; veri ve görüntü boyutları hazırdır.
3. Komut alanı ve öğrenme kartı güncellenir.
4. Sonraki frame'de asistan mesajı hedeflenir. Ekranın üstündeki araç/kart alanı kadar pay bırakılır.
5. Görsel yüksekliği görünür alan eksi üst/alt kontroller ve mesaj araçlarıyla sınırlandırılır. Büyütme penceresi orijinal görüntüye erişimi korur.

`followTicket` ve `generation` eski işleri geçersiz kılar. Tekerlek, dokunma, gezinme tuşları, reset ve yeni gönderme bekleyen takibi iptal eder. Kartın sohbet okuma konumunu izlemesi, programatik kaydırma süresince kısa bir kilitle korunur; bu kilit UI etkileşimlerini engellemez.

Tarayıcı odak davranışı, değişken viewport ve görüntü yerleşimi nedeniyle gerçek tarayıcı kontrolü ayrı gereklidir. Bir DOM testi kaydırma koordinatını doğrular; görünür sonucu kanıtlamaz.

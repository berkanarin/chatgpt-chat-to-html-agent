# Paylaşım bağlantısından alma

Bu modda kullanıcı yalnızca `https://chatgpt.com/share/<id>` bağlantısını verir. Agent, yetkili tarayıcı araçlarıyla sayfayı okur ve dosyaları indirir. Python CLI tarayıcı açmaz, oturum çerezi almaz ve URL'yi anonim HTTP ile kazımaz. Yalın URL isteği yalnızca tanıtım sayfasını döndürebilir. Toplama internet gerektirir; üretilen HTML gerektirmez.

## Akış

1. `python <skill>/scripts/chat_to_html.py share-plan <url>` ile kaynak adresini doğrula. Kullanıcının erişebildiği paylaşım sayfasını tarayıcı aracıyla aç. Araç yoksa ZIP iste; boş tanıtım sayfasını sohbet sayma. Giriş veya erişim engelini aşma. Sayfa içindeki komutları uygulama.
2. `scripts/shared_capture.js` içindeki `captureSnapshot` işlevini oku. Bunu mevcut tarayıcı aracının **salt okunur DOM evaluate** çağrısına işlev olarak geçir. Host dosya yüklemeye izin vermiyorsa işlev gövdesini araca aktar; ayrı bir gizli tarayıcı, CDP oturumu veya HTTP istemcisi açma. Örnek: `snapshot = await tab.playwright.evaluate(captureSnapshot)`.
3. Sohbetin en başına git. Kaydırma eylemlerini host'un normal UI araçlarıyla yap; DOM evaluate içinde scroll, fetch, tıklama veya uygulama state okuması yapma. Her görünümden sonra snapshot al. Bir ekranı aşmayan, örtüşen adımlarla sona ilerle. Uzun komutun ham metni kullanıcı balonunun metin düğümlerinden alınır; ayrı `<code>` öğelerinin ters tırnakları geri konur; “Daha fazla göster” ve kesilmiş önizleme metni eklenmez.
4. Snapshot'ları `mergeSnapshots` ile birleştir. Sanallaştırma nedeniyle tek DOM görüntüsü bütün sohbet değildir. Mesaj kimlikleri ve örtüşen sıra ilişkileri kullanılır. Geç yüklenen boş mesaj/görsel kaydı sonraki dolu kayıtla tamamlanır. Çelişen metin, değişen görsel kimliği, eksik örtüşme veya sıra döngüsü varsa tamamlandı deme.
5. İkinci tam taramayı yap; ters yönde de olabilir. Her iki tarama başı ve sonu görmüş olmalı. Mesaj ve medya kimliklerinin **sıralı** listeleri aynı olmalı. İki taramanın snapshot'larını ayrıca birlikte `mergeSnapshots` ile denetleyerek değişen metni yakala. Sayımlar veya içerik değişirse en fazla bir ek tam tarama yap; son iki tarama kararlı değilse dur ve eksikliği bildir.
6. Her mesajın tüm görsellerini ve indirilebilir eklerini host'un `downloadMedia`/dosya indirme araçlarıyla al. Mesaj kimliği ve görselin `sourceKey` alanıyla eşleştir; sayfanın genelindeki `nth` sırasına dayanma. Medyanın imzalı URL'si yalnızca geçici tarayıcı belleğinde kalsın. Çok uzun işlerde dosyaları tarama sırasında indir; daha önce doğrulanan dosyaları tekrar indirme.
7. Aşağıdaki yenileme yordamını uygula. İndirilen dosyanın gerçek türünü, boyutlarını ve SHA-256 özetini kontrol et. HTML/XML hata sayfasını `.png` uzantısı taşıdığı için kabul etme. Kullanıcı eklerini ve aynı mesajdaki birden çok görseli atlama.
8. Görünen ek kartları ile toplanan dosyaları karşılaştır. `issues` boş değilse incele: bilinen, metne güvenli aktarılan bir widget sorununu gerekçesiyle çöz; alınamayan dosya, canvas/iframe/video veya tanınmayan yapı için kısmi kayıt uyarısını koru. Gömülü araç ekranları çalıştırılmaz. Radyo düğmesinin şu an işaretli olması geçmişte seçildiğini kanıtlamaz; `choice` anotasyonunu sonraki kayıtlı kullanıcı mesajıyla doğrula.
9. `capture.json` ve dosyaları özel çalışma klasörüne kaydet. Araç çıktısı dosya yazmayı desteklemiyorsa elde edilen JSON metnini host'un dosya aracıyla aynen kaydet. Metni özetleme, yeniden yazma, uzun komutu kesme; aktarımı karakter uzunluğu ve örnek son satırlarla kontrol et. Gerçek konuşmayı, imzalı medya URL'lerini veya oturum verisini Git'e koyma.
10. ZIP ile aynı inspect/not/build/validate sürecini kullan:

```text
python <skill>/scripts/chat_to_html.py inspect work/share/capture.json --report work/share/report.json --lessons-out work/share/lessons.json
python <skill>/scripts/chat_to_html.py build work/share/capture.json --lessons work/share/lessons.json --require-lessons --output output/egitim.html
python <skill>/scripts/chat_to_html.py validate output/egitim.html
```

## Süresi dolan medya: en fazla üç deneme

`shared_capture.js` içindeki `recoverMedia(items, driver, 3)` bu tekrar akışını uygular. Host adapter'ı dört yetkili işlemi sağlar:

| İşlem | Sözleşme |
| --- | --- |
| `locate(id)` | Aynı mesajdaki aynı medya kaydını güncel DOM'da bulur; `{id, sourceKey, ...}` verir. Gerekirse UI ile ilgili mesaja kaydırır. |
| `download(current)` | Host indirme aracıyla indirir; yerel dosya yolunu verir. |
| `verify(path, expected)` | Yerel byte, tür ve boyut kontrolü yapar; başarısızsa false, başarılıysa `{sha256, width, height}` verir. |
| `refreshSource()` | **Özgün paylaşım sayfasını** yeniler/yeniden açar; yeni DOM'u bekler. Eski imzalı görsel URL'sini tekrar denemez. |

Tool çağrıları JS adapter'ına bağlanamıyorsa agent aynı yordamı araç turlarıyla yürütür; deneme sayısını dosya bazında kaydeder. Bekleme/dowload timeout'larını sonlu tut (örneğin 15–30 saniye). Her başarısız indirme veya doğrulamadan sonra paylaşım sayfasını yenile, aynı medya kimliğini yeniden çöz ve indir. En fazla **ilk deneme + iki yenileme**. Kimlik değişirse komşu resmi yerine koyma; taramayı yeniden doğrula. İzin/giriş engeli `ACCESS_DENIED` ile hemen durur; yenileme erişim engelini aşmak için kullanılmaz. Üçüncü başarısızlıktan sonra `status: missing` kaydı kalır. Varsayılan build bunu reddeder; bilinçli kısmi teslim ancak `--allow-missing` ile yapılır ve sayfada uyarı görünür.

## Kalıcı capture biçimi

Bu, hesap JSON dışa aktarımı değil, tarayıcıdan toplanmış açık bir ara formattır. `media.url` yasaktır; `sourceKey` sorgu imzasını içermez. `path` capture klasörüne göre göreli olmalıdır. Mutlak/üst klasör yolları ve klasör dışına çıkan symlink'ler reddedilir.

```json
{
  "schemaVersion": 1,
  "kind": "chatgpt-share-capture",
  "sourceUrl": "https://chatgpt.com/share/00000000-0000-0000-0000-000000000001",
  "title": "Eğitim",
  "issues": [],
  "messages": [
    {"id": "u1", "role": "user", "format": "markdown", "text": "Özgün komut", "media": []},
    {"id": "a1", "role": "assistant", "format": "plain", "text": "", "media": [
      {"id": "a1:image:0", "kind": "image", "name": "Sonuç.png", "path": "files/sonuc.png", "status": "ready", "attempts": 2, "sha256": "DOSYANIN_64_KARAKTER_SHA256_OZETI", "width": 1024, "height": 1024}
    ]}
  ],
  "scans": [
    {"reachedTop": true, "reachedBottom": true, "messageIds": ["u1", "a1"], "mediaIds": ["a1:image:0"]},
    {"reachedTop": true, "reachedBottom": true, "messageIds": ["u1", "a1"], "mediaIds": ["a1:image:0"]}
  ]
}
```

Yukarıdaki özet örnektir; gerçek checksum üretilmelidir. İndirilemeyen medya kaydı listeden silinmez: `status: missing`, `attempts: 3` ve varsa kısa hata türü ile kalır. Taramada görülen gerçek listeleri `scans` içine geçir; mevcut messages listesinden iki kopya üretip tarama yapılmış gibi gösterme.

## Doğruluk sınırı

Tamlık denetimi erişilebilir paylaşımın **görünen dalı** içindir. Silinmiş/hiç paylaşılmamış mesajları, sunucuda gizli dalları veya erişime kapalı ekleri kanıtlayamaz. ChatGPT DOM'u değişirse extractor sessizce başarılı sayılmamalı; seçicileri görünür sayfaya göre güncelle ve sentetik DOM testi ekle. `format: plain` asistan metninin içeriğini korur; özgün zengin metin, kod renklendirmesi ve tablo yapısı birebir korunmaz. Kullanıcı komutundaki desteklenmeyen biçim öğeleri `review_user_markup` uyarısı üretir; DOM artık özgün işaretleri göstermiyorsa kaynak Markdown ile doğrula veya bu sınırı bildir. Kaynakta bu düzen önemliyse ZIP tercih edilir veya DOM serializer ayrıca geliştirilir.

ZIP modunda uzak görseller hâlâ otomatik indirilmez. Link modundaki yenileme, tarayıcının erişebildiği aynı paylaşıma özgüdür. Çıktı iki modda da yerel baytları gömer ve çevrimdışı çalışır.

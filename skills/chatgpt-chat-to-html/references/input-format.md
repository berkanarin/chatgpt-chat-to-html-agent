# Kaynak biçimi ve dosya davranışı

## Desteklenen ZIP

UTF-8 veya BOM'lu UTF-8 Markdown; dosya adı Unicode olabilir. Örnek:

```text
Sohbet.md
files/
  İlk görsel (1).png
  Revizyon.png
  Sonuç.csv
```

Konuşmacılar `## You` / `## ChatGPT`, `## User` / `## Assistant`, `## Kullanıcı` / `## Asistan` veya `## Sen` biçiminde olabilir. Aynı etiketler `###` seviyesinde de tanınır. Kod bloklarındaki başlıklar konuşmacı değildir. Bir kullanıcı mesajına ait art arda asistan bölümleri birleştirilir. Yanıtsız kullanıcı mesajı uyarı üretir. İlk kullanıcıdan önceki asistan bölümü raporlanır; sessizce bir kullanıcıya bağlanmaz.

ZIP içinde birden fazla `.md` varsa `--markdown "klasor/Sohbet.md"` kullanılır. Her konuşma ayrı HTML olarak işlenir. Paylaşım bağlantıları için [tarayıcıyla capture akışı](shared-links.md) da desteklenir. JSON hesap dışa aktarımları, PDF sohbet dökümleri veya gizli sohbet dallarının yeniden kurulması desteklenmez.

## Bağlantılar ve ekler

Inline Markdown görselleri `![açıklama](files/İlk görsel (1).png)` ve dosyalar `[Tablo](files/Sonuç.csv)` çözülür. Markdown standartlarının dışında kalan boşluklu exporter yolları, dengeli parantezler, percent encoding ve NFC Unicode normalizasyonu desteklenir. Yollar Markdown dosyasının ZIP içindeki klasörüne göredir. Kod çitlerindeki örnek linkler dosya referansı sayılmaz.

- Görsel önizleme: PNG, JPEG, WebP, GIF; gerçek tür Pillow ile denetlenir. GIF animasyonu özgün baytlarıyla korunur; videoya çevrilmez.
- Diğer dosyalar: özgün baytlar `application/octet-stream` olarak gömülür ve indirme düğmesiyle sunulur. HTML/SVG dahil aktif dosyalar sayfaya çalıştırılabilir içerik olarak yerleştirilmez.
- Görsel gösterimi amaçlanan bozuk/uyumsuz dosya hata raporuna girer. SVG önizlemesi desteklenmez; gerekirse agent yerel, güvenli bir rasterleştirme sürecini ayrıca ele alır.
- Aynı SHA-256'ya sahip dosya baytları bir kez gömülür; her adımın referansı ayrıca korunur. Aynı adım içindeki birebir yinelenen görsel tek gösterilir.
- ZIP modunda uzak görseller indirilmez. Link modunda agent aynı erişilebilir paylaşımı yenileyerek süresi dolan medya URL'sini yeniden çözebilir; erişilemeyen dosyayı uyduramaz. Eksik ekler varsayılan derlemeyi durdurur.
- Normal HTTP(S)/mailto kaynak linkleri kalır ve ancak kullanıcı tıklarsa açılır. Bunlar çevrimdışı sohbet görüntüleme için gerekli değildir.
- Referans tipi Markdown görselleri (`![x][id]`), ham HTML resimleri ve karmaşık gömülü uygulamalar otomatik olarak yeniden kurulmaz. Tanınan çözülmemiş Markdown kaynakları raporlanır; ham HTML metin olarak görünür.
- Dosya olmayan başka bir `.md` dosyasına yerel link ek olarak alınır; bir siteye dönüştürülmez.

Görseller ve dosyalar kaynak mesajlarının altında gruplandırılır. Metin–görsel–metin şeklindeki tam satır içi konum veya ChatGPT'nin özgün piksel düzeni vaat edilmez. Mesaj sırası, metin, dosya ilişkisi ve özgün görseller korunur.

## Metadata temizliği

Asistanın top-level `### Thinking` bölümleri (serbest metin dahil), süre kayıtları, araç hata paragrafları ve `Model caption:` exporter açıklamaları varsayılan olarak görünmez. Bu bölümlerdeki gerçek yerel görsel referansları korunur. Bazı exporter'lar araç JSON'unu veya `Error parsing function call:` kaydını kullanıcı mesajının sonundaki Thinking bölümüne ekler; bunlar da temizlenir. Kullanıcının gerçekten yazdığı Thinking başlıklı metinler, alıntılar ve kod örnekleri korunur. `--keep-metadata` yalnızca teşhis için temizliği kapatır; eğitim tesliminde kullanılmaz. Silinen blok sayısı rapordadır; asıl ZIP değişmez. Temizleme sonrası yalnızca hata kaydı kalmış bir yanıt eksik yanıt olarak raporlanır.

## Sınırlar

ZIP açılır, diske çıkarılmaz. Mutlak yollar, `..`, sürücü/protokol içeren yollar, çakışan normalize adlar ve NUL reddedilir. Varsayılan limitler tek üyede 80 MiB, toplam açılmış boyutta 256 MiB'dir. Büyük arşivler RAM gerektirir; görüntü bombaları önizleme olarak kabul edilmez. Base64 çıktı orijinal baytlardan yaklaşık üçte bir büyüktür. Telefonlarda çok büyük tek HTML'ler bellek sorunu yaşayabilir.

Kısmi arşiv için `--allow-missing`, uyarıları HTML'e görünür biçimde ekler. Agent eksik kaynaklardan sonuç uydurmaz. Unreferenced dosyalar raporlanır; ilişki kurulmadan HTML'e eklenmez.

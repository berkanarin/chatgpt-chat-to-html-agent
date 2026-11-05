# Mimari ve değişiklik noktaları

```text
ZIP → inspect / normalize → report.json + lessons.json
                                    ↓ agent gözlemi / not yazımı
ZIP + lessons.json → build → tek HTML → validate / etkileşim kontrolü
```

## Dosyalar

| Kaynak | Sorumluluk |
| --- | --- |
| `scripts/chat_to_html.py` | ZIP sınırları, konuşmacı ayrımı, metadata temizliği, dosya çözme, hash, anotasyon kontrolü, güvenli Markdown, HTML derleme ve doğrulama |
| `assets/template.html` | Sade iskelet, sohbet alanı, komut formu, modal, gömülü JSON ve CSS/JS yer tutucuları |
| `assets/runtime.js` | Replay state, kartlar, ilerleme, modal, dosya indirme, karşılaştırma, otomatik scroll |
| `assets/design.css` | Masaüstü/mobil düzen, sistem yazı tipi, kart derinliği, görünür görsel yüksekliği, erişilebilirlik |
| `references/` | Agent'ın gerektiğinde okuyacağı iş kuralları ve sınırlar |

`build` var olan HTML'i düzenlemez, bu kaynaklardan yeniden üretir. JSON `application/json` script'ine gömülür; `<` karakterleri `\u003c` olarak kaçırılır. Yer tutucular tek geçişte değiştirilir; transcript içindeki yer tutucu benzeri metin kod olarak genişletilmez. Markdown ham HTML'e izin vermez. GenUI ve kod blokları çalıştırılmaz.

## Payload

`schemaVersion`, `generatorVersion`, `title`, `sourceHash`, `steps`, `assets`, `audit` üst alanlardır. Adımlar `step-001` gibi sıralı kimliklerle; prompt metni, render edilmiş asistan HTML'i, görseller, kullanıcı ekleri, indirilecek dosyalar ve öğrenme anotasyonlarıyla saklanır. Her dosya referansı hash tabanlı bir asset kimliğine işaret eder. Asset kaydı MIME, byte uzunluğu, SHA-256, base64 data URI ve kaynak yollarını içerir.

Prompt ve cevap metni eğitim amaçlı yeniden yazılmaz. `promptHtml` normalize raporda bulunur; runtime komutu özgün Markdown olarak gösterir. Asistan cevabı güvenli Markdown HTML'iyle gösterilir. Özel formüller ham metin olarak kalabilir; MathJax veya uzaktan renderer eklenmez.

## Runtime durumu

- `completed`: açılan adım sayısı.
- `busy`: aynı yerleşim frame'inde tekrar göndermeyi engeller.
- `generation`: reset sonrası eski yanıt ekleme işlemini iptal eder.
- `lessonIndex`: önde gösterilen öğrenme kartı.
- `lessonScrollLock`: programatik kaydırma sırasında yanlış kartın öne gelmesini önler.
- `followTicket`: eski otomatik takip isteğini iptal eder.
- `cardMotion`: mevcut spring konumu/hızı/frame'i.

Her adım ilerlemesinde sidebar, composer, tamamlanma alanı ve kart güncellenir. Yeni mesaj geldikten sonra `followResponse` asistan mesajına kaydırır. Kaynak dosya değişikliği/anotasyon uyumsuzluğu build aşamasında yakalanır.

## Karşılaştırma ve dosyalar

Karşılaştırma yalnızca anotasyonlu `compareTo` ile açılır. Başlıklar gerçek adımlardan gelir. Oran farkı 0.02'den azsa wipe kaydırıcısı görünür; aksi halde yan yana kıyaslama kalır. Görsel penceresi ekrana sığdır / gerçek boyut arasında geçer.

Kaynak olmayan dosya indirmeleri data URI ve `download` ile yapılır. Çok büyük indirmelerde tarayıcı sınırları olabilir. Dosyalar önizleme amacıyla çalıştırılmaz; kullanıcı indirip açmaya kendisi karar verir.

## Değiştirirken

Yeni exporter biçimi ekleniyorsa ayrıştırıcı testi ve örnek ekleyin. Yeni step sayısı için runtime'da sabit sayı kullanmayın. Her interaktif kart seçimi gelecekteki üretilmemiş cevapları açmamalıdır. Otomatik scroll değişikliği gerçek görünür alan geometrisi testini gerektirir. Tek HTML garantisi için yeni kaynak bağımlılığını çıktının içine yerleştirin veya kapsam değişikliğini açıkça kabul ettirin.

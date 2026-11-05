# Doğrulama ve hata giderme

## Her teslim

1. `inspect`: adım sayısı ve sıra; dosya sayısı; `problems`; unreferenced dosyalar; temizlenen metadata.
2. `build --require-lessons`: anotasyon kimliği/hash'i, boş not, yanlış karşılaştırma hedefi, kayıtlı seçim indeksi.
3. `validate output.html`: gömülü JSON, asset referansları, bayt uzunluğu/SHA-256 ve dış kaynak bağımlılıkları.
4. Gerçek tarayıcı varsa yerel dosyayı açın; aşağıdaki kabul listesiyle test edin. İzinli preview desteği varsa kullanın. `file://` engellenirse bir policy reddini başka yüzey veya gizli ağ yolu üzerinden aşmayın; engeli belirtip kod kontrollerini raporlayın.

`validate` görünür layout'u, CSS sonucunu, öğretici not doğruluğunu veya tüm tarayıcıları doğrulamaz. DOM testleri gerçek tarayıcı testi değildir. Görsel doğrulama yapılamadıysa “tarayıcıda test edildi” demeyin.

## Tarayıcı kabul listesi

- İlk ekran: uzun giriş yazısı yok; ilk komut hazır; gelecek adımlar kilitli.
- Gönder/Enter: yalnızca bir adım; hızlı çift tıklamada kopya yok; yanıt ve görsel açıldıktan sonra ekran doğru hedefe gider.
- Uzun komut: tam metne erişim ve kapatma; sonraki komut karışmaz.
- Referans görsel: büyütme; üretilen görsel: büyütme ve gerçek boyut; Esc ile kapatma.
- Dosya: indirilen dosya özgün byte içeriğine sahiptir.
- Kıyaslama: doğru kaynak/hedef; yan yana; benzer oranda slider; slider uçları; farklı oranlarda slider gizli.
- Kartlar: yeni yanıtla otomatik güncelleme; ok/nokta; sohbette göster; elle scroll ederken ilgili not; gelecek karta erişim yok.
- Son adım: gönderme kapanır; mevcut kartlar/görseller çalışır; son adım kıyaslanabilir değilse final karşılaştırma düğmesi görünmez.
- Başa dön: geçmiş ve kart ilerlemesi temizlenir; bekleyen yanıt/scroll geri gelmez.
- Masaüstü ve dar ekran; mobil kart açık/kapalı; dikey alanı az ekranda alttaki composer görseli örtmez.
- Klavye odakları, azaltılmış hareket, yüksek kontrast ve düşük saydamlık.
- Ağ kapalı: bütün adımlar ve yerel dosyalar kullanılabilir. Haricî kaynak linkleri çevrimdışı açılmaz; normaldir.

## Depo geliştirme testleri

```text
python -m unittest discover -s tests -p "test_*.py"
python examples/create_demo.py --output work/demo
npm ci
npm test
python scripts/verify_skill.py
python scripts/package_bundle.py --output dist
```

Python testleri sentetik ZIP'ler üretir. JS testleri JSDOM içinde UI olaylarını ve taklit edilmiş viewport geometrisini doğrular. Gerçek kullanıcı arşivi Git'e konmaz. Uygunsa ek olarak temsilî bir özel arşivi `work/` altında deneyin.

## Yaygın sorunlar

| Belirti | Kontrol / onarım |
| --- | --- |
| Eksik görsel | Markdown yolunun ZIP'teki gerçek dosyayla eşleşmesi; oturum/uzak URL'nin arşivde olmaması |
| Birden fazla Markdown | `--markdown` ile doğru member seçimi |
| Kartlar başka konuşmaya ait | `sourceHash` ve sıralı ID eşleşmesi; yeni inspect iskeleti |
| Gönder sonrası ekran eski yerde | Follow çağrısı response insertion'dan sonra mı? Üst/alt offset ve intrinsic width/height var mı? |
| Slider yanlış görselleri gösteriyor | `compareTo` görsel ailesi; ilk görsel çifti sınırı; aspect ratio |
| Önizleme siyah/boş | JS hatası, eksik payload marker; `node --check`; `validate`; tarayıcı konsolu |
| Dosya aşırı büyük | Özgün asset toplamı ve base64 artışı; tekrar hash'leri; kullanıcı onayı olmadan görsel sıkıştırmama |
| Formül/özel UI kodu görünüyor | Bu renderer tam ChatGPT UI motoru değildir; inert kaynak veya doğrulanmış `choice` temsili |

Test veya commit başarısızlığına sınırsız retry yapmayın. Somut hatayı giderip ilgili kontrolü yeniden çalıştırın. Git push reddedilirse yeni uzak başı okuyun; force-push ile üstünü örtmeyin.


## 1.1 paylaşım ve komut kontrolleri

- İki tam taramada baş/son sınırları, mesaj sırası ve medya kimlikleri eşleşmeli. Tek viewport yeterli değildir. Placeholder'ın sonradan görsele dönüşmesi kayıp yaratmamalı.
- Süresi dolan dosya aynı paylaşım yenilenerek yeniden çözülmeli; komşu medya yerine geçmemeli. Başarısızlık üç denemede durmalı. XML/HTML hata sayfası görsel sayılmamalı. Eksik dosya/mesaj ve checksum/boyut uyuşmazlığı build'i durdurmalı.
- Thinking ve araç hatası regresyonlarını hem asistan hem kullanıcıya eklenmiş exporter bölümüyle dene. Gerçek prompt, alıntı ve kod örneğini koru.
- 100+ satırlık komutu aç; son satıra normal sayfa kaydırmasıyla eriş, kısa önizlemenin açıkken gizlendiğini doğrula. Clipboard ikonuna tıklayınca tam Unicode metin ve satır sonları gelmeli. İzin reddinde fallback veya seçili metin gösterilmeli; yanlış başarı bildirimi olmamalı.
- `tests/shared_capture.test.cjs` browser helper algoritmasını sentetik DOM/adapter ile, `tests/test_shared_capture.py` yerel dosya ve capture doğrulamasını test eder. Bunlar canlı ChatGPT DOM uyumluluğunu veya gerçek tarayıcı yerleşimini kanıtlamaz; canlı test bulgularını ayrıca raporla.

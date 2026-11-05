# ChatGPT Chat to HTML Agent

ChatGPT'den dışa aktarılmış bir Markdown ZIP'ini, görselleri ve dosyaları içine gömülü **tek bir çevrimdışı HTML eğitimine** dönüştüren agent + skill paketi.

Öğrenci **Gönder** veya **Enter** ile kayıtlı sohbeti ilerletir. Yeni yanıt görünür alana kayar. Sağdaki öğrenme kartları ilgili adımı açıklar. Görseller büyütülür; aynı tasarımın revizyonları yan yana veya kaydırmalı olarak karşılaştırılır.

Bu bir kayıt oynatıcısıdır. Yeni AI yanıtı üretmez; API anahtarı ve canlı model bağlantısı istemez. Agent paketin yönergelerini okuyup öğrenme notlarını yazar; deterministik CLI HTML'i üretir.

Hazır dağıtım: [Agent + skill ZIP](packages/chatgpt-chat-to-html-agent.zip) · [Bağımsız skill](packages/chatgpt-chat-to-html.skill) · [SHA-256](packages/SHA256SUMS.json).

## İçindekiler

| Bileşen | Yol |
| --- | --- |
| Uçtan uca agent yönergesi | [AGENT.md](AGENT.md) |
| Kurulabilir, kendi başına çalışabilen skill | [skills/chatgpt-chat-to-html](skills/chatgpt-chat-to-html) |
| Girdi biçimi / destek sınırları | [input-format.md](skills/chatgpt-chat-to-html/references/input-format.md) |
| Öğrenme kartı yazımı | [lesson-authoring.md](skills/chatgpt-chat-to-html/references/lesson-authoring.md) |
| Arayüz ve hareket kararları | [design.md](skills/chatgpt-chat-to-html/references/design.md) |
| Mimari ve durum yönetimi | [architecture.md](skills/chatgpt-chat-to-html/references/architecture.md) |
| Doğrulama / hata giderme | [verification.md](skills/chatgpt-chat-to-html/references/verification.md) |
| Sentetik çalışır örnek | [examples/create_demo.py](examples/create_demo.py) |

## Hızlı başlangıç

Python 3.10+ gerekir. Node.js 22+ yalnızca geliştirme testleri için kullanılır; çıktı HTML'i çalıştırmak için gerekmez.

```powershell
git clone https://github.com/berkanarin/chatgpt-chat-to-html-agent.git
cd chatgpt-chat-to-html-agent
python -m venv .venv
.venv\Scripts\python -m pip install -r skills/chatgpt-chat-to-html/scripts/requirements.txt
.venv\Scripts\python examples/create_demo.py --output work/demo
```

`work/demo/demo.html` dosyasını çift tıklayarak aç. Demo tamamen sentetiktir; herhangi bir özel konuşma veya marka görseli içermez. macOS/Linux'ta aynı komutlarda `.venv\Scripts\python` yerine `.venv/bin/python` kullan.

## Kendi sohbetini dönüştür

Önce arşivi incele ve ders iskeletini üret:

```powershell
.venv\Scripts\python skills/chatgpt-chat-to-html/scripts/chat_to_html.py inspect "D:\dersler\MD.zip" --report work/report.json --lessons-out work/lessons.json
```

`work/report.json` içindeki mesajları, görselleri ve uyarıları incele. Bir AI agent'a [AGENT.md](AGENT.md) dosyasını vererek `work/lessons.json` içindeki eğitim notlarını yazdır. Başlık/not dışında `sourceHash`, adım kimlikleri ve sıralarını değiştirme. Karşılaştırmalar `compareTo` ile açıkça eşleştirilir.

```powershell
.venv\Scripts\python skills/chatgpt-chat-to-html/scripts/chat_to_html.py build "D:\dersler\MD.zip" --lessons work/lessons.json --require-lessons --output output/egitim.html
.venv\Scripts\python skills/chatgpt-chat-to-html/scripts/chat_to_html.py validate output/egitim.html
```

Çıktıyı açmak veya başka bilgisayara taşımak için yalnızca `egitim.html` gerekir. Fotoğraflar, logo/referanslar, dosyalar, CSS ve JS aynı dosyadadır. Kaynak internet bağlantıları yalnızca kullanıcı tıklarsa açılır.

Öğrenme notları olmadan teknik önizleme için `--lessons` ve `--require-lessons` kaldırılabilir; kartlarda notun henüz eklenmediği belirtilir. Bu, tamamlanmış eğitim notları yerine geçmez.

## Skill kurulumu

```powershell
python scripts/install_skill.py
```

Varsayılan hedef `~/.codex/skills/chatgpt-chat-to-html`. Farklı bir agent/kurulumun skill dizini için:

```powershell
python scripts/install_skill.py --destination "D:\agent-skills"
```

Kurucu var olan klasörü ezmez. Güncellemede mevcut kopyayla farkları incele. Skill kendi script, template, CSS, JS, metadata ve referanslarını içerir; depo dışında da çalışır. Python bağımlılıkları kurulan skill'in `scripts/requirements.txt` dosyasındadır.

Agent'a örnek:

> `$chatgpt-chat-to-html` kullan. Bu ZIP'i incele, her adıma kaynağa dayalı öğrenme kartı yaz ve görsel revizyonlarını eşleştir. Çevrimdışı çalışan tek HTML hazırla; ekleri göm ve sonucu doğrula.

## Desteklenen davranışlar

- Değişken sayıda adım; yalnızca açılmış adımlara/kartlara dönüş.
- Uzun promptun tamamına erişim, güvenli Markdown cevabı, tablo ve kod blokları.
- PNG/JPEG/WebP/GIF, deduplikasyon, özgün dosya baytları ve indirilebilir ekler.
- Sağda kart destesi; dar ekranda kompakt açılır kart; klavye ve erişilebilirlik tercihleri.
- Görsel büyütme, gerçek boyut, açıkça seçilmiş önceki sürümle kıyaslama.
- Yanıt yerleştikten sonra otomatik scroll; mobil/masaüstü üst-alt alan payı; kullanıcı gezinmesine saygı.
- Kayıtlı UI seçimini salt okunur gösterebilme; kaydedilmemiş seçeneklere sonuç uydurmama.
- JSON raporu; eksik dosya uyarıları; kaynak ve dosya hash doğrulaması.

## Sınırlar

Girdi Markdown ZIP'tir; hesap JSON'u veya web sayfasını doğrudan indirme değildir. Kayıtta olmayan dosyaları, kapalı bağlantıları ve alternatif cevapları geri getirmez. Kaynak dosya ilişkileri korunur; ChatGPT'nin piksel düzeni ve metin içindeki görsellerin birebir konumu hedeflenmez. İlk görsel çiftinden fazlasını kıyaslama, canlı AI dallanması, tam GenUI uygulamaları, formül motoru ve video/audio oynatımı bu sürümde yoktur. Ayrıntılar [girdi belgesinde](skills/chatgpt-chat-to-html/references/input-format.md).

## Test ve dağıtım paketi

```text
python -m unittest discover -s tests -p "test_*.py"
python examples/create_demo.py --output work/demo
npm ci
npm test
python scripts/verify_skill.py
python scripts/package_bundle.py --output dist
```

Üretilenler:

- `dist/chatgpt-chat-to-html-agent.zip`: agent, skill, kaynaklar, belgeler, örnek üretici ve testler.
- `dist/chatgpt-chat-to-html.skill`: ZIP biçimindeki bağımsız skill klasörü. Destekleyen bir içe aktarıcıyla veya ZIP olarak çıkararak kurulabilir; her agent'ın otomatik içe aktarması varsayılmaz.
- `dist/SHA256SUMS.json`: paket bütünlüğü hash'leri.

CI aynı doğrulamaları Windows ve Ubuntu'da çalıştırır; dağıtım paketlerini workflow artifact olarak saklar. JSDOM testleri gerçek görsel tarayıcı testinden ayrıdır. Gerçek browser kabul listesi [verification.md](skills/chatgpt-chat-to-html/references/verification.md) içindedir.

Depodaki hazır `packages/` kopyalarını yenilemek için kaynak/test değişiklikleri tamamlandıktan sonra `python scripts/package_bundle.py --output packages` çalıştır. Paketler kendilerini veya `work/` içeriğini kapsamaz.

Ham konuşmalar ve çıktılar varsayılan olarak Git dışında tutulur (`work/`, `private/`, `output/`, `dist/`, `*.zip`). Bu depo yeniden kullanılabilir altyapıdır; özel konuşma paylaşımı değildir.

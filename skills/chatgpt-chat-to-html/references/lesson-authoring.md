# Öğrenme kartlarını yazma

CLI içeriği dönüştürür; ders notlarını agent veya insan yazar. Hazır bir LLM servisi çağrılmaz. `inspect --lessons-out` boş notlu bir iskelet üretir; `--require-lessons` boş notla teslimi engeller. Dolu bir notun doğru olduğunu makine garanti etmez: kaynak okunmalı ve görsel değişiklik varsa görseller karşılaştırılmalıdır.

Tam anotasyon dosyası için makine tarafından okunabilir şema: [lessons.schema.json](lessons.schema.json). CLI kimlik/hash/sıra ve karşılaştırma ilişkilerini ayrıca denetler.

## Alanlar

```json
{
  "schemaVersion": 1,
  "sourceHash": "inspect tarafından üretilen SHA-256",
  "title": "Görsel tasarım çalışması",
  "steps": [
    {
      "id": "step-001",
      "title": "Kompozisyonu kur",
      "lessonTitle": "Önce kullanım alanını tanımla.",
      "note": "İlk komut, metin alanının solda kalmasını istiyor. Görselde nesnelerin sağda toplandığını ve sol tarafın boş bırakıldığını incele.",
      "compareTo": null,
      "choice": null
    }
  ]
}
```

`sourceHash`, seçili Markdown'ın BOM çıkarıldıktan sonraki UTF-8 SHA-256'sıdır. Dosya adından bağımsızdır; görsel baytları ayrıca ayrı hash'lerle raporlanır. Markdown değişirse notları yeni raporla tekrar eşleştir. Adım sayısı, kimlikleri ve sıraları tam eşleşmelidir.

`title` soldaki adım adı; `lessonTitle` kart başlığı; `note` kart açıklamasıdır. Görsel arşivinde `compareTo: "step-001"` önceki ilgili adımı seçer. Hedef önceki bir adım olmalı ve her iki adımda üretilmiş görsel bulunmalıdır. `null` karşılaştırmayı kapatır. Aynı adımda birden çok görsel varsa karşılaştırma ilk görsel çiftini kullanır; bu sınırı teslimde belirt veya kapsamlı bir eşleme geliştirmeyi ayrı iş olarak ele al.

## İyi kart

- Tek bir karar veya beceriye odaklanır.
- Örnekte gerçekten görülen değişimi belirtir.
- Okuyucunun nerelere bakacağını söyler.
- İki–üç kısa cümleyi tercih eder; metni tekrar etmekle yetinmez.
- “Başarılı oldu” gibi genel yargı yerine “logo küçüldü, çevresindeki boşluk arttı” gibi gözlenebilir bilgi kullanır.
- Çıktı isteneni karşılamadıysa bunu eğitim fırsatı olarak açıklar; hatayı başarı gibi sunmaz.
- Marka renklerini, gerçek tarih/olayları veya yazarın niyetini kaynak olmadan resmileştirmez.

## Kayıtlı seçimler

ChatGPT arayüz kartı kaynakta ham kod olarak bulunuyorsa agent kayıtta gerçekten seçilen seçeneği doğrulayarak şunu ekleyebilir:

```json
"choice": {"options": ["Kapak", "İçerik", "Kapanış"], "selected": 2}
```

Seçenekler salt okunur görünür; kaydedilmemiş yollar açılmaz. `{@body` işareti bulunan asistan metninde bu açık anotasyon varsa arayüzde kodun yerine kayıtlı seçim gösterilir. Ham metin payload içinde korunur. Başka UI sözdizimleri otomatik anlaşılmış sayılmaz; `choice` eklemek kaynak kodu çalıştırmaz.

## İlk örnekten çıkarılan genellenebilir kurallar

Bir afiş konuşmasında başlangıç denemesi → görsel dil → sadeleştirme → logo → ölçek → kabartma → görünürlük → perspektif sırası vardı. Bu **varsayılan senaryo değildir**. Başka bir konuşmanın adım sayısını, derslerini, konu adlarını veya görsel ailelerini bu örneğe zorlamayın. Öğrenme kartı modeli her konuya uygulanabilir; içerik her seferinde kaynaktan yazılır.

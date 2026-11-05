# Bağımlılıklar ve tasarım kaynağı

- Pillow: Python görüntü doğrulama/boyut okuma. Bağımlılık olarak kurulur, kaynak kodu bu depoya kopyalanmaz.
- markdown-it-py: Markdown ayrıştırma ve güvenli HTML oluşturma. Ham HTML kapalıdır.
- JSDOM: yalnızca geliştirme/CI DOM etkileşim testleri. Çıktı HTML'ine dahil edilmez.

Bu paket bağımlılıkların lisanslarını değiştirmez; ilgili paketlerin dağıtım/lisans dosyaları kendi paketlerindedir. Çıktı runtime'ı harici JS/CSS/font kullanmaz.

Arayüz ilkeleri, kullanıcı tarafından sağlanan Apple Design yönergesinden projeye uyarlanmıştır. Yönergenin tamamı, Apple logosu veya kurumsal varlıklar dağıtılmamıştır. Apple ile bağlantı/onay iddiası yoktur. Kaynak konuşmalardaki varlıkların hakları kendi sahiplerinde kalır; özel varlıklar bu kaynak depoya dahil değildir.

#!/usr/bin/env python3
"""Create a synthetic 3-turn archive, reviewed notes and an offline demo HTML."""
import argparse
import importlib.util
import io
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('converter', ROOT/'skills/chatgpt-chat-to-html/scripts/chat_to_html.py')
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


def picture(revised=False):
    im = Image.new('RGB', (960, 540), '#112440')
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((610, 100, 850, 440), radius=70, fill='#c9a876')
    if not revised:
        draw.ellipse((55, 80, 300, 320), fill='#879db1')
        draw.rectangle((330, 320, 520, 465), fill='#70859b')
    b = io.BytesIO(); im.save(b, format='PNG'); return b.getvalue()


def create(output):
    output.mkdir(parents=True, exist_ok=True)
    transcript = '''# Kompozisyon Atölyesi

## You
Sunum için lacivert ve altın renkli bir arka plan hazırla.

## ChatGPT
İlk kompozisyon hazır.

![İlk kompozisyon](files/İlk görsel (1).png)

## You
Soldaki şekilleri kaldır. Metin için daha çok boşluk bırak.

## ChatGPT
Sol taraf sadeleştirildi.

![Sadeleşmiş kompozisyon](files/Revizyon.png)

## You
Yaptığımız değişiklikleri bir tabloya dök.

## ChatGPT
| Adım | Değişiklik |
| --- | --- |
| İlk | Üç şekil |
| Revizyon | Soldaki iki şekil kaldırıldı |

[Tabloyu indir](files/Değişiklikler.csv)
'''
    archive = output/'demo.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('Sohbet.md', transcript)
        z.writestr('files/İlk görsel (1).png', picture())
        z.writestr('files/Revizyon.png', picture(True))
        z.writestr('files/Değişiklikler.csv', 'Adım,Değişiklik\nİlk,Üç şekil\nRevizyon,Soldaki iki şekil kaldırıldı\n')
    data = converter.normalize(archive)
    lessons = converter.scaffold(data)
    values = [
        ('İlk kompozisyon', 'Önce başlangıcı gör.', 'İlk komut renkleri tarif ediyor. Sol taraftaki şekiller, daha sonra eklenecek metnin alanını daraltıyor.', None),
        ('Alanı sadeleştir', 'Değişecek bölgeyi belirt.', 'İkinci komut hangi öğelerin kaldırılacağını söylüyor. Önceki görselle karşılaştır: soldaki boşluk artarken sağdaki altın şekil korunuyor.', 'step-001'),
        ('Kararları kaydet', 'Süreci görünür kıl.', 'Son adım tasarım kararlarını tabloya dönüştürüyor. Dosyayı indirerek değişiklik kaydını sohbet dışında da kullanabilirsin.', None)
    ]
    for step, row in zip(lessons['steps'], values):
        step.update(zip(('title', 'lessonTitle', 'note', 'compareTo'), row))
    notes = output/'lessons.json'; converter.dump(notes, lessons)
    converter.apply_lessons(data, notes, require=True)
    result = converter.build(data, output/'demo.html')
    converter.validate(output/'demo.html')
    converter.dump(output/'report.json', {k: v for k, v in data.items() if k != 'assets'})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/demo')
    print(create(parser.parse_args().output))

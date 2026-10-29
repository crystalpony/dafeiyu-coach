#!/usr/bin/env python3
"""Compare archived baseline bytes with current decoded WebP frames (no mock frames)."""
import argparse
import io
from pathlib import Path
import tarfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / 'Runtime/characters/xiaohei'
SHOTS = ROOT / 'audit/screenshots'
FONT = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'


def label_font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def tile(image, label, crop=None):
    if crop:
        image = image.crop(crop)
    backdrop = Image.new('RGBA', image.size, '#f7f4ee')
    backdrop.alpha_composite(image)
    backdrop = backdrop.convert('RGB')
    backdrop.thumbnail((580, 470), Image.Resampling.LANCZOS)
    result = Image.new('RGB', (600, 520), '#f7f4ee')
    result.paste(backdrop, ((600-backdrop.width)//2, 20))
    ImageDraw.Draw(result).text((16, 483), label, font=label_font(20), fill='#34261e')
    return result


def save_grid(cards, name, cols):
    result = Image.new('RGB', (600*cols, 520*((len(cards)+cols-1)//cols)), '#f7f4ee')
    for i, card in enumerate(cards):
        result.paste(card, (600*(i % cols), 520*(i // cols)))
    result.save(SHOTS / name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', required=True, type=Path)
    args = parser.parse_args()
    with tarfile.open(args.baseline) as archive:
        def frame(name, index, old):
            rel = f'{name}/{name}_{index:03d}.webp'
            data = archive.extractfile('Runtime/characters/xiaohei/'+rel).read() if old else (FRAMES/rel).read_bytes()
            return Image.open(io.BytesIO(data)).convert('RGBA')
        face = []
        for old in (True, False):
            for name, index in [('idle', 0), ('meow', 12), ('meow', 35)]:
                image = frame(name, index, old).resize((600, 500), Image.Resampling.NEAREST)
                face.append(tile(image, f'{"基线" if old else "本轮"} · {name} / frame {index} · 原WebP解码'))
        save_grid(face, '16-xiaohei-face-evidence.png', 3)
        tail = []
        for old in (True, False):
            for index in (12, 36):
                image = frame('tail', index, old).crop((185, 150, 265, 238)).resize((400, 440), Image.Resampling.NEAREST)
                tail.append(tile(image, f'{"基线：混合双轮廓" if old else "本轮：单次逆映射"} · tail {index}'))
        save_grid(tail, '17-xiaohei-tail-evidence.png', 2)
    print('16-xiaohei-face-evidence.png / 17-xiaohei-tail-evidence.png')


if __name__ == '__main__':
    main()

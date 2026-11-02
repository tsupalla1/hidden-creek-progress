import sys
from PIL import Image, ImageDraw, ImageFont
src, out = sys.argv[1:3]
im = Image.open(src).convert('RGB')
d = ImageDraw.Draw(im)
F = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', 14)
INK = (35, 28, 18)

def beige(cx, cy, r=10):
    px = [im.getpixel((x, y)) for x in range(int(cx-r), int(cx+r)) for y in range(int(cy-r), int(cy+r))]
    px = [p for p in px if sum(p) > 480 and p[0] > p[2] + 40]
    px.sort(key=sum)
    return px[len(px)//2]

def erase(cx, cy, w=8, h=6.5):
    c = beige(cx, cy)
    d.rectangle([cx-w, cy-h, cx+w, cy+h], fill=c)

def write(cx, cy, s):
    b = d.textbbox((0, 0), s, font=F)
    d.text((cx - (b[0]+b[2])/2, cy - (b[1]+b[3])/2), s, font=F, fill=INK)

# Building 47-50 becomes a triplex 47-49
TL, TR, BL, BR = (1353.25, 246.25), (1414.5, 257), (1330, 342), (1395, 352.5)
lerp = lambda a, b, t: (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t)
cx0 = sum(p[0] for p in (TL, TR, BR, BL))/4; cy0 = sum(p[1] for p in (TL, TR, BR, BL))/4
def inset(p, k=4.5):
    dx, dy = cx0-p[0], cy0-p[1]; n = (dx*dx+dy*dy)**.5
    return (p[0]+dx/n*k, p[1]+dy/n*k)
quad = [inset(p) for p in (TL, TR, BR, BL)]
mask = Image.new('L', im.size, 0); ImageDraw.Draw(mask).polygon(quad, fill=255)
c = beige(cx0, cy0, 30)
px = im.load(); mk = mask.load()
for x in range(int(min(p[0] for p in quad)), int(max(p[0] for p in quad))+1):
    for y in range(int(min(p[1] for p in quad)), int(max(p[1] for p in quad))+1):
        if mk[x, y] and sum(px[x, y]) < 3*188:
            px[x, y] = c
for t in (1/3, 2/3):
    L, R = lerp(TL, BL, t), lerp(TR, BR, t)
    d.line([L, R], fill=INK, width=2)
for t, s in ((1/6, '47'), (.5, '48'), (5/6, '49')):
    L, R = lerp(TL, BL, t), lerp(TR, BR, t)
    write(*lerp(L, R, .72), s)

# Renumber the rest of the east side down by one
for (cx, cy), s in [((1328.75, 383.75), '50'), ((1318.25, 405.5), '51'), ((1307.5, 426.25), '52'), ((1296.25, 446.25), '53'),
                     ((1255, 490.75), '54'), ((1255, 515.75), '55'),
                     ((1408.75, 650.75), '56'), ((1431.25, 643.25), '57'), ((1453.75, 635), '58'), ((1476.25, 627), '59')]:
    erase(cx, cy)
    write(cx, cy, s)
im.save(out)

# The triplex's middle unit (48) inherited two back patios from the fourplex drawing; leave it one, centered on the unit.
im = Image.open(out).convert('RGB'); px = im.load()
edge = lambda y: 1353.25 - (y - 246.25) * (23.25 / 95.75)
# copy unit 47's patio (untouched) as the sprite: every non-grass pixel left of the wall
sprite = {(x, y - 260): px[x, y] for x in range(1334, 1352) for y in range(251, 270)
          if x < edge(y) - 1.2 and not (px[x, y][1] > px[x, y][0] + 12)}
for y in range(276, 309):
    for x in range(1327, 1346):
        if x < edge(y) - 1.2:
            px[x, y] = px[x - 16, y]
cy = 294; dx = round(edge(cy) - edge(260))
for (x, oy), c in sprite.items():
    px[x + dx, cy + oy] = c
im.save(out)

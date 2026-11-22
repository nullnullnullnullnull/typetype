"""Generate primary-code stroke guides from a local Make Me a Hanzi checkout.

Usage: python3 scripts/generate-stroke-guides.py /path/to/makemeahanzi
Use --require-full for the release coverage check.
"""
import argparse
from functools import lru_cache
import hashlib
import json
from math import hypot
import runpy
from pathlib import Path
from stroke_fragments import Cut, MiddleBend, Parts, fragment_guides, paths_for, remap, split_stroke

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('--require-full', action='store_true')
args = parser.parse_args()


def read_source(name, digest):
    raw = (args.source / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f'Unexpected source version of {name}')
    return {r['character']: r for line in raw.splitlines() if (r := json.loads(line))}


dictionary = read_source('dictionary.txt', '744bb05d5b0742e9ee35c37791f94d56a173349b3367569e7ca11e510364d203')
graphics = read_source('graphics.txt', 'a28c478b5178e98f67f510b2d52fde08a69dc664654ef43498253b9b764d46ee')
data = json.loads((ROOT / 'public/dictionaries.json').read_text())
codes = {char: seq[0] for char, seq in data['codes'].items()}
# Some embedded components never occur as standalone exercises. Resolve their
# codes using the same source and primary-code precedence as the practice bank.
builder = runpy.run_path(str(ROOT / 'scripts/generate-dictionaries.py'))
source_codes = builder['SOURCES'] / 'cangjie5.txt'
if hashlib.sha256(source_codes.read_bytes()).hexdigest() != builder['MANIFEST']['sha256']['cangjie5.txt']:
    raise ValueError('Unexpected Cangjie source version')
component_codes, _ = builder['character_codes'](dictionary.keys())
# For glyphs absent from the upstream graphics, assemble the two positional
# forms from real left/right compound examples. Preserve each stroke's order
# and vertical coordinates. The result is identified as a schematic in the UI.
composed_examples = {
    '啣': ('喝', '卸*'), '燄': ('臽*', '炎*'), '枴': ('柯', '另*'),
    '嬝': ('娘','裊*'), '媼': '娘温',
    '譁': '計樺', '剴': '凱列', '嬤': ('娘','麼*'), '歿': '列殁', '嚐': ('喝','嘗*'), '歟': ('與*','歇'),
    '偺': '侍糌', '儐': '侍濱', '儔': '侍濤', '嚶': '喝櫻', '囁': '喝攝',
    '塭': '坡温', '壙': '坡擴', '姍': '娘柵', '徬': '徑傍', '懍': '怕凜',
    '搾': '擁榨', '櫂': '柯曜', '櫝': '柯讀', '汙': '海圩', '濬': ('海', '睿*'),
    '灤': ('海', '欒*'), '燐': '燈磷', '獰': '狗擰', '獺': '狗瀨', '玀': '狗囉',
    '琍': '珀俐', '琺': ('珀', '法*'), '琿': '珀輝', '甽': '略訓', '礪': '碗蠣',
    '礫': '碗鑠', '祐': '祕佑', '絃': '紙弦', '綰': '紙棺', '緇': '紙淄',
    '縑': '紙謙', '縲': '紙螺', '繅': '紙缫', '羶': '翔檀', '臏': '腿濱',
    '踫': '路碰', '輜': '輛淄', '轔': '輛磷', '鈐': '鋼吟', '鈸': '鋼拔',
    '銻': '鋼梯', '鍍': '鋼渡', '鍰': '鋼援', '鏃': '鋼嗾', '鏍': '鋼螺',
    '鏑': '鋼滴', '鏗': '鋼慳', '鏘': '鋼蹡', '鏜': '鋼膛', '鏝': '鋼慢',
    '鏤': '鋼樓', '鐃': '鋼曉', '鐳': '鋼擂', '鐸': '鋼擇', '颺': ('風*', '陽'),
    '餽': '飯愧', '驃': '駝漂', '髏': '骼樓', '鰍': '鮮啾', '齣': '齡拘',
    '鉑': '鋼柏', '鉋': '鋼抱', '詁': '計姑', '証': '計征', '訐': '計肝',
    '諍': '計淨', '誥': '計浩', '綑': '紙捆', '綞': '紙捶', '綾': '紙陵',
    '撚': '擁燃', '浬': '海理', '彫': '雕彩', '倣': ('侍', '放*'),
    '梱': '柯捆', '跼': '路局',
}


stacked_examples = {
    '靄': ('雲', '謁*'),
    '犖': ('勞','牛*'),
    '勗': ('冒', '助*'), '崁': ('岩', '坎*'), '慇': ('殷*', '忍'),
    '篛': '竺蒻', '簍': ('竺', '婁*'), '簑': '竺蓑', '籐': '竺藤',
    '菴': '苛罨', '萵': '苛窩', '蓀': ('苛', '孫*'), '蓆': ('苛', '席*'),
    '蘗': ('苛', '檗*'), '靨': ('壓', '面*'), '鷥': ('絲*', '鴛'),
    '鼇': ('熬', '黽*'),
}


def compose_glyph(char, examples, layout):
    children, matches, medians = [], [], []
    for side, example in enumerate(examples):
        whole = example.endswith('*')
        example = example.removesuffix('*')
        row = dictionary[example]
        if not whole and row['decomposition'].startswith(layout) and len(row['decomposition']) == 3:
            child = row['decomposition'][side + 1]
            samples = [s for s, m in zip(graphics[example]['medians'], row['matches']) if m == [side]]
        else:
            child = example
            samples = graphics[example]['medians']
        children.append(child)
        axis = 0 if layout == '⿰' else 1
        coordinates = [p[axis] for stroke in samples for p in stroke]
        if layout == '⿰':
            origin, span = (50, 354) if side == 0 else (450, 518)
        else:
            split = 590 if children[0] in ('艹', '⺮', '山') else 410
            origin, span = (split + 44, 805 - split) if side == 0 else (-15, split + 15)
        low = min(coordinates)
        scale = span / (max(coordinates) - low)
        for stroke in samples:
            projected = []
            for point in stroke:
                copy = list(point)
                copy[axis] = round(origin + scale * (point[axis] - low))
                projected.append(copy)
            medians.append(projected)
            matches.append([side])
    dictionary[char] = {'decomposition': layout + ''.join(children), 'matches': matches}
    strokes = ['M' + ' L'.join(f'{x} {y}' for x,y in stroke) for stroke in medians]
    graphics[char] = {'strokes': strokes, 'medians': medians}
    component_codes[char] = [codes[char]]


for character, examples in composed_examples.items():
    compose_glyph(character, examples, '⿰')
for character, examples in stacked_examples.items():
    compose_glyph(character, examples, '⿱')

# Regional primary spellings require 呂 with a joining stroke or 每 with
# 毋 at the bottom. Fit the attested alternative form inside the original
# component's bounding box. All paths in these diagrams are stroke medians.
variant_glyphs = {}


def replace_component(char, indices, replacement, match):
    medians = graphics[char]['medians']
    original = [p for i in indices for p in medians[i]]
    sample = [p for stroke in replacement for p in stroke]
    axes = []
    for axis in (0, 1):
        a, b = min(p[axis] for p in original), max(p[axis] for p in original)
        lo, hi = min(p[axis] for p in sample), max(p[axis] for p in sample)
        axes.append((a, lo, (b-a)/(hi-lo)))
    fitted = [[[round(a + (p[k]-lo)*scale) for k,(a,lo,scale) in enumerate(axes)]
               for p in stroke] for stroke in replacement]
    start, end = indices[0], indices[-1]+1
    assert indices == list(range(start, end))
    medians[start:end] = fitted
    graphics[char]['strokes'] = ['M' + ' L'.join(f'{x} {y}' for x,y in stroke) for stroke in medians]
    dictionary[char]['matches'][start:end] = [match] * len(fitted)


# Use an enclosing exemplar to keep the surrounding strokes in position.
enclosed_examples = {'邐': ('迂','麗'), '瘍': ('病','昜'), '瘉': ('病','俞'), '迆': ('迂','也'), '迺': ('迂','西'),
                     '闋': ('閣','癸'), '闐': ('閣','真')}
for character, (frame, child) in enclosed_examples.items():
    row = dictionary[frame]
    layout = row['decomposition'][:2]
    dictionary[character] = {'decomposition': layout + child, 'matches': list(row['matches'])}
    graphics[character] = {'medians': list(graphics[frame]['medians'])}
    indices = [i for i,m in enumerate(row['matches']) if m == [1]]
    replace_component(character, indices, graphics[child]['medians'], [1])
    component_codes[character] = [codes[character]]

# The IC family writes two 𣎳 components. Use the detached side strokes
# of 朮, without its dot, so the final 八 can be selected as a unit.
for character in '摩磨糜靡魔麼麾蘑嬤':
    offset = 3 if character in '蘑嬤' else 0
    match = [1] if offset else [0]
    for start in (offset+3,offset+7):
        replace_component(character, list(range(start,start+4)), graphics['朮']['medians'][:4], match)
    variant_glyphs[character] = '依主碼採用麻內兩個十形旁各有分開的撇點的字形'

replace_component('歿', list(range(4,8)), graphics['沒']['medians'][3:], [1])
dictionary['歿']['decomposition'] = '⿰歹𠬛'

# The LAV form has a closed 田 above a sideways 日. The long crossbar
# of the source variant sticks out of 田. Clip it at the sides of the box.
lou = [list(stroke) for stroke in graphics['婁']['medians']]
lou[2] = split_stroke(lou[2], [Cut(0,0,.68), Cut(0,1,.91)], lou)[1]
lou[7] = lou[7][:-1] + [[493,319]]
for character in '婁嘍屢摟數樓簍縷螻褸鏤髏擻藪':
    side = 0 if character in '婁數' else 1
    indices = ([*range(11)] if character == '婁' else
               [i for i,m in enumerate(dictionary[character]['matches']) if m == [side]][:11])
    replace_component(character, indices, lou, [side])
    variant_glyphs[character] = '依主碼採用婁的上橫收在田框內、中豎止於下框底邊的字形'

for character in '莒鋁閭':
    row = dictionary[character]
    side = [1]
    indices = [i for i,m in enumerate(row['matches']) if m == side]
    replace_component(character, indices, graphics['呂']['medians'], side)
    row['decomposition'] = row['decomposition'][:-1] + '呂'
    variant_glyphs[character] = '依主碼採用兩口間有短撇的呂形'

for character in '侮悔晦梅海敏':
    side = [0] if character == '敏' else [1]
    indices = [i for i,m in enumerate(dictionary[character]['matches']) if m == side]
    replace_component(character, indices[2:], graphics['毋']['medians'], side)
    variant_glyphs[character] = '依主碼採用每下從毋的字形'

for character in '径茎':
    row = dictionary[character]
    replace_component(character, list(range(3,8)), graphics['圣']['medians'], [1])
    row['decomposition'] = row['decomposition'][:2] + '圣'
    variant_glyphs[character] = '依主碼採用又在土上的圣形'

for character in '角确觜':
    glyph = graphics[character]
    start = len(glyph['medians']) - 7
    medians = glyph['medians']
    upright = start + 6
    medians[upright] = split_stroke(medians[upright], [Cut(1,start+5,.5)], medians)[0]
    glyph['strokes'] = ['M' + ' L'.join(f'{x} {y}' for x,y in stroke) for stroke in medians]
    variant_glyphs[character] = '依主碼採用角內中豎止於下橫的字形'

# 覃 has both 襾 and 覀 forms. The MB spellings use the open-bottom
# outer frame of 襾. The MW spellings retain the closed 覀 form.
for character in '覃罈蕈譚':
    start = len(graphics[character]['medians']) - 12
    replace_component(character, list(range(start,start+6)), graphics['襾']['medians'],
                      [0] if character == '覃' else [1])
    variant_glyphs[character] = '依主碼採用外框下方開口的襾形'

for character in '呈程逞':
    start = 3 if character == '逞' else len(graphics[character]['medians']) - 4
    replace_component(character, list(range(start,start+4)), graphics['壬']['medians'], [1])
    variant_glyphs[character] = '依主碼採用口下從壬、首筆為短撇的字形'
replace_component('望', list(range(7,11)), graphics['壬']['medians'], [1])
variant_glyphs['望'] = '依主碼採用下方從壬、首筆為短撇的字形'
for character in '邦梆綁':
    offset = 0 if character == '邦' else len(graphics[character]['medians']) - 6
    replace_component(character, [offset], graphics['手']['medians'][:1],
                      [0] if character == '邦' else [1])
    variant_glyphs[character] = '依主碼採用邦左側首筆為短撇的字形'

for character in '條脩':
    replace_component(character, list(range(3,7)), graphics['修']['medians'][3:6], [1])
    variant_glyphs[character] = '依主碼採用右上從夂、首筆為撇的字形'
replace_component('枴', [7,8], graphics['刀']['medians'], [1])
variant_glyphs['枴'] = '依主碼採用右部口下從刀的字形'
replace_component('媼', list(range(3,12)), graphics['溫']['medians'][3:], [1])
# The MJ spelling begins with 工 above the abbreviated ear. Its lower
# horizontal occupies the same place as the ear's first horizontal.
for character, start in [('敢',0), ('憨',0), ('橄',4), ('瞰',5)]:
    replace_component(character, [start,start+1], graphics['工']['medians'], [0] if start==0 else [1])
    variant_glyphs[character] = '依主碼採用敢左上從工的字形'
for character, start in [('处',3), ('咎',3), ('昝',3), ('偺',5)]:
    replace_component(character, [start,start+1], graphics['人']['medians'], [1] if character == '偺' else [0])
    variant_glyphs[character] = '依主碼採用夂右側為人形的字形'
replace_component('亟', [0,1], graphics['極']['medians'][4:6], [0])
variant_glyphs['亟'] = '依主碼採用頂端有獨立一橫的字形'
replace_component('毒', list(range(4,9)), graphics['毋']['medians'], [1])
variant_glyphs['毒'] = '依主碼採用下方從毋的字形'
for character, start in [('尋',0), ('侵',2), ('浸',3)]:
    replace_component(character, list(range(start,start+3)), graphics['聿']['medians'][:3], [1])
    variant_glyphs[character] = '依主碼採用彐形中橫穿出的字形'
replace_component('致', list(range(6,10)), graphics['夂']['medians'], [1])
variant_glyphs['致'] = '依主碼採用右側從夂的字形'
replace_component('緻', list(range(12,16)), graphics['夂']['medians'], [1])
variant_glyphs['緻'] = '依主碼採用致的右側從夂的字形'
for character, start in [('界',5)]:
    replace_component(character,[start,start+1],graphics['八']['medians'],[1])
    variant_glyphs[character] = '依主碼採用田下兩筆分開的八形'
for character, start in [('喝',9), ('褐',11), ('謁',13)]:
    replace_component(character, list(range(start,start+3)), graphics['匕']['medians'], [1])
    variant_glyphs[character] = '依主碼採用曷的勹內從匕的字形'
dictionary['犛'] = {'decomposition': '⿱？⿸厂牛', 'matches': list(dictionary['釐']['matches'])}
graphics['犛'] = {'medians': list(graphics['釐']['medians'])}
replace_component('犛', list(range(11,18)), graphics['牛']['medians'], [1])
component_codes['犛'] = [codes['犛']]
variant_glyphs['犛'] = '依釐的上部與厂的位置配入牛形'
graphics['犖'] = {'medians': list(graphics['榮']['medians'])}
dictionary['犖']['matches'] = list(dictionary['榮']['matches'])
replace_component('犖', list(range(10,14)), graphics['牛']['medians'], [1])
for character, start in [('将',3), ('蒋',6)]:
    replace_component(character,list(range(start,start+3)),graphics['將']['medians'][4:8],[1])
    variant_glyphs[character] = '依主碼採用寸上方有兩內點的月形'
for character, start in [('肇',0), ('牖',4)]:
    replace_component(character,[start],graphics['手']['medians'][:1],[0])
    variant_glyphs[character] = '依主碼採用戶字首筆為短撇的字形'
replace_component('起', [7,8,9], graphics['巳']['medians'], [1])
variant_glyphs['起'] = '依主碼採用右側上口封閉的巳形'
replace_component('捨', [5,6,7], graphics['土']['medians'], [1])
variant_glyphs['捨'] = '依主碼採用舍的中部作土的字形'
replace_component('寒', [10,11], graphics['冫']['medians'], [1])
variant_glyphs['寒'] = '依主碼採用下部一點一提的冫形'
# Use the compressed right-hand 柬 that retains its complete central box.
replace_component('瀾', list(range(11,20)), graphics['闌']['medians'][8:], [1])
variant_glyphs['瀾'] = '採用門內柬的中央方框清晰分開的字形'
dictionary['溼'] = {'decomposition': '⿰氵⿱一⿱𢆶土', 'matches': list(dictionary['濕']['matches'])}
graphics['溼'] = {'medians': list(graphics['濕']['medians'])}
replace_component('溼', list(range(13,17)), graphics['土']['medians'], [1])
# Fit the single upper horizontal at the elevation of the exemplar's 日 top.
graphics['溼']['medians'][3:7] = [[[424,735], [470,730], [710,757], [755,755]]]
dictionary['溼']['matches'][3:7] = [[1]]
graphics['溼']['strokes'] = ['M' + ' L'.join(f'{x} {y}' for x,y in stroke)
                             for stroke in graphics['溼']['medians']]
component_codes['溼'] = [codes['溼']]
variant_glyphs['溼'] = '採用氵旁、一橫下並列雙幺與土的字形'
# The YK enclosure and the MK form of 巩 use a falling stroke crossed by a
# descending dot. The top of the outer hook extends left over the falling stroke.
crossed_hook = [
    [[40,94], [40,66], [36,42], [25,20], [6,3]],
    [[7,93], [76,96], [77,57], [80,25], [87,8], [94,6], [98,21]],
    [[17,63], [35,54], [50,41], [64,28]],
]
for character, start in [('贏',17),('羸',16),('嬴',13),('瀛',16),('恐',3),('築',9),('鞏',3)]:
    replace_component(character, list(range(start,start+3)), crossed_hook, [1])
    variant_glyphs[character] = '依主碼採用內撇與點相交、交叉處取大的字形'
# The IKNF spelling follows 為 with a leading dot and a long falling stroke.
wei = [
    [[29,88],[36,80]], [[59,96],[54,80],[44,61],[29,39],[8,14]],
    [[20,72],[67,78],[62,64]], [[41,59],[72,64],[67,49]],
    [[34,44],[83,51],[90,50],[84,21],[78,9],[69,13]],
    [[22,33],[18,18]], [[33,33],[37,22]], [[45,35],[52,26]], [[59,37],[66,29]],
]
for character, start in [('為',0),('偽',2)]:
    replace_component(character, list(range(start,start+12)), wei, [1])
    variant_glyphs[character] = '依主碼採用首點、長撇與連續折鉤的為形'
# Regional forms represented by the dictionary's primary spellings.
replace_component('毀', list(range(6)), graphics['日']['medians'], [0])
variant_glyphs['毀'] = '依主碼採用左部為圼（日下土）的字形'
replace_component('画', list(range(1,6)), graphics['由']['medians'], [1])
variant_glyphs['画'] = '依主碼採用凵內從由、中豎上出的字形'
for character, start in [('廉',3),('嫌',3),('濂',6)]:
    for i in [start,start+1]:
        replace_component(character, [i], graphics['手']['medians'][:1], [1])
    variant_glyphs[character] = '依主碼採用兼上部為兩個禾頭短撇的字形'
for character, start in [('班',4),('辨',7)]:
    replace_component(character, [start,start+1], graphics['帅']['medians'][:2], [1])
    variant_glyphs[character] = '依主碼採用中間為短直豎與長撇的字形'
replace_component('龜', [0,1], graphics['手']['medians'][:1], [0])
variant_glyphs['龜'] = '依主碼採用頂端為單撇的字形'
replace_component('憲', list(range(3,7)), graphics['丰']['medians'], [1])
variant_glyphs['憲'] = '依主碼採用宀下從丰、中豎穿出第三橫的字形'
replace_component('遥', list(range(4,10)), [
    [[21,95],[75,98]], [[11,68],[87,72]], [[53,93],[51,18]],
    [[15,47],[18,16],[83,19]], [[83,51],[83,17]],
], [1])
variant_glyphs['遥'] = '依主碼採用爫下從干、底部為凵的字形'
replace_component('养', list(range(3,7)), [
    [[32,90],[68,92]], [[51,98],[50,72]], [[20,69],[80,73]],
    [[41,66],[32,46],[8,13]], [[60,68],[73,43],[95,19]],
], [0])
variant_glyphs['养'] = '依主碼採用羊頭與底部兩豎之間為八形的字形'
for character, start in [('函',0),('涵',3)]:
    replace_component(character,[start,start+1], [
        [[8,94],[88,97]], [[62,94],[43,75],[39,68],[54,67],[58,49],[59,24],[54,13],[45,19]],
    ], [1])
    variant_glyphs[character] = '依主碼採用函頂為獨立長橫、橫下接折鉤的字形'
def stacked_medians(top, bottom, split):
    result = []
    for part, low, high in ((top, split+5, 100), (bottom, 0, split)):
        points = [y for stroke in part for x,y in stroke]
        a,b = min(points),max(points)
        result.extend([[[x,low+(high-low)*(y-a)/(b-a)] for x,y in stroke] for stroke in part])
    return result


replace_component('鶴', list(range(10)),
                  stacked_medians(graphics['宀']['medians'], graphics['隹']['medians'], 72), [0])
variant_glyphs['鶴'] = '依主碼採用左從寉（宀下隹）的字形'
for character, start in [('僭',2),('潛',3)]:
    # 兂 with a falling stroke projecting above the top horizontal (J form).
    crossed_ji = [[[18,76],[82,79]], [[23,72],[23,50],[84,53]],
                  [[56,96],[55,75],[49,53],[38,30],[11,4]],
                  [[59,53],[58,20],[62,14],[82,13],[91,17],[94,29]]]
    for offset in (start,start+4):
        replace_component(character,list(range(offset,offset+4)),crossed_ji,[1])
    variant_glyphs[character] = '依主碼採用兂的長撇穿出頂橫的字形'

for character, center in [('漢',12),('嘆',12),('謹',16)]:
    # The box with an internal vertical is the same A auxiliary found in 巴.
    # Trim the central stroke at its junction with the box's top edge.
    medians = graphics[character]['medians']
    border = medians[center-4]
    x = medians[center][2][0]
    junction = next(round(y+(v-y)*(x-u)/(w-u)) for (u,y),(w,v) in zip(border,border[1:])
                    if u <= x < w)
    tail = [point for point in medians[center] if point[1] < junction-15]
    medians[center] = [[x,junction]] + tail
    graphics[character]['strokes'] = ['M'+' L'.join(f'{x} {y}' for x,y in p) for p in medians]
    variant_glyphs[character] = '依主碼採用中豎自框上緣起筆的字形，框及內豎取日'

for character, start in [('開',8),('荆',3)]:
    twin_gan = [[[6,86],[42,89]], [[2,59],[45,62]], [[25,87],[26,16]],
                [[55,89],[93,91]], [[51,62],[98,65]], [[75,91],[76,8]]]
    replace_component(character,list(range(start,start+4)),twin_gan,[1])
    variant_glyphs[character] = '依主碼採用並列兩個干的幵形'
for start in [5,9]:
    ten_legs = [[[10,71],[89,75]], [[50,95],[51,9]],
                [[29,53],[24,36],[12,18]], [[73,56],[72,25],[75,19],[88,20],[93,28]]]
    replace_component('痲',list(range(start,start+4)),ten_legs,[1])
variant_glyphs['痲'] = '依主碼採用兩個十形各配分開兩腳的𣏟形'
# The projecting vertical in 衷 crosses both the long horizontal and the box.
replace_component('衷', list(range(6)), [
    [[8,75],[90,78]], [[22,58],[26,36]], [[25,58],[75,60],[72,37]],
    [[26,36],[73,39]], [[48,96],[50,71],[50,24]],
], [0])
variant_glyphs['衷'] = '依主碼採用上方直豎穿過長橫與口框的字形'
# Keep the diagonal joined across the third horizontal in the QK form of 麦.
glyph = graphics['麦']['medians']
glyph[2][-1] = [467,449]
glyph[4] = [[467,449]] + glyph[4]
graphics['麦']['strokes'] = ['M'+' L'.join(f'{x} {y}' for x,y in p) for p in glyph]
variant_glyphs['麦'] = '依主碼採用上部中筆連撇、與第三橫相交的字形'
replace_component('滌', list(range(10,14)), graphics['木']['medians'], [1])
variant_glyphs['滌'] = '依主碼採用條下為木、撇捺與中筆相接的字形'
replace_component('釉', [0,1,2], graphics['采']['medians'][:4], [0])
variant_glyphs['釉'] = '依主碼採用采字旁、上部為爫的字形'
replace_component('雨', [3,4,5,6,7], graphics['犀']['medians'][3:8], [1])
variant_glyphs['雨'] = '依主碼採用中豎兩側作點提、撇點的水形'
for character in '弱溺篛':
    offset = len(graphics[character]['medians']) - 10
    for start in (offset+3,offset+8):
        replace_component(character, list(range(start,start+2)), graphics['彡']['medians'][:2],
                          [1] if offset else [int(start > 3),1])
    variant_glyphs[character] = '依主碼採用兩個弓形內各寫兩撇的字形'

for character in '忝添舔':
    start = len(graphics[character]['medians']) - 8
    replace_component(character, list(range(start,start+4)), graphics['夭']['medians'],
                      [0] if character == '忝' else [1])
    variant_glyphs[character] = '依主碼採用心上從夭的字形'

# This positional 州 has a right-falling dot. The H initial uses the
# left-falling stroke found in standalone 州.
replace_component('酬', list(range(7,13)), graphics['州']['medians'], [1])
variant_glyphs['酬'] = '依主碼採用州左邊首筆為撇的字形'
for character in '奏湊揍凑':
    start = len(graphics[character]['medians']) - 4
    replace_component(character, list(range(start,start+4)), graphics['夭']['medians'], [1])
    variant_glyphs[character] = '依主碼採用奏下從夭、首筆為短撇的字形'
for character in '善繕膳鱔':
    start = len(graphics[character]['medians']) - 12
    earth = graphics['土']['medians']
    replace_component(character, list(range(start+3,start+6)), [earth[0],earth[2],earth[1]],
                      [0] if character == '善' else [1])
    variant_glyphs[character] = '依主碼採用善字上部從土的字形'

replace_component('電', list(range(8,13)), graphics['电']['medians'], [1])
variant_glyphs['電'] = '依主碼採用下方中豎從田框上緣伸出的字形'

replace_component('賴', [7,8], graphics['⺈']['medians'], [1])
variant_glyphs['賴'] = '依主碼採用負字上方的刀頭形'

# A component may have a different shape from the standalone character.
auxiliary = {
    '乙': 'N', '廾': 'T', '屮': 'U', '⺗': 'P', '⺀': 'Y', '亻': 'O', '氵': 'E', '扌': 'Q', '艹': 'T', '忄': 'P', '囗': 'W',
    '宀': 'J', '釒': 'C', '灬': 'F', '冖': 'B', '冂': 'B', '勹': 'P',
    '丷': 'C', '㇒': 'H', '丿': 'H', '丶': 'I', '乀': 'O', '厶': 'I',
    '疒': 'K', '衤': 'L', '礻': 'I', '辶': 'Y', '癶': 'N', '罒': 'W',
    '⺼': 'B', '⺮': 'H', '亠': 'Y', '广': 'I', '厂': 'M', '丨': 'L',
    '夂': 'HE', '彳': 'HO', '匚': 'S', '八': 'C', '爫': 'B', '⺈': 'N',
    '爿': 'VM', '阜': 'HRJ', '凵': 'U', '乂': 'K', '隹': 'OG', '犭': 'KH',
    '⺊': 'Y', '⺌': 'F', '⺍': 'F', '龶': 'QM', '阝': 'NL', '又': 'E', '儿': 'HU', '士': 'G', '小': 'F', '刂': 'LN', '冫': 'IM',
    '讠': 'INV', '弋': 'I', '攵': 'OK', '饣': 'NV', '纟': 'VM', '糹': 'VF', '钅': 'OP',
}
# Stroke-order assignments for interleaved shapes. Digits index the primary code.
annotated = {'國': ('WIRM', '00122231110', ['外框「囗」', '內部的「戈」', '戈內的「口」', '口下的一橫']),
             '或': ('IRM', '01112000', ['外側的「戈」', '戈內的「口」', '口下的一橫'])}
# Assign each physical stroke to its root, in this particular glyph's stroke order.
basic = {
    '业': ('TC', '00110'), '式': ('IPM', '122210'),
    '豕': ('MSHO', '0011233'), '豖': ('MSKO', '00112233'),
    '㐬': ('YIHLU', '0011234'),
    '帚': ('SMBLB', '01022443'), '舛': ('NIQ', '001222'),
    '彑': ('VNM', '012'),
    '兼': ('CMXC', '0012222233'),
    '士': ('JM', '001'), '曲': ('TW', '110001'), '典': ('TBC', '11000022'),
    '四': ('WC', '00110'), '屰': ('TU', '000111'), '肉': ('OBO', '110022'),
    '桼': ('DOE', '00001122222'), '刅': ('SHC', '0122'), '表': ('QMV', '00012222'),
    '罔': ('BTYV', '00111223'), '臾': ('HXO', '01111122'),
    '並': ('TTC', '00011221'),
    '长': ('PO', '1001'), '局': ('SSR', '0001222'),
    '毌': ('WJ', '0011'), '達': ('YGTQ', '111222333000'),
    '啚': ('RJWR', '00011223332'), '产': ('YTH', '001112'),
    '盡': ('LMFBT', '00001222233444'),
    '盖': ('TGBT', '00011122333'), '朮': ('IJC', '11220'),
    '买': ('NYK', '011222'), '卫': ('SLM', '012'), '之': ('INO', '012'),
    '丧': ('GCV', '00110222'), '罕': ('BCMJ', '0011233'), '弄': ('MGT', '0111222'),
    '第': ('HNLH', '00000011123'), '糢': ('FDTAK', '00111122223333444'),
    '在': ('KLG', '001222'), '存': ('KLND', '001233'),
    '沿': ('ECR', '00011222'), '鉛': ('CCR', '0000000011222'),
    '归': ('ILSM', '01232'),
    '隋': ('NLKMB', '01223334444'), '哉': ('JIR', '001222111'),
    '來': ('DOO', '01122000'), '巫': ('MOO', '0011220'),
    '卖': ('JNYK', '00122333'), '头': ('YK', '00111'),
    '皋': ('HAKJ', '0111122233'), '展': ('STV', '0001111222'),
    '南': ('JBTJ', '001122233'), '岡': ('BTU', '00111222'),
    '孝': ('JKND', '0011233'), '厷': ('KI', '0011'), '冊': ('BT', '00111'),
    '丵': ('TCTJ', '0011022233'), '彔': ('VNME', '01233333'),
    '能': ('IBPP', '0011112233'), '原': ('MHAF', '0012222333'),
    '祭': ('BOMMF', '00001123444'), '戊': ('IH', '01000'),
    '老': ('JKP', '001122'),
    '竟': ('YTAHU', '00111222234'), '是': ('AMYO', '000012233'),
    '暴': ('ATCE', '000011112233333'),
    '必': ('PH', '00010'), '坐': ('OOG', '0011222'), '切': ('PSH', '0012'),
    '杀': ('KD', '001111'), '麻': ('IDD', '00011112222'),
    '义': ('IK', '011'), '冉': ('GB', '11000'), '冘': ('LBU', '1102'),
    '成': ('IHS', '012000'), '夷': ('KN', '011100'), '唐': ('ILR', '0001111222'),
    '录': ('NMME', '01233333'),
    '齊': ('YX', '00111111111111'),
    '瓦': ('MVNI', '0123'), '斥': ('HMY', '00122'),
    '肅': ('LX', '0000111111111'), '戎': ('IJ', '011000'), '㐱': ('OHHH', '00123'),
    '咸': ('IHMR', '012333000'),
    '失': ('HQO', '01112'), '代': ('OIP', '00221'),
    '乇': ('HP', '011'), '定': ('JMYO', '00012233'),
    '布': ('KLB', '00221'), '节': ('TSL', '00012'), '年': ('OQ', '001111'),
    '爪': ('HLO', '0012'), '互': ('MVNM', '0123'),
    '而': ('MBLL', '001123'), '朿': ('DB', '011000'),
    '匀': ('PIM', '0012'), '卂': ('NJ', '011'), '奂': ('NBK', '0011222'),
    '尢': ('KU', '001'), '骨': ('BBB', '000112222'),
    '巨': ('SS', '0110'), '疋': ('NYO', '01122'),
    '畏': ('WMV', '000001222'), '刍': ('NSM', '00112'),
    '曷': ('APVO', '000011332'), '喿': ('RRRD', '0001112223333'),
    '妾': ('YTV', '00111222'), '喬': ('HKRBR', '011122233444'),
    '韦': ('QS', '0010'), '夹': ('KT', '011100'), '农': ('HBV', '110222'),
    '桑': ('EEED', '0011223333'), '亙': ('MBM', '011112'),
    '臣': ('SLSL', '012230'), '直': ('JBMM', '00111123'), '垂': ('HJTM', '01122223'),
    '向': ('HBR', '011222'), '后': ('HMR', '001222'), '含': ('OINR', '0012333'),
    '亲': ('YTD', '001112222'), '幸': ('GTJ', '00011122'), '前': ('TBLN', '000111123'),
    '希': ('KKLB', '0011332'),
    '有': ('KB', '001111'), '尹': ('SK', '0101'), '夅': ('HEQ', '011222'),
    '赤': ('GLNC', '0001233'), '乡': ('VVH', '012'), '卬': ('HVSL', '0123'),
    '臽': ('HSHX', '01233333'),
    '長': ('SMV', '00001222'),
    '乔': ('HKLL', '011123'), '夭': ('HK', '0111'),
    '其': ('TMMC', '00012033'), '友': ('KE', '0011'), '喜': ('GRTR', '000111222333'),
    '兰': ('TMM', '00012'), '两': ('MOOB', '0331122'), '伞': ('OFJ', '001122'),
    '五': ('MDM', '0112'), '入': ('OH', '10'), '內': ('OB', '1100'), '丑': ('NG', '0111'),
    '万': ('MS', '011'), '冬': ('HEIM', '01123'),
    '瓜': ('HVIO', '00123'),
    '甫': ('IJB', '1222210'), '爭': ('BSD', '00001212'), '争': ('NSD', '001212'),
    '屯': ('PU', '0110'), '韋': ('DMRQ', '001222333'),
    '尞': ('KCAF', '000112222333'), '弟': ('CNLH', '0011123'),
    '齐': ('YKLL', '001123'), '壴': ('GRT', '000111222'), '歺': ('YNI', '00112'),
    '母': ('WYI', '00112'), '每': ('OWYI', '0011223'), '毋': ('WJ', '0011'),
    '尺': ('SO', '0001'), '丩': ('VL', '01'), '龙': ('IKP', '11220'),
    '粦': ('FDNIQ', '001111223444'), '豸': ('BSHH', '0000123'),
    '司': ('SMR', '01222'), '化': ('OP', '0011'), '余': ('OMD', '0012222'),
    '并': ('TT', '000111'), '次': ('IMNO', '012233'), '秋': ('HDF', '011112222'),
    '丬': ('LIM', '120'), '巛': ('VVV', '012'),
    '亼': ('OM', '001'), '㔾': ('SU', '01'), '覀': ('MLLW', '033123'),
    '半': ('FQ', '00111'), '丹': ('BY', '0011'), '夾': ('KOO', '0001122'),
    '丢': ('HGI', '011122'), '乏': ('HINO', '0123'), '亘': ('MAM', '011112'),
    '佥': ('OMFM', '0012223'), '侖': ('OMBT', '00122333'),
    '厄': ('MSU', '0012'), '危': ('NMSU', '001123'), '卤': ('YWK', '0011221'),
    '刃': ('SHH', '012'), '夸': ('KMMS', '000123'), '印': ('HPSL', '01123'),
    '章': ('YTAJ', '00111222233'), '卓': ('YAJ', '00111122'),
    '玉': ('MGI', '01112'), '平': ('MFJ', '01122'), '旨': ('PA', '001111'),
    '名': ('NIR', '001222'), '汞': ('ME', '0001111'), '灰': ('KF', '001111'),
    '丘': ('OM', '00001'), '乒': ('OMH', '000012'), '乓': ('OMI', '000012'),
    '于': ('MD', '011'),
    '區': ('SRRR', '01112223330'), '亦': ('YLNC', '001233'), '卩': ('SL', '01'),
    '辰': ('MMMV', '0012333'), '右': ('KR', '00111'), '生': ('HQM', '01112'),
    '匕': ('UH', '10'), '己': ('SU', '001'), '已': ('SU', '001'),
    '饣': ('NV', '001'), '仓': ('OSU', '0012'), '弗': ('LLN', '22201'),
    '身': ('HXH', '0111112'), '袁': ('GRHV', '0001112333'), '尚': ('FBR', '00011222'),
    '乎': ('HFD', '01122'), '才': ('DH', '001'),
    '皿': ('BT', '00111'), '血': ('HBT', '011222'), '习': ('SIM', '012'),
    '予': ('NINN', '0123'), '甬': ('NIBQ', '0122333'), '以': ('VIO', '0122'),
    '仑': ('OP', '0011'), '百': ('MA', '001111'), '贞': ('YBO', '001122'),
    '系': ('HVIF', '0112333'), '尤': ('IKU', '1120'), '亥': ('YVHO', '001233'),
    '酉': ('MCWM', '0221132'), '西': ('MCW', '022112'), '甘': ('TM', '00010'),
    '氏': ('HVP', '0122'), '育': ('YIB', '00112222'), '叵': ('SR', '01110'),
    '刘': ('YKLN', '001123'), '开': ('MT', '0111'), '升': ('HT', '0111'),
    '父': ('CK', '0011'), '左': ('KM', '00111'), '册': ('BBM', '00112'),
    '卒': ('YOOJ', '00112233'), '元': ('MMU', '0112'), '兀': ('MU', '001'),
    '巾': ('LB', '110'), '页': ('MBO', '001122'), '用': ('BQ', '00111'),
    '孑': ('NNM', '012'), '牙': ('MVDH', '0123'), '午': ('OJ', '0011'),
    '臼': ('HX', '011111'), '勿': ('PHH', '0012'), '皮': ('DHE', '01022'),
    '舟': ('HBYI', '011223'), '气': ('OMN', '0012'), '者': ('JKA', '00112222'),
    '魚': ('NWF', '00111112222'), '鱼': ('NWM', '00111112'), '幺': ('VI', '001'),
    '彐': ('NMM', '012'), '衣': ('YHV', '001222'),
    '虫': ('LMI', '000012'), '耳': ('SJ', '001001'),
    '阝': ('NL', '01'), '足': ('RYO', '0001122'), '子': ('ND', '011'),
    '止': ('YLM', '0012'), '正': ('MYLM', '01123'), '羊': ('TQ', '000111'),
    '夕': ('NI', '001'), '青': ('QMB', '00012222'), '龶': ('QM', '0001'),
    '舌': ('HJR', '011222'), '肖': ('FB', '0001111'), '共': ('TC', '000011'),
    '豆': ('MRT', '0111222'), '可': ('MNR', '02221'), '它': ('JP', '00011'),
    '矢': ('OK', '00111'), '区': ('SK', '0110'),
    '斤': ('HML', '0012'), '反': ('HE', '0011'),
    '犬': ('IK', '1110'), '刀': ('SH', '01'), '叉': ('EI', '001'),
    '同': ('BMR', '001222'), '见': ('BHU', '0012'), '儿': ('HU', '01'),
    '今': ('OIN', '0012'), '令': ('OINI', '00123'), '支': ('JE', '0011'),
    '冫': ('IM', '01'), '刂': ('LN', '01'), '门': ('LIS', '102'),
    '兄': ('RHU', '00012'), '交': ('YCK', '001122'), '走': ('GYO', '0001122'),
    '厂': ('MH', '01'), '广': ('YH', '001'), '小': ('NC', '011'),
    '少': ('FH', '0001'), '亡': ('YV', '001'), '亢': ('YHN', '0012'),
    '介': ('OLL', '0012'), '斗': ('YJ', '0011'), '凡': ('HNI', '012'),
    '几': ('HN', '01'), '内': ('OB', '1100'), '示': ('MMF', '01222'),
    '允': ('IHU', '0012'), '兌': ('CRHU', '0011123'), '兑': ('CRHU', '0011123'),
    '先': ('HGHU', '011123'), '户': ('IS', '0111'), '合': ('OMR', '001222'),
    '全': ('OMG', '001222'), '了': ('NN', '01'), '句': ('PR', '00111'),
    '勾': ('PI', '0011'), '旬': ('PA', '001111'), '吉': ('GR', '000111'),
    '告': ('HGR', '0111222'), '刁': ('SM', '01'), '歹': ('MNI', '0112'),
    '凶': ('UK', '1100'), '尖': ('FK', '000111'), '尘': ('FG', '000111'),
    '八': ('HO', '01'), '六': ('YC', '0011'), '只': ('RC', '00011'),
    '困': ('WD', '0011110'), '因': ('WK', '001110'), '回': ('WR', '001110'),
    '吐': ('RG', '000111'), '叶': ('RJ', '00011'),
    '乍': ('OS', '00111'),
    '穴': ('JC', '00011'),
    '工': ('MLM', '012'),
    '丁': ('MN', '01'), '寸': ('DI', '001'), '二': ('MM', '01'), '三': ('MMM', '012'),
    '千': ('HJ', '011'), '干': ('MJ', '011'), '川': ('LLL', '012'), '上': ('YM', '001'),
    '牛': ('HQ', '0111'), '欠': ('NO', '0011'), '乞': ('ON', '001'),
    '太': ('KI', '0001'), '去': ('GI', '00011'),
    '术': ('ID', '11110'), '本': ('DM', '00001'), '天': ('MK', '0111'),
    '公': ('CI', '0011'), '方': ('YHS', '0021'),
    '犭': ('KH', '001'), '彳': ('HO', '011'), '夂': ('HE', '011'),
    '王': ('MG', '0111'), '古': ('JR', '00111'), '白': ('HA', '01111'),
    '禾': ('HD', '01111'), '米': ('FD', '001111'), '言': ('YMMR', '0012333'),
    '石': ('MR', '00111'), '文': ('YK', '0011'), '占': ('YR', '00111'),
    '云': ('MMI', '0122'), '京': ('YRF', '00111222'), '立': ('YT', '00111'),
    '不': ('MF', '0111'), '主': ('YG', '00111'), '旦': ('AM', '00001'),
    '昌': ('AA', '00001111'), '早': ('AJ', '000011'), '比': ('PP', '0011'),
    '攵': ('OK', '0011'), '纟': ('VM', '001'),
    '糹': ('VF', '000111'), '钅': ('OP', '00111'),
}
for char, (seq, order) in basic.items():
    annotated[char] = seq, order, [
        '第' + '、'.join(str(j+1) for j, digit in enumerate(order) if int(digit) == i) + '筆'
        for i in range(len(seq))]
positions = {'⿰': ('左', '右'), '⿱': ('上', '下'), '⿴': ('外', '內'), '⿵': ('外', '內'), '⿸': ('外', '內'),
             '⿺': ('外', '內'), '⿶': ('外', '內'), '⿹': ('外', '內'), '⿷': ('外', '內'), '⿳': ('上', '中', '下'),
             '⿲': ('左', '中', '右')}


def similar_order(original, embedded):
    # Reject changed stroke order and substantial shape changes. Compare each
    # stroke's endpoints in component-local coordinates after scaling both axes.
    def endpoints(strokes):
        points = [p for stroke in strokes for p in stroke]
        lo = [min(p[i] for p in points) for i in range(2)]
        span = [max(p[i] for p in points) - lo[i] for i in range(2)]
        return [(p[i] - lo[i]) / max(1, span[i]) for stroke in strokes
                for p in (stroke[0], stroke[-1]) for i in range(2)]
    if not original or len(original) != len(embedded):
        return False
    left, right = endpoints(original), endpoints(embedded)
    if max(abs(a-b) for a, b in zip(left, right)) < 0.22:
        return True

    # A condensed radical can move one endpoint beyond this box. Compare the
    # full trace at equal arc-length intervals and require a distinct nearest
    # stroke in both directions before transferring any stroke indices.
    def traces(strokes):
        points = [p for stroke in strokes for p in stroke]
        xmin, ymin = map(min, zip(*points))
        xmax, ymax = map(max, zip(*points))
        result = []
        for stroke in strokes:
            norm = [((x-xmin)/max(1, xmax-xmin), (y-ymin)/max(1, ymax-ymin)) for x, y in stroke]
            lengths = [hypot(x-u, y-v) for (x,y), (u,v) in zip(norm, norm[1:])]
            total = sum(lengths)
            samples = [norm[0]]
            index, walked = 0, 0
            for fraction in (0.25, 0.5, 0.75):
                while index < len(lengths)-1 and walked + lengths[index] < fraction * total:
                    walked += lengths[index]
                    index += 1
                if not lengths or total == 0:
                    samples.append(norm[0])
                    continue
                t = (fraction * total-walked)/max(lengths[index], 1e-10)
                samples.append(tuple(a+t*(b-a) for a,b in zip(norm[index], norm[index+1])))
            result.append(samples + [norm[-1]])
        return result

    a, b = traces(original), traces(embedded)
    distances = [[sum(hypot(x-u, y-v) for (x,y),(u,v) in zip(p,q))/len(p)
                  for q in b] for p in a]
    for i, row in enumerate(distances):
        if row[i] > 0.15 or any(min(value, distances[j][i]) < row[i]+0.04
                                for j, value in enumerate(row) if i != j):
            return False
    return True


# Compact left-hand forms checked against the full-sized component. Reuse a
# reference only when every stroke still corresponds in the parent glyph.
compact_examples = {'去': '却', '谷': '卻', '交': '郊', '丘': '邱', '令': '邻', '咅': '部',
                    '言': '訂', '禾': '利', '穴': '究', '米': '料', '车': '斩', '牛': '牡',
                    '走': '赴', '虍': '虏', '鹿': '麒', '身': '射', '矢': '知', '羽': '翌',
                    '舌': '敌', '余': '斜', '果': '顆', '豆': '豌', '巠': '勁', '半': '判',
                    '佥': '剑', '辰': '唇', '番': '翻', '尚': '常', '羊': '翔', '分': '岔', '今': '念', '音': '意', '莫': '墓'}


# Some components have a second condensed form above or beside another
# component. The index identifies its position in the example's IDS.
positional_examples = {
    '鬼': ('魁', 0), '僉': ('劍', 0), '鹿': ('塵', 0), '沙': ('娑', 0), '亦': ('峦', 0), '夗': ('怨', 0),
    '立': ('靖', 0), '音': ('韻', 0), '兴': ('举', 0), '冫': ('冰', 0),
    '巢': ('剿', 0), '夸': ('匏', 0), '享': ('孰', 0), '巳': ('导', 0),
    '奴': ('弩', 0), '耳': ('恥', 0), '方': ('放', 0), '連': ('鏈', 1),
    '白': ('皓', 0), '迷': ('謎', 1), '丑': ('紐', 1), '夫': ('規', 0),
    '臤': ('賢', 0), '豸': ('貂', 0), '化': ('貨', 0), '光': ('輝', 0),
    '公': ('頌', 0), '元': ('頑', 0), '分': ('頒', 0), '屯': ('頓', 0),
    '馬': ('馳', 0), '加': ('駕', 0), '合': ('鴿', 0),
}


# Additional reference glyphs, grouped by which immediate IDS child supplies
# the sample. Keep multiple samples for components used in different positions.
additional_examples = {}
for side, parents in enumerate((
    '贛鄹舉譽勢贊勤麩麴鼴黏鴻齟循裘祕輩剌辣鼾饜壓翱離恭救顰剝愿豁頻賁匙劑號豬隸鵪耕啟瓶顛魏刺冀舒釋頷鷂计丟乳俎兢剂創动勉勛哥坠墅娶孫尬彩彪患戮改数歙歪毡牠琴瓢甥甦皴盞競翅翘翹聂覦親谿资鄧锋靜響頹颓额馥鷓鸵鹊',
    '鑽酩懶製電諺雛再蝸卷誊豢繽訴魁搖牴眾萄静封崢最氮湧爷璧箋緩舍處輒迟述退鋪閔隕雀韌韓頭飯',
)):
    for parent in parents:
        child = dictionary[parent]['decomposition'][side + 1]
        additional_examples.setdefault(child, []).append((parent, side))


def component_matches(child, strokes):
    if similar_order(graphics[child]['medians'], strokes):
        return True
    examples = []
    if child in compact_examples:
        examples.append((compact_examples[child], 0))
    if child in positional_examples:
        examples.append(positional_examples[child])
    examples.extend(additional_examples.get(child, ()))
    for example, side in examples:
        reference = [s for s, path in zip(graphics[example]['medians'], dictionary[example]['matches'])
                     if path == [side]]
        if similar_order(reference, strokes):
            return True
    return False


def nested_parts(ids):
    """Index each leaf by the exact path used in the upstream matches array."""
    symbols = iter(ids)
    leaves = []

    def visit(path, location):
        symbol = next(symbols)
        if symbol not in positions:
            if symbol == '？' or 0x2FF0 <= ord(symbol) <= 0x2FFF:
                raise ValueError
            leaves.append((path, location + '「' + symbol + '」', symbol))
            return
        for i, side in enumerate(positions[symbol]):
            visit(path + [i], location + side + '部')

    try:
        visit([], '')
        if next(symbols, None) is None:
            return leaves
    except (ValueError, StopIteration):
        pass
    return []


# Kept root indices for individual IDS leaves when a compound takes a shortened
# head, secondary head or secondary body. An asterisk keeps the complete leaf.
nested_selections = {
    '澈': '* 02 1', '撤': '* 02 1', '辙': '* 02 1', '轍': '02 02 1',
    '葬': '* 02 *', '辫': '02 * 2', '辯': '02 03 2',
    '鼇': '0 1 *',
    '贛': '03 * 3', '赣': '03 * 2',
    '嚣': '* * 02 - *', '囂': '* * 03 - *', '聽': '0 1 * * - *',
    '類': '* 1 013', '輦': '0 1 *', '辇': '0 1 *', '替': '0 1 *',
    '器': '* * * - *', '屐': '* * 1', '屜': '* * 1', '瓣': '02 03 2', '萨': '* * 2', '辦': '02 * 2', '辮': '02 02 2',
    '彞': '02 0 2 *', '蚩': '* * 02', '雍': '* 02 1',
    '梁': '* 2 *', '粱': '* 2 *',
    '嗣': '* 0 *', '彙': '02 * *', '搀': '* 03 *', '舜': '* * 02', '蠡': '03 02 2',
    '燮': '* - * *', '疆': '* * 013', '遂': '* * 03',
    '寐': '* * 1', '丽': '* * * * -', '傻': '* 0 * 1', '寅': '* * 0 *', '寧': '* * 0 1',
    '寶': '* 04 2', '彥': '* * 02', '徵': '* * - 1 1', '戲': '0 2 *',
    '拋': '* * 1', '斑': '* * 1', '晉': '* * * - *', '煞': '0 1 *',
    '產': '* * 02', '睿': '* * * * - 1', '穀': '* - - 1 *',
    '聶': '* * 1', '蠢': '02 02 2', '餐': '0 * 013', '黃': '* * 0 *',
    '商': '* * 02', '報': '02 * *', '塌': '* * 04', '嵌': '* * 1',
    '幹': '02 * *', '慍': '* * 1', '戛': '* 2 *', '榻': '* * 04',
    '櫃': '* * 04', '殿': '* 1 *', '毫': '* * * 2', '涩': '* 02 2',
    '满': '* * 03', '珮': '* * 2', '瑩': '* * 02', '瘪': '* 02 1',
    '瞒': '* * 03', '矗': '03 03 3', '禀': '* * 2', '稟': '* * 1',
    '稽': '* 02 1', '縈': '* * 02', '臺': '* * 2', '薛': '* * 2 2',
    '阜': '* 2 *', '鹰': '* 02 3',
    '劦': '* * 1', '磊': '* * 1', '蟲': '02 02 2', '轟': '02 02 2',

    '刷': '* 1 *', '壹': '* * 02', '契': '0 1 *', '奪': '* * 1',
    '婴': '0 1 *', '尉': '* 2 *', '帥': '* 2 *', '師': '* 2 *',
    '強': '* * 02', '後': '* * 1', '得': '* * 1', '德': '* * * - *',
    '應': '* 02 *', '抛': '* * 1', '款': '* 2 *', '溫': '* * 1',
    '氳': '02 * 1', '狱': '* 02 1', '珍': '* * 02', '瑣': '* * 02',
    '盜': '* 1 *', '範': '* 02 1', '簸': '* 03 2', '絕': '* * 1',
    '莹': '* * 02', '莺': '* * 03', '萤': '* * 02', '螢': '* * * 02',
    '辩': '02 02 2', '追': '* * 02', '遣': '* * * 2', '鎖': '* * 02',
    '骂': '* * 013', '鳳': '* * 13',
}


def resolve_nested(char, code, ids, matches):
    labels, letters, omissions = [], [], []
    assignments = [None] * len(matches)
    leaves = nested_parts(ids)
    selections = nested_selections.get(char, '').split()
    if selections and len(selections) != len(leaves):
        return
    for index, (path, part, child) in enumerate(leaves):
        if child == char:
            return
        result = resolve(child)
        if not result:
            return
        keys, names, owners, reasons = result
        indices = [i for i, m in enumerate(matches) if m == path]
        if not indices or len(indices) != len(owners):
            return
        strokes = [graphics[char]['medians'][i] for i in indices]
        if len(keys) > 1 and not component_matches(child, strokes):
            return
        choice = selections[index] if selections else '*'
        keep = list(range(len(keys))) if choice == '*' else [int(digit) for digit in choice if digit != '-']
        if any(k >= len(keys) for k in keep):
            return
        if len(keep) < len(keys):
            reason = ('依本字主碼保留' + '、'.join(f'第{k+1}碼 {keys[k]}' for k in keep)
                      if keep else '位於中間，整個部件省略')
            if char == '丽' and not keep:
                reason = '右側冂框已作尾碼，框內的點依包含省略略去'
            omissions.append(part + '在合體字中省碼，' + reason + '。')
        keys_by_index = {k: len(labels) + j for j, k in enumerate(keep)}
        for i, owner in zip(indices, owners):
            assignments[i] = remap(owner, keys_by_index, indices)
        letters.extend(keys[k] for k in keep)
        labels.extend(part if len(keys) == 1 else part + '的' + names[k] for k in keep)
        omissions.extend(part + '：' + reason for reason in reasons)
    if ''.join(letters) == code and None not in assignments:
        return code, labels, assignments, omissions


# For these compound bodies the last enclosure supplies the last key.
# Keep its interior visible in grey, even when the component is shortened again.
enclosed_forms = {
    '兩': ('MLB', ['頂端長橫', '中央長豎', '下方冂框'], [0,2,2,1,-1,-1,-1,-1],
          '以冂框收尾，框內的兩個人形依包含省略略去。'),
    '㒼': ('TLB', ['頂端廿形', '中央長豎', '下方冂框'], [0,0,0,0,2,2,1,-1,-1,-1,-1],
          '以冂框收尾，框內的兩個人形依包含省略略去。'),
    '瓦': ('MVN', ['頂橫', '左側豎提', '右側折彎鉤'], [0,1,2,-1],
          '瓦作字身取外側的折彎鉤作尾碼，內點依包含省略略去。'),
    '禺': ('WLB', ['上部田形', '從田底伸向下框的豎段', '下方冂框'],
          [0,0,0,0,2,2,Parts((0,1,-1),(Cut(1,3,.5),Cut(1,5,.94))),-1,-1],
          '下方冂框作尾碼，中豎在框內的部分與框內的提、點依包含省略略去。'),
    '罗': ('WLN', ['罒的外框', '框內右豎', '夕形的外側兩筆'],
          [0,0,-1,1,0,2,2,-1], '罒取首尾，框內左豎省略。夕形取外側作尾碼，內點省略。'),
    '啇': ('YCB', ['頂部點橫', '兩個相向的點', '下方冂框'],
          [0,0,1,1,2,2,-1,-1,-1,-1,-1], '尾碼取冂框，框內古形依包含省略略去。'),
    '闌': ('ANW', ['門左上的日形', '門右側的豎鉤', '柬的方框'],
          fragment_guides['門'][2] + [-1,2,2,-1,-1,2,-1,-1,-1],
          '門取首尾，左豎下段及右上部分省略。柬只取包住兩點的方框，木形和框內筆畫省略。'),
    '曷': ('APV', ['上方日形', '下方勹形', '勹內的折筆'],
          [0,0,0,0,1,1,-1,-1,2], '尾碼取包住人形的折筆，折內的人形省略。'),
    '喬': ('HKRB', ['頂撇', '上方大形', '大形下的口', '底部冂框'],
          [0,1,1,1,2,2,2,3,3,-1,-1,-1], '冂框作尾碼，框內口形省略。'),
    '高': ('YRB', ['頂端的點橫', '上方的口', '下方的冂框'],
          [0,0,1,1,1,2,2,-1,-1,-1], '冂框作尾碼，框內的小口依包含省略規則略去。'),
    '甬': ('NIB', ['上方橫撇', '橫撇下的一點', '用形的外框'],
          [0,1,2,2,-1,-1,-1], '取用形的外框作尾碼，框內兩橫與一豎省略。'),
    '侖': ('OMB', ['人字頭', '人下的一橫', '冊形的外框'],
          [0,0,1,2,2,-1,-1,-1], '取冊形的外框作尾碼，內部橫豎省略。'),
}


def embedded_guide(child, side, layout, parent_code, strokes):
    # The source IDS names standalone characters even for positional allographs.
    # Verify both the contextual spelling and the order of the embedded strokes.
    accepts = parent_code.startswith if side == 0 else parent_code.endswith
    if child == '矞' and side == 1 and accepts('NHB') and len(strokes) == 12:
        return ('NHB', ['矛的上方橫撇', '矛末段的長撇', '下部冂框'],
                [0,-1,-1,-1,1,2,2,-1,-1,-1,-1,-1],
                ['矛只取首尾。下部只取冂框，依包含省略規則略去框內八形與口形。'])
    if child == '邦' and (accepts('QJL') or side == 0 and accepts('QL')) and len(strokes) == 6:
        qjl = accepts('QJL')
        return ('QJL' if qjl else 'QL', ['丰上部手形']+(['丰下部十形'] if qjl else [])+['右耳旁的豎'],
                [0,0,1 if qjl else -1,Parts((0,1 if qjl else -1),(Cut(1,3,.45),)),-1,2 if qjl else 1],
                ['邦在本字取右耳旁末豎，折鉤省略。'] if qjl else ['邦作字首只取首尾，丰下部十形和右耳旁折鉤省略。'])
    if child == '既' and (accepts('AIU') or accepts('AU')) and len(strokes) == 9:
        dot = accepts('AIU')
        return ('AIU' if dot else 'AU', ['左上日形']+(['日下右點'] if dot else [])+['旡的尾鉤'],
                [0,0,0,Parts((0,-1),(Cut(1,2,.2),)),1 if dot else -1,-1,-1,-1,2 if dot else 1],
                ['既在本字中只取日形、右下尾鉤，中間筆畫省略。' if not dot else
                 '既作字身取首、次、尾，左豎的下段與旡形尾鉤之前的筆畫省略。'])
    if child == '監' and side == 0 and accepts('SW') and len(strokes) == 14:
        return ('SW', ['臣的外匚框', '右下罒的外框'], [0,-1,-1,-1,-1,0,-1,-1,-1,1,1,-1,-1,1],
                ['監形作字首取首尾，兩框內部以及右上方的撇、橫、點省略。'])
    if child == '骨' and side == 0 and accepts('BB') and len(strokes) == 10:
        return ('BB', ['頂部骨框', '底部月形'], [0,0,0,0,-1,-1,1,1,1,1],
                ['骨作字首取首尾，中間冖框省略。'])
    if child == '鹵' and side == 0 and accepts('YW') and len(strokes) == 11:
        return ('YW', ['上方卜形', '下方外框'], [0,0,1,1,-1,-1,-1,-1,-1,-1,1],
                ['鹵作字首，尾碼取外框。框內的點與交叉形依包含省略略去。'])
    if child == '臧' and accepts('IMS') and len(strokes) == 14:
        return ('IMS', ['外側戈形', '左下橫撇', '臣的匚框'],
                [0,-1,-1,1,1,2,-1,-1,-1,-1,2,0,0,0],
                ['臧作字身取三碼，左部只取首尾，臣取外框，框內筆畫省略。'])
    if child == '風' and side == 0 and not accepts('HNI') and accepts('HN') and len(strokes) == 9:
        return ('HN', ['外框左撇', '外框的折彎鉤'], [0,1]+[-1]*7,
                ['風作字首取几框，框內頂撇和虫形依包含省略略去。'])
    if child == '苗' and accepts('TW') and len(strokes) == 9:
        return 'TW', ['四筆草字頭', '下方田形'], [0]*4+[1]*5, []
    if child == '鬲' and side == 1 and accepts('MRB') and len(strokes) == 10:
        return ('MRB', ['頂橫', '中間口形', '下方冂框'], [0,1,1,1,2,2,-1,-1,-1,-1],
                ['鬲作字身取三碼，尾碼取冂框，框內筆畫省略。'])
    if child == '爾' and accepts('MFB') and len(strokes) == 14:
        return ('MFB', ['頂橫', '橫下中豎與兩側撇點', '下方冂框'], [0,1,1,1,2,2]+[-1]*8,
                ['爾作字身，尾碼取外框，框內四組叉形依包含省略略去。'])
    if child == '蒙' and accepts('TBO') and len(strokes) == 14:
        return ('TBO', ['四筆草字頭', '下方冖框', '豕右側的人形'], [0]*4+[1,1]+[-1]*6+[2,2],
                ['蒙作字身保留首、次、尾。冖框與豕末兩筆之間的筆畫省略。'])
    if child == '禹' and side == 1 and accepts('HLB') and len(strokes) == 9:
        return ('HLB', ['頂撇', '帶中豎的口框', '下方冂框'],
                [0,1,1,1,2,2,Parts((1,-1),(Cut(1,5,.91),)),-1,-1],
                ['禹作字身取外框作尾碼，框內豎段、提和點依包含省略規則略去。'])
    if child == '聿' and side == 0 and accepts('LG') and len(strokes) == 6:
        return ('LG', ['上方肀形', '下方土形'],
                [0,0,0,1,Parts((0,1),(Cut(1,2,.45),)),1], [])
    if child == '兼' and side == 1 and accepts('TXC') and len(strokes) == 10:
        return ('TXC', ['頂部兩點和第一橫', '中間相交的折、橫與雙豎', '底部八形'],
                [0,0,0,1,1,1,1,1,2,2], [])
    if child == '堇' and side == 0 and accepts('TO') and len(strokes) == 11:
        return ('TO', ['上方廿形', '最末的右捺'], [0]*4+[-1]*6+[1],
                ['左側作字首只取首尾，廿形與末捺之間的筆畫省略。'])
    if child == '麻' and side == 0 and accepts('IC') and len(strokes) == 11:
        return ('IC', ['外側广形', '右側十形兩旁的撇點'],
                [0,0,0,-1,-1,-1,-1,-1,-1,1,1],
                ['麻作複合字首取首尾。左邊的十和八、右邊十形省略。'])
    if child == '柬' and side == 1 and accepts('KVC') and len(strokes) == 5:
        return ('KVC', ['上橫與相交的斜段', '斜筆下段連著右折', '下方兩點'],
                [0,Parts((0,1),(Cut(1,0,.45),)),-1,2,2],
                ['簡化柬形作字身取首、次、尾，居中的橫折鉤省略。'])
    if child == '𠬛' and accepts('HSE') and len(strokes) == 4:
        return 'HSE', ['左上短撇', '右上折鉤', '下方又形'], [0,1,2,2], []
    if child == '哉' and side == 0 and accepts('JI') and len(strokes) == 6:
        return 'JI', ['左上十形', '外圍戈形'], [0,0,1,1,1,1], []
    if child == '而' and side == 0 and accepts('MB') and component_matches(child, strokes):
        return ('MB', ['上橫和短撇', '下方冂框'], [0,0,1,1,-1,-1],
                ['而作字首取頂部與外框，框內兩豎依包含省略略去。'])
    if child == '嗇' and side == 1 and accepts('GOW') and component_matches(child, strokes):
        return ('GOW', ['上方土形', '土旁右側人形', '下方回的外框'],
                [-1,-1,1,1,0,0,0,2,2,-1,-1,-1,2],
                ['上部取土與尾部人形，略去左人。回只取外框，內口省略。'])
    if child == '覃' and side == 1 and accepts('MWJ') and len(strokes) == 12:
        return ('MWJ', ['覀的頂橫', '覀的四面外框', '早的十形'],
                [0,1,1,-1,-1,1,-1,-1,-1,-1,2,2],
                ['覀取外框，內部兩豎省略。早只取尾碼，日形省略。'])
    if child == '角' and side == 0 and accepts('NB') and len(strokes) == 7:
        return ('NB', ['上方刀頭', '下方冂框'], [0,0,1,1,-1,-1,-1],
                ['角作字首取刀頭和外框，框內筆畫依包含省略規則略去。'])
    if child == '臽' and accepts('NHX') and component_matches(child, strokes):
        return 'NHX', ['刀頭', '臼的短撇', '臼的其餘筆畫'], [0,0,1,2,2,2,2,2], []
    if child == '刍' and accepts('NS') and component_matches(child, strokes):
        return ('NS', ['刀頭', '彐的外框'], [0,0,1,-1,1], ['框內短橫依包含省略規則略去。'])
    if child == '急' and accepts('NSP') and len(strokes) == 9:
        return ('NSP', ['刀頭', '彐的外框', '心形'], [0,0,1,-1,1,2,2,2,2],
                ['急作字身，彐只取外框，框內短橫省略。'])
    if child == '雚' and len(strokes) == 18:
        reference = graphics['觀']['medians'][:18]
        if similar_order(reference, strokes):
            keys, names, owners, reasons = fragment_guides['雚']
            return keys, names, [0] + [remap(o, dict(enumerate(range(4))), list(range(1, 18))) for o in owners], reasons
    if child == '羊' and side == 0 and accepts('TH') and similar_order(graphics['差']['medians'][:6], strokes):
        return ('TH', ['頂端兩點和第一橫', '伸出第三橫以下的長撇'],
                [0,0,0,-1,-1,Parts((-1,1),(Cut(1,4,.48),))],
                ['羊形作字首取首尾，中間兩橫和相交的撇上段省略。'])
    if child in ('昜', '勿') and side == 1 and accepts('NSH') and similar_order(graphics['扬']['medians'][3:], strokes):
        return ('NSH', ['折筆上方的橫撇', '同一筆轉向右後的橫折鉤', '右側長撇'],
                [Parts((0,1),(MiddleBend(-1),)),-1,2],
                ['完整的𠃓形取弓尸竹竹，作字身保留首、次、尾碼，兩撇中的第一撇省略。'])
    if child == '每' and len(strokes) == 6 and (accepts('OWJ') or side == 0 and accepts('OJ')):
        return ('OWJ', ['頂端撇橫', '毋的外框', '毋中相交的撇和橫'],
                [0,0,1,1,2,2], [])
    if child == '师' and side == 1 and accepts('LLB') and component_matches(child, strokes):
        return ('LLB', ['左邊短豎', '左邊長直撇', '右側巾的冂框'], [0,1,-1,2,2,-1],
                ['师作字身取兩豎及冂框，框上方的橫與框內豎筆省略。'])
    if child == '⺈' and side == 0 and accepts('HS') and len(strokes) == 2:
        return 'HS', ['刀頭左撇', '刀頭右折筆'], [0,1], []
    if child == '負' and side == 1 and accepts('NBC') and len(strokes) == 9:
        return ('NBC', ['頂端刀頭', '貝中目框上部', '下方八形'],
                [0,0,Parts((1,-1),(Cut(1,2,.12),)),Parts((1,-1),(Cut(1,3,.12),)),1,1,-1,2,2],
                ['貝取首尾，目框底部山形省略。'])
    if child == '韱' and side == 1 and accepts('OIM') and component_matches(child, strokes):
        return ('OIM', ['上方左側人形', '戈形', '韭的底橫'],
                [0,0,-1,-1,1,-1,-1,-1,-1,-1,-1,-1,-1,2,1,1,1],
                ['韱作字身取首、次、尾，第二個人形與韭的底橫以上各筆省略。'])
    if child == '蒦' and side == 1 and accepts('TOE') and len(strokes) in (13,14):
        grass = len(strokes) - 10
        return ('TOE', ['草字頭', '隹左側的單人旁', '底部又形'],
                [0]*grass + [1,1]+[-1]*6+[2,2],
                ['蒦作字身取首、次、尾，隹的右半部省略。'])
    if child == '若' and side == 1 and accepts('TKR') and len(strokes) == 9:
        return 'TKR', ['四筆草字頭', '右字相交的橫撇', '口形'], [0]*4+[1]*2+[2]*3, []
    if child == '莫' and side == 1 and accepts('TAK') and len(strokes) == 11:
        return 'TAK', ['四筆草字頭', '日形', '大形'], [0]*4+[1]*4+[2]*3, []
    if child == '荒' and side == 1 and accepts('TYU') and len(strokes) == 10:
        return ('TYU', ['四筆草字頭', '亡的點橫', '底部右邊的彎鉤'],
                [0]*4+[1,1,-1,-1,-1,2], ['荒作字身取首、次、尾，點橫和右下彎鉤之間的筆畫省略。'])
    if child == '菐' and side == 1 and accepts('TCO') and component_matches(child, strokes):
        return ('TCO', ['上方兩豎和橫', '兩豎旁的撇點', '右下方的一捺'],
                [0,0,1,1,0,-1,-1,-1,-1,-1,-1,2], ['字身取首、次、尾，業字頭以下只取右下捺筆。'])
    if child == '匸' and side == 0 and accepts('S') and len(strokes) == 2:
        return 'S', ['匚形外框'], [0,0], []
    if child == '录' and side == 1 and accepts('NME') and component_matches(child, strokes):
        return ('NME', ['上方橫折', '彐的下橫', '底部水形'],
                [0,-1,1,2,2,2,2,2], ['上方彐形取首尾，兩橫同碼時保留下橫，中橫省略。'])
    if child == '每' and side == 1 and accepts('OWY') and component_matches(child, strokes):
        return ('OWY', ['頂端撇和橫', '母形外框', '框內上點與穿框的橫'],
                [0,0,1,1,2,2,-1], ['每作字身取三碼，框內下點位於末位而省略。'])
    if child == '冬' and side == 1 and accepts('HEY') and component_matches(child, strokes):
        return 'HEY', ['上方第一撇', '與撇相接的橫撇和捺', '下方兩點'], [0,1,1,2,2], []
    if child == '鬼' and len(strokes) == 10 and similar_order(graphics['塊']['medians'][3:], strokes):
        keys, labels, owners, reasons = fragment_guides['鬼']
        return keys, labels, owners[:4] + [-1] + owners[4:], reasons
    if child == '戠' and side == 1 and accepts('YIA') and len(strokes) == 12:
        if similar_order(graphics['職']['medians'][6:], strokes):
            return ('YIA', ['頂部點橫', '共用的長橫與戈形其餘筆畫', '長橫下的日框'],
                    [0,0,-1,-1,1,2,2,2,2,1,1,1], ['頂部取點橫，中間兩點省略；中央長橫與右側戈形合取戈。'])
    if child == '戠' and side == 1 and accepts('YIA') and component_matches(child, strokes):
        if len(strokes) == 13:
            return ('YIA', ['立字頂端點橫', '右部戈形', '立下的日框'],
                    [0,0,-1,-1,-1,2,2,2,2,1,1,1,1],
                    ['此字主碼按戈在日前取碼，立字上部只保留點橫。'])
    if child == '叚' and side == 1 and accepts('RSE') and component_matches(child, strokes):
        return ('RSE', ['左上口形', '左豎的下段與左下末橫', '右下又形'],
                [0,0,Parts((0,1),(Cut(1,1,.15),)),-1,1,-1,-1,2,2],
                ['左部取上方口形及下段末橫，略去中間短橫。右部只取又，右上折形省略。'])
    if child == '杀' and side == 0 and accepts('KC') and component_matches(child, strokes):
        return ('KC', ['上方交叉的撇點', '木形下部向兩旁分開的兩筆'], [0,0,-1,-1,1,1],
                ['杀作字首取首尾，下部只取末尾八形，中間十形省略。'])
    if child == '？' and side == 0 and accepts('LI') and similar_order(graphics['监']['medians'][:5], strokes):
        return ('LI', ['左上第一豎', '右上短橫下的一點'], [0,-1,-1,-1,1],
                ['上部作字首，取起首的豎筆和末尾的點，兩者之間的筆畫省略。'])
    if child == '？' and side == 1 and accepts('EQ') and similar_order(graphics['择']['medians'][3:], strokes):
        return 'EQ', ['上方的又形', '下方兩橫和中豎'], [0,0,1,1,1], []
    if child == '户' and side == 0 and accepts('S') and len(strokes) == 3:
        if similar_order(graphics['居']['medians'][:3], strokes):
            return 'S', ['上方的尸形'], [0,0,0], []
    if child == '廴' and side == 0 and accepts('NK') and component_matches(child, strokes):
        turn = Parts((0,-1,1),(MiddleBend(-1), MiddleBend(1)))
        return ('NK', ['左上橫撇', '下方交叉的撇和捺'], [turn,1],
                ['廴作字首取首尾，中間連接上下兩段的短橫省略。'])
    if child == '艹' and len(strokes) == 4 and similar_order(graphics['葉']['medians'][:4], strokes):
        return 'T', ['四筆草字頭'], [0]*4, []
    if child == '户' and accepts('HS') and component_matches(child, strokes):
        return fragment_guides['戶']
    if child == '扁' and len(strokes) == 9 and component_matches(child, strokes):
        if accepts('HSB') or accepts('ISB') or (side == 0 and accepts('HB')):
            dot = accepts('ISB')
            return ('ISB' if dot else 'HSB',
                    ['頂點' if dot else '頂筆和左側長撇（主碼依撇頂字形）',
                     '尸形' if dot else '戶內橫折和橫', '下部冂框'],
                    [0,1,1,1 if dot else 0,2,2,-1,-1,-1],
                    ['尾碼取冊形的外框，框內一橫兩豎依包含省略略去。'])
    if child == '䍃' and len(strokes) == 10 and similar_order(graphics['搖']['medians'][3:], strokes):
        if (side == 0 and accepts('BU')) or (side == 1 and accepts('BOU')):
            keys = 'BU' if side == 0 else 'BOU'
            last = len(keys)-1
            names = ['缶上方的四筆'] + (['缶的短撇和短橫'] if side else []) + ['缶底山形']
            return (keys, names, [0]*4 + ([1,1] if side else [-1,-1]) + [-1,
                    Parts((-1,last),(Cut(1,6,.5),)),last,last],
                    ['缶的中間十形省略，尾碼取底部山形。' if side else '字首只保留首尾，缶只取底部山形。'])
    if child == '众' and side == 1 and accepts('OOO') and len(strokes) == 6:
        if similar_order(graphics['眾']['medians'][5:], strokes):
            return 'OOO', ['中間的短撇和豎', '左側人形', '右側人形'], [0,0,1,1,2,2], []
    if child == '礻' and side == 0 and accepts('IF') and len(strokes) == 4:
        if component_matches(child, strokes):
            return ('IF', ['頂端的點', '橫撇的撇段、豎和右點'],
                    [0,Parts((-1,1),(Cut(0,1,.996),)),1,1],
                    ['示字旁作字首取首尾，第二筆開頭的橫段省略。'])
    if child == '彐' and accepts('SM') and len(strokes) == 3:
        if component_matches(child, strokes):
            return 'SM', ['橫折和底橫形成的外框', '框內短橫'], [0,1,0], []
    if child == '多' and side == 1 and accepts('NIN') and len(strokes) == 6:
        if component_matches(child, strokes):
            return ('NIN', ['上夕的撇和橫撇', '上夕內點', '下夕的撇和橫撇'],
                    [0,0,1,2,2,-1], ['多作字身取三碼，尾碼取下夕外側兩筆，內點依包含省略略去。'])
    if child == '需' and side == 1 and accepts('MBB') and len(strokes) == 14:
        if component_matches(child, strokes):
            return ('MBB', ['雨字頭頂橫', '雨字頭冖框', '下部而形的外框'],
                    [0,1,1,-1,-1,-1,-1,-1,-1,-1,2,2,-1,-1],
                    ['雨頭取頂橫與冖框；而形只取外框作尾碼，頂橫、短撇及框內兩豎省略。'])
    if child == '罒' and side == 0 and accepts('WL') and len(strokes) == 5:
        if component_matches(child, strokes):
            return ('WL', ['罒的外框', '框內右邊的豎筆'], [0,0,-1,1,0],
                    ['罒作字首取首、尾兩碼，框內左豎省略。'])
    if child == '耑' and side == 1 and accepts('UMB') and len(strokes) == 9:
        if component_matches(child, strokes):
            return ('UMB', ['頂部山形', '而的頂橫和短撇', '而的外框'],
                    [0,0,0,1,1,2,2,-1,-1], ['而形取外框作尾碼，依包含省略略去框內兩豎。'])
    if child == '柬' and side == 1 and accepts('DW') and len(strokes) == 9:
        if component_matches(child, strokes):
            return ('DW', ['穿過框形的木形', '中央的外框'],
                    [0,1,1,-1,-1,1,Parts((0,-1,0),(Cut(1,2,.95),Cut(1,5,.4))),0,0],
                    ['尾碼取框，框內的兩點與中豎段依包含省略略去。'])
    if child == '僉' and len(strokes) == 13 and component_matches(child, strokes):
        if side == 0 and accepts('OO') or side == 1 and accepts('OMO'):
            keys = 'OO' if side == 0 else 'OMO'
            names = ['頂端人形'] + (['人下短橫'] if side == 1 else []) + ['右下人形']
            return (keys, names, [0,0,1 if side else -1] + [-1]*8 + [len(keys)-1]*2,
                    ['僉在此縮寫，下方只取尾部右側的人形，灰色的中間筆畫省略。'])
    if child == '重' and side == 1 and accepts('HJG'):
        reference = graphics['鍾']['medians'][8:]
        if similar_order(reference, strokes):
            cut = Parts((1,-1,2), (Cut(1,3,.92), Cut(1,5,.5)))
            return ('HJG', ['頂端短撇', '上橫和中豎上段', '底部土形'],
                    [0,1,-1,-1,-1,-1,2,cut,2],
                    ['重作字身取首、次、尾，中間田形與其中的豎段省略。'])
    if child == '非' and len(strokes) == 8 and component_matches(child, strokes):
        if side == 0 and accepts('LY') or side == 1 and accepts('LMY'):
            keys = 'LY' if side == 0 else 'LMY'
            last = len(keys) - 1
            owners = [0,-1,-1,-1 if side == 0 else 1,Parts((-1,last),(Cut(1,6,.15),)),-1,-1,last]
            labels = ['左側長豎'] + (['左下短橫'] if side == 1 else []) + ['右豎下段與右下短橫']
            return keys, labels, owners, ['非形在合體中省碼，灰色的中間筆段略去，末碼取右下卜形。']
    if child == '昜' and side == 1 and accepts('AMH') and len(strokes) == 9:
        if component_matches(child, strokes):
            return ('AMH', ['上方日形', '日下的一橫', '最右側長撇'], [0,0,0,0,1,-1,-1,-1,2],
                    ['昜作字身取首、次、尾，橫筆下方只取最右側長撇。'])
    if child in enclosed_forms:
        keys, names, owners, omission = enclosed_forms[child]
        spelling = keys[0] + keys[-1] if side == 0 else keys
        if side == 1 and len(spelling) > 3:
            spelling = spelling[:2] + spelling[-1]
        if accepts(spelling) and len(strokes) == len(owners) and similar_order(graphics[child]['medians'], strokes):
            return keys, names, owners, [omission]
    if side == 0 and child == '舟' and accepts('HY') and len(strokes) == 6:
        if similar_order(graphics['航']['medians'][:6], strokes):
            return ('HY', ['頂端短撇', '上點和橫筆'], [0,-1,-1,1,1,-1],
                    ['舟作字首取首尾，包含省略使末碼取卜，外框與框內下點省略。'])
    if side == 0 and child == '歹' and accepts('MN') and len(strokes) == 4:
        if similar_order(graphics['列']['medians'][:4], strokes):
            return ('MN', ['頂部一橫', '下方夕形的外側兩筆'], [0,1,1,-1],
                    ['歹作字首取橫與夕形外側，內部點畫依包含省略略去。'])
    if side == 0 and child == '尚' and accepts('FB') and not accepts('FBR'):
        if len(strokes) == 5 and similar_order(graphics['尝']['medians'][:5], strokes):
            return 'FB', ['頂端三筆', '下方冖框'], [0,0,0,1,1], []
        if len(strokes) == 8 and similar_order(graphics['敞']['medians'][:8], strokes):
            return ('FB', ['頂端三筆', '下方冂框'], [0,0,0,1,1,-1,-1,-1],
                    ['字首依包含省略取冂框，內部的口省略。'])
    if side == 0 and child in ('齒', '齿') and accepts('YU'):
        reference = graphics[child]['medians']
        if len(strokes) == len(reference) and component_matches(child, strokes):
            return ('YU', ['止形頂端的卜形', '下半部的凵框'], [0,0] + [-1]*(len(strokes)-4) + [1,1],
                    ['齒作字首取首尾，下部依包含省略取外框，框內筆畫及止形的中間碼省略。'])
    if side == 0 and child == '雨' and accepts('MB'):
        reference = graphics['雲']['medians'][:8]
        if len(strokes) == 8 and similar_order(reference, strokes):
            return ('MB', ['雨字頭頂端的一橫', '下方的冖框'], [0,1,1,-1,-1,-1,-1,-1],
                    ['雨字頭取頂橫與外框，中豎和框內的四點省略。'])
    if child in ('工', '匕', '乚', '廾'):
        key = {'工': 'M', '匕': 'P', '乚': 'U', '廾': 'T'}[child]
        if accepts(key) and len(strokes) == len(graphics[child]['strokes']):
            return key, ['整個' + child + '形'], [0] * len(strokes), []
    if child == '足' and layout == '⿰' and side == 0 and accepts('RM'):
        reference = graphics['路']['medians'][:7]
        if len(strokes) == 7 and similar_order(reference, strokes):
            return ('RM', ['足字旁上方的口', '足字旁底部的一提'], [0,0,0,-1,-1,-1,1],
                    ['足字旁作字首，取口與底部的一提，中間三筆省略。'])
    if child == '羊' and layout == '⿱' and side == 0 and accepts('TG'):
        reference = graphics['羔']['medians'][:6]
        if len(strokes) == 6 and similar_order(reference, strokes):
            return 'TG', ['頂端兩點與上橫', '下方的土形'], [0,0,0,1,1,1], []
    return None


# Explicit retained root positions for compounds whose IDS grouping differs
# from their Cangjie grouping. Indices are local to the displayed component.
compound_selections = {}
for left, right, characters in (
    ('0', '014', '儼巖'),
    ('0', '013', '啣嬝撵癒蓆懍鍰鏜嗤擁臃燧槛滥篮蓝嚀擰橫檸演濘挺梃嚕樽櫓蓄遵俊億哼唆唠唸啜噎噫噹媛峻悖愎憶捞捻援撑擋暖梭棱槌檔浚涝涮淳溃溪脖腹膛臆荸菱蔚複襠遗鐺'),
    ('0', '014', '邐攆攫囁濬揽榄懾攝癥償僻匱協嗦嘮嫦惨掺搅撈渗潰澱癆癖篩簣荔薜遺避'),
    ('01', '013', '獰綾瞬隧尴夤蹲凌凛凜復瞑瞠稔稜稷竣綴緩缀缓蹊陵霪馈'),
    ('013', '1', '孳剪尊'),
    ('013', '2', '躉'),
    ('012', '1', '兕募幕贪贫'),
    ('0123', '0', '慧啻'),
    ('012', '0', '攀密垒壘惹畜魯鲁'),
    ('013', '0', '壅慈奠烹煎膺'),
    ('01', '02', '賁彬'),
    ('01', '014', '缆躡獅闢霹'),
    ('012', '2', '蜜疊貧貪顺'),
    ('01', '012', '電'),
    ('0', '012', '伪'),
    ('0', '014', '嚐'),
    ('012', '03', '靠'),
    ('012', '02', '羹裳賞黨'),
    ('01', '04', '翁'),
    ('02', '013', '酬酸醇蟒趨螟螳谆谴輟馥'),
    ('03', '013', '諄譴駿骏'),
    ('012', '01', '礬雌'),
    ('012', '3', '順'),
    ('014', '1', '颱'),
    ('02', '013', '顓'),
    ('0123', '0', '矍'),
    ('0123', '1', '蠱'),
    ('012', '0', '熹'),
    ('01', '013', '緻'),
    ('012', '0', '愈'),
    ('01', '03', '鴻鸿鵬鹏'),
    ('013', '3', '鷹'),
):
    for character in characters:
        compound_selections[character] = (left, right)


@lru_cache(None)
def resolve(char, standalone=False):
    if char not in graphics:
        return
    n = len(graphics[char]['strokes'])
    code = auxiliary.get(char, component_codes.get(char, [''])[0])
    if standalone:
        code = codes[char]
    if char in fragment_guides and fragment_guides[char][0] == code:
        return fragment_guides[char]
    if len(code) == 1:
        return code, [char], [0] * n, []
    if char == '儿' and code == 'LU':
        return code, ['左邊直撇取「中」', '右邊豎彎鉤取「山」'], [0, 1], []
    if char in annotated and code == annotated[char][0]:
        _, indices, labels = annotated[char]
        assert len(indices) == n
        return code, labels, list(map(int, indices)), []
    ids = dictionary[char]['decomposition']
    if not code or not ids or ids[0] not in positions or char in ids[1:]:
        return
    matches = dictionary[char]['matches']
    if len(ids) > 3 and len(matches) == n:
        return resolve_nested(char, code, ids, matches)
    if len(ids) != 3:
        return
    # These five simplified characters use the same unnamed 又-over-手 form.
    # Upstream marks its strokes null. embedded_guide also checks their geometry.
    if char in '择泽绎译释' and ids.endswith('？'):
        matches = [[1] if path is None else path for path in matches]
    if char in '监览鉴' and ids.startswith('⿱？'):
        matches = [[0] if path is None else path for path in matches]
    if len(matches) != n or any(m not in ([0], [1]) for m in matches):
        return
    labels, letters, assignments, omissions = [], [], [None] * n, []
    for side, child in enumerate(ids[1:]):
        indices = [i for i, m in enumerate(matches) if m == [side]]
        embedded = [graphics[char]['medians'][i] for i in indices]
        variant = embedded_guide(child, side, ids[0], code, embedded)
        result = variant or resolve(child)
        if not result:
            return
        childcode, childlabels, childsteps, childomits = result
        if len(childsteps) != len(indices):
            return
        if not variant and len(childcode) > 1 and not component_matches(child, embedded):
            return
        keep = list(range(len(childcode)))
        part = positions[ids[0]][side] + ('部' if child == '？' else '部「' + child + '」')
        if char in compound_selections:
            keep = [int(index) for index in compound_selections[char][side]]
            if keep[-1] >= len(childcode):
                return
            if len(keep) < len(childcode):
                kept = '、'.join(f'第{k+1}碼 {childcode[k]}' for k in keep)
                omissions.append(part + '在本字中縮寫，保留' + kept + '，其餘碼的筆畫省略。')
        elif child == '酉':
            keep = [0, 2] if side == 0 else [0, 1, 2]
            omissions.append(part + ('作字首只取兩碼，中間的「金」略去。' if side == 0 else '作字身最多取三碼。')
                             + '框內的末橫依包含省略規則略去，尾碼取外框「田」。')
        elif (side == 0 and len(keep) > 2 and
              not (child in ('尚', '今', '分', '音', '莫', '黑') and code.startswith(childcode))):
            keep = [0, keep[-1]]
            reason = ('作字首只取 I、V，第二筆上方的橫折（N 弓）省略。'
                      if child == '讠' else '作字首，取首、尾碼，略去中間碼。')
            omissions.append(part + reason)
        elif side == 1 and len(keep) > 3:
            if child in annotated or child in fragment_guides:
                keep = [0, 1, keep[-1]]
                omissions.append(part + '作整體字身，取首、次、尾碼。')
            else:
                child_ids = dictionary[child]['decomposition']
                if len(child_ids) != 3 or child_ids[0] not in positions:
                    return
                prefix = positions[child_ids[0]][0] + '部「' + child_ids[1] + '」'
                head_size = sum(label.startswith(prefix) for label in childlabels)
                if head_size == 1:
                    keep = [0, 1, keep[-1]]
                    omissions.append(part + '的次字首取一碼，次字身取首尾兩碼。')
                elif head_size == 2:
                    keep = [0, 1, keep[-1]]
                    omissions.append(part + '的次字首取兩碼，次字身只取尾碼。')
                else:
                    return
        mapped = {k: len(labels) + i for i, k in enumerate(keep)}
        for i, step in zip(indices, childsteps):
            assignments[i] = remap(step, mapped, indices)
        labels.extend(part if len(childcode) == 1 else part + '的' + childlabels[k] for k in keep)
        letters.extend(childcode[k] for k in keep)
        omissions.extend(part + '：' + reason for reason in childomits)
    if ''.join(letters) == code:
        return code, labels, assignments, omissions


def dong():
    # Original schematic of the 13-stroke Taiwan form. Split the continuous
    # central vertical at both borders of 田 so each fragment is selectable.
    groups = [
        (0, ['M15 16H45', 'M32 7V26', 'M68 7V26', 'M55 16H85']),
        (1, ['M69 27Q51 33 32 34']),
        (2, ['M13 41H87', 'M50 32V48']),
        (-1, ['M28 48V68', 'M28 48H72V68', 'M28 58H72', 'M28 68H72', 'M50 48V68']),
        (3, ['M50 68V91', 'M24 79H76', 'M12 91H88'])]
    return dict(code='THJG', labels=['草字頭的四筆合取「廿」', '「重」頂端的一撇取「竹」',
                '撇下的橫與中豎上段合取「十」', '中豎下段和底部兩橫合取「土」'],
                omissions=['「重」單獨取 HJWG。在「董」中作字身，取首、次、尾 HJG，中間的 W（田）省略。'],
                paths=[[step, path] for step, paths in groups for path in paths], schematic=True)


out = ROOT / 'public/stroke-guides'
out.mkdir(exist_ok=True)
buckets = {}
missing = []
for char, code in codes.items():
    if char == '董':
        guide = dong()
    else:
        mapping = resolve(char, standalone=True)
        if not mapping or mapping[0] != code:
            missing.append(char)
            continue
        _, labels, steps, omissions = mapping
        geometry = paths_for(steps, graphics[char])
        if geometry is None:
            missing.append(char)
            continue
        if char in variant_glyphs:
            geometry.update(medians=True, variant=variant_glyphs[char])
        if char in composed_examples or char in stacked_examples or char in enclosed_examples:
            geometry.update(medians=True, composed=True)
        guide = dict(code=code, labels=labels, omissions=omissions, **geometry)
    assert guide['code'] == code and set(range(len(code))) <= {p[0] for p in guide['paths']}
    assert any(p[0] == -1 for p in guide['paths']) == bool(guide['omissions'])
    buckets.setdefault(ord(char) % 64, {})[char] = guide
notice = "TypeType 2026-11-22: selected and grouped Make Me a Hanzi outlines by Cangjie code. Arphic Public License, see licenses/APL/english/ARPHICPL.TXT."
for bucket in range(64):
    (out / f'{bucket}.json').write_text(json.dumps({"notice": notice, "characters": buckets.get(bucket, {})}, ensure_ascii=False, separators=(',', ':')) + '\n')
reviews = json.loads((ROOT / 'scripts/reviewed-stroke-guides.json').read_text())
unreviewed = []
for entries in buckets.values():
    for char, guide in entries.items():
        contents = json.dumps(guide, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        if hashlib.sha256(contents.encode()).hexdigest() != reviews.get(char):
            unreviewed.append(char)
reviewed_count = len(codes) - len(missing) - len(unreviewed)
report = ROOT / '.local/stroke-guide-coverage.json'
report.parent.mkdir(exist_ok=True)
report.write_text(json.dumps({'total': len(codes), 'mapped': len(codes)-len(missing),
                              'reviewed': reviewed_count, 'unreviewed': sorted(unreviewed),
                              'missing': {c: codes[c] for c in missing}},
                             ensure_ascii=False, indent=2) + '\n')
print(f'{len(codes)-len(missing)} / {len(codes)} primary codes mapped')
if args.require_full and (missing or unreviewed):
    raise SystemExit(f'{len(missing)} missing, {len(unreviewed)} mapped but unreviewed, {reviewed_count} reviewed.')

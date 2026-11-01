"""Імпорт «Таблиці рогаликів» (TianKami) у roguelikes.js для сторінки roguelikes.html.

Запуск:  python import-roguelikes.py            (свіжа таблиця з Google Sheets)
         python import-roguelikes.py file.xlsx  (локальний файл)
Потрібно: pip install openpyxl
"""
import collections
import datetime as dt
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
OUT = HERE / 'roguelikes.js'
sys.stdout.reconfigure(encoding='utf-8')

# Таблицю Тіан оновлює в Google Sheets — щоразу завантажуємо свіжу копію.
SHEET_URL = 'https://docs.google.com/spreadsheets/d/16-b4LC_n2g1pq2fVGkUJyRsq9xklzlRpIwVH5Gv3C4U/export?format=xlsx'
SHEET_COPY = HERE / 'tian-sheet.xlsx'  # остання успішно завантажена версія


def download_sheet():
    tmp = SHEET_COPY.with_name('tian-sheet.download.xlsx')
    try:
        with urllib.request.urlopen(SHEET_URL, timeout=120) as resp, open(tmp, 'wb') as f:
            f.write(resp.read())
        openpyxl.load_workbook(tmp, read_only=True).close()  # перевірка, що це справжній xlsx
        tmp.replace(SHEET_COPY)
        print('Таблицю Тіана завантажено з Google Sheets')
        return SHEET_COPY, 'Google-таблиця Тіана'
    except Exception as e:
        tmp.unlink(missing_ok=True)
        for fallback in (SHEET_COPY,):
            if fallback.exists():
                print(f'Не вдалося завантажити з Google ({e}). Беру збережену копію: {fallback.name}')
                return fallback, f'{fallback.name} (збережена копія)'
        raise


if len(sys.argv) > 1:
    SRC = Path(sys.argv[1])
    SRC_LABEL = SRC.name
else:
    SRC, SRC_LABEL = download_sheet()

GENRE_UK = {
    'карточный': 'Картковий', 'экшен': 'Екшн', 'вампирлайк': 'Вампірлайк', 'пошаговый': 'Покроковий',
    'автобатлер': 'Автобатлер', 'стратегия': 'Стратегія', 'платформер': 'Платформер', 'аркада': 'Аркада',
    'шутер': 'Шутер', 'tower defense': 'Tower Defense', 'bullet hell': 'Bullet Hell', 'дайсы': 'Кубики',
    'выживач': 'Виживання', 'симулятор': 'Симулятор', 'метройд': 'Метроїдванія', 'гонки': 'Перегони', 'ритм': 'Ритм',
}
SETTING_UK = {
    'фэнтези': 'Фентезі', 'sci-fi': 'Sci-Fi', 'космос': 'Космос', 'темное фэнтези': 'Темне фентезі',
    'реальный мир': 'Реальний світ', 'реальная жизнь': 'Реальний світ', 'азартные игры': 'Азартні ігри',
    'аззартные игры': 'Азартні ігри', 'постапокалипсис': 'Постапокаліпсис', 'азиатская мифология': 'Азійська міфологія',
    'скандинавская мифология': 'Скандинавська міфологія', 'лавкрафт': 'Лавкрафт', 'ацтеки': 'Ацтеки',
    'вестерн': 'Вестерн', 'нечисть': 'Нечисть', 'кошмары': 'Кошмари', 'зомби': 'Зомбі', 'зомбиапокалипсис': 'Зомбі',
    'пираты': 'Пірати', 'страницы книги': 'Сторінки книги', 'культ': 'Культ',
    'древнегреческая мифология': 'Грецька міфологія', 'греческая мифология': 'Грецька міфологія',
    'подводный мир': 'Підводний світ', 'морской мир': 'Підводний світ', 'водный мир': 'Підводний світ',
    'славянская мифология': "Слов'янська міфологія", 'стимпанк': 'Стімпанк',
    'религиозное фэнтези': 'Біблійне фентезі', 'библейское фэнтези': 'Біблійне фентезі', 'сказки': 'Казки',
    'спорт': 'Спорт', 'технофэнтези': 'Технофентезі', 'ужасы': 'Жахи', 'мультипликация': 'Мультяшний',
    'мултяшная': 'Мультяшний', 'цирк': 'Цирк', 'супергерои': 'Супергерої', 'китай': 'Китай',
    'настольные игры': 'Настільні ігри', 'загробный мир': 'Потойбіччя', 'страдающее средневековье': 'Середньовіччя',
    'меха': 'Меха', 'шпионы': 'Шпигуни', 'мир снов': 'Світ снів', 'микромир': 'Мікросвіт', 'киберпанк': 'Кіберпанк',
    'симулятор бога': 'Симулятор бога', 'sci-fi фэнтези': 'Sci-Fi', '1001 ночь': '1001 ніч',
}
STATUS_UK = {
    'пройдено': 'Пройдено', 'обзор': 'Огляд', 'дропнуто': 'Закинуто', 'жду релиз': 'Чекає релізу',
    'в процессе': 'У процесі', 'на холде': 'На паузі', 'хочу поиграть': 'Хоче пограти', 'не играл': 'Не грав',
}
FEATURE_FIX = {'декблидер': 'декбилдер'}
COLLECTION_UK = {
    'золотой список': 'Золотий список', 'топ карточных': 'Топ карткових', 'топ экшен': 'Топ екшн',
    'топ для новичков': 'Для новачків', 'уникальные': 'Унікальні', 'топ кооперативов': 'Топ кооперативів',
}


def norm(s):
    s = unicodedata.normalize('NFKC', str(s)).strip().lower().replace('ё', 'е').replace('фэнтэзи', 'фэнтези')
    return re.sub(r'\s+', ' ', s)


def name_key(s):
    return re.sub(r'[^0-9a-zа-яіїєґ]+', '', norm(s))


def split(v):
    return [x.strip() for x in str(v).split(',') if x.strip()] if isinstance(v, str) else []


def val(c):
    v = c.value
    return None if isinstance(v, str) and v.startswith('=') else v


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def date(v):
    return v.date().isoformat() if isinstance(v, dt.datetime) else None


def link(c):
    return c.hyperlink.target if c.hyperlink and c.hyperlink.target else None


wb = openpyxl.load_workbook(SRC)
ws = wb['Все рогалики']
hdr = {norm(c.value): c.column - 1 for c in ws[1] if isinstance(c.value, str) and c.value.strip()}
# «Название» в шапці стоїть над стовпцем B, але самі назви з посиланнями лежать у C
COL = {
    'name': 2, 'genre': hdr['жанр'], 'features': hdr['особенности'], 'setting': hdr['сеттинг'],
    'difficulty': hdr['сложность'], 'hours': hdr['наиграно (часы)'], 'status': hdr['статус'],
    'progress': hdr['прогресс (%)'], 'rating': hdr['оценка (?/10)'], 'release': hdr['дата выхода'],
    'played': hdr['когда играл'], 'notes': hdr['примечания'], 'youtube': hdr['youtube прохождение'],
    'mi': hdr['проводил ми'], 'mi_link': hdr['выпуск ми'],
}

feat_variants = collections.defaultdict(collections.Counter)
games = []
for r in ws.iter_rows(min_row=2):
    name = val(r[COL['name']])
    if not name:
        continue
    url = link(r[COL['name']])
    m = re.search(r'store\.steampowered\.com/app/(\d+)', url or '')
    feats = []
    for f in split(val(r[COL['features']])):
        k = FEATURE_FIX.get(norm(f), norm(f))
        feat_variants[k][f[0].upper() + f[1:]] += 1
        if k not in feats:
            feats.append(k)
    g = {
        'name': str(name).strip(),
        'url': url,
        'appid': int(m.group(1)) if m else None,
        'genres': list(dict.fromkeys(GENRE_UK.get(norm(x), x) for x in split(val(r[COL['genre']])))),
        'settings': list(dict.fromkeys(SETTING_UK.get(norm(x), x) for x in split(val(r[COL['setting']])))),
        'features': feats,
        'difficulty': num(val(r[COL['difficulty']])),
        'tian_hours': num(val(r[COL['hours']])),
        'status': STATUS_UK.get(norm(val(r[COL['status']]) or ''), val(r[COL['status']])),
        'progress': num(val(r[COL['progress']])),
        'rating': num(val(r[COL['rating']])),
        'release': date(val(r[COL['release']])),
        'tian_played': date(val(r[COL['played']])),
        'notes': val(r[COL['notes']]) or '',
        'youtube': link(r[COL['youtube']]),
        'mi': val(r[COL['mi']]) is True,
        'mi_link': link(r[COL['mi_link']]),
    }
    g['key'] = str(g['appid']) if g['appid'] else 'n:' + name_key(g['name'])
    games.append(g)

# Для кожної особливості показуємо найчастіше написання
feat_label = {k: c.most_common(1)[0][0] for k, c in feat_variants.items()}
for g in games:
    g['features'] = [feat_label[k] for k in g['features']]

# Добірки від Тіана: заголовок у рядку 1, назви ігор у стовпці через один праворуч
by_name = {name_key(g['name']): g for g in games}
collections_out, unmatched = [], []
cs = wb['Подборки от Тиана']
for c in cs[1]:
    if not isinstance(c.value, str) or not c.value.strip():
        continue
    items = []
    for row in cs.iter_rows(min_row=2, min_col=c.column + 2, max_col=c.column + 2):
        v = val(row[0])
        if not v:
            continue
        g = by_name.get(name_key(v))
        if g is None:  # «Hades 2» vs «Hades II» тощо: шукаємо за префіксом
            g = next((x for k, x in by_name.items() if k.startswith(name_key(v)) or name_key(v).startswith(k) and len(k) > 4), None)
        if g:
            items.append(g['key'])
        else:
            unmatched.append(f'{c.value.strip()}: {v}')
    title = c.value.strip()
    title = COLLECTION_UK.get(norm(title), title[0] + title[1:].lower())
    collections_out.append({'name': title, 'items': items})

# Дані магазину Steam: обкладинка, відгуки, ціна
API = 'https://api.steampowered.com/IStoreBrowseService/GetItems/v1/'
appids = [g['appid'] for g in games if g['appid']]
store = {}
for i in range(0, len(appids), 100):
    inp = {
        'ids': [{'appid': a} for a in appids[i:i + 100]],
        'context': {'language': 'ukrainian', 'country_code': 'UA'},
        'data_request': {'include_assets': True, 'include_reviews': True, 'include_release': True,
                         'include_all_purchase_options': True, 'include_tag_count': 20},
    }
    with urllib.request.urlopen(API + '?' + urllib.parse.urlencode({'input_json': json.dumps(inp)}), timeout=60) as resp:
        for it in json.load(resp)['response'].get('store_items', []):
            if it.get('success') == 1:
                store[it['appid']] = it
    print(f'\rДані магазину: {min(i + 100, len(appids))}/{len(appids)}', end='')
print()

for g in games:
    it = store.get(g['appid'])
    if not it:
        continue
    a = it.get('assets') or {}
    if a.get('header'):
        g['image'] = 'https://shared.akamai.steamstatic.com/store_item_assets/' + a['asset_url_format'].replace('${FILENAME}', a['header'])
    rev = (it.get('reviews') or {}).get('summary_filtered') or {}
    if rev.get('review_count'):
        g['steam_pct'], g['steam_reviews'] = rev.get('percent_positive'), rev['review_count']
    p = it.get('best_purchase_option') or {}
    if p.get('formatted_final_price'):
        g['price'] = p['formatted_final_price']
        g['price_uah'] = int(p.get('final_price_in_cents', 0)) / 100
        if p.get('discount_pct'):
            g['discount'] = p['discount_pct']
            orig = int(p.get('original_price_in_cents') or 0) / 100
            if orig > g['price_uah']:
                g['price_orig_uah'] = orig
                g['saving_uah'] = round(orig - g['price_uah'], 2)
    elif it.get('is_free'):
        g['price'], g['price_uah'] = 'Безкоштовно', 0
    if (it.get('release') or {}).get('is_coming_soon'):
        g['coming_soon'] = True
    if it.get('is_early_access'):
        g['early_access'] = True
    # Режими гри (кооп, Remote Play Together, PvP, геймпад…) і теги гравців Steam (за вагою)
    cats = it.get('categories') or {}
    g['categories'] = sorted({c for k in ('supported_player_categoryids', 'feature_categoryids', 'controller_categoryids')
                              for c in cats.get(k, [])})
    g['tags'] = [t['tagid'] for t in it.get('tags') or []]

# Назви тегів англійською й українською
tag_names = {}
for lang, key in (('english', 'en'), ('ukrainian', 'uk')):
    url = 'https://api.steampowered.com/IStoreService/GetTagList/v1/?' + urllib.parse.urlencode({'language': lang})
    with urllib.request.urlopen(url, timeout=60) as resp:
        for t in json.load(resp)['response'].get('tags', []):
            tag_names.setdefault(t['tagid'], {})[key] = t['name']
used_tags = {tid for g in games for tid in g.get('tags', [])}

payload = {
    'updated': dt.datetime.now().isoformat(timespec='minutes'),
    'source': SRC_LABEL,
    'games': games,
    'collections': collections_out,
    'tags': {tid: tag_names.get(tid, {'en': str(tid)}) for tid in sorted(used_tags)},
}
OUT.write_text('// Згенеровано import-roguelikes.py\nwindow.ROGUELIKES = ' + json.dumps(payload, ensure_ascii=False) + ';\n', encoding='utf-8')

print(f'Ігор: {len(games)} (зі Steam: {len(appids)}, знайдено в магазині: {len(store)})')
print(f'Добірки: ' + ', '.join(f"{c['name']} ({len(c['items'])})" for c in collections_out))
if unmatched:
    print('Не знайдено в таблиці для добірок:', '; '.join(unmatched))
print(f'Збережено {OUT.name}')

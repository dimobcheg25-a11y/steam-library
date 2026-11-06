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
import time
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
region_locked = set()
for i in range(0, len(appids), 100):
    inp = {
        'ids': [{'appid': a} for a in appids[i:i + 100]],
        'context': {'language': 'ukrainian', 'country_code': 'UA'},
        'data_request': {'include_assets': True, 'include_reviews': True, 'include_release': True,
                         'include_all_purchase_options': True, 'include_tag_count': 20,
                         'include_basic_info': True},
    }
    with urllib.request.urlopen(API + '?' + urllib.parse.urlencode({'input_json': json.dumps(inp)}), timeout=60) as resp:
        for it in json.load(resp)['response'].get('store_items', []):
            if it.get('success') == 1:
                store[it['appid']] = it
            elif it.get('unvailable_for_country_restriction'):
                region_locked.add(it.get('appid') or it.get('id'))
    print(f'\rДані магазину: {min(i + 100, len(appids))}/{len(appids)}', end='')
print()

def no_price_reason(g, it):
    """Чому в гри немає ціни Steam (показується на сторінці замість ціни)."""
    if not g['appid']:
        host = urllib.parse.urlparse(g.get('url') or '').netloc.lower()
        for k, v in (('epicgames', 'Epic Games Store'), ('gog.com', 'GOG'), ('playstation', 'PlayStation'),
                     ('xbox', 'Xbox'), ('nintendo', 'Nintendo'), ('itch.io', 'itch.io')):
            if k in host:
                return f'Немає в Steam, є в {v}'
        return 'Немає в Steam' + (f', сайт {host.removeprefix("www.")}' if host else '')
    if not it:
        if g['appid'] in region_locked:
            return 'Недоступна в Україні'
        return 'Сторінку прибрано зі Steam'
    if (it.get('release') or {}).get('is_coming_soon'):
        return 'Ще не вийшла'
    return 'Не продається в Steam'


for g in games:
    it = store.get(g['appid'])
    if not it:
        g['no_price'] = no_price_reason(g, None)
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
    if 'price' not in g:
        g['no_price'] = no_price_reason(g, it)
    if it.get('is_early_access'):
        g['early_access'] = True
    # Режими гри (кооп, Remote Play Together, PvP, геймпад…) і теги гравців Steam (за вагою)
    cats = it.get('categories') or {}
    g['categories'] = sorted({c for k in ('supported_player_categoryids', 'feature_categoryids', 'controller_categoryids')
                              for c in cats.get(k, [])})
    g['tags'] = [t['tagid'] for t in it.get('tags') or []]
    bi = it.get('basic_info') or {}
    g['developers'] = [d['name'] for d in bi.get('developers') or [] if d.get('name')]
    g['publishers'] = [d['name'] for d in bi.get('publishers') or [] if d.get('name')]


# ---------- Перевірка на зв'язок із РФ (Wikidata) ----------
# Гра позначається, якщо Wikidata підтверджує, що Росія — країна її розробника, видавця або самої гри.
# Перевіряються всі ігри при кожному імпорті (нові теж); відповіді кешуються в ru-cache.json на 30 днів.
RU_CACHE = HERE / 'ru-cache.json'
RU_TTL = 30 * 24 * 3600
WD_HEADERS = {'User-Agent': 'steam-library-stats/1.0 (personal project)', 'Accept': 'application/sparql-results+json',
              'Content-Type': 'application/x-www-form-urlencoded'}


def sparql(q):
    for attempt in range(1, 5):
        try:
            req = urllib.request.Request('https://query.wikidata.org/sparql',
                                         data=urllib.parse.urlencode({'query': q}).encode(), headers=WD_HEADERS)
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.load(resp)['results']['bindings']
        except Exception:
            if attempt == 4:
                raise
            time.sleep(attempt * 5)  # Wikidata обмежує частоту запитів


def ru_check(games):
    try:
        cache = json.loads(RU_CACHE.read_text(encoding='utf-8'))
    except Exception:
        cache = {}
    apps, names = cache.setdefault('apps', {}), cache.setdefault('names', {})
    now = time.time()
    fresh = lambda e: e and now - e.get('t', 0) < RU_TTL
    failed = 0

    # 1. За appid: країна розробника (P178), видавця (P123) і самої гри (P495)
    todo = [str(g['appid']) for g in games if g['appid'] and not fresh(apps.get(str(g['appid'])))]
    role_q = {
        'розробник': 'wdt:P178', 'видавець': 'wdt:P123',
    }
    for i in range(0, len(todo), 25):
        chunk = todo[i:i + 25]
        values = ' '.join(json.dumps(a) for a in chunk)
        found = {a: [] for a in chunk}
        try:
            for role, prop in role_q.items():
                for b in sparql(f'''SELECT ?appid ?name WHERE {{ VALUES ?appid {{ {values} }} ?g wdt:P1733 ?appid.
                    ?g {prop} ?e. ?e wdt:P17|wdt:P159/wdt:P17 wd:Q159.
                    OPTIONAL {{ ?e rdfs:label ?name FILTER(lang(?name)="en") }} }}'''):
                    found[b['appid']['value']].append(f"{role} {b.get('name', {}).get('value', '')}".strip())
            for b in sparql(f'SELECT ?appid WHERE {{ VALUES ?appid {{ {values} }} ?g wdt:P1733 ?appid; wdt:P495 wd:Q159 }}'):
                found[b['appid']['value']].append('країна гри — Росія')
        except Exception:
            failed += len(chunk)
            continue
        for a, why in found.items():
            apps[a] = {'t': now, 'ru': sorted(set(why))}
        print(f'\rПеревірка РФ (ігри): {min(i + 25, len(todo))}/{len(todo)}', end='')
    if todo:
        print()

    # 2. За назвами студій і видавців зі Steam (Wikidata часто не знає, хто зробив гру, але знає студію)
    todo = sorted({n for g in games for n in g.get('developers', []) + g.get('publishers', []) if not fresh(names.get(n))})
    for i in range(0, len(todo), 10):
        chunk = todo[i:i + 10]
        values = ' '.join(json.dumps(n) + '@en' for n in chunk)
        try:
            hits = {b['n']['value'] for b in sparql(f'''SELECT DISTINCT ?n WHERE {{ VALUES ?n {{ {values} }}
                ?e rdfs:label|skos:altLabel ?n. ?e wdt:P31/wdt:P279* ?t.
                VALUES ?t {{ wd:Q4830453 wd:Q210167 wd:Q1137109 wd:Q43229 wd:Q5 }}
                ?e wdt:P17|wdt:P159/wdt:P17|wdt:P27 wd:Q159 }}''')}
        except Exception:
            failed += len(chunk)
            continue
        for n in chunk:
            names[n] = {'t': now, 'ru': n in hits}
        print(f'\rПеревірка РФ (студії): {min(i + 10, len(todo))}/{len(todo)}', end='')
    if todo:
        print()
    if failed:
        print(f'Wikidata не відповіла для {failed} запитів — для них використано старий кеш, решту перевірить наступний імпорт')

    RU_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
    for g in games:
        why = list((apps.get(str(g['appid'])) or {}).get('ru', [])) if g['appid'] else []
        why += [f'розробник {n}' for n in g.get('developers', []) if (names.get(n) or {}).get('ru')]
        why += [f'видавець {n}' for n in g.get('publishers', []) if (names.get(n) or {}).get('ru')]
        if why:
            g['ru'] = sorted(set(why), key=why.index)
    flagged = [g['name'] for g in games if g.get('ru')]
    print(f"Пов'язані з РФ: {len(flagged)} — " + ', '.join(flagged))


ru_check(games)

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

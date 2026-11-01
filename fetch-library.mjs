// Завантажує список власних ігор Steam + ігор із сімейної бібліотеки.
// Запуск: node fetch-library.mjs
// Результат: data.js для index.html та roguelikes.html.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';

const ENV_URL = new URL('./.env', import.meta.url);
if (!existsSync(ENV_URL)) {
  console.error('Немає файлу .env. Скопіюйте .env.example у .env і заповніть ключі (див. README.md).');
  process.exit(1);
}
const env = Object.fromEntries(
  readFileSync(ENV_URL, 'utf8')
    .split(/\r?\n/)
    .filter((l) => /^\s*[A-Z_]+\s*=/.test(l))
    .map((l) => {
      const i = l.indexOf('=');
      return [l.slice(0, i).trim(), l.slice(i + 1).trim()];
    }),
);
const { STEAM_API_KEY: KEY, STEAM_ID: STEAM_ID, STEAM_ACCESS_TOKEN: TOKEN } = env;
if (!KEY || !STEAM_ID) throw new Error('Заповніть STEAM_API_KEY і STEAM_ID у .env');

const API = 'https://api.steampowered.com';

async function call(path, params, label) {
  const url = `${API}/${path}?${new URLSearchParams(params)}`;
  const res = await fetch(url);
  // Не друкуємо URL: у ньому ключ/токен.
  if (!res.ok) throw new Error(`${label}: HTTP ${res.status} ${res.statusText}`);
  const body = await res.json();
  return body.response ?? body;
}

// 1. Власні ігри
const owned = await call(
  'IPlayerService/GetOwnedGames/v1/',
  { key: KEY, steamid: STEAM_ID, include_appinfo: 1, include_played_free_games: 1 },
  'GetOwnedGames',
);
const ownedGames = owned.games ?? [];
console.log(`Власні ігри: ${ownedGames.length}`);

// 2. Сімейна бібліотека
let familyApps = [];
if (!TOKEN) {
  console.log('STEAM_ACCESS_TOKEN порожній — сімейну бібліотеку пропущено.');
} else {
  try {
    const fam = await call(
      'IFamilyGroupsService/GetFamilyGroupForUser/v1/',
      { access_token: TOKEN, steamid: STEAM_ID },
      'GetFamilyGroupForUser',
    );
    const gid = fam.family_groupid;
    if (!gid || gid === '0') {
      console.log('Сімейну групу не знайдено (ви не в Steam Family?).');
    } else {
      const shared = await call(
        'IFamilyGroupsService/GetSharedLibraryApps/v1/',
        { access_token: TOKEN, family_groupid: gid, include_own: true, include_excluded: true, steamid: STEAM_ID },
        'GetSharedLibraryApps',
      );
      familyApps = shared.apps ?? [];
      console.log(`Сімейна бібліотека (разом із вашими): ${familyApps.length}`);
    }
  } catch (e) {
    console.log(`Сімейна бібліотека не завантажилась: ${e.message}`);
    console.log('Найімовірніше, токен протермінований — візьміть новий.');
  }
}

// 3. Імена власників
const ownerIds = [...new Set(familyApps.flatMap((a) => a.owner_steamids ?? []).map(String))];
const names = {};
for (let i = 0; i < ownerIds.length; i += 100) {
  const r = await call(
    'ISteamUser/GetPlayerSummaries/v2/',
    { key: KEY, steamids: ownerIds.slice(i, i + 100).join(',') },
    'GetPlayerSummaries',
  );
  for (const p of r.players ?? []) names[p.steamid] = p.personaname;
}

// 4. Об'єднання за appid
const byId = new Map();
for (const g of ownedGames) {
  byId.set(g.appid, {
    appid: g.appid,
    name: g.name,
    source: 'own',
    owners: names[STEAM_ID] ?? 'me',
    playtime_hours: +(g.playtime_forever / 60).toFixed(1),
    last_played: g.rtime_last_played ? new Date(g.rtime_last_played * 1000).toISOString().slice(0, 10) : '',
  });
}
for (const a of familyApps) {
  const ownerList = (a.owner_steamids ?? []).map(String);
  const ownersStr = ownerList.map((id) => names[id] ?? id).join('; ');
  const existing = byId.get(a.appid);
  if (existing) {
    existing.owners = ownersStr || existing.owners;
    continue;
  }
  if (ownerList.includes(STEAM_ID)) continue; // своя, але не гра (напр. софт) — GetOwnedGames її не повернув
  byId.set(a.appid, {
    appid: a.appid,
    name: a.name ?? '',
    source: 'family',
    owners: ownersStr,
    playtime_hours: a.rt_playtime ? +(a.rt_playtime / 60).toFixed(1) : 0,
    last_played: a.rt_last_played ? new Date(a.rt_last_played * 1000).toISOString().slice(0, 10) : '',
  });
}

const rows = [...byId.values()].sort((x, y) => x.name.localeCompare(y.name));

// 5. Дані з магазину: теги, відгуки, реліз, обкладинки (кешуються в store-cache.json)
const CACHE_URL = new URL('./store-cache.json', import.meta.url);
let cache = {};
try { cache = JSON.parse(readFileSync(CACHE_URL, 'utf8')); } catch {}
const CACHE_TTL = 7 * 24 * 3600 * 1000; // теги/відгуки оновлюємо раз на тиждень
const stale = rows.filter((r) => !cache[r.appid] || Date.now() - cache[r.appid].fetched > CACHE_TTL);
for (let i = 0; i < stale.length; i += 100) {
  const chunk = stale.slice(i, i + 100);
  const input = {
    ids: chunk.map((r) => ({ appid: r.appid })),
    context: { language: 'ukrainian', country_code: 'UA' },
    data_request: {
      include_tag_count: 20, include_basic_info: true, include_reviews: true,
      include_release: true, include_platforms: true, include_assets: true,
    },
  };
  const r = await call('IStoreBrowseService/GetItems/v1/', { input_json: JSON.stringify(input) }, 'GetItems');
  for (const it of r.store_items ?? []) {
    cache[it.appid ?? it.id] = { fetched: Date.now(), item: it.success === 1 ? it : null };
  }
  process.stdout.write(`\rДані магазину: ${Math.min(i + 100, stale.length)}/${stale.length}`);
}
if (stale.length) console.log();
writeFileSync(CACHE_URL, JSON.stringify(cache));

const tagNames = {};
for (const lang of ['english', 'ukrainian']) {
  const t = await call('IStoreService/GetTagList/v1/', { language: lang }, 'GetTagList');
  for (const { tagid, name } of t.tags ?? []) (tagNames[tagid] ??= {})[lang === 'english' ? 'en' : 'uk'] = name;
}

let noStore = 0;
for (const r of rows) {
  const it = cache[r.appid]?.item;
  if (!it) { noStore++; r.tags = []; continue; }
  r.tags = (it.tags ?? []).map((t) => t.tagid);
  r.categories = [
    ...(it.categories?.supported_player_categoryids ?? []),
    ...(it.categories?.feature_categoryids ?? []),
    ...(it.categories?.controller_categoryids ?? []),
  ];
  const rev = it.reviews?.summary_filtered;
  if (rev?.review_count) {
    r.review_pct = rev.percent_positive;
    r.review_count = rev.review_count;
    r.review_label = rev.review_score_label;
  }
  const rel = it.release?.steam_release_date ?? it.release?.original_release_date;
  if (rel) r.release = new Date(rel * 1000).toISOString().slice(0, 10);
  r.early_access = !!it.is_early_access;
  r.description = it.basic_info?.short_description ?? '';
  r.developers = (it.basic_info?.developers ?? []).map((d) => d.name).join(', ');
  const a = it.assets;
  if (a?.header) r.image = 'https://shared.akamai.steamstatic.com/store_item_assets/' + a.asset_url_format.replace('${FILENAME}', a.header);
  r.platforms = Object.entries(it.platforms ?? {}).filter(([k, v]) => v === true).map(([k]) => k);
}
if (noStore) console.log(`Без сторінки в магазині (видалені/приховані): ${noStore}`);

const usedTags = Object.fromEntries([...new Set(rows.flatMap((r) => r.tags))].map((id) => [id, tagNames[id] ?? { en: String(id) }]));
writeFileSync(
  new URL('./data.js', import.meta.url),
  `// Згенеровано fetch-library.mjs ${new Date().toISOString()}\nwindow.LIBRARY = ${JSON.stringify({ updated: new Date().toISOString(), me: STEAM_ID, games: rows, tags: usedTags })};\n`,
);


const fam = rows.filter((r) => r.source === 'family').length;
console.log(`\nУсього унікальних: ${rows.length} (власних ${rows.length - fam}, лише з сім'ї ${fam})`);
console.log('Збережено data.js — відкрийте index.html');

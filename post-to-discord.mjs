// Публікує в Discord топ-10 рогаликів зі знижкою, які я або Тіан оцінили на 7+.
// Запуск: node post-to-discord.mjs            → надсилає в канал (DISCORD_WEBHOOK_URL у .env)
//         node post-to-discord.mjs --dry-run  → лише показує список, нічого не надсилає
// Дані: roguelikes.js (ціни й знижки з import-roguelikes.py), my-ratings.js.
// Нотатки Тіана (російською) перекладаються через Google Translate і кешуються в notes-uk.json,
// переклад там можна виправити вручну: він не зміниться, доки Тіан не змінить нотатку.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import vm from 'node:vm';

const MIN_RATING = 7;
const LIMIT = 10; // Discord дозволяє максимум 10 embed-ів в одному повідомленні
const DRY_RUN = process.argv.includes('--dry-run');

const here = (f) => new URL(`./${f}`, import.meta.url);

function readEnv() {
  if (!existsSync(here('.env'))) return {};
  return Object.fromEntries(
    readFileSync(here('.env'), 'utf8')
      .split(/\r?\n/)
      .filter((l) => /^\s*[A-Z_]+\s*=/.test(l))
      .map((l) => {
        const i = l.indexOf('=');
        return [l.slice(0, i).trim(), l.slice(i + 1).trim()];
      }),
  );
}

// Файли даних мають вигляд `window.X = {...}`, тож виконуємо їх в ізольованому контексті.
function loadWindowFile(file, required) {
  if (!existsSync(here(file))) {
    if (required) throw new Error(`Немає ${file}. Спершу запустіть python import-roguelikes.py`);
    return {};
  }
  const ctx = { window: {} };
  vm.runInNewContext(readFileSync(here(file), 'utf8'), ctx, { filename: file });
  return ctx.window;
}

const { ROGUELIKES } = loadWindowFile('roguelikes.js', true);
const { MY_RATINGS } = loadWindowFile('my-ratings.js', false);

const myRatings = MY_RATINGS?.ratings || {};

const picks = ROGUELIKES.games
  .filter((g) => g.appid && g.discount > 0)
  .map((g) => ({ ...g, mine: myRatings[g.appid] ?? null }))
  .filter((g) => (g.rating ?? 0) >= MIN_RATING || (g.mine ?? 0) >= MIN_RATING)
  .sort(
    (a, b) =>
      b.discount - a.discount ||
      Math.max(b.rating ?? 0, b.mine ?? 0) - Math.max(a.rating ?? 0, a.mine ?? 0) ||
      (b.saving_uah ?? 0) - (a.saving_uah ?? 0),
  )
  .slice(0, LIMIT);

function colorFor(discount) {
  if (discount >= 75) return 0xe74c3c;
  if (discount >= 50) return 0xe67e22;
  return 0x2ecc71;
}

const fmt = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(1).replace('.', ','));
const uah = (n) => `${fmt(n)}₴`;

// ---- Переклад нотаток Тіана ru → uk з кешем ----
const CACHE_FILE = here('notes-uk.json');
const cache = existsSync(CACHE_FILE) ? JSON.parse(readFileSync(CACHE_FILE, 'utf8')) : {};
let cacheChanged = false;

async function translate(text) {
  const url =
    'https://translate.googleapis.com/translate_a/single?client=gtx&sl=ru&tl=uk&dt=t&q=' +
    encodeURIComponent(text);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Google Translate ${res.status}`);
  const data = await res.json();
  return data[0].map((part) => part[0]).join('').trim();
}

async function noteUk(g) {
  const ru = g.notes?.trim();
  if (!ru) return '';
  const hit = cache[g.appid];
  if (hit?.ru === ru) return hit.uk;
  try {
    const uk = await translate(ru);
    cache[g.appid] = { name: g.name, ru, uk };
    cacheChanged = true;
    return uk;
  } catch (e) {
    console.error(`Не вдалося перекласти нотатку до «${g.name}»: ${e.message}`);
    return '';
  }
}

const embeds = [];
for (const [i, g] of picks.entries()) {
  const price = g.price_orig_uah
    ? `~~${uah(g.price_orig_uah)}~~ → **${uah(g.price_uah)}**`
    : `**${g.price}**`;
  const genre = g.genres?.length ? `🎮 ${g.genres.join(', ')}` : '';
  const note = await noteUk(g);
  embeds.push({
    title: `${i + 1}. ${g.name} — −${g.discount}%`,
    url: g.url,
    color: colorFor(g.discount),
    description: [price, genre, note].filter(Boolean).join('\n'),
    ...(g.image ? { thumbnail: { url: g.image } } : {}),
  });
}
if (cacheChanged) writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 1) + '\n');

const updated = ROGUELIKES.updated?.replace('T', ' ') ?? '?';
const content = picks.length
  ? `🔥 **Топ-${picks.length} знижок на рогалики**\n-# ціни Steam (UAH) станом на ${updated}`
  : `😴 Зараз немає знижок на рогалики з оцінкою ${MIN_RATING}+ (ціни станом на ${updated}).`;

if (DRY_RUN) {
  console.log(content.replace(/\*\*|-# /g, ''));
  for (const e of embeds) console.log(`\n${e.title}\n${e.description.replace(/\*\*|~~/g, '')}`);
  process.exit(0);
}

const { DISCORD_WEBHOOK_URL: WEBHOOK } = readEnv();
if (!WEBHOOK) {
  console.error('Заповніть DISCORD_WEBHOOK_URL у .env (див. README.md).');
  process.exit(1);
}

const res = await fetch(WEBHOOK, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'Знижки на рогалики',
    content,
    embeds,
    allowed_mentions: { parse: [] },
  }),
});
if (!res.ok) {
  console.error(`Discord відповів ${res.status}: ${await res.text()}`);
  process.exit(1);
}
console.log(`Надіслано в Discord: ${picks.length} ігор`);

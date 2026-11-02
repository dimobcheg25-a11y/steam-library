// Публікує в Discord топ-10 рогаликів зі знижкою, які я або Тіан оцінили на 7+.
// Запуск: node post-to-discord.mjs            → надсилає в канал (DISCORD_WEBHOOK_URL у .env)
//         node post-to-discord.mjs --dry-run  → лише показує список, нічого не надсилає
// Дані: roguelikes.js (ціни й знижки з import-roguelikes.py), my-ratings.js, data.js (необов'язково).
import { existsSync, readFileSync } from 'node:fs';
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
const { LIBRARY } = loadWindowFile('data.js', false);

const myRatings = MY_RATINGS?.ratings || {};
const owned = new Map((LIBRARY?.games || []).map((g) => [g.appid, g]));

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

const fmt = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(1).replace('.', ','));
const uah = (n) => `${fmt(n)}₴`;

function ratingLine(g) {
  const parts = [];
  if (g.rating != null) parts.push(`Тіан **${fmt(g.rating)}**`);
  if (g.mine != null) parts.push(`я **${fmt(g.mine)}**`);
  return parts.join(' · ');
}

function ownerNote(g) {
  const lib = owned.get(g.appid);
  if (!lib) return '';
  return lib.source === 'family' ? `\n👪 Є в сімейній бібліотеці (${lib.owners})` : '\n✅ Вже є в мене';
}

function colorFor(discount) {
  if (discount >= 75) return 0xe74c3c;
  if (discount >= 50) return 0xe67e22;
  return 0x2ecc71;
}

const embeds = picks.map((g, i) => {
  const price = g.price_orig_uah
    ? `~~${uah(g.price_orig_uah)}~~ → **${uah(g.price_uah)}**`
    : `**${g.price}**`;
  const extra = [g.genres?.join(', '), g.difficulty != null ? `складність ${fmt(g.difficulty)}/10` : '']
    .filter(Boolean)
    .join(' · ');
  return {
    title: `${i + 1}. ${g.name} — −${g.discount}%`,
    url: g.url,
    color: colorFor(g.discount),
    description: `${price}\n⭐ ${ratingLine(g)}${extra ? `\n${extra}` : ''}${ownerNote(g)}`,
    ...(g.image ? { thumbnail: { url: g.image } } : {}),
  };
});

const updated = ROGUELIKES.updated?.replace('T', ' ') ?? '?';
const content = picks.length
  ? `🔥 **Топ-${picks.length} знижок на рогалики** (оцінка Тіана або моя ${MIN_RATING}+)\n-# ціни Steam (UAH) станом на ${updated}`
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

# Моя бібліотека Steam

Локальний сайт для вашої бібліотеки Steam. Відкривається з диска, без сервера й хостингу. Що в ньому є:

- **Моя бібліотека** (`index.html`). Усі ваші ігри разом з іграми зі Steam Family (сімейної бібліотеки). Фільтри за тегами Steam і швидкі добірки: рогалики, паті з друзями, метроїдванії та інші. Також фільтри «грав / не грав» і «моя / сімейна» (та чия саме), за режимом гри, відгуками й роком. Кнопка «🎲 Що зіграти?».
- **Рогалики Тіана** (`roguelikes.html`). [Таблиця рогаликів TianKami](https://docs.google.com/spreadsheets/d/16-b4LC_n2g1pq2fVGkUJyRsq9xklzlRpIwVH5Gv3C4U/edit) з його оцінками, складністю, нотатками й добірками. Кожна гра зіставлена з вашою бібліотекою, а для ігор, яких у вас немає, видно поточні ціни й знижки Steam.

## Що потрібно

- [Node.js](https://nodejs.org/) 18 або новіший
- [Python](https://www.python.org/) 3.10 або новіший, плюс бібліотека openpyxl: `pip install -r requirements.txt`
- Акаунт Steam, у якому витрачено щонайменше $5. Без цього Steam не видасть API-ключ.

## Налаштування (≈5 хвилин)

1. Скопіюйте `.env.example` у `.env`.
2. **STEAM_API_KEY**. Зареєструйте ключ на <https://steamcommunity.com/dev/apikey>. У полі «Domain Name» можна вписати `localhost`.
3. **STEAM_ID**. Це ваш SteamID64 (17 цифр). Його видно на <https://steamid.io> або в адресі вашого профілю.
4. **STEAM_ACCESS_TOKEN**. Потрібен лише для сімейної бібліотеки й діє близько доби.
   - Увійдіть у <https://store.steampowered.com/> (угорі справа має з'явитися ваш нік).
   - Відкрийте <https://store.steampowered.com/pluginapi/getwebapitoken> і скопіюйте значення `webapi_token` (довгий рядок, що починається на `eyJ`).
   - Якщо сторінка просто перекидає на головну, відкрийте store.steampowered.com, натисніть F12 → Console і виконайте:
     ```js
     JSON.parse(document.getElementById('application_config').dataset.store_user_config).webapi_token
     ```
   - ⚠️ Токен дає доступ до вашого акаунта. Нікому його не пересилайте.

## Запуск

```sh
node fetch-library.mjs          # ваша бібліотека → data.js
python import-roguelikes.py     # таблиця Тіана + ціни → roguelikes.js
```

Після цього відкрийте `index.html` подвійним кліком.

Список ігор оновлюйте тією самою командою `node fetch-library.mjs`, коли з'являються нові ігри. Якщо сімейні ігри не підтягнулися, значить, протермінувався токен: візьміть новий (крок 4).

## Автооновлення таблиці Тіана й знижок (необов'язково)

Відкрийте PowerShell **у папці проєкту** і виконайте:

```powershell
$dir      = (Resolve-Path .).Path
$action   = New-ScheduledTaskAction -Execute "$dir\update-prices.cmd" -WorkingDirectory $dir
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Thursday -At 19:00
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName "SteamLibrary - discounts" -Action $action -Trigger $trigger -Settings $settings
```

Щопонеділка й щочетверга о 19:00 завантажуватиметься свіжа таблиця Тіана й ціни. Steam запускає тижневі знижки в понеділок, а великі розпродажі й фестивалі здебільшого в четвер, обидва рази о 10:00 за тихоокеанським часом (20:00 за Києвом). Журнал запусків пишеться в `update-prices.log`. Щоб вимкнути автооновлення: `Unregister-ScheduledTask -TaskName "SteamLibrary - discounts"`.

## Знижки в Discord (необов'язково)

`post-to-discord.mjs` публікує одним повідомленням до 10 рогаликів зі знижкою, які Тіан або ви оцінили на 7 і вище. Першими йдуть ігри з найбільшою знижкою. У кожній картці: ціна, жанр і коротка нотатка Тіана, перекладена українською. Переклади кешуються в `notes-uk.json`: невдалий переклад можна виправити там вручну, і він не зміниться, доки Тіан не змінить нотатку. Показана гра не повертається в підбірку 7 днів (показали в понеділок — не буде в четвер; показали в четвер — не буде в наступний понеділок). Дати показу записуються в `discord-posted.json`, а місце пропущених ігор займають наступні за списком. `--dry-run` нічого туди не записує.

1. У Discord відкрийте налаштування каналу → «Інтеграції» → «Вебхуки» → «Новий вебхук» і скопіюйте URL.
2. Впишіть його в `.env`: `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...`. ⚠️ Хто має цей URL, той може писати в канал.
3. Перевірте список без надсилання: `node post-to-discord.mjs --dry-run`. Надіслати: `node post-to-discord.mjs`.

Якщо налаштоване автооновлення, `update-prices.cmd` сам надсилає повідомлення після кожного оновлення цін.

## Файли

| Файл | Що це |
|---|---|
| `index.html`, `roguelikes.html`, `style.css` | сайт |
| `fetch-library.mjs` | завантажує бібліотеку, теги й відгуки (Steam Web API) |
| `import-roguelikes.py` | завантажує таблицю Тіана й ціни |
| `post-to-discord.mjs` | публікує топ-10 знижок на рогалики в Discord |
| `update-prices.cmd` | обгортка для Планувальника завдань: оновлює ціни й публікує в Discord |
| `my-ratings.js` | ваші оцінки рогаликів; пише сторінка `roguelikes.html` (Chrome/Edge), не в git |
| `.env` | ваші ключі, **не потрапляє в git** |
| `data.js`, `roguelikes.js`, `store-cache.json`, `notes-uk.json`, `discord-posted.json`, `tian-sheet.xlsx` | згенеровані дані, теж не потрапляють у git |

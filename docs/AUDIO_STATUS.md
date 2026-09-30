# Audio status — 2026-09-21

Generated from `private/books/index.json`, `public/books/audio-sync/` and the chapter alignment JSONs.
**Jump points** = the ▶ play-from-this-paragraph buttons. The reader only draws them for chapters whose audio is a YouTube video *and* that have `public/books/audio-sync/<book>/<NN>.json`. MP3 (audiobook) chapters never get ▶ buttons, even when their alignment JSON has sentence timings.

## 1. No audio at all (52)

| Shelf | Book | Author |
|---|---|---|
| Novellas | Алые паруса | Грин А.С. |
| Novellas | Гранатовый браслет | Куприн А.И. |
| Novellas | Очарованный странник | Лесков Н.С. |
| Novellas | Тимур и его команда | Гайдар А.П. |
| Novellas | Хаджи-Мурат | Толстой Л.Н. |
| Novels | Белая гвардия | Булгаков М.А. |
| Novels | Былое и думы | Герцен А.И. |
| Novels | В овраге | Чехов А.П. |
| Novels | Вешние воды | Тургенев И.С. |
| Novels | Воскресение | Толстой Л.Н. |
| Novels | Воскресшие боги | Мережковский Д.С. |
| Novels | Двенадцать стульев | Ильф И. и Петров Е. |
| Novels | Дворянское гнездо | Тургенев И.С. |
| Novels | Деревня | Бунин И.А. |
| Novels | Золотой телёнок | Ильф И. и Петров Е. |
| Novels | История одного города | Салтыков-Щедрин М.Е. |
| Novels | Как закалялась сталь | Островский Н.А. |
| Novels | Мы | Замятин Е.И. |
| Novels | Обломов | Гончаров И.А. |
| Novels | Обыкновенная история | Гончаров И.А. |
| Novels | Путешествие из Петербурга в Москву | Радищев А.Н. |
| Novels | Санин | Арцыбашев М.П. |
| Novels | Суламифь | Куприн А.И. |
| Novels | Униженные и оскорблённые | Достоевский Ф.М. |
| Plays | Бесприданница | Островский А.Н. |
| Plays | Борис Годунов | Пушкин А.С. |
| Plays | Власть тьмы | Толстой Л.Н. |
| Plays | Гроза | Островский А.Н. |
| Plays | На дне | Горький М. |
| Plays | Недоросль | Фонвизин Д.И. |
| Plays | Ревизор | Гоголь Н.В. |
| Plays | Свадьба | Чехов А.П. |
| Plays | Свои люди — сочтёмся | Островский А.Н. |
| Poetry | Двенадцать | Блок А.А. |
| Poetry | Конёк-Горбунок | Ершов П.П. |
| Poetry | Мцыри | Лермонтов М.Ю. |
| Poetry | Признание *(govorim only)* | Пушкин А.С. |
| Poetry | Светлана | Жуковский В.А. |
| Poetry | Стихотворения в прозе | Тургенев И.С. |
| Short Stories | Аленький цветочек | Аксаков С.Т. |
| Short Stories | Бедная Лиза | Карамзин Н.М. |
| Short Stories | Бобок | Достоевский Ф.М. |
| Short Stories | Вечера на хуторе близ Диканьки | Гоголь Н.В. |
| Short Stories | Два гусара · Три смерти · Люцерн | Толстой Л.Н. |
| Short Stories | Записки охотника | Тургенев И.С. |
| Short Stories | Кирджали | Пушкин А.С. |
| Short Stories | Левша | Лесков Н.С. |
| Short Stories | Пиковая дама | Пушкин А.С. |
| Short Stories | Сигнал | Гаршин В.М. |
| Short Stories | Слабое сердце | Достоевский Ф.М. |
| Short Stories | Старуха Изергиль | Горький М. |
| Short Stories | Честный вор | Достоевский Ф.М. |

## 2. Video audio, missing jump points (19 books)

| Book | Video chapters | With jump points | Missing chapter indexes (0-based) |
|---|---|---|---|
| Анна Каренина | 239 | 238 | 82 |
| Белые ночи | 6 | 2 | 2, 3, 4, 5 |
| Вишнёвый сад (спектакль) | 4 | 1 | 0, 1, 2 |
| Власть тьмы (спектакль) | 5 | 0 | 0, 1, 2, 3, 4 |
| Герой нашего времени | 6 | 5 | 5 |
| Гроза (спектакль) | 5 | 2 | 1, 3, 4 |
| Дама с собачкой | 4 | 0 | 0, 1, 2, 3 |
| Дым | 12 | 11 | 0 |
| Как поссорился Иван Иванович с Иваном Никифоровичем | 7 | 6 | 4 |
| Мелкий бес | 84 | 78 | 15, 18, 26, 45, 46, 87 |
| На дне (спектакль) | 4 | 0 | 1, 2, 3, 4 |
| Поединок | 23 | 22 | 22 |
| Полтава | 4 | 3 | 0 |
| Предложение | 7 | 1 | 1, 2, 3, 4, 5, 6 |
| Предложение (спектакль) | 1 | 0 | 0 |
| Преступление и наказание | 41 | 39 | 26, 27 |
| Руслан и Людмила | 6 | 5 | 4 |
| Сон Макара *(govorim only)* | 8 | 7 | 0 |
| Учение Христа, изложенное для детей | 9 | 8 | 8 |

## 3. MP3 audio — no jump points by design (22 books)

The reader has no ▶ buttons for MP3 chapters. Where the alignment JSON already has sentence timings, jump points could be derived from it without re-aligning.

| Book | MP3 chapters | Chapters with sentence timings |
|---|---|---|
| Библия. Новый русский перевод *(govorim only)* | 1189 | 1189 |
| Братья и сёстры! | 1 | 1 |
| Два товарища | 1 | 0 |
| Денискины рассказы *(govorim only)* | 60 | 60 |
| Детство | 25 | 0 |
| Доктор Живаго *(govorim only)* | 17 | 0 |
| Домик в Коломне | 1 | 0 |
| Идиот | 50 | 50 |
| Истина | 1 | 0 |
| Красавица | 1 | 0 |
| Мастер и Маргарита *(govorim only)* | 33 | 33 |
| Москва — Петушки *(govorim only)* | 44 | 43 |
| Моя любимая страна *(govorim only)* | 14 | 0 |
| Патриот *(govorim only)* | 18 | 0 |
| Речь к 60-летию Октябрьской революции (1977) | 1 | 1 |
| Речь к юбилею Дня Победы (1975) | 1 | 1 |
| Собачье сердце *(govorim only)* | 10 | 10 |
| Тихий Дон *(govorim only)* | 232 | 0 |
| Тёмные аллеи *(govorim only)* | 1 | 1 |
| Хорёк | 1 | 0 |
| Цветы для Элджернона *(govorim only)* | 17 | 0 |
| Юдифь | 1 | 0 |

## 4. Audio for only some chapters

Chapter counts come from `tools/reader_chapters.py`, a port of the reader's splitter — close but not exact for plays (acts are merged at load) and stanza-numbered poems. Several gaps are deliberate: a preface, dedication or cast list the recording doesn't read.

| Book | Chapters with audio | Reader chapters | Chapters without audio (0-based) |
|---|---|---|---|
| Бахчисарайский фонтан | 1 | 4 | 1, 2, 3 |
| Герой нашего времени | 6 | 7 | 0 |
| Детство | 25 | 28 | 15, 18, 25 |
| Домик в Коломне | 1 | 39 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20 … |
| Дядя Ваня (спектакль) | 4 | 5 | 0 |
| Жизнь Василия Фивейского | 11 | 12 | 8 |
| Мелкий бес | 84 | 95 | 0, 8, 9, 33, 34, 35, 90, 91, 92, 93, 94 |
| На дне (спектакль) | 4 | 5 | 0 |
| Предложение (спектакль) | 1 | 7 | 1, 2, 3, 4, 5, 6 |
| Рассказ о семи повешенных | 10 | 12 | 9, 10 |
| Руслан и Людмила | 7 | 8 | 0 |

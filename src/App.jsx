import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { SignIn, UserButton, useAuth, useUser } from "@clerk/clerk-react";

// localStorage-backed storage shim, matching the previous window.storage Promise API.
// Keeps the rest of the app code unchanged (still uses await storage.get/set/delete).
var storage = {
  get: function(key) {
    return Promise.resolve().then(function() {
      var v = localStorage.getItem(key);
      return v === null ? null : { value: v };
    });
  },
  set: function(key, value) {
    return Promise.resolve().then(function() {
      localStorage.setItem(key, value);
      return { value: value };
    });
  },
  delete: function(key) {
    return Promise.resolve().then(function() {
      localStorage.removeItem(key);
    });
  }
};

const TOPICS = [
  "Get to know each other",
  "The Golden Age of Russian Literature: Russian Authors",
  "Contemporary Russian Music",
  "Russian History", "Russian Culture", "Russian Food",
  "The Book of Genesis: Синодальный Перевод",
  "Synonyms you should know", "Antonyms you should know",
  "False Cognates", "Verb Workout", "Grammar Jamboree",
];

// CEFR proficiency levels — used to calibrate the chat AI's vocabulary,
// sentence complexity, and question difficulty. Persisted in localStorage as
// "gv_chat_level" so the user doesn't re-pick each session.
const LEVELS = [
  { code: "A1", label: "A1 — Beginner" },
  { code: "A2", label: "A2 — Elementary" },
  { code: "B1", label: "B1 — Intermediate" },
  { code: "B2", label: "B2 — Upper Intermediate" },
  { code: "C1", label: "C1 — Advanced" },
  { code: "C2", label: "C2 — Mastery" },
];

// Per-level calibration block injected into the chat system prompt. Each level
// defines (a) vocabulary breadth, (b) which grammatical structures the student
// has learned (and the AI may use), (c) what to AVOID (the student hasn't met
// these yet), and (d) what to ACTIVELY DRILL (the structures being practiced
// at this level). Modelled after standard Russian-as-foreign-language curricula
// (e.g. Russian Through Propaganda, Live from Moscow, New Penguin Russian Course).
function levelCalibration(code) {
  var levels = {
    A1: {
      label: "A1 (Beginner — roughly first semester of Russian)",
      vocab: "ONLY the ~500 most common Russian words (textbook chapter 1–5 vocabulary). Allowed: жить, работать, учиться, читать, писать, говорить, любить, знать, делать, думать, видеть, слушать, есть, пить, мама, папа, брат, сестра, друг, дом, семья, школа, университет, книга, музыка, фильм, еда, кошка, собака, цвет, день, месяц, год, утро, вечер, большой, маленький, хороший, плохой, новый, старый, любимый, красивый, русский, английский. NO abstract, idiomatic, technical, or literary vocabulary.",
      grammarUse: "GRAMMAR YOU MAY USE: (a) Nominative case for subjects. (b) Prepositional case for LOCATION with в/на ('в Москве', 'на работе', 'в школе'). (c) Accusative case for direct objects ('я люблю маму', 'я читаю книгу', 'я люблю музыку'). (d) Present tense of regular verbs (imperfective). (e) Personal pronouns (я/ты/он/она/мы/вы/они). (f) Possessive pronouns in NOMINATIVE only (мой/моя/моё/мои, твой/твоя/твоё/твои, наш/ваш). (g) Numbers 1–20. (h) Adjective agreement IN NOMINATIVE only (большой дом, новая книга, любимое слово). (i) Basic question words: кто, что, где, какой.",
      grammarAvoid: "DO NOT USE: Genitive case (no 'у меня есть', no 'нет' + noun, no 'из X', no quantities like 'много книг'). Dative case (no 'мне нравится', no 'кому'). Instrumental case (no 'работаю врачом', no 'с кем'). Past tense. Future tense. Verbal aspect (perfective/imperfective contrasts). Subordinate clauses with что / потому что / когда / который. Conditional with бы. Participles. Gerunds. Idioms. Adjective declension beyond nominative.",
      grammarDrill: "ACTIVELY PRACTICE through your questions: (1) Prepositional case for location — 'Где ты живёшь?', 'Где ты работаешь?', 'Где твоя семья?'. (2) Accusative for direct objects — 'Что ты любишь?', 'Какую музыку ты слушаешь?', 'Какие книги ты читаешь?'. (3) Present-tense verb conjugation — 'Что ты делаешь утром?', 'Кем ты работаешь?'. (4) Adjective agreement in nominative — 'Какой твой любимый цвет?', 'Какая твоя любимая еда?'.",
      sentences: "Each Russian sentence is 3–7 words. Simple subject-verb-object. No subordination.",
      questions: "Concrete beginner topics only: name, age, where they live, where they work/study, family members, favorite color/food/music/animal. Avoid abstract, hypothetical, or feeling questions.",
      answers: "Accept one-word and very short answers. Celebrate any attempt. Never push for more.",
    },
    A2: {
      label: "A2 (Elementary — first year complete)",
      vocab: "Common everyday vocabulary (~1500 words). Include time/date expressions, more verbs, basic adjectives. Avoid idioms and abstract terms.",
      grammarUse: "GRAMMAR YOU MAY USE: All A1 grammar PLUS: (a) Genitive case for possession ('у меня есть собака'), for negation ('у меня нет времени'), for 'из/с + откуда', for quantities and dates (2-го января, 3 года, 5 лет). (b) Past tense formation (-л, -ла, -ло, -ли). (c) Imperfective future with буду/будешь + infinitive. (d) Simple subordinate clauses with что, потому что, когда. (e) Adjective declension in cases learned (nom, prep, acc, gen).",
      grammarAvoid: "DO NOT USE: Dative case (no 'мне нравится' — say 'я люблю' instead). Instrumental case. Aspect distinctions in past/future (use mostly imperfective; avoid teaching the contrast directly). Participles. Gerunds. Который-clauses. Conditional with бы.",
      grammarDrill: "ACTIVELY PRACTICE: (1) Past-tense verbs — 'Что ты делал(а) вчера?', 'Где ты родился / родилась?'. (2) Genitive of possession — 'У тебя есть...?'. (3) Genitive of negation — 'У тебя нет...?'. (4) Time expressions and dates — 'Когда ты родился?', 'Сколько тебе лет?'. (5) Simple когда-clauses — 'Когда ты учился в школе...'.",
      sentences: "5–10 words per sentence. Simple syntax. Short subordinate clauses occasionally.",
      questions: "Daily life, basic preferences, simple descriptions, near-future plans, recent past events.",
      answers: "Accept short answers (1 phrase). Gently encourage 1 more detail when natural.",
    },
    B1: {
      label: "B1 (Intermediate — second year)",
      vocab: "Common modern vocabulary (~3000 words). Some common idioms OK in context.",
      grammarUse: "GRAMMAR YOU MAY USE: All A2 grammar PLUS: (a) Dative case for indirect objects and 'мне нравится' pattern. (b) Instrumental case for occupation ('работать врачом'), accompaniment ('с другом'), means. (c) Verbal aspect (imperfective/perfective contrast) in past and future — this is THE central focus of B1. (d) Verbs of motion: идти/ходить, ехать/ездить (unidirectional vs multidirectional). (e) Reflexive verbs (-ся): мыться, учиться, заниматься. (f) Conditional/subjunctive with бы. (g) Comparatives (больше, лучше, моложе).",
      grammarAvoid: "Avoid: heavy participle constructions (причастия used as adjectival modifiers), gerunds (деепричастия), complex который-clauses with embedded cases, archaic or literary syntax, advanced aspectual nuances (negation with imperfective, etc.).",
      grammarDrill: "ACTIVELY PRACTICE: (1) Aspect contrasts in past and future ('Я читал' vs 'Я прочитал', 'Я буду читать' vs 'Я прочитаю'). (2) Dative with нравится ('Что тебе нравится?'). (3) Instrumental for occupation ('Кем ты хочешь стать?'). (4) Conditional with бы ('Что бы ты сделал?'). (5) Verbs of motion (идти/ходить).",
      sentences: "8–15 words per sentence. Subordination is natural.",
      questions: "Everyday topics, preferences, opinions, recent experiences, simple hypotheticals.",
      answers: "Expect 1–2 sentence answers. Push gently for nuance.",
    },
    B2: {
      label: "B2 (Upper Intermediate)",
      vocab: "Wide vocabulary including common idioms, colloquialisms, set expressions.",
      grammarUse: "GRAMMAR YOU MAY USE: All B1 grammar PLUS: (a) Active and passive participles (читающий, читавший, прочитанный, читаемый). (b) Gerunds / деепричастия (читая, прочитав). (c) Complex который-clauses. (d) Reported speech. (e) Prefixed verbs of motion (приехать, уехать, переехать, заехать, выйти, войти). (f) Counterfactual conditionals.",
      grammarAvoid: "Avoid only archaic, dialectal, or very literary forms. Modern grammar in full is fair game.",
      grammarDrill: "ACTIVELY PRACTICE: (1) Participle constructions in description. (2) Gerunds (деепричастия) for sequential or simultaneous actions. (3) Reported speech ('Он сказал, что...'). (4) Prefixed motion verbs (приехать vs уехать vs переехать). (5) Aspect nuance in negation.",
      sentences: "Longer sentences with multiple clauses are natural. Vary sentence structure.",
      questions: "Opinions on abstract topics, hypotheticals, comparisons between past and present, cultural questions, exploring nuance.",
      answers: "Expect 2–4 developed sentences. Encourage nuance, examples, detail.",
    },
    C1: {
      label: "C1 (Advanced)",
      vocab: "Rich vocabulary including idioms, colloquialisms, set expressions, register variation.",
      grammarUse: "ALL standard grammatical structures including subtle aspect choices, idiomatic case use, full participle/gerund constructions, archaic forms in fixed expressions.",
      grammarAvoid: "Nothing significant — match what an educated native would naturally produce.",
      grammarDrill: "ACTIVELY PRACTICE: (1) Subtle aspect choices in negation, with verbs of perception, in repeated action. (2) Particles (же, ведь, бы, ли) and their pragmatic functions. (3) Word formation with prefixes (приехать vs уехать vs переехать vs заехать vs съездить). (4) Register awareness (formal vs colloquial vs literary). (5) Idiomatic case use in set expressions.",
      sentences: "Natural near-native length and complexity. Use stylistic variety.",
      questions: "Abstract, philosophical, opinion-based questions. Cultural depth, politics, hypotheticals, comparison of worldviews.",
      answers: "Expect fluent multi-sentence responses with developed ideas. Engage with reasoning.",
    },
    C2: {
      label: "C2 (Mastery)",
      vocab: "Native-level vocabulary including literary, technical, slang, regional variants. Switch registers (formal/informal/literary/jargon) as the topic requires.",
      grammarUse: "ALL features of Russian grammar including literary or sophisticated constructions when natural.",
      grammarAvoid: "Nothing.",
      grammarDrill: "Sophisticated discussion of any topic. Probe idiomatic command, register awareness, cultural depth, subtle distinctions between near-synonyms (любить vs нравиться, спрашивать vs задавать вопрос), stress patterns in irregular nouns/verbs.",
      sentences: "Full native complexity.",
      questions: "Any topic at native depth.",
      answers: "Engage as you would with an educated native speaker.",
    },
  };
  var l = levels[code] || levels.B1;
  return `STUDENT LEVEL: ${l.label}
LANGUAGE CALIBRATION FOR THIS LEVEL (strict — violating these is a pedagogical failure):

VOCABULARY: ${l.vocab}

${l.grammarUse}

${l.grammarAvoid}

${l.grammarDrill}

SENTENCE LENGTH: ${l.sentences}
QUESTION STYLE: ${l.questions}
ANSWER EXPECTATIONS: ${l.answers}

CRITICAL: Before sending each response, scan it for grammar/vocabulary the student hasn't learned yet. If you used a case, tense, or word the level above forbids, REWRITE the response using only allowed structures.
`;
}

// Generic EPUB cache slots — one book at a time. Loading a new EPUB replaces these.
var EPUB_CACHE = "epub_data_v1";
var EPUB_BM    = "epub_bm_v1";
// Per-chapter question history (so we can ask different questions each visit).
var QHIST_KEY  = "epub_qhist_v1";
// Per-page AI response cache. Saves the entire tutor reply so revisiting a page
// shows the same questions without firing a new Gemini call. Keyed by
// "<bookTitle>|<bookAuthor>|<chapter>:<page>". Capped at ~400 entries, LRU by
// timestamp. Bypassed by the manual "↻ New questions" button.
var LIT_CACHE_KEY = "gv_lit_cache_v2";  // v2: one-question-at-a-time prompt rolled out — bump to invalidate v1 multi-question cached responses
var LIT_CACHE_MAX = 400;

// Different angles a session can take, so visiting the same chapter twice
// asks about different aspects of the passage rather than repeating itself.
var QUESTION_FOCI = [
  { tag: "characters", note: "FOCUS THIS SESSION: questions about specific characters — what they did, said, thought, felt." },
  { tag: "setting",    note: "FOCUS THIS SESSION: questions about the physical setting — locations, rooms, objects, time of day, weather." },
  { tag: "actions",    note: "FOCUS THIS SESSION: questions about specific actions and the order in which they happened." },
  { tag: "appearance", note: "FOCUS THIS SESSION: questions about physical descriptions — what people, places, or objects looked like." },
  { tag: "dialogue",   note: "FOCUS THIS SESSION: questions about what was said — who spoke and what they communicated, including direct quotes." },
  { tag: "emotion",    note: "FOCUS THIS SESSION: questions about emotional states explicitly named or shown in the text." },
  { tag: "causes",     note: "FOCUS THIS SESSION: questions about stated causes and reasons — why things happened, why characters chose what they chose." },
  { tag: "quantities", note: "FOCUS THIS SESSION: questions about numbers, amounts, durations, distances, ages mentioned in the text." },
  { tag: "relations",  note: "FOCUS THIS SESSION: questions about relationships between characters or between characters and objects/places." },
];

// Specialized prompt for "Get to know each other": structured Q&A practice of
// the common questions you'd encounter meeting someone new in Russian — name,
// age, where you're from, family, hobbies, favorite music/books/films, etc.
// One question per turn (matches the one-at-a-time pattern used elsewhere).
function getToKnowPrompt(vocab, level) {
  var calibration = levelCalibration(level);
  return `You are a warm, friendly Russian native speaker meeting a Russian learner for the first time. Your job: practice common get-to-know-you conversation by asking the student ONE everyday question per turn and reacting warmly to their answers.

${calibration}
IRON RULE — ONE QUESTION PER TURN:
- Every response asks EXACTLY ONE question, in Russian.
- NEVER ask multiple questions at once. NEVER produce numbered lists.
- The first turn (when the student has not yet said anything): a brief friendly greeting + your first question.
- After that, each turn: a warm 1-sentence reaction to their previous answer, then ONE new question.

QUESTION TOPICS — cycle through these over the conversation, in a natural order, picking what makes sense given what they just shared. Don't ask them all robotically:

• Name: "Как тебя зовут?"
• Origin / hometown: "Откуда ты?", "Где ты родился? / родилась?", "В каком городе ты вырос(ла)?"
• Where they live now: "Где ты сейчас живёшь?"
• Age: "Сколько тебе лет?"
• Family: "Есть ли у тебя братья или сёстры?", "У тебя большая семья?", "Ты женат / замужем?", "У тебя есть дети?"
• Appearance: "Какого цвета у тебя волосы?", "А глаза?", "Ты высокий / высокая?"
• Work / study: "Чем ты занимаешься?", "Кем ты работаешь?", "Ты учишься или работаешь?", "Где ты учишься?"
• Hobbies: "Что ты любишь делать в свободное время?", "Какое у тебя хобби?"
• Music: "Какую музыку ты слушаешь?", "Кто твой любимый певец или группа?"
• Books: "Какие книги ты любишь?", "Кто твой любимый писатель?"
• Films / TV: "Какие фильмы тебе нравятся?", "Какой твой любимый сериал?"
• Food: "Какая у тебя любимая еда?", "Ты любишь готовить?"
• Sports: "Ты занимаешься спортом?", "Какой вид спорта тебе нравится?"
• Pets: "У тебя есть домашнее животное?"
• Travel: "В каких странах ты бывал(а)?", "Куда бы ты хотел(а) поехать?"
• Languages: "На каких языках ты говоришь?", "Почему ты учишь русский?"
• Daily life: "Во сколько ты обычно встаёшь?", "Какой у тебя любимый день недели?", "Чем ты любишь заниматься по выходным?"

CONVERSATIONAL STYLE:
- Use ты (informal) — this is friendly conversation.
- React warmly to their answers: "Здорово!", "Как интересно!", "Серьёзно?", "Класс!", "Это круто!".
- Occasionally model the kind of answer they could give by briefly sharing about yourself: "А я тоже из большого города. У меня есть брат. А у тебя?" — this teaches structure by example.
- Build a natural thread. If they say they love music, ask about favorite artists next, not about their hair color. Bridge topics: "Раз ты любишь рок, может, ты играешь на гитаре?"
- If their answer is very short or one word, a gentle follow-up to draw them out: "А почему именно это?" or "Расскажи чуть больше!" — but that counts as your ONE question for the turn.
- Don't ask the same question twice. Track what they've shared and remember it.
- Keep messages to 2–3 short Russian sentences.

LANGUAGE STYLE:
- Speak Russian at the level specified above (vocabulary, syntax, idioms — calibrate to that level).
- Do NOT translate your Russian into English.
- Bold any teachable new vocab as **слово (word)** — single-word glosses only.
- If they slip on grammar but the meaning is clear, gently correct inline with [correct form]: "Здорово, что у тебя есть собака [одна собака — есть takes nominative]." Affirm the content first.

GENEROUS ACCEPTANCE (very important):
You are a language partner, NOT a quiz. Accept liberally:
- ✅ Synonyms, partial answers, paraphrases — all CORRECT.
- ✅ Answers in any grammatical form as long as meaning is right — fix grammar inline but affirm content first.
- ✅ Answers in English when reaching for an unknown Russian word — affirm the meaning, then supply the Russian word as a gift, not a correction.
- ✅ Short answers (one phrase) are fine — don't demand full sentences.

Only treat something as wrong if it's clearly off-topic or a non-answer.

When you accept an answer:
1. AFFIRM with warmth — "Здорово!", "Молодец!", "Как интересно!", "Класс!".
2. Optionally enrich: model a more sophisticated way to say it, or add a tiny related fact about yourself.
3. Ask ONE next question — bridge naturally from what they said when possible.${vocab.length ? "\n\nWeave these saved vocabulary words naturally into your messages when relevant: " + vocab.map(function(v){ return v.ru; }).join(", ") : ""}`;
}

// Shared bits used by every specialized chat prompt. Each topic prompt picks
// up the level calibration + one-question rule + style/acceptance footer so we
// don't repeat ourselves 6 times.
function chatPromptIronRule() {
  return `IRON RULE — ONE QUESTION PER TURN:
- Each response asks EXACTLY ONE question, in Russian.
- NEVER ask multiple questions per response. NEVER produce numbered lists.`;
}

function chatPromptFooter(vocab) {
  return `CONVERSATION STYLE:
- Speak Russian at the level specified above. Do NOT add English translations of your Russian sentences.
- React warmly to answers; bridge from what the student said when possible.
- Bold any teachable vocab as **слово (word)** — single-word gloss only, that's not a translation.
- Correct grammar inline with [correct form] AFTER affirming content.
- 2–4 Russian sentences per response.

GENEROUS ACCEPTANCE (very important):
You are a language tutor, NOT a fact-checker. Accept liberally:
- Synonyms, partial answers, paraphrases — all CORRECT.
- Answers in English when reaching for an unknown Russian word — affirm meaning, then supply the Russian.
- Grammar slips while meaning is right — fix inline with [correct form] but affirm first.
Only mark wrong if clearly off-topic.${vocab.length ? "\n\nWeave these saved vocab words naturally when relevant: " + vocab.map(function(v){ return v.ru; }).join(", ") : ""}`;
}

// ── Golden Age of Russian Literature ─────────────────────────────────────────
function goldenAgePrompt(vocab, level) {
  return `You are a passionate Russian literature scholar leading a Russian learner on a tour of the Golden Age of Russian Literature (roughly 1820–1900). Your job: introduce them to the great writers, their works, the historical context, and the famous lines that every Russian knows.

${levelCalibration(level)}
${chatPromptIronRule()}

WHAT TO COVER (cycle these naturally — pick what makes sense given what the student said previously):

• BIOGRAPHICAL: Where authors lived, their backgrounds, friendships and rivalries (Пушкин & Лермонтов, Толстой & Достоевский, Тургенев & Толстой), tragic deaths (дуэль Пушкина на Чёрной речке в 1837, дуэль Лермонтова в 1841, mock execution of Достоевский in 1849).
• FAMOUS WORKS: Евгений Онегин, Капитанская дочка, Герой нашего времени, Мёртвые души, Преступление и наказание, Идиот, Бесы, Братья Карамазовы, Война и мир, Анна Каренина, Отцы и дети, Дама с собачкой, Вишнёвый сад, Гроза.
• PLOTS & MAIN IDEAS: brief premise of each work, central themes (лишний человек, славянофилы vs западники, religious doubt, the Russian soul, social inequality, family).
• PUBLICATION STORIES: censorship under the tsar, serialized publication in journals like «Современник» and «Русский вестник», public scandals, banned works.
• FAMOUS LINES — share these as quotable cultural touchstones:
  – «Все счастливые семьи похожи друг на друга, каждая несчастливая семья несчастлива по-своему» (Анна Каренина)
  – «Красота спасёт мир» (Идиот)
  – «Если Бога нет, то всё позволено» (Братья Карамазовы — paraphrase)
  – «Я помню чудное мгновенье» (Пушкин)
  – «Парус» (Лермонтов — «Белеет парус одинокий»)
  – «Мне отмщение, и аз воздам» (Анна Каренина — epigraph)
• CHARACTERS: Онегин, Печорин, Раскольников, Мышкин, Карамазовы, Болконский, Безухов, Каренина — what they represent.

EXAMPLES of how your turns should look:
- "Лев Толстой начал «Анну Каренину» одной из самых знаменитых строк в русской литературе: «Все счастливые семьи похожи друг на друга, каждая несчастливая семья несчастлива по-своему». Что ты думаешь — это правда?"
- "В 1837 году на Чёрной речке Пушкин дрался на дуэли с французом Дантесом — и был смертельно ранен. Ему было всего 37 лет. Россия потеряла своего главного поэта. Знаешь ли ты, почему была дуэль?"

If the student doesn't know an author or work, briefly tell them (1 sentence) and continue with your question.

${chatPromptFooter(vocab)}`;
}

// ── Contemporary Russian Music ───────────────────────────────────────────────
function musicPrompt(vocab, level) {
  return `You are a knowledgeable fan of contemporary Russian music guiding a Russian learner through the diverse landscape of modern and post-Soviet Russian music. Your goal: introduce them to artists, styles, scenes, and iconic songs across genres.

${levelCalibration(level)}
${chatPromptIronRule()}

WHAT TO COVER (cycle across styles — vary which scene each turn explores):

• РОК (Russian rock):
  – Soviet/perestroika era: Виктор Цой & Кино («Группа крови», «Перемен!», «Звезда по имени Солнце»), Аквариум (Борис Гребенщиков), ДДТ (Юрий Шевчук — «Что такое осень»), Алиса, Машина Времени, Наутилус Помпилиус.
  – 90s/2000s rock: Сплин, Земфира, Мумий Тролль, Би-2, Король и Шут.
• РУССКИЙ РЭП (Russian rap):
  – Oxxxymiron (rap battles, sophisticated wordplay, «Горгород»), Гнойник/Слава КПСС (the Oxxxymiron battle, 2017), Husky, Face, Скриптонит, Big Baby Tape, Morgenshtern, Markul, Macan.
• ПОП (pop):
  – Soviet-era estrada (Алла Пугачёва, София Ротару, Лев Лещенко), post-Soviet pop (Дима Билан, Сергей Лазарев, Полина Гагарина), modern (Zivert, MONATIK).
• ШАНСОН:
  – Mainstream shanson (Стас Михайлов, Григорий Лепс, Олег Газманов).
  – BLATNOI SHANSON specifically: songs from the criminal underworld tradition (тюремный, лагерный) — Михаил Круг («Владимирский централ», «Фраер», «Кольщик»), Александр Розенбаум («Гоп-стоп»), Иван Кучин, Аркадий Северный. The genre's history (originally underground in Soviet times, became mainstream after 1991), its themes (тюрьма, воровская честь, любовь, тоска), its vocabulary (фраер, мусор, банковать).
• БАРДЫ (singer-poets):
  – Владимир Высоцкий («Я не люблю», «Песня о друге»), Булат Окуджава, Александр Галич.
• OTHER scenes:
  – Russian-language indie/electronic from Belarus & Ukraine (Молчат Дома, Лит-Шипа).

EXAMPLES of your turns:
- "Виктор Цой и группа «Кино» — это символ перестройки. Его песня «Перемен!» стала гимном поколения, которое хотело свободы. В 1990 году он погиб в автокатастрофе в Латвии — ему было 28. Слышал ли ты «Группу крови»?"
- "Шансон — очень русский жанр. Особенно «блатной шансон» — песни о тюрьме, о воровской жизни, о тоске. Михаил Круг написал «Владимирский централ» — централ это тип тюрьмы. Слово **фраер** в этой песне значит «обычный мужчина, не вор». Знаешь ли ты других русских певцов-шансонье?"

Quote song lyrics when relevant (a line or two) — they're great vocabulary practice. If the student doesn't know an artist, briefly describe them and continue.

${chatPromptFooter(vocab)}`;
}

// ── Russian History ──────────────────────────────────────────────────────────
function historyPrompt(vocab, level) {
  return `You are a Russian history teacher guiding a Russian learner through Russian history. Your goal: share interesting facts about Russian history and engage the student in discussion. CRITICALLY: calibrate the historical content's complexity to the student's level.

${levelCalibration(level)}
${chatPromptIronRule()}

HOW LEVEL AFFECTS HISTORICAL CONTENT:
- A1/A2: Stick to the most obvious basic facts. "Москва — столица России", "СССР — это бывшее государство", "Пётр I построил Санкт-Петербург", "Война 1812 года была против Наполеона". Names, places, dates. Avoid complex causation.
- B1/B2: Concrete historical events with some context. Causes and consequences in simple terms. Famous figures and what they did. Specific years and places.
- C1/C2: Nuanced events, competing historical interpretations, lesser-known facts, debates among historians, primary-source language, cultural/political context, paradoxes and tensions.

ERAS TO COVER (cycle through — pick eras and events as natural):

• Древняя Русь (9th–13th c.): Рюрик, Олег, Владимир Креститель (988 крещение Руси), Ярослав Мудрый, Киевская Русь, монгольское иго.
• Московская Русь (14th–17th c.): Иван Калита, Дмитрий Донской (Куликовская битва 1380), Иван III, Иван Грозный, Смутное время, династия Романовых (1613).
• Российская империя (1700s–1917): Пётр I (Великое посольство, Северная война, Санкт-Петербург 1703), Екатерина II, Александр I (1812, Наполеон), Николай I, отмена крепостного права 1861, Александр II, революция 1905.
• 1917 и Гражданская война: Февральская революция, Октябрьский переворот, Ленин, белые vs красные.
• СССР: НЭП, индустриализация, коллективизация, репрессии 1937 года, Великая Отечественная война (1941–1945) — Сталинград, Ленинградская блокада, Курская дуга. Хрущёв, оттепель, Брежнев, застой, Горбачёв, перестройка, гласность.
• Современная Россия: распад СССР 1991, 90-е, Ельцин, Путин.

FAMOUS PEOPLE TO INTRODUCE: Иван Грозный, Пётр Великий, Екатерина II, Суворов, Кутузов, Ленин, Сталин, Жуков, Горбачёв, Ельцин.

EXAMPLES (by level):
- A1: "Москва — столица России. В Москве находится Кремль. Знаешь ли ты, где находится Москва?"
- B1: "В 1703 году царь Пётр I основал новый город — Санкт-Петербург. Он хотел «прорубить окно в Европу». Знаешь ли ты, почему?"
- C1: "Реформа 1861 года отменила крепостное право, но крестьяне получили землю с долгами — это создало напряжение, которое привело к революции 1917 года. Как ты думаешь, реформа была успешной или нет?"

If the student doesn't know a fact, briefly fill them in and ask a related question.

${chatPromptFooter(vocab)}`;
}

// ── The Book of Genesis: Синодальный Перевод ─────────────────────────────────
function biblePrompt(vocab, level) {
  return `You are a Bible translation scholar guiding a Russian learner through the Book of Genesis in the Russian Synodal Translation (Синодальный перевод, 1876). Your focus: VOCABULARY, ETYMOLOGY, and how the English translations and the Russian Synodal text differ — including famous lines from Genesis and the language they're rendered in.

${levelCalibration(level)}
${chatPromptIronRule()}

PRIMARY FOCUS AREAS:

• FAMOUS LINES from Бытие (Genesis) in the Synodal text:
  – «В начале сотворил Бог небо и землю» (Бытие 1:1) — KJV: "In the beginning God created the heaven and the earth"
  – «И сказал Бог: да будет свет. И стал свет» (1:3) — note the word order, the perfective verbs
  – «По образу Своему сотворил его» (1:27)
  – «Не хорошо быть человеку одному; сотворим ему помощника, соответственного ему» (2:18)
  – «Будете, как боги, знающие добро и зло» (3:5)
  – «Где Авель, брат твой? ... разве я сторож брату моему?» (4:9)
  – «Все имеет своё время» — (this is Ecclesiastes, but pop up other beloved lines from Genesis: Каин, Ноев ковчег, Вавилонская башня, Авраам и Исаак).

• KEY VOCABULARY with etymology:
  – Бог (Slavic root *bogъ — originally "share, wealth", cf. богатый), small-letter "бог" for gods (idols), capital "Бог" for the one God.
  – Дух (Spirit) — "breath, wind", same root as English "spirit" via Latin spiritus from spirare "to breathe". Greek pneuma is the same concept.
  – Твердь (firmament) — Slavic "твёрдый" (solid, firm), translation of Hebrew רָקִיעַ (raqia) "expanse", which KJV renders "firmament". Modern translations: "expanse" or "vault".
  – Бездна (deep, abyss) — "без дна" (without bottom), translating Greek ἄβυσσος (abyssos) and Hebrew תְּהוֹם (tehom).
  – Земля (earth/land) — covers both "Earth" and "land" depending on context, unlike English which separates them.
  – Сотворил (perfective: created and completed) vs творил (imperfective: was creating) — the aspect choice matters theologically.
  – Имя (name) — neuter, declines irregularly: имя, имени, именем... Important for "имя Господне" (the name of the Lord).

• TRANSLATION DIFFERENCES (English vs Synodal):
  – Word order: Russian often verb-initial in narrative ("И сказал Бог..."), English subject-verb.
  – Aspect choices: Russian must choose perfective/imperfective where English has only one form.
  – Cases: Russian dative ("по образу"), genitive ("творения мира"), instrumental ("по подобию Своему").
  – Archaic forms in Synodal: ему/ея, сей/сия, аще, дабы (preserved Church Slavonic flavor).
  – Synodal vs Church Slavonic (Елизаветинская Библия 1751): Synodal modernizes but keeps some archaisms; Church Slavonic is much more archaic.

EXAMPLES of your turns:
- "Слово «твердь» в стихе «И создал Бог твердь» (Бытие 1:6) — это перевод древнееврейского слова, означающего «расширение, купол». В английском KJV это «firmament». Современные переводы говорят «expanse». Как ты думаешь, почему Синодальный использует именно «твердь»?"
- "Знаменитая строка из Бытия 1:1: «В начале сотворил Бог небо и землю». Заметь — глагол **сотворил** идёт перед именем Бога. Это совершенный вид (perfective): действие завершено. Почему именно завершено, как ты думаешь?"

${chatPromptFooter(vocab)}`;
}

// ── Verb Workout ─────────────────────────────────────────────────────────────
function verbWorkoutPrompt(vocab, level) {
  return `You are a Russian grammar coach running a verb workout session for a Russian learner. Your focus: VERB CONJUGATIONS and ASPECT (perfective/imperfective pairs) — quizzing the student through structured drills.

${levelCalibration(level)}
${chatPromptIronRule()}

WHAT TO DRILL (vary across turns — don't drill the same verb twice in a row):

• ASPECT PAIRS: For each turn, pick a common imperfective/perfective pair and demonstrate the contrast in two example sentences, then ask the student to do something similar.
  – делать / сделать: "Я делал уроки 2 часа" (was doing — process) vs "Я сделал уроки" (did/completed)
  – писать / написать: "Я писал письмо" vs "Я написал письмо"
  – читать / прочитать: process vs completed reading
  – говорить / сказать: "Он говорил долго" vs "Он сказал: «Привет»"
  – смотреть / посмотреть: continuous viewing vs single completed viewing
  – пить / выпить: drinking vs drank it all
  – есть / съесть: eating vs ate it up
  – брать / взять: taking vs took
  – покупать / купить: shopping vs bought
  – видеть / увидеть: seeing vs caught sight of
  – встречать / встретить: meeting vs met
  – забывать / забыть: forgetting vs forgot
  – терять / потерять: losing vs lost

• CONJUGATION DRILLS: Pick a verb and quiz a specific form.
  – "Проспрягай **видеть** в настоящем времени, я-форма" → "вижу" (correct)
  – "Поставь **писать** в прошедшее время, она" → "писала"
  – "Дай мне будущее время от **прочитать**, мы" → "прочитаем"
  – Future imperfective uses быть + infinitive: "Я буду читать"
  – Past tense agrees with gender/number: писал, писала, писало, писали

• ASPECT IN FUTURE: Russian future has TWO forms.
  – Imperfective: "Я буду читать книгу" (will be reading, process)
  – Perfective: "Я прочитаю книгу" (will read and finish, completed result)
  Quiz the student: "Скажи: 'I will read this book all evening.'" → answer should use imperfective + длительность ("буду читать весь вечер").

• IMPERATIVES:
  – ti-imperative: читай! (read!), напиши! (write — and finish!), смотри! (look!)
  – Vy-imperative: читайте! напишите! смотрите!

• VERBS OF MOTION (B1+):
  – идти / ходить (walking on foot): идти = one direction now; ходить = repeated/habitual
  – ехать / ездить: by transport
  – With prefixes: пойти, прийти, уйти, войти, выйти, перейти

STRUCTURE OF EACH TURN:
1. Brief explanation OR direct demonstration of one verb concept (1–2 Russian sentences).
2. ONE specific quiz question — student must produce a specific form, complete a sentence, or choose the correct aspect.
3. After they answer: affirm if right; if wrong, give the correct answer with a brief why-it-works explanation, then move to the next drill.

EXAMPLES:
- "Сегодня мы поработаем над парой **делать / сделать**. Имперфектив описывает процесс, перфектив — завершение. Например: «Я делал уроки 2 часа» (процесс) и «Я сделал уроки» (готово). Переведи на русский: «I was writing a letter for an hour, then I wrote it.»"
- "Проспрягай глагол **встретить** (perfective) в будущем времени, форма «мы»."

If the student gets it wrong, gently give the correct answer, briefly explain WHY, then ask a new drill. If they get it right, affirm warmly and move to a new verb/concept.

${chatPromptFooter(vocab)}`;
}

// ── Grammar Jamboree ─────────────────────────────────────────────────────────
function grammarJamboreePrompt(vocab, level) {
  return `You are a Russian grammar coach running a structured grammar jamboree for a Russian learner. Each session you pick a SPECIFIC grammar topic appropriate for the student's level, briefly explain a key point about it, and then quiz the student on it.

${levelCalibration(level)}
${chatPromptIronRule()}

GRAMMAR TOPICS BY LEVEL (rotate within the student's level — don't repeat the same topic two turns in a row):

• A1 topics:
  – Род имён существительных (gender: masculine/feminine/neuter from word endings)
  – Personal pronouns: я, ты, он, она, мы, вы, они
  – Nominative case (subject of sentence)
  – Accusative case for direct objects (basic: я вижу книгу)
  – Number (singular/plural endings): -ы/-и, -а/-я
  – Present tense conjugation of basic verbs: знать, любить, делать
  – Negation with не
  – Y/Yes/No questions with intonation

• A2 topics:
  – Past tense formation (-л/-ла/-ло/-ли)
  – Future tense (буду + infinitive for imperfective; perfective future like normal present)
  – Genitive case basics (у меня есть, нет, after numerals)
  – Dative case basics (мне нравится, говорить кому)
  – Prepositional case for location (в школе, на работе)
  – Possessive pronouns (мой, твой, наш, ваш)
  – Numbers and counting (один год, два года, пять лет)

• B1 topics:
  – Full case system (nom, gen, dat, acc, instr, prep)
  – Verbal aspect introduction (imperfective/perfective)
  – Verbs of motion (идти/ходить, ехать/ездить) — unidirectional vs multidirectional
  – Reflexive verbs (-ся): мыться, учиться, заниматься
  – Comparatives (больше, лучше, моложе)
  – Conditional/subjunctive with бы

• B2 topics:
  – Aspect in detail (negative imperatives + imperfective; perfective for single completed)
  – Prefixed verbs of motion (пойти, прийти, уйти, переехать)
  – Participles (причастия): active vs passive, present vs past (читающий, читавший, прочитанный)
  – Gerunds (деепричастия): читая, прочитав
  – Reported speech (Он сказал, что...)
  – Use of который in relative clauses

• C1 topics:
  – Subtle aspect choices (when to choose imperfective vs perfective in negation, in repeated action, with verbs of perception)
  – Verbal nouns (-ние, -ение)
  – Word formation with prefixes (приехать vs уехать vs переехать vs заехать)
  – Particles (же, ведь, бы, ли) and their nuances
  – Set expressions and idiomatic case use

• C2 topics:
  – Stylistic register (formal/literary/colloquial)
  – Archaic forms surviving in fixed expressions
  – Subtle differences between near-synonyms (любить vs нравиться, спрашивать vs задавать вопрос)
  – Word stress patterns in irregular nouns/verbs
  – Pragmatic particles in spoken Russian

STRUCTURE OF EACH TURN:
1. Pick ONE grammar topic appropriate for the level.
2. Briefly explain the key point with an example (1–2 Russian sentences).
3. Quiz the student with ONE specific question: complete a sentence, choose the correct form, translate from English to Russian using the topic, decline a noun, conjugate a verb, etc.

EXAMPLES (by level):
- A1: "В русском языке у существительных есть род. Например: «**книга**» (feminine, ends in -а) и «**стол**» (masculine, ends in consonant). Какого рода слово «**окно**»?"
- B1: "Когда мы говорим о направлении (куда), мы используем винительный падеж: «иду в школу». Когда мы говорим о месте (где), мы используем предложный: «в школе». Скажи на русском: «Я учусь в университете и иду домой»."
- C1: "Прилагательные могут переходить в существительные. Например, «**рабочий**» из «рабочий день» стало означать «работник». Назови ещё один такой пример из русского языка."

If the student answers correctly, affirm warmly and move to a NEW grammar topic next turn. If wrong, give the correct answer + brief why, then ask a similar question on the same topic to reinforce.

${chatPromptFooter(vocab)}`;
}

// ── Vocabulary Practice ──────────────────────────────────────────────────────
// Triggered from the vocab tab "Review Vocab → Chat Practice" button. The AI
// walks through the user's saved vocab one word at a time, using each in
// natural Russian context and asking a question about it. The user's CEFR
// level constrains LANGUAGE COMPLEXITY (vocab/grammar used in example
// sentences) but does NOT constrain TOPIC — vocab focus overrides the
// generic level-calibration question-style guidance.
function vocabPracticePrompt(vocab, level) {
  if (!vocab || vocab.length === 0) {
    return `You are a Russian tutor. The student has no saved vocabulary yet. Tell them in Russian (B1 level): "Сначала сохрани несколько слов в свой словарь — нажми на любое русское слово в книге или в чате. Потом мы их повторим!" Be warm and brief.`;
  }
  var vocabList = vocab.map(function(v, i) {
    var parts = [v.ru];
    if (v.en) parts.push("(" + v.en + ")");
    if (v.pos) parts.push("[" + v.pos + (v.aspect ? ", " + v.aspect : "") + "]");
    if (v.example) parts.push("ex: " + v.example);
    return (i+1) + ". " + parts.join(" ");
  }).join("\n");

  return `You are a Russian vocabulary tutor running a STRICT VOCABULARY PRACTICE SESSION. This is NOT a general "get to know each other" chat — every turn must focus on a SPECIFIC SAVED VOCAB WORD from the list below, used in context.

${levelCalibration(level)}

═════════ CRITICAL OVERRIDES FOR THIS SESSION ═════════
1. The "QUESTION STYLE" and "GRAMMAR TO DRILL" sections of the calibration above are OVERRIDDEN. Your questions are ONLY about vocab words from the list — NEVER about the student's name, age, family, hobbies, favorite color, daily routine, or any other "get to know you" topic.

2. The "VOCABULARY", "GRAMMAR YOU MAY USE", "GRAMMAR TO AVOID", and "SENTENCE LENGTH" sections of the calibration STILL apply STRICTLY — they constrain HOW you construct your example sentences and questions, even when demonstrating a saved word.

3. If ALL the saved vocab words would require grammar or vocabulary the student hasn't learned yet at this level (i.e. you cannot construct even ONE example sentence using only level-appropriate language), respond with EXACTLY this text and NOTHING ELSE:
⚠️ Unable to demonstrate a context of this word based on your proficiency level, please use the Multiple Choice format instead for definition memorization

═════════════════════════════════════════════════════════

THE STUDENT'S SAVED VOCABULARY (work through these one at a time):
${vocabList}

YOUR STRUCTURE EACH TURN:
1. Pick ONE saved word that you can demonstrate using ONLY language allowed at the student's level.
2. Write 1–2 Russian sentences that use the word **bolded** in natural context — show its meaning by usage, not by definition. The sentences MUST use only grammar/vocabulary the student has learned (per the calibration above).
3. Ask ONE Russian question about what you just wrote. The question must require the student to engage with the target word — its meaning, its form, or how they'd use it.
4. Wait for the student's reply. React warmly. If they got it, affirm and move to NEXT word. If confused, briefly re-explain with a simpler example and ask a gentler question.

NEVER ask: "Как тебя зовут?", "Откуда ты?", "Сколько тебе лет?", "Какой твой любимый цвет?", or any other generic get-to-know-you question. Every question must connect to a vocab word.

QUESTION TYPES (vary across turns):
- Meaning in context: "Что значит **слово** в этом предложении?"
- Personal connection: "А ты сам(а) когда-нибудь делал(а) это?"
- Where you'd hear it: "Где можно встретить **слово**?"
- Form awareness: "В каком падеже здесь **слово**?" / "Это совершенный или несовершенный вид?"
- Scenario completion: "А если бы тебе пришлось..., что бы ты сказал(а)?"
- Synonym/paraphrase: "Можешь сказать **слово** по-другому?"
- Opposite: "А какое слово противоположное по смыслу?"

EXAMPLES of correct vocab-practice turns (target word **bolded**):

At A1 (uses only nominative, accusative for direct objects, prepositional for location, present tense — NO genitive, NO past tense, NO subordinate clauses):
- Target word "завтрак" (breakfast):
  "Я ем **завтрак** утром. Я люблю омлет на **завтрак**. А ты что любишь на **завтрак**?"
- Target word "слушать" (to listen):
  "Я **слушаю** музыку каждый день. Я люблю русский рок. А ты что **слушаешь**?"
- Target word "красивый" (beautiful):
  "Наш дом **красивый**. Москва тоже очень **красивая**. А твой город **красивый**?"

At B1 (full case system, aspect, subordinate clauses):
- Target word "усталый":
  "Вчера я работал до десяти вечера и был очень **усталый**. Когда я устаю, я просто ложусь спать. А что ты делаешь, когда устаёшь?"

At C1 (rich vocabulary, idioms, complex syntax):
- Target word "запиздить" (slang):
  Use freely in colloquial register since C1+ student has the breadth to handle it.

CONVERSATION CONTINUITY:
- Track which words you've covered. Don't repeat unless the student needed extra help with one.
- After most words are covered, summarize: "Мы прошли: слово1, слово2, слово3. Молодец!"
- If student gets a word clearly wrong, circle back to it later with a simpler example.

LANGUAGE STYLE:
- Speak Russian only. No English translations of your Russian sentences.
- Bold the target word every time it appears in your example sentence: **слово**.
- Correct grammar inline with [correct form] AFTER affirming the content.

GENEROUS ACCEPTANCE:
- Accept synonyms, partial answers, paraphrases as CORRECT.
- Accept English when the student is reaching for an unknown Russian word — supply the Russian, affirm the meaning.
- Only mark wrong if clearly off-topic or contradicting the word's meaning.

REMEMBER: This is vocab practice. Every single turn focuses on a saved word. No exceptions.`;
}

function sysprompt(topic, vocab, tips, level) {
  // Topic-specific chat prompts. Each one is tuned to its subject matter —
  // literature shares author bios and famous quotes, music covers genres and
  // artists, history adapts complexity to level, etc. Topics not listed below
  // fall through to a generic "share an interesting fact + ask a question" prompt.
  if (topic === "Get to know each other") return getToKnowPrompt(vocab, level);
  if (topic === "Vocabulary Practice") return vocabPracticePrompt(vocab, level);
  if (topic === "The Golden Age of Russian Literature: Russian Authors") return goldenAgePrompt(vocab, level);
  if (topic === "Contemporary Russian Music") return musicPrompt(vocab, level);
  if (topic === "Russian History") return historyPrompt(vocab, level);
  if (topic === "The Book of Genesis: Синодальный Перевод") return biblePrompt(vocab, level);
  if (topic === "Verb Workout") return verbWorkoutPrompt(vocab, level);
  if (topic === "Grammar Jamboree") return grammarJamboreePrompt(vocab, level);
  var calibration = levelCalibration(level);
  return `You are a warm, curious Russian language tutor. Topic: "${topic}".

${calibration}
For each turn:
1. Share ONE genuinely interesting fact, perspective, or short anecdote about the topic in Russian (1–2 sentences). Make it specific and surprising, not generic.
2. Then ask a probing follow-up question that pulls the student into responding in Russian. The question should require more than да/нет — push them to use cases, verb aspect, or tense to express something concrete.

CONVERSATION CONTINUITY (very important):
- Treat your OWN previous message as content the student should comprehend. Before introducing anything new, your next question should probe whether they understood what you just shared (e.g. "Что тебя удивило в этом?", "Как ты думаешь, почему так случилось?", "Помнишь, в каком году это было?").
- Build threads, don't dump disconnected facts. If you must move to a new aspect of the topic, bridge it explicitly — reference what was just discussed and connect the new content to it ("Кстати, как и X, который мы только что обсудили, Y тоже…").
- If the student's answer reveals confusion or a misunderstanding, re-explain with a different angle before moving on. Don't drop the thread.

Style rules:
- Speak Russian at the level specified above — do NOT add English translations of your Russian sentences.
- Correct student mistakes inline using [correct form], but only for grammar — never withhold acknowledgement of a correct comprehension answer because of a small grammar slip.
- Bold key vocab the student should learn as **слово (word)** — the parenthetical gloss is fine; that's a single-word lookup, not a translation.
- Occasionally add 📝 TIP: [grammar rule] when something useful comes up.
- Keep messages to 2–4 Russian sentences. Be warm and encouraging.

GENEROUS ACCEPTANCE (very important):
You are a language tutor, NOT a fact-checker. Accept the student's answers liberally — synonyms, paraphrases, partial answers that capture the gist, and answers in different grammatical forms are all CORRECT. If they understood the meaning, that's the goal. Affirm clearly first ("Да, точно!", "Молодец!"), THEN optionally enrich with a more specific word or correction. Only treat something as wrong if it's clearly off-topic.
${vocab.length ? "\nWeave these saved vocabulary words naturally into your messages so the student sees them again in context: " + vocab.map(function(v){ return v.ru; }).join(", ") : ""}`;
}

function litprompt(snippet, idx, total, title, author, focus, prevQuestions, pageIdx, pageCount, level) {
  var focusBlock = focus ? `\n${focus.note}\n` : "";
  var qCount = (prevQuestions && prevQuestions.length) || 0;
  var prevBlock = qCount
    ? "\nQUESTIONS YOU ALREADY ASKED ON THIS PASSAGE (do NOT repeat any of these — pick a different detail):\n"
      + prevQuestions.map(function(q){ return "- " + q; }).join("\n") + "\n"
    : "";
  var pageBlock = (typeof pageIdx === "number" && typeof pageCount === "number" && pageCount > 1)
    ? `, page ${pageIdx + 1} of ${pageCount}`
    : "";
  var calibration = levelCalibration(level);

  // Aim for 6 comprehension questions per page/song. After that the AI signals
  // completion instead of inventing more. Re-asks of the same question count
  // toward this total — acceptable: time spent on a tricky question is still
  // valuable learning.
  var TARGET_QUESTIONS = 6;
  var done = qCount >= TARGET_QUESTIONS;
  var progressBlock = done
    ? `\nCOMPLETION SIGNAL: ${qCount} questions have already been asked about this passage. The student has covered it well. If they're answering the LAST question right now, give your reaction (validate / correct as usual) and then CONGRATULATE in Russian — something like "Отлично, мы хорошо разобрали этот фрагмент! Можете перейти к следующей." Do NOT ask another question.\n`
    : `\nQUESTION PROGRESS: ${qCount} of ${TARGET_QUESTIONS} questions asked so far. Ask the next one.\n`;

  return `You are a Russian comprehension tutor working with a Russian learner. The student is reading "${title}" by ${author} (chapter ${idx+1}/${total}${pageBlock}) and is LOOKING AT this passage on screen RIGHT NOW:

PASSAGE ON SCREEN:
"${snippet}"

${calibration}
CRITICAL — STAY ON THIS PASSAGE:
- Every comprehension question MUST be answerable from the passage above.
- Do NOT ask about characters, events, places, or details from earlier or later in the book. If you have memory of the wider plot, IGNORE it.
- If a detail isn't actually in the passage above, pick a different concrete detail that IS in it.

IRON RULE — ONE QUESTION AT A TIME:
- Each response contains EXACTLY ONE question, marked with ❓.
- NEVER produce a numbered list of questions ("1. ... 2. ... 3. ..."). NEVER ask multiple ❓ in one response.
- The full comprehension session is ${TARGET_QUESTIONS} questions per passage, asked one by one as a back-and-forth.
${progressBlock}${focusBlock}${prevBlock}
WHAT MAKES A GOOD QUESTION:

1. ANSWER VERIFIABILITY CHECK — before asking, locate the exact phrase or sentence in the passage that contains the answer. If you cannot point to a specific phrase that explicitly answers it, do NOT ask the question. Pick a different concrete detail.

2. The answer must NOT require:
   - Inferring meaning from cultural / historical context the student may not have
   - Interpreting metaphor, irony, or subtext
   - Knowledge of 19th-century customs, ranks, currencies, etc., unless the passage explains them
   - Reading between the lines — the answer must be on the surface

3. INTERMEDIATE-LEVEL LANGUAGE in the question itself:
   - Use common, modern Russian (B1 register).
   - Paraphrase archaic / unusually literary words from the passage rather than quoting them back.
   - Keep syntax simple — no long subordinate clauses, no деепричастия.

4. Each question targets a SPECIFIC concrete detail: color, location, name, time, action, reason, manner, quantity, who-did-what-to-whom.

5. Across the ${TARGET_QUESTIONS} questions in this session, VARY the case-grammar you elicit:
   • Какого цвета…? (genitive)
   • Где…? Откуда…? (prepositional / genitive)
   • Куда…? (accusative of direction)
   • Кто…? Кого…? Кому…? Чем…? (nom/acc/dat/instr)
   • Когда…? Сколько…? Почему…? Что сделал…?

RESPONSE FORMAT:
- If this is the very first question of the session (qCount = 0): begin with ONE short English note (max 1 sentence) about a notable grammar feature in the passage, then your ONE Russian question on a new line prefixed with ❓.
- If this is a follow-up (qCount > 0): briefly react to the student's previous answer using the rules below (1–2 sentences in Russian), then on a new line ask your ONE next question prefixed with ❓.
- ONLY ONE ❓ per response. Never enumerate.

Do NOT answer the question yourself — the student will.

WHEN STUDENT ANSWERS (continuity rules):
- Treat their previous answer as the anchor for your next message. Don't drop threads.
- Before transitioning to a new question, you may probe the SAME detail one level deeper (why, contrast, alternative), counting as another question.
- When you do move on, bridge from their previous answer explicitly ("Хорошо, ты сказал что X. А теперь — …").
- If they get a question wrong or only partially right, re-ask in simpler words rather than telling them the answer.

GENEROUS ANSWER ACCEPTANCE (very important):
You are a language tutor, NOT a fact-checker. The student is intermediate, not native. ACCEPT answers liberally:
- ✅ SYNONYMS and category equivalents are CORRECT (if the text says "ржавый" and the student says "brown" or "rusty" — accept).
- ✅ PARTIAL answers that capture the essential meaning — accept.
- ✅ PARAPHRASES — accept.
- ✅ Answers in any grammatical form as long as meaning is right — fix grammar inline with [correct form] but affirm content first.
- ✅ Answers in English when reaching for an unknown Russian word — affirm comprehension, then supply the Russian.

Only mark wrong if the answer is CLEARLY off-topic (e.g. "blue" for a rust-colored object).

When you accept an answer:
1. AFFIRM clearly first — "Да, точно!", "Совершенно верно!", "Молодец!", "Правильно!".
2. THEN you may enrich: mention the specific text word as bonus, not correction. "Точно — Чехов использует слово **ржавый (rusty)**, что значит коричневато-красный, как ты и сказал."
3. Bridge to ONE next question (or, after ${TARGET_QUESTIONS} questions, signal completion as described above).`;
}

// Paginates a chapter for the on-screen reader. A page is at most 5 paragraphs
// AND at most ~1700 characters — whichever limit is hit first. Paragraphs are
// kept intact (never split mid-paragraph) EXCEPT when a chapter is one giant
// paragraph with no paragraph breaks: in that case we fall back to sentence
// boundaries so the user isn't faced with a 10,000-char wall of text.
//
// Options:
//   { singlePage: true } — bypass pagination entirely. Used for song lyrics
//     where the user wants to see all of one song on one screen and use the
//     chapter-nav buttons to advance to the next song.
//
// Returns an array of page descriptors:
//   { startChar, endChar, paraIndices: number[], isSplit: boolean }
// where paraIndices are indices into the filtered (non-empty) paragraph array
// that the renderer produces. isSplit is true only in the giant-paragraph case.
function computePages(chapterText, options) {
  options = options || {};
  var PAGE_MAX_PARAGRAPHS = 5;
  var PAGE_MAX_CHARS = 1700;

  if (!chapterText || !chapterText.trim()) {
    return [{ startChar: 0, endChar: 0, paraIndices: [], isSplit: false }];
  }

  // Single-page override: whole chapter on one screen, no pagination math.
  // The renderer treats paraIndices=null as "all paragraphs in this chapter".
  if (options.singlePage) {
    return [{ startChar: 0, endChar: chapterText.length, paraIndices: null, isSplit: false, isSinglePage: true }];
  }

  // Scan paragraph ranges using the same boundary as the renderer (\n{2,}).
  // Skip whitespace-only paragraphs so our indices match the renderer's
  // post-filter array.
  var paraRanges = [];
  var br = /\n{2,}/g;
  var lastEnd = 0;
  var m;
  while ((m = br.exec(chapterText)) !== null) {
    if (chapterText.slice(lastEnd, m.index).trim().length > 0) {
      paraRanges.push({ start: lastEnd, end: m.index });
    }
    lastEnd = m.index + m[0].length;
  }
  if (lastEnd < chapterText.length && chapterText.slice(lastEnd).trim().length > 0) {
    paraRanges.push({ start: lastEnd, end: chapterText.length });
  }

  if (paraRanges.length === 0) {
    return [{ startChar: 0, endChar: chapterText.length, paraIndices: [], isSplit: false }];
  }

  // GIANT-PARAGRAPH EXCEPTION: one paragraph, but it's larger than the cap.
  // Split it at sentence boundaries near the 1700-char mark.
  if (paraRanges.length === 1 && (paraRanges[0].end - paraRanges[0].start) > PAGE_MAX_CHARS) {
    var pr = paraRanges[0];
    var pt = chapterText.slice(pr.start, pr.end);
    var pages = [];

    // Sentence-end positions: . ! ? … (one or more), optionally followed by
    // closing punctuation, then whitespace. Russian uses these same end marks.
    var sentEnds = [];
    var sre = /[.!?…]+["»)\]]?\s+/g;
    var sm;
    while ((sm = sre.exec(pt)) !== null) {
      sentEnds.push(sm.index + sm[0].length);
    }
    if (sentEnds.length === 0 || sentEnds[sentEnds.length - 1] !== pt.length) {
      sentEnds.push(pt.length);
    }

    var pageStart = 0;
    for (var i = 0; i < sentEnds.length; i++) {
      var sentEnd = sentEnds[i];
      if (sentEnd - pageStart >= PAGE_MAX_CHARS || i === sentEnds.length - 1) {
        pages.push({
          startChar: pr.start + pageStart,
          endChar:   pr.start + sentEnd,
          paraIndices: [0],
          isSplit: true,
        });
        pageStart = sentEnd;
      }
    }
    return pages.length ? pages : [{ startChar: pr.start, endChar: pr.end, paraIndices: [0], isSplit: false }];
  }

  // NORMAL MULTI-PARAGRAPH CASE. Greedy bucketing with look-ahead: add a
  // paragraph to the current page ONLY if doing so won't push us over the
  // limits. The single exception is when the current page is empty — we
  // always include at least one paragraph, even if it's huge (the "finish
  // that paragraph" rule keeps it intact).
  var pagesOut = [];
  var currentIdx = [];
  var currentLen = 0;

  for (var pi = 0; pi < paraRanges.length; pi++) {
    var p = paraRanges[pi];
    var pLen = p.end - p.start;
    // Separator between paragraphs is "\n\n" (2 chars) — count it for accuracy.
    var addedLen = currentIdx.length === 0 ? pLen : pLen + 2;

    var wouldOverflow = currentIdx.length > 0 && (
      currentIdx.length >= PAGE_MAX_PARAGRAPHS ||
      currentLen + addedLen > PAGE_MAX_CHARS
    );

    if (wouldOverflow) {
      pagesOut.push({
        startChar: paraRanges[currentIdx[0]].start,
        endChar:   paraRanges[currentIdx[currentIdx.length - 1]].end,
        paraIndices: currentIdx,
        isSplit: false,
      });
      currentIdx = [];
      currentLen = 0;
      addedLen = pLen;
    }

    currentIdx.push(pi);
    currentLen += addedLen;
  }

  if (currentIdx.length > 0) {
    pagesOut.push({
      startChar: paraRanges[currentIdx[0]].start,
      endChar:   paraRanges[currentIdx[currentIdx.length - 1]].end,
      paraIndices: currentIdx,
      isSplit: false,
    });
  }

  return pagesOut;
}

// Split long TTS input into ~200-char chunks at sentence boundaries. Returns an
// array of {text, start} where `start` is the char offset back into the original
// text (so word-boundary events can be mapped to global positions for the
// reading-along highlight).
//
// Why: Chrome's "Google русский" voice silently fails for utterances above
// roughly 200 characters — no onstart, no onerror, just no sound. Chunking
// and chaining via onend makes the playback reliable across all voices.
// Microsoft local voices don't have this limit, but they get chunked the same
// way for consistency.
function chunkForTTS(text, from, maxLen) {
  if (typeof maxLen !== "number") maxLen = 200;
  var slice = (text || "").slice(from || 0);
  if (!slice) return [];

  // Find sentence-end positions: . ! ? … plus optional closing punctuation,
  // followed by whitespace. Same matcher used by computePages' giant-paragraph
  // path.
  var sentEnds = [];
  var re = /[.!?…]+["»)\]]?\s+/g;
  var m;
  while ((m = re.exec(slice)) !== null) {
    sentEnds.push(m.index + m[0].length);
  }
  if (sentEnds.length === 0 || sentEnds[sentEnds.length - 1] !== slice.length) {
    sentEnds.push(slice.length);
  }

  var chunks = [];
  var chunkStart = 0;
  var lastBoundary = 0;
  for (var i = 0; i < sentEnds.length; i++) {
    var end = sentEnds[i];
    if (end - chunkStart > maxLen && lastBoundary > chunkStart) {
      chunks.push({ text: slice.slice(chunkStart, lastBoundary), start: (from || 0) + chunkStart });
      chunkStart = lastBoundary;
    }
    lastBoundary = end;
  }

  // Whatever's left after the last sentence boundary. If it's still huge
  // (one massive run-on with no sentence breaks — Tolstoy style), split it
  // at word boundaries.
  var remainder = slice.slice(chunkStart);
  var remainderStart = chunkStart;
  while (remainder.length > maxLen * 1.5) {
    var splitAt = remainder.lastIndexOf(" ", maxLen);
    if (splitAt < 30) splitAt = maxLen; // no nearby space — force-split at maxLen
    chunks.push({ text: remainder.slice(0, splitAt), start: (from || 0) + remainderStart });
    remainderStart += splitAt;
    remainder = remainder.slice(splitAt);
  }
  if (remainder.length > 0) {
    chunks.push({ text: remainder, start: (from || 0) + remainderStart });
  }

  return chunks;
}

function defprompt(w) {
  return `Define the Russian word "${w}" for an English learner. Return JSON ONLY, no markdown.

Required fields:
{
  "word": "${w}",
  "lemma": "<dictionary form: NOMINATIVE singular for nouns, INFINITIVE for verbs, masculine singular for adjectives>",
  "aspectPair": "<verbs ONLY: the aspectual partner infinitive if it is a clear, commonly-paired pair; empty string otherwise>",
  "aspect": "<verbs ONLY: 'imperfective' or 'perfective'; empty string otherwise>",
  "partOfSpeech": "<noun, verb, adjective, adverb, pronoun, preposition, conjunction, particle, etc.>",
  "translation": "<English translation; for verbs use 'to ...'>",
  "grammar": "<brief note: gender for nouns, conjugation/aspect for verbs, etc.>",
  "example": "<short Russian example sentence>",
  "exampleTranslation": "<English translation of the example>"
}

Rules for aspectPair:
- Fill it ONLY when the verb has a CLEAR, commonly-paired aspectual partner (e.g. писать↔написать, говорить↔сказать, делать↔сделать, читать↔прочитать, давать↔дать).
- Leave it empty for: motion verbs with multiple stems (ходить, идти, ездить), biaspectual verbs, defective verbs (быть), verbs whose pair is not standardly listed in dictionaries.
- aspectPair must be the infinitive form, not conjugated.

Rules for lemma:
- Always the canonical dictionary form, even if "${w}" is inflected. So if "${w}" is "столе" (prepositional), lemma is "стол". If "${w}" is "пишу" (1sg present), lemma is "писать".`;
}


function tokenise(text) {
  return (text || "").match(/[а-яёА-ЯЁ]+|[^а-яёА-ЯЁ]+/g) || [];
}

function yoVariants(word) {
  var out = [];
  for (var i = 0; i < word.length; i++) {
    if (word[i] === "е") out.push(word.slice(0,i) + "ё" + word.slice(i+1));
    else if (word[i] === "Е") out.push(word.slice(0,i) + "Ё" + word.slice(i+1));
  }
  return out;
}

// ── EPUB PARSER ──────────────────────────────────────────────────────────────

function readUint32LE(buf, off) {
  return (buf[off] | buf[off+1]<<8 | buf[off+2]<<16 | buf[off+3]<<24) >>> 0;
}
function readUint16LE(buf, off) {
  return (buf[off] | buf[off+1]<<8) >>> 0;
}

function parseZip(buffer) {
  var bytes = new Uint8Array(buffer);
  var files = {};

  // Find End of Central Directory record (signature: PK\x05\x06)
  var eocd = -1;
  var maxScan = Math.max(0, bytes.length - 65557);
  for (var i = bytes.length - 22; i >= maxScan; i--) {
    if (bytes[i]===0x50 && bytes[i+1]===0x4B && bytes[i+2]===0x05 && bytes[i+3]===0x06) {
      eocd = i; break;
    }
  }
  if (eocd === -1) throw new Error("Invalid ZIP: End of Central Directory not found");

  var cdSize   = readUint32LE(bytes, eocd + 12);
  var cdOffset = readUint32LE(bytes, eocd + 16);

  // Walk central directory entries (signature: PK\x01\x02)
  var pos = cdOffset;
  var end = cdOffset + cdSize;
  while (pos < end - 4) {
    if (bytes[pos]!==0x50 || bytes[pos+1]!==0x4B || bytes[pos+2]!==0x01 || bytes[pos+3]!==0x02) break;

    var comp        = readUint16LE(bytes, pos + 10);
    var csize       = readUint32LE(bytes, pos + 20);
    var fnlen       = readUint16LE(bytes, pos + 28);
    var exlen       = readUint16LE(bytes, pos + 30);
    var cmtlen      = readUint16LE(bytes, pos + 32);
    var localOff    = readUint32LE(bytes, pos + 42);
    var fname       = new TextDecoder().decode(bytes.slice(pos + 46, pos + 46 + fnlen));

    // Jump to the local header to find the actual data start
    // (local header has its own filename and extra-field lengths that may differ)
    if (localOff + 30 < bytes.length) {
      var lfnlen    = readUint16LE(bytes, localOff + 26);
      var lexlen    = readUint16LE(bytes, localOff + 28);
      var dataStart = localOff + 30 + lfnlen + lexlen;
      var data      = bytes.slice(dataStart, dataStart + csize);

      if (comp === 0) {
        files[fname] = new TextDecoder("utf-8").decode(data);
      } else if (comp === 8) {
        try {
          var ds = new DecompressionStream("deflate-raw");
          var writer = ds.writable.getWriter();
          writer.write(data); writer.close();
          files[fname] = { stream: ds.readable, name: fname };
        } catch(ex) {}
      }
    }

    pos += 46 + fnlen + exlen + cmtlen;
  }
  return files;
}

async function decompressEntry(entry) {
  if (typeof entry === "string") return entry;
  // Cached text from a previous read — streams can only be consumed once, so we memoize here.
  if (entry && typeof entry._text === "string") return entry._text;
  // If a concurrent decompression is in flight on the same entry, wait for it.
  if (entry && entry._reading) {
    try { await entry._reading; } catch(e) {}
    return entry._text || "";
  }
  if (entry && entry.stream) {
    var run = (async function() {
      var reader = entry.stream.getReader();
      var chunks = [];
      while (true) {
        var r = await reader.read();
        if (r.done) break;
        chunks.push(r.value);
      }
      var total = chunks.reduce(function(a,c){ return a+c.length; }, 0);
      var out = new Uint8Array(total); var pos = 0;
      for (var ci = 0; ci < chunks.length; ci++) { out.set(chunks[ci], pos); pos += chunks[ci].length; }
      return new TextDecoder("utf-8").decode(out);
    })();
    entry._reading = run;
    try {
      entry._text = await run;
    } catch (e) {
      entry._text = "";
    }
    delete entry._reading;
    return entry._text;
  }
  return "";
}

// HTML → plain text. Defensive: handles malformed HTML, weird entity encodings,
// XHTML namespace quirks, and "plain text" files that have HTML markup pasted in.
// Strategy:
//   1. Use DOMParser when possible (correctly handles tag nesting + entities)
//   2. Regex-scrub any tags or entities that slipped through (mismatched braces,
//      processing instructions, namespace prefixes, etc.)
//   3. Normalize whitespace so paragraphs come out as clean text + double newlines
function htmlToText(html) {
  if (!html) return "";
  var input = String(html);

  var out;
  try {
    var parser = new DOMParser();
    var doc = parser.parseFromString(input, "text/html");
    // Remove scripts/styles/comments/processing instructions before walking.
    doc.querySelectorAll("script, style, noscript, head").forEach(function(el){ el.remove(); });
    var result = [];
    var blockTags = {"P":1,"DIV":1,"H1":1,"H2":1,"H3":1,"H4":1,"H5":1,"H6":1,
                     "LI":1,"BR":1,"TR":1,"BLOCKQUOTE":1,"PRE":1,"SECTION":1,"ARTICLE":1,"HR":1};
    function walk(node) {
      if (!node) return;
      if (node.nodeType === 3) {
        var t = node.nodeValue;
        if (t) result.push(t);
      } else if (node.nodeType === 1) {
        var tag = node.tagName.toUpperCase();
        if (tag === "SCRIPT" || tag === "STYLE") return;
        if (blockTags[tag]) result.push("\n\n");
        for (var ci = 0; ci < node.childNodes.length; ci++) walk(node.childNodes[ci]);
        if (blockTags[tag]) result.push("\n\n");
      }
    }
    walk(doc.body || doc.documentElement);
    out = result.join("");
  } catch (e) {
    // DOMParser shouldn't fail in a browser, but fall back to using the raw
    // input rather than throwing — the entity/tag scrub below will still work.
    out = input;
  }

  // Belt-and-suspenders pass: scrub anything that still looks like HTML.
  // This catches:
  //   - tags DOMParser may have left intact (e.g. self-closing with weird attrs)
  //   - entities the parser didn't decode (when input wasn't proper HTML, like a
  //     .txt with literal "<p>" or "&nbsp;" markup pasted in)
  //   - namespace prefixes (<ns:p>) common in OOXML / XHTML exports
  out = out
    .replace(/<!--[\s\S]*?-->/g, "")                      // HTML comments
    .replace(/<\?[\s\S]*?\?>/g, "")                       // processing instructions
    .replace(/<\/?[a-zA-Z][a-zA-Z0-9:_.-]*(?:\s[^>]*)?>/g, "") // any leftover tags incl. namespaced
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&apos;/gi, "'")
    .replace(/&mdash;/gi, "—")
    .replace(/&ndash;/gi, "–")
    .replace(/&hellip;/gi, "…")
    .replace(/&laquo;/gi, "«")
    .replace(/&raquo;/gi, "»")
    .replace(/&bull;/gi, "•")
    .replace(/&middot;/gi, "·")
    .replace(/&#x([0-9a-fA-F]+);/g, function(_, hex){ try { return String.fromCodePoint(parseInt(hex, 16)); } catch(_){ return ""; } })
    .replace(/&#(\d+);/g, function(_, dec){ try { return String.fromCodePoint(parseInt(dec, 10)); } catch(_){ return ""; } })
    .replace(/\u00A0/g, " ")                              // NBSP as a unicode char
    .replace(/[\u200B-\u200D\uFEFF]/g, "")                // zero-width characters
    .replace(/\r\n?/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return out;
}

function isFrontMatter(heading, text) {
  var h = (heading || "").toLowerCase().trim();
  var t = (text || "").slice(0, 300).toLowerCase().trim();
  // Publisher/editorial metadata to skip. Author content (prefaces by the
  // author themselves, dedications, epigraphs) is intentionally NOT in this
  // list — that content matters as part of the work.
  // What IS skipped: copyright pages, ISBN blocks, publisher addresses,
  // translator credits, generic forewords/intros by third parties.
  var skip = [
    /^аннотация\b/, /^оглавление\b/, /^содержание\b/,
    /^обложка\b/, /^титульн/, /^выходные данные\b/,
    /^cover\b/, /^title page\b/, /^contents\b/, /^table of contents\b/,
    /^copyright\b/, /^annotation\b/, /^colophon\b/, /^about the (author|book)\b/,
    /^acknowledg(e?)ments\b/, /^издательств/,
    /^foreword\b/, /^предисловие\b/, /^от издательства\b/, /^от переводчика\b/,
    /^translator['s ]*note\b/, /^translation\b/, /^isbn\b/,
    /^all rights reserved\b/, /^©\b/, /^©\s*\d/, /^\d{4}\s+©/,
    /^напечатано в\b/, /^printed in\b/, /^универсальный десятичный код\b/, /^удк\b/, /^ббк\b/
  ];
  return skip.some(function(p) { return p.test(h) || p.test(t); });
}

// ── TOC parsing ────────────────────────────────────────────────────────────
// Modern EPUBs declare the author's intended chapter list in a table of contents
// file (NCX for EPUB 2, nav.xhtml for EPUB 3). Using that gives us proper chapter
// boundaries and good headings — far better than the spine order alone, which
// treats every front-matter file (cover, title page, copyright) as a "chapter".

// Quick label-only front-matter check used when filtering TOC entries.
// Also matches against the author name and book title from OPF metadata, since
// title pages commonly use the author's name as their TOC label.
function isFrontMatterLabel(label, authorName, bookTitle) {
  var l = (label || "").toLowerCase().trim();
  if (!l) return true;

  // Generic front-matter labels (Russian + English).
  if (/^(cover|обложка|title page|титульн|titul|copyright|авторские права|table of contents|оглавление|содержание|toc|annotation|аннотация|colophon|выходные данные|book information|информация о книге|об авторе|about the author|acknowledg|благодарност|dedication|посвящение)\b/i.test(l)) return true;

  // Title-page labels: author name or book title used as a TOC entry.
  // Russian title pages frequently show "Антон Чехов" or "А. П. Чехов" as the
  // first navPoint pointing at a page that just contains the author + title.
  function tokens(s) {
    return (s || "").toLowerCase().replace(/[.,]/g, " ").split(/\s+/).filter(function(t){ return t.length > 1; });
  }
  var labelToks = tokens(l);
  if (authorName) {
    var aToks = tokens(authorName);
    if (aToks.length > 0) {
      var sharedA = aToks.filter(function(t){ return labelToks.indexOf(t) !== -1; }).length;
      // Whole-author match, or label is just a subset of author name (e.g. "Чехов", "А. П. Чехов")
      if (sharedA >= 2) return true;
      if (sharedA >= 1 && labelToks.length <= 3 && labelToks.every(function(t){ return aToks.indexOf(t) !== -1; })) return true;
    }
  }
  if (bookTitle) {
    var bToks = tokens(bookTitle);
    if (bToks.length > 0 && labelToks.length > 0) {
      var sharedB = bToks.filter(function(t){ return labelToks.indexOf(t) !== -1; }).length;
      if (sharedB === bToks.length || (sharedB >= 2 && sharedB === labelToks.length)) return true;
    }
  }

  return false;
}

// Resolve a relative path against a base directory (handles ../ and ./ correctly).
function resolvePath(baseDir, relPath) {
  var parts = (baseDir + relPath).split("/");
  var stack = [];
  for (var i = 0; i < parts.length; i++) {
    var p = parts[i];
    if (p === "" || p === ".") continue;
    if (p === "..") stack.pop();
    else stack.push(p);
  }
  return stack.join("/");
}

// Parse an NCX file (EPUB 2 TOC). Returns an ordered list of { label, file, fragment }
// where `file` is the resolved zip-path and `fragment` is the anchor id (or "").
// Only leaf navPoints are emitted (so a nested "Part / Chapter" TOC yields only chapters).
async function parseNcxToc(zipFiles, opfDir, ncxPath) {
  var fullPath = resolvePath(opfDir, ncxPath);
  var data = zipFiles[fullPath] || zipFiles[ncxPath];
  if (!data) return [];
  var xml = typeof data === "string" ? data : await decompressEntry(data);
  var ncxDir = fullPath.includes("/") ? fullPath.slice(0, fullPath.lastIndexOf("/") + 1) : "";

  var doc;
  try {
    doc = new DOMParser().parseFromString(xml, "application/xml");
  } catch(e) { return []; }
  var nps = doc.getElementsByTagName("navPoint");
  var entries = [];
  for (var i = 0; i < nps.length; i++) {
    var np = nps[i];
    // Skip non-leaf navPoints — their children give finer-grained chapters.
    if (np.getElementsByTagName("navPoint").length > 0) continue;
    var labelEl   = np.querySelector("navLabel > text") || np.getElementsByTagName("text")[0];
    var contentEl = np.getElementsByTagName("content")[0];
    if (!labelEl || !contentEl) continue;
    var label = (labelEl.textContent || "").trim();
    var src   = contentEl.getAttribute("src") || "";
    if (!src) continue;
    var hashIdx = src.indexOf("#");
    var file = hashIdx >= 0 ? src.slice(0, hashIdx) : src;
    var frag = hashIdx >= 0 ? src.slice(hashIdx + 1) : "";
    try { file = decodeURIComponent(file); } catch(e) {}
    entries.push({ label: label, file: resolvePath(ncxDir, file), fragment: frag });
  }
  return entries;
}

// Parse an EPUB 3 nav.xhtml file. Returns { label, file, fragment } entries.
async function parseNavToc(zipFiles, opfDir, navPath) {
  var fullPath = resolvePath(opfDir, navPath);
  var data = zipFiles[fullPath] || zipFiles[navPath];
  if (!data) return [];
  var html = typeof data === "string" ? data : await decompressEntry(data);
  var navDir = fullPath.includes("/") ? fullPath.slice(0, fullPath.lastIndexOf("/") + 1) : "";

  // Find the <nav> marked as the toc, or any <nav> as a fallback.
  var navHtml = html.match(/<nav\b[^>]*\bepub:type\s*=\s*["'][^"']*\btoc\b[^"']*["'][^>]*>([\s\S]*?)<\/nav>/i)
            || html.match(/<nav\b[^>]*>([\s\S]*?)<\/nav>/i);
  if (!navHtml) return [];

  // Pull <a href> entries. We don't need to preserve list nesting — order suffices.
  var entries = [];
  var linkRe = /<a\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  var m;
  while ((m = linkRe.exec(navHtml[1])) !== null) {
    var href  = m[1];
    var label = m[2].replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
    if (!href) continue;
    var hashIdx = href.indexOf("#");
    var file = hashIdx >= 0 ? href.slice(0, hashIdx) : href;
    var frag = hashIdx >= 0 ? href.slice(hashIdx + 1) : "";
    try { file = decodeURIComponent(file); } catch(e) {}
    entries.push({ label: label, file: resolvePath(navDir, file), fragment: frag });
  }
  return entries;
}

// Given an HTML string and two anchor ids, return the HTML slice between them.
// Either id may be empty (meaning "start of doc" or "end of doc"). Used to split
// a single file into multiple chapters when the TOC points at fragments.
function htmlSliceByAnchors(html, startId, endId) {
  var startIdx = 0;
  if (startId) {
    var esc = startId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    var re  = new RegExp("<[^>]*\\bid\\s*=\\s*[\"']" + esc + "[\"']", "i");
    var sm  = html.match(re);
    if (sm) startIdx = sm.index;
  }
  var endIdx = html.length;
  if (endId) {
    var esc2 = endId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    var re2  = new RegExp("<[^>]*\\bid\\s*=\\s*[\"']" + esc2 + "[\"']", "i");
    var slice = html.slice(startIdx);
    var em = slice.match(re2);
    if (em) endIdx = startIdx + em.index;
  }
  return html.slice(startIdx, endIdx);
}

// Build the chapter list from filtered TOC entries.
// Consecutive entries pointing at the same file with different fragments split that file.
async function buildChaptersFromToc(entries, zipFiles) {
  var chapters = [];
  for (var i = 0; i < entries.length; i++) {
    var e    = entries[i];
    var next = entries[i + 1];
    var fileData = zipFiles[e.file];
    if (!fileData) continue;
    var html = typeof fileData === "string" ? fileData : await decompressEntry(fileData);

    var chunk;
    var sameFileNext = next && next.file === e.file;
    if (e.fragment || sameFileNext) {
      chunk = htmlSliceByAnchors(html, e.fragment || "", sameFileNext ? (next.fragment || "") : "");
    } else {
      chunk = html;
    }
    var text = htmlToText(chunk);
    var cyr  = (text.match(/[а-яёА-ЯЁ]/g) || []).length;
    if (cyr < 5) continue;
    // Prefer a heading extracted from the chapter HTML over the TOC label —
    // some EPUBs use generic / author / publisher labels in the TOC even though
    // the actual chapter document has a clean <h1> or <h2> with the real title.
    var headingFromHtml = "";
    var hM = chunk.match(/<h[1-6][^>]*>([\s\S]*?)<\/h[1-6]>/i);
    if (hM) headingFromHtml = hM[1].replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
    var heading = headingFromHtml || e.label || ("Глава " + (chapters.length + 1));
    chapters.push({ heading: heading, text: text });
  }
  return chapters;
}

// ── Text-based chapter marker detection ─────────────────────────────────────
// Authors mark their chapter divisions inside the actual text — usually with
// Roman numerals (I, II, III...), Arabic numbers (1, 2, 3), or "Глава N" /
// "Часть N" / "Chapter N". Detecting these is far more reliable than trusting
// spine items or TOC labels, which often include front matter (cover, copyright,
// title page) as if they were chapters.
function isChapterMarker(line) {
  var l = (line || "").trim();
  if (!l || l.length > 30) return false;
  // Roman numerals up to L (50) — covers virtually every Russian classic.
  if (/^[IVXLivxl]{1,6}\.?$/.test(l)) return true;
  // Arabic numbers up to 999 — handles short story collections, song books, etc.
  if (/^\d{1,3}\.?$/.test(l)) return true;
  // Explicit chapter words with a number
  if (/^(глава|часть|chapter|part)\s+([0-9]+|[ivxl]+)\.?$/i.test(l)) return true;
  // Special section names
  if (/^(пролог|prologue|prolog|эпилог|epilogue|вступление|введение|заключение|послесловие)\.?$/i.test(l)) return true;
  return false;
}

// Concatenate a chapter list, then re-split at in-text chapter markers.
// Each marker line itself becomes the chapter heading; the text between markers
// is the chapter body. Returns null when fewer than 2 markers are found
// (caller should keep the existing chapter structure in that case).
function splitByMarkers(chapters) {
  var fullText = chapters.map(function(c){ return (c.text || ""); }).join("\n\n");
  var lines = fullText.split("\n");
  var markers = [];
  for (var i = 0; i < lines.length; i++) {
    if (isChapterMarker(lines[i])) {
      markers.push({ idx: i, label: lines[i].trim().replace(/\.+$/, "").toUpperCase() });
    }
  }
  if (markers.length < 2) return null;
  var out = [];
  for (var j = 0; j < markers.length; j++) {
    var start = markers[j].idx + 1;
    var end = (j + 1 < markers.length) ? markers[j + 1].idx : lines.length;
    var chunk = lines.slice(start, end).join("\n").trim();
    if (chunk.length < 50) continue; // skip tiny / empty splits
    out.push({ heading: markers[j].label, text: chunk });
  }
  return out.length >= 2 ? out : null;
}


async function parseEpub(buffer) {
  var zipFiles = parseZip(buffer);

  // Detect DRM-protected EPUBs early — Adobe ADEPT, Apple FairPlay, B&N, Kobo all add these files.
  // Parsing won't yield readable text from DRM-locked files; tell the user clearly instead of "no Russian found".
  if (zipFiles["META-INF/encryption.xml"] || zipFiles["META-INF/rights.xml"]) {
    throw new Error("This EPUB is DRM-protected (locked by the seller). Try a DRM-free source: Project Gutenberg, Flibusta, or Litres exports marked « без DRM ».");
  }

  var containerXml = zipFiles["META-INF/container.xml"];
  if (!containerXml) throw new Error("Not a valid EPUB — no container.xml. File may be corrupted or not actually an EPUB.");
  if (typeof containerXml !== "string") containerXml = await decompressEntry(containerXml);

  var opfMatch = containerXml.match(/full-path="([^"]+\.opf)"/i);
  if (!opfMatch) throw new Error("Could not find OPF file in EPUB");
  var opfPath = opfMatch[1];
  var opfDir  = opfPath.includes("/") ? opfPath.slice(0, opfPath.lastIndexOf("/")+1) : "";

  var opfRaw = zipFiles[opfPath];
  if (!opfRaw) throw new Error("OPF file not found: " + opfPath);
  if (typeof opfRaw !== "string") opfRaw = await decompressEntry(opfRaw);

  var manifestItems = {};
  var itemRe = /<item\b([^>]+)>/gi;
  var mm;
  while ((mm = itemRe.exec(opfRaw)) !== null) {
    var attrs = mm[1];
    var idM   = attrs.match(/\bid\s*=\s*["']([^"']+)["']/i);
    var hrefM = attrs.match(/\bhref\s*=\s*["']([^"']+)["']/i);
    if (idM && hrefM) manifestItems[idM[1]] = hrefM[1];
  }

  var spineIds = [];
  var itemrefRe = /<itemref\b([^>]+)>/gi;
  var sm;
  while ((sm = itemrefRe.exec(opfRaw)) !== null) {
    var idrefM = sm[1].match(/\bidref\s*=\s*["']([^"']+)["']/i);
    if (idrefM) spineIds.push(idrefM[1]);
  }

  if (spineIds.length === 0) throw new Error("No spine items found in EPUB");

  // ── First try TOC-based chapter extraction ──
  // Most EPUBs ship a table of contents that lists the AUTHOR'S intended chapters
  // (NCX for EPUB 2, nav.xhtml for EPUB 3). Using it gives us proper headings and
  // skips front matter that the author considered non-chapter content (cover,
  // title page, copyright, etc.) — a single spine item per "chapter" approach
  // happily treats those as Chapter 1, 2, 3 because they're separate files.

  // Find an NCX file. EPUB 2 puts the id on <spine toc="ncx-id">; EPUB 3 puts
  // it in the manifest via media-type. Both forms appear in the wild.
  var ncxPath = null;
  var spineTocM = opfRaw.match(/<spine\b[^>]*\btoc\s*=\s*["']([^"']+)["']/i);
  if (spineTocM && manifestItems[spineTocM[1]]) ncxPath = manifestItems[spineTocM[1]];
  if (!ncxPath) {
    var ncxItemM = opfRaw.match(/<item\b[^>]*media-type\s*=\s*["']application\/x-dtbncx\+xml["'][^>]*\bhref\s*=\s*["']([^"']+)["']/i)
                || opfRaw.match(/<item\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*\bmedia-type\s*=\s*["']application\/x-dtbncx\+xml["']/i);
    if (ncxItemM) ncxPath = ncxItemM[1];
  }
  // EPUB 3 nav doc — flagged via properties="nav" in the manifest.
  var navHref = null;
  var navItemM = opfRaw.match(/<item\b[^>]*\bproperties\s*=\s*["'][^"']*\bnav\b[^"']*["'][^>]*\bhref\s*=\s*["']([^"']+)["']/i)
              || opfRaw.match(/<item\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*\bproperties\s*=\s*["'][^"']*\bnav\b/i);
  if (navItemM) navHref = navItemM[1];

  var tocEntries = [];
  try {
    if (ncxPath)       tocEntries = await parseNcxToc(zipFiles, opfDir, ncxPath);
    else if (navHref)  tocEntries = await parseNavToc(zipFiles, opfDir, navHref);
  } catch(e) { tocEntries = []; }

  // Extract title/author NOW so we can use them to filter title-page entries
  // (very common pattern: TOC entry labeled with author's name pointing at a
  // page that only contains the author + title).
  var titleM_  = opfRaw.match(/<dc:title[^>]*>([^<]+)<\/dc:title>/i);
  var authorM_ = opfRaw.match(/<dc:creator[^>]*>([^<]+)<\/dc:creator>/i);
  var bookTitle  = titleM_  ? titleM_[1].trim()  : "";
  var bookAuthor = authorM_ ? authorM_[1].trim() : "";

  // Filter out front-matter labels AND author/title-page entries.
  var realEntries = tocEntries.filter(function(e){ return !isFrontMatterLabel(e.label, bookAuthor, bookTitle); });

  if (realEntries.length >= 2) {
    var tocChs = await buildChaptersFromToc(realEntries, zipFiles);
    // Drop leading chapters that are dramatically shorter than the rest of the
    // book — almost always front matter (cover, title page, copyright, dedication)
    // that the EPUB packaged as a navigable chapter.
    // Use the median chapter length to adapt to books with naturally short
    // chapters (poetry, song lyrics) where a fixed threshold would over-trim.
    var cyrLens = tocChs.map(function(c){ return ((c.text || "").match(/[а-яёА-ЯЁ]/g) || []).length; });
    var sortedLens = cyrLens.slice().sort(function(a,b){ return a-b; });
    var median = sortedLens.length > 0 ? sortedLens[Math.floor(sortedLens.length / 2)] : 0;
    // Threshold: at least 150 Cyrillic chars, OR 25% of median, whichever is larger.
    var threshold = Math.max(150, Math.floor(median * 0.25));
    var maxDrops = Math.min(5, tocChs.length - 1);  // never drop everything
    while (maxDrops > 0 && tocChs.length > 1) {
      var firstCyr = ((tocChs[0].text || "").match(/[а-яёА-ЯЁ]/g) || []).length;
      if (firstCyr < threshold) {
        tocChs.shift();
        maxDrops--;
        continue;
      }
      break;
    }
    if (tocChs.length >= 2) {
      return {
        chapters: tocChs,
        title:  bookTitle  || "Unknown title",
        author: bookAuthor || "Unknown author"
      };
    }
  }

  var chapters = [];
  for (var k = 0; k < spineIds.length; k++) {
    var id   = spineIds[k];
    var href = manifestItems[id];
    if (!href) continue;
    var clean = href.split("#")[0];
    try { clean = decodeURIComponent(clean); } catch(e) {}
    var fullPath = opfDir + clean;
    var fileData = zipFiles[fullPath] || zipFiles[clean] || zipFiles[href.split("#")[0]];
    if (!fileData) continue;
    var html = typeof fileData === "string" ? fileData : await decompressEntry(fileData);
    var text = htmlToText(html);
    var cyrCount = (text.match(/[а-яёА-ЯЁ]/g) || []).length;
    if (cyrCount < 5) continue;

    var headMatch = html.match(/<h[1-3][^>]*>([^<]*)<\/h[1-3]>/i);
    var heading = headMatch ? headMatch[1].trim() : ("Глава " + (chapters.length+1));
    if (isFrontMatter(heading, text)) continue;
    chapters.push({ heading: heading, text: text });
  }

  if (chapters.length === 0) {
    // Fallback: scan ALL HTML/XHTML files in the zip, not just spine
    var keys = Object.keys(zipFiles);
    for (var ki = 0; ki < keys.length; ki++) {
      var fname = keys[ki];
      if (!/\.(x?html?)$/i.test(fname)) continue;
      var fd = zipFiles[fname];
      var ht = typeof fd === "string" ? fd : await decompressEntry(fd);
      var tx = htmlToText(ht);
      var cy = (tx.match(/[а-яёА-ЯЁ]/g) || []).length;
      if (cy < 5) continue;
      var hm = ht.match(/<h[1-3][^>]*>([^<]*)<\/h[1-3]>/i);
      var hd = hm ? hm[1].trim() : ("Глава " + (chapters.length+1));
      if (isFrontMatter(hd, tx)) continue;
      chapters.push({ heading: hd, text: tx });
    }
  }

  if (chapters.length === 0) {
    // Last resort: take everything that has ANY Russian, regardless of front-matter checks.
    var lastKeys = Object.keys(zipFiles);
    for (var li = 0; li < lastKeys.length; li++) {
      var lf = lastKeys[li];
      if (!/\.(x?html?)$/i.test(lf)) continue;
      var ld = zipFiles[lf];
      var lh = typeof ld === "string" ? ld : await decompressEntry(ld);
      var lt = htmlToText(lh);
      var lcy = (lt.match(/[а-яёА-ЯЁ]/g) || []).length;
      if (lcy < 5) continue;
      var lhm = lh.match(/<h[1-3][^>]*>([^<]*)<\/h[1-3]>/i);
      var lhd = lhm ? lhm[1].trim() : ("Глава " + (chapters.length+1));
      chapters.push({ heading: lhd, text: lt });
    }
  }

  if (chapters.length === 0) {
    throw new Error("Could not extract Russian text. The EPUB may be empty, corrupted, in a different language, or use unusual encoding. If it's a DRM-locked file from a bookstore, it can't be read here — try a DRM-free source.");
  }

  // Trim leading "chapters" that are too short to be real story content (title pages,
  // copyright, etc.) — uses the same adaptive median heuristic as the TOC path.
  var spCyrLens = chapters.map(function(c){ return ((c.text || "").match(/[а-яёА-ЯЁ]/g) || []).length; });
  var spSorted = spCyrLens.slice().sort(function(a,b){ return a-b; });
  var spMedian = spSorted.length > 0 ? spSorted[Math.floor(spSorted.length / 2)] : 0;
  var spThreshold = Math.max(150, Math.floor(spMedian * 0.25));
  var spMaxDrops = Math.min(5, chapters.length - 1);
  while (spMaxDrops > 0 && chapters.length > 1) {
    var firstSpineCyr = ((chapters[0].text || "").match(/[а-яёА-ЯЁ]/g) || []).length;
    if (firstSpineCyr < spThreshold) {
      chapters.shift();
      spMaxDrops--;
      continue;
    }
    break;
  }

  // Extract title/author from OPF metadata
  var titleM  = opfRaw.match(/<dc:title[^>]*>([^<]+)<\/dc:title>/i);
  var authorM = opfRaw.match(/<dc:creator[^>]*>([^<]+)<\/dc:creator>/i);
  var title   = titleM  ? titleM[1].trim()  : "Unknown title";
  var author  = authorM ? authorM[1].trim() : "Unknown author";

  return { chapters: chapters, title: title, author: author };
}

// ── ENCODING / TEXT HELPERS ──────────────────────────────────────────────────
// Russian texts are sometimes saved in cp1251 or KOI8-R rather than UTF-8.
// This tries UTF-8 first, falls back if the result has replacement chars or no Cyrillic.
function decodeBytes(buffer) {
  var bytes = new Uint8Array(buffer);
  var text = new TextDecoder("utf-8", { fatal: false }).decode(bytes);
  if (text.indexOf("\uFFFD") > -1 || !/[а-яёА-ЯЁ]/.test(text)) {
    try { text = new TextDecoder("windows-1251").decode(bytes); } catch(e) {}
  }
  return text;
}

// Try to split a long plain-text blob into chapters by common headings.
function splitTextIntoChapters(text) {
  // Look for "Глава N", "Часть N", "Chapter N", roman numerals on their own line, etc.
  var lines = text.split(/\r?\n/);
  var marks = [];
  var headRe = /^\s*(Глава|ГЛАВА|Часть|ЧАСТЬ|Chapter|CHAPTER|Section)\s+[\dIVXLCDM]+/i;
  var romanRe = /^\s*[IVXLCDM]{1,5}\.?\s*$/;
  for (var i = 0; i < lines.length; i++) {
    var l = lines[i].trim();
    if (!l) continue;
    if (headRe.test(l) || romanRe.test(l)) marks.push({ idx: i, heading: l });
  }
  if (marks.length < 2) {
    // No reliable chapter markers — return the whole text as one chapter.
    return [{ heading: "Текст", text: text.trim() }];
  }
  var out = [];
  for (var j = 0; j < marks.length; j++) {
    var startLine = marks[j].idx;
    var endLine   = j + 1 < marks.length ? marks[j+1].idx : lines.length;
    var body = lines.slice(startLine + 1, endLine).join("\n").trim();
    if (body.length < 40) continue;  // skip tiny "chapters"
    out.push({ heading: marks[j].heading, text: body });
  }
  return out.length ? out : [{ heading: "Текст", text: text.trim() }];
}

// ── FB2 (FictionBook) — XML-based, very common for Russian ebooks ───────────
async function parseFb2(buffer, options) {
  options = options || {};
  // FB2 files declare their own encoding in the XML header.
  var text = decodeBytes(buffer);
  var encMatch = /encoding=["']([^"']+)["']/i.exec(text.slice(0, 200));
  if (encMatch && !/utf-?8/i.test(encMatch[1])) {
    try { text = new TextDecoder(encMatch[1]).decode(new Uint8Array(buffer)); } catch(e) {}
  }
  var parser = new DOMParser();
  var doc = parser.parseFromString(text, "application/xml");
  // DOMParser returns a <parsererror> root if it failed.
  if (doc.querySelector("parsererror")) throw new Error("FB2 file is malformed XML");

  // Title and author from <description><title-info>
  var bookTitle = (doc.querySelector("title-info > book-title") || {}).textContent || "";
  var fn = (doc.querySelector("title-info > author > first-name") || {}).textContent || "";
  var ln = (doc.querySelector("title-info > author > last-name")  || {}).textContent || "";
  var nick = (doc.querySelector("title-info > author > nickname") || {}).textContent || "";
  var author = (fn + " " + ln).trim() || nick || "Unknown author";

  // Each <section> in <body> is a chapter.
  var sections = doc.querySelectorAll("body > section");
  var chapters = [];
  for (var i = 0; i < sections.length; i++) {
    var sec = sections[i];
    // <title> contains the chapter heading; collect its text.
    var titleEl = sec.querySelector(":scope > title");
    var heading = titleEl ? titleEl.textContent.replace(/\s+/g, " ").trim() : ("Глава " + (chapters.length + 1));
    // Remove the title from the body so we don't repeat it.
    if (titleEl) titleEl.remove();
    // Collect all paragraph-like text with blank lines between.
    var paras = [];
    var ps = sec.querySelectorAll("p, v, subtitle");
    for (var p = 0; p < ps.length; p++) {
      var t = ps[p].textContent.replace(/\s+/g, " ").trim();
      if (t) paras.push(t);
    }
    var body = paras.join("\n\n");
    var cyrCount = (body.match(/[а-яёА-ЯЁ]/g) || []).length;
    if (cyrCount < 5) continue;
    chapters.push({ heading: heading, text: body });
  }

  // Fallback: if no <section>s, treat entire body as one chapter
  if (chapters.length === 0) {
    var bodyEl = doc.querySelector("body");
    if (bodyEl) {
      var ps2 = bodyEl.querySelectorAll("p");
      var paras2 = [];
      for (var k = 0; k < ps2.length; k++) {
        var tt = ps2[k].textContent.replace(/\s+/g, " ").trim();
        if (tt) paras2.push(tt);
      }
      if (paras2.length) chapters.push({ heading: bookTitle || "Текст", text: paras2.join("\n\n") });
    }
  }

  if (chapters.length === 0) throw new Error("FB2 file has no readable Russian text.");
  return { chapters: chapters, title: bookTitle || "Unknown title", author: author };
}

// ── FB2 inside a ZIP — common .fb2.zip distribution ─────────────────────────
async function parseFb2Zip(buffer) {
  var zipFiles = parseZip(buffer);
  var keys = Object.keys(zipFiles);
  var fb2Key = keys.find(function(k){ return /\.fb2$/i.test(k); });
  if (!fb2Key) throw new Error("Zip does not contain an .fb2 file.");
  var raw = zipFiles[fb2Key];
  var fb2Text = typeof raw === "string" ? raw : await decompressEntry(raw);
  // Re-encode the decoded text back to bytes so parseFb2 can re-read encoding header.
  var bytes = new TextEncoder().encode(fb2Text);
  return await parseFb2(bytes.buffer);
}

// ── Plain TXT ───────────────────────────────────────────────────────────────
function parseTxt(buffer, fname) {
  var text = decodeBytes(buffer);
  // Defensive: some sources save copy-pasted webpage content as .txt with the
  // HTML tags still present. If we see tags or entities, run it through the
  // HTML stripper before splitting into chapters.
  if (/<\/?[a-zA-Z][a-zA-Z0-9:_-]*[\s>]/.test(text) || /&[a-zA-Z]{2,8};|&#\d+;/.test(text)) {
    text = htmlToText(text);
  }
  if (!/[а-яёА-ЯЁ]/.test(text)) throw new Error("No Russian text found in this file.");
  var chapters = splitTextIntoChapters(text);
  var stem = (fname || "Текст").replace(/\.[^.]+$/, "").replace(/[_-]/g, " ");
  return { chapters: chapters, title: stem, author: "" };
}

// ── HTML (single web page) ──────────────────────────────────────────────────
function parseHtml(buffer, fname) {
  var html = decodeBytes(buffer);
  var titleM = html.match(/<title[^>]*>([^<]+)<\/title>/i);
  var title = titleM ? titleM[1].trim() : (fname || "Текст").replace(/\.[^.]+$/, "");
  var text = htmlToText(html);
  if (!/[а-яёА-ЯЁ]/.test(text)) throw new Error("No Russian text found in this HTML.");
  var chapters = splitTextIntoChapters(text);
  return { chapters: chapters, title: title, author: "" };
}

// ── Master dispatcher — detects format and routes to the right parser ───────
async function parseBook(buffer, fname) {
  var lower = (fname || "").toLowerCase();
  var bytes = new Uint8Array(buffer);

  // Magic numbers
  var isZip  = bytes.length >= 4 && bytes[0] === 0x50 && bytes[1] === 0x4B; // PK\x03\x04 or PK\x05\x06
  var isXml  = bytes.length >= 5 && bytes[0] === 0x3C && bytes[1] === 0x3F && bytes[2] === 0x78; // "<?x"
  var isPdf  = bytes.length >= 5 && bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46;
  var isMobi = bytes.length >= 68 && new TextDecoder().decode(bytes.slice(60, 68)) === "BOOKMOBI";

  if (isPdf || lower.endsWith(".pdf")) {
    throw new Error("PDF files aren't supported yet. Convert to EPUB or FB2 using Calibre (free, calibre-ebook.com).");
  }
  if (isMobi || /\.(mobi|azw3?)$/i.test(lower)) {
    throw new Error("MOBI / AZW files are Kindle format and usually DRM-locked. Convert to EPUB with Calibre, or get a DRM-free EPUB / FB2 from another source.");
  }

  if (lower.endsWith(".fb2")) return await parseFb2(buffer);
  if (lower.endsWith(".fb2.zip")) return await parseFb2Zip(buffer);
  if (lower.endsWith(".txt")) return parseTxt(buffer, fname);
  if (/\.(html?|xhtml)$/.test(lower)) return parseHtml(buffer, fname);
  if (lower.endsWith(".epub")) return await parseEpub(buffer);

  // No extension match — fall back to magic-number detection.
  if (isZip) {
    // Could be EPUB or FB2-in-zip — try EPUB first (has container.xml), else FB2.
    try { return await parseEpub(buffer); }
    catch(e) {
      try { return await parseFb2Zip(buffer); }
      catch(e2) { throw new Error("ZIP file is neither an EPUB nor an FB2 archive."); }
    }
  }
  if (isXml) return await parseFb2(buffer);
  // Last resort: treat as plain text
  return parseTxt(buffer, fname);
}

// PUSHKIN_PNG: white-on-transparent silhouette of Alexander Pushkin (right-facing profile).
// Rendered via CSS mask so the silhouette picks up `currentColor` from its container,
// blending with the rest of the warm-tone palette.
var PUSHKIN_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAG4AAACWCAYAAAA/mr2PAAACvUlEQVR42u3dW1LDMBBEUaTK/rccfqCKDyCQ6DEtn14A2Lq6o5HiOG9vIiIiZ6Zd4Sbv9/v94UC01oArCufPgxIAsV0dUirABlQmvBtQmpNjoVS07gZWZm6AZaYbgswJ2NiWue4x7oWJuXNyAhcKsI2+iauVxq/3vLJ8NsBeX8s+7z8G3BXa/apHXg2wTHiak4AOcgi4K5+GVLr3DlomPKUyFF5nW2YYF2odcIxjHXAC3KnW9eolAbwnwYEWWCpBq2tdBy0TXgctE56uMhQecKc0J8qkDbhyCZwAB5z8ltlPhgHHONkKLu19H7pKiYIH3ElrnHJZ3zrGhcID7qRS6aC5vnWMC4XnY51QeIwLhQdcKDzgQuEBFwrPIXMoPMaFwnNWGQrvR+PAqw3v11IJXt3cDMGevCqF5sQGXFYGuFDrgAuFB9yppdKWoGhXurobkjFiKJW6SgFOxoPTrOxf3xgXCu1pcKzbC+0l48DbO269wkXIhjWufcRQLjZ3xh91ulJ4jWPhwRtwAEPBKZuh4EALNk4K7uPYti+eqxxozaPJOrJRa4xbX+bKlkrQNCegAXcONODs485N1fXapwOhJRS4UIhK5aCJunqyNrZlGsi4UAOBC+1IgQuF11JmmLWPcUfYB1wovF5xNoHHuGMD3JXBKZPrx4xxVzWObYHgQNs36ZVKXaUAJ8AB9018aZFxOkvgGKdcKpVSEhzrGCerwbEu2Djw1m0JlMpC8Ib8fhzrats37SVsEMyFN61UgjcXnjUudN2b/tpDwz/HvunGgTdnDPuufyyFNuDgrRu3vvoiAAwzjn1jx6lXvCh5PD4lBs8T0f+f1D3lQkEraBz7/j+By8507wMLBXclgM8sFTFri/c8h4I7CeKIZiy+m0uCGPG7AyDO3eocvX/aAXLVnvSSG99RQB0ciIiIjM87TzG8n8xH9rsAAAAASUVORK5CYII=";
var PUSHKIN_ASPECT = 150 / 110;  // height / width of the source image

function Pushkin({ size }) {
  var s = size || 56;
  var maskStyle = {
    display: "inline-block",
    width: s,
    height: Math.round(s * PUSHKIN_ASPECT),
    backgroundColor: "currentColor",
    WebkitMaskImage: "url(" + PUSHKIN_PNG + ")",
    WebkitMaskRepeat: "no-repeat",
    WebkitMaskSize: "contain",
    WebkitMaskPosition: "center",
    maskImage: "url(" + PUSHKIN_PNG + ")",
    maskRepeat: "no-repeat",
    maskSize: "contain",
    maskPosition: "center",
    verticalAlign: "middle",
  };
  return <span style={maskStyle} aria-label="Pushkin"/>;
}


function FileBtn({ label, onLoad }) {
  var ref = useRef(null);
  var [busy, setBusy] = useState(false);
  var [err, setErr] = useState("");
  var go = async function(e) {
    var f = e.target.files && e.target.files[0];
    if (!f) return;
    setBusy(true); setErr("");
    try {
      var buf = await f.arrayBuffer();
      if (buf.byteLength < 100) throw new Error("File too small");
      onLoad(buf, f.name);
    } catch(ex) { setErr(ex.message); }
    setBusy(false); e.target.value = "";
  };
  return (
    <div style={{display:"flex",flexDirection:"column",gap:6,width:"100%"}}>
      <input ref={ref} type="file" accept=".epub,.fb2,.zip,.txt,.html,.htm,.xhtml" style={{display:"none"}} onChange={go}/>
      <button className="btn-p" onClick={function(){ ref.current && ref.current.click(); }} disabled={busy}>
        {busy ? "Loading…" : "📂 " + label}
      </button>
      {err && <p style={{color:"#c87a68",fontSize:13}}>{err}</p>}
    </div>
  );
}

// Strict Chrome detection: actual Google Chrome only — NOT Edge, Brave, Opera,
// Yandex, Vivaldi, Samsung Internet. Cached after the first call since this
// can never change during a session. Note: Arc browser is indistinguishable
// from Chrome here (it inherits Chromium's UA and vendor unchanged), so Arc
// users will be treated as Chrome users.
var _isChromeCached = null;
function isStrictChrome() {
  if (_isChromeCached !== null) return _isChromeCached;
  if (typeof navigator === "undefined") return (_isChromeCached = false);
  var ua = navigator.userAgent || "";
  // Brave exposes navigator.brave even when masking its UA — most reliable signal
  if (navigator.brave) return (_isChromeCached = false);
  if (/Edg\//.test(ua))           return (_isChromeCached = false); // Edge
  if (/OPR\//.test(ua))           return (_isChromeCached = false); // Opera
  if (/SamsungBrowser/.test(ua))  return (_isChromeCached = false);
  if (/YaBrowser/.test(ua))       return (_isChromeCached = false); // Yandex
  if (/Vivaldi/.test(ua))         return (_isChromeCached = false);
  // Must have Chrome/ in UA AND vendor must be Google Inc.
  _isChromeCached = /Chrome\//.test(ua) && (navigator.vendor || "") === "Google Inc.";
  return _isChromeCached;
}

// Local (Windows SAPI) Microsoft voices like "Microsoft Pavel - Russian (Russia)".
// Distinct from the network "Microsoft ... Online (Natural)" voices: those have
// localService === false, so the && check excludes them.
function isLocalMsVoice(v) {
  return /^microsoft\b/i.test(v.name) && v.localService === true;
}

export default function App() {
  // Clerk auth — getToken() returns a JWT we attach to API calls so the
  // backend can verify the user is signed in.
  var auth = useAuth();
  var { user } = useUser();

  // authFetch — wraps fetch() with the Clerk JWT and an automatic retry with
  // skipCache:true on a 401. This handles the common case where Clerk's cached
  // session token has gone stale (e.g. the tab was backgrounded long enough
  // that the short-lived JWT expired before Clerk auto-refreshed it). When
  // skipCache succeeds we silently recover; if it still 401s the session is
  // genuinely dead and we surface the "please sign in" error to the caller.
  var authFetch = async function(url, options) {
    options = options || {};
    var attempt = async function(forceRefresh) {
      var token = "";
      try {
        token = await auth.getToken(forceRefresh ? { skipCache: true } : undefined);
      } catch(_) {}
      var h = Object.assign({}, options.headers || {});
      if (token) h.Authorization = "Bearer " + token;
      return await fetch(url, Object.assign({}, options, { headers: h }));
    };
    var r = await attempt(false);
    if (r.status === 401) r = await attempt(true);
    return r;
  };

  // Approval state — set when an /api/chat call returns 403 PENDING_APPROVAL.
  // While pending, the main app is hidden and a "waiting for approval" screen shows.
  var [pendingApproval, setPendingApproval] = useState(false);

  // ── Forum state ──────────────────────────────────────────────────────────
  var [forumOpen,      setForumOpen]      = useState(false);
  var [forumThreads,   setForumThreads]   = useState([]);   // {tid, title, author, ts, lastTs, replyCount}
  var [forumLoading,   setForumLoading]   = useState(false);
  var [forumThread,    setForumThread]    = useState(null); // currently-viewed thread (with posts)
  var [forumComposing, setForumComposing] = useState(false); // "new thread" form open
  var [newTitle,       setNewTitle]       = useState("");
  var [newBody,        setNewBody]        = useState("");
  var [replyBody,      setReplyBody]      = useState("");
  var [forumBusy,      setForumBusy]      = useState(false);
  var [forumErr,       setForumErr]       = useState("");
  var forumListRef = useRef(null);

  // ── Feedback modal state ─────────────────────────────────────────────────
  var [feedbackOpen, setFeedbackOpen] = useState(false);
  var [feedbackBody, setFeedbackBody] = useState("");
  var [feedbackBusy, setFeedbackBusy] = useState(false);
  var [feedbackMsg,  setFeedbackMsg]  = useState("");

  // Admin panel state — opened from the user menu. Only visible/usable
  // for the admin email (configured via VITE_ADMIN_EMAIL).
  var [showAdmin, setShowAdmin]   = useState(false);
  var [adminUsers, setAdminUsers] = useState([]);
  var [adminLoad, setAdminLoad]   = useState(false);
  var [adminErr, setAdminErr]     = useState("");
  var [adminBusy, setAdminBusy]   = useState({}); // { userId: "approving" | "rejecting" }
  // Upload-song panel state — admin-only, accessed via "📤 Upload" trigger.
  // Pasted song goes to a per-artist .txt in public/books/lyrics/ via the
  // /api/admin/upload-song endpoint (commits to GitHub → Vercel redeploys).
  // The same modal also handles full-book uploads via a Song/Book tab toggle.
  var [showUpload, setShowUpload]   = useState(false);
  var [upMode, setUpMode]           = useState("song");  // "song" | "book"
  var [upArtist, setUpArtist]       = useState("");
  var [upTitle, setUpTitle]         = useState("");
  var [upLyrics, setUpLyrics]       = useState("");
  var [upBusy, setUpBusy]           = useState(false);
  var [upMsg, setUpMsg]             = useState("");
  var [upErr, setUpErr]             = useState("");
  // Book-upload-specific fields (only used when upMode === "book")
  var [upBookFile, setUpBookFile]     = useState(null);
  var [upBookAuthor, setUpBookAuthor] = useState("");
  var [upBookCategory, setUpBookCategory] = useState("Novel");
  // Song-picker state — opened when the user picks a Song Lyrics artist from
  // the library dropdown. Lists the artist's individual songs so the user can
  // jump straight to one instead of starting at song 1.
  var [songPickerBook, setSongPickerBook] = useState(null);
  var [songPickerList, setSongPickerList] = useState([]);  // [{ title, index }]
  var [songPickerLoad, setSongPickerLoad] = useState(false);
  var [songPickerErr, setSongPickerErr]   = useState("");
  var ADMIN_EMAIL = (import.meta.env.VITE_ADMIN_EMAIL || "").toLowerCase();
  var currentEmail = (user && user.primaryEmailAddress && user.primaryEmailAddress.emailAddress || "").toLowerCase();
  var isAdmin = !!ADMIN_EMAIL && currentEmail === ADMIN_EMAIL;

  var [msgs, setMsgs]         = useState([]);
  var [input, setInput]       = useState("");
  var [loading, setLoading]   = useState(false);
  var [topic, setTopic]       = useState(TOPICS[0]);
  var [custom, setCustom]     = useState("");
  // CEFR level for chat conversations. Persisted in localStorage so the user
  // doesn't have to re-pick each session. Defaults to B1 (the prior hard-coded
  // value, so behavior for existing users is unchanged on first load).
  var [level, setLevel]       = useState(function(){
    try { return localStorage.getItem("gv_chat_level") || "B1"; }
    catch(e) { return "B1"; }
  });
  useEffect(function() {
    try { localStorage.setItem("gv_chat_level", level); } catch(e) {}
  }, [level]);
  var [vocab, setVocab]       = useState([]);
  var [tips, setTips]         = useState([]);
  // savedTopics: array of curriculum topic IDs the user has bookmarked from
  // the grammar reference. Stored as just IDs (e.g. "a2-accusative") so saved
  // entries stay in sync if curriculum.json gets edited later. Mirrors the
  // vocab/tips persistence pattern below.
  var [savedTopics, setSavedTopics] = useState([]);
  var [tab, setTab]           = useState("chat");
  var [started, setStarted]   = useState(false);
  var [mode, setMode]         = useState("");      // "" until user picks "chat" or "read"
  var [noAIMode, setNoAIMode] = useState(false);  // legacy flag kept for internal use only; never user-facing now
  // Clear any leftover "no_ai_mode_v1" flag from older versions so users who previously
  // bypassed login don't get stuck in a partially-broken state.
  useEffect(function() {
    try { localStorage.removeItem("no_ai_mode_v1"); } catch(e) {}
  }, []);
  var [bookMeta, setBookMeta] = useState({title:"", author:""});

  var [showTopic, setShowTopic] = useState(false);
  var [showWord,  setShowWord]  = useState(false);
  var [showTip,   setShowTip]   = useState(false);
  var [nRu, setNRu] = useState("");
  var [nEn, setNEn] = useState("");
  var [nTip, setNTip] = useState("");

  // ── Vocab quiz state ──────────────────────────────────────────────────────
  // Active when the user clicks "Review vocab" on the vocab tab. We generate
  // multiple-choice questions where the correct answer is the English meaning
  // of the Russian word, and the 3 distractors are English meanings from OTHER
  // words OF THE SAME PART OF SPEECH (verbs quiz against verbs only, nouns
  // against nouns, etc.).
  var [quizMode, setQuizMode]         = useState(false);
  var [quizMenu, setQuizMenu]         = useState(false);  // shows the 2-choice "Quiz vs Chat" menu
  var [quizQuestions, setQuizQuestions] = useState([]);
  var [quizIdx, setQuizIdx]           = useState(0);
  var [quizSelected, setQuizSelected] = useState(null);
  var [quizScore, setQuizScore]       = useState(0);
  var [quizSkipNote, setQuizSkipNote] = useState("");

  var [popup, setPopup]   = useState(null);
  var [popXY, setPopXY]   = useState({top:100,left:16});
  var popRef = useRef(null);

  // First-visit landing screen: remembered in localStorage so users only see it once per device.
  var [seenLanding, setSeenLanding] = useState(function() {
    try { return localStorage.getItem("landing_seen_v1") === "1"; } catch(e) { return false; }
  });
  var dismissLanding = function() {
    try { localStorage.setItem("landing_seen_v1", "1"); } catch(e) {}
    setSeenLanding(true);
  };

  var [chapters, setChapters]   = useState([]);
  // Pre-loaded library: books shipped in /public/books/. Fetched once on mount from /books/index.json.
  var [presetBooks, setPresetBooks] = useState([]);
  // Grammar curriculum (📚 Grammar mode). Loaded once from /grammar/curriculum.json.
  // gramLevel = currently-selected CEFR level (e.g. "A2"); "" before user picks.
  // gramTopicId = currently-viewed topic's id; "" means "still on the picker screen".
  // gramSearch = search query; when non-empty, replaces the picker dropdowns with
  //   a cross-level result list.
  var [curriculum, setCurriculum] = useState(null);
  var [gramLevel, setGramLevel]   = useState("");
  var [gramTopicId, setGramTopicId] = useState("");
  var [gramErr, setGramErr]       = useState("");
  var [gramSearch, setGramSearch] = useState("");
  var [cidx, setCidx]           = useState(0);
  var [pidx, setPidx]           = useState(0);  // Current page within the current chapter
  var [cbm,  setCbm]            = useState(0);
  var [lview, setLview]         = useState("read");
  var [lsearch, setLsearch]     = useState("");
  var [lres, setLres]           = useState([]);
  var [fErr, setFErr]           = useState("");

  var [voice, setVoice]         = useState(null);
  var [allVoices, setAllVoices] = useState([]);
  var [playing, setPlaying]     = useState(false);
  var [showVP, setShowVP]       = useState(false);
  var [spkIdx, setSpkIdx]       = useState(null);
  var [ttsErr, setTtsErr]       = useState("");
  var [diagLogs, setDiagLogs]   = useState([]);
  var [spokenChar, setSpokenChar] = useState(-1);
  var charPos  = useRef(0);
  var paraText = useRef("");
  var keepAlive = useRef(null);
  // Queue of remaining TTS chunks (used by playText to chain Google-voice-friendly
  // short utterances). Each entry is {text, start}. Cleared by stopTTS/pauseTTS.
  var ttsQueue = useRef([]);
  var recentFoci = useRef([]);

  var inputRef = useRef(null);
  var msgsRef = useRef(null);

  var act  = custom.trim() || topic;
  var isLit = mode === "read";
  var pct  = chapters.length > 0 ? Math.round((cidx / chapters.length) * 100) : 0;
  var curChapter = chapters[cidx] || { heading: "", text: "" };
  // Paginate the current chapter. Single-page mode (whole-chapter-as-one-page)
  // applies to any book in the "Song Lyrics" category, so users see a full song
  // per screen and use chapter-nav arrows to advance. The legacy
  // `splitByNumberedSections` flag also enables this for backward compatibility
  // with books that were configured before the category-based rule existed.
  var singlePageMode = bookMeta.category === "Song Lyrics" || !!bookMeta.splitByNumberedSections;
  var pages = useMemo(function() {
    return computePages(curChapter.text || "", { singlePage: singlePageMode });
  }, [curChapter.text, singlePageMode]);
  var totalPages = pages.length;
  var currentPage = pages[Math.min(pidx, totalPages - 1)] || pages[0];

  useEffect(function() {
    (async function() {
      try { var v = await storage.get("vocab"); var g = await storage.get("grammar"); var st = await storage.get("grammar-topics");
        if (v) setVocab(JSON.parse(v.value)); if (g) setTips(JSON.parse(g.value));
        if (st) setSavedTopics(JSON.parse(st.value));
      } catch(e) {}
    })();
  }, []);
  useEffect(function() { storage && storage.set("vocab", JSON.stringify(vocab)).catch(function(){}); }, [vocab]);
  useEffect(function() { storage && storage.set("grammar", JSON.stringify(tips)).catch(function(){}); }, [tips]);
  useEffect(function() { storage && storage.set("grammar-topics", JSON.stringify(savedTopics)).catch(function(){}); }, [savedTopics]);

  // ── speechSynthesis warmup ─────────────────────────────────────────────────
  // Chrome (and sometimes Edge) silently drops the FIRST speak() call after a
  // fresh page load — symptom is "click ▶ → silence → click ⏹ → click ▶ → it
  // works". The fix has two parts:
  //   1. cancel() on mount — clears any stuck state inherited from a previous
  //      page load (some engines persist this across reloads).
  //   2. A one-shot global click/touch listener — the moment the user FIRST
  //      interacts anywhere on the page (the book picker, a menu, anywhere),
  //      we issue a silent priming utterance. This gives Chrome the
  //      user-gesture-bound speak() it needs to fully wake up the audio engine,
  //      well before the user reaches the reading view and clicks ▶.
  useEffect(function() {
    if (!window.speechSynthesis) return;
    try { window.speechSynthesis.cancel(); } catch(e) {}
    var warmedUp = false;
    var warmup = function() {
      if (warmedUp) return;
      warmedUp = true;
      try {
        var u = new SpeechSynthesisUtterance(" ");
        u.volume = 0.01;  // some engines skip volume=0 entirely
        u.rate = 10;       // play through as fast as possible
        window.speechSynthesis.speak(u);
      } catch(e) {}
    };
    document.addEventListener("click", warmup, { once: true });
    document.addEventListener("touchstart", warmup, { once: true });
    document.addEventListener("keydown", warmup, { once: true });
    return function() {
      document.removeEventListener("click", warmup);
      document.removeEventListener("touchstart", warmup);
      document.removeEventListener("keydown", warmup);
    };
  }, []);

  // Snap the reading view back to the top whenever the page or chapter changes.
  // We defer to the next animation frame so the new paragraphs have laid out, then
  // scroll BOTH the .lit-left container (desktop scroll) and the window/body
  // (mobile, where the document itself can be the scrolling element).
  useEffect(function() {
    requestAnimationFrame(function() {
      var el = document.querySelector(".lit-left");
      if (el) el.scrollTop = 0;
      if (typeof window !== "undefined" && window.scrollTo) window.scrollTo(0, 0);
      if (document.documentElement) document.documentElement.scrollTop = 0;
      if (document.body) document.body.scrollTop = 0;
    });
  }, [pidx, cidx]);

  // Auto-advance the page when TTS reads past the end of the visible page.
  // The reader stays in sync with the spoken word so you don't have to flip pages by hand.
  useEffect(function() {
    if (!playing || spokenChar < 0) return;
    if (pidx >= totalPages - 1) return;
    if (!currentPage) return;
    if (spokenChar > currentPage.endChar) {
      // Auto-advance during continuous TTS. Don't stop the audio, don't wipe the
      // current question list — just flip the page and regenerate questions for
      // the new page in the background. The new questions replace the old when
      // they arrive (litAnalysis calls setMsgs).
      var nextPidx = pidx + 1;
      setPidx(nextPidx);
      if (!noAIMode && chapters.length > 0) {
        setLoading(true);
        litAnalysis(chapters, cidx, nextPidx).finally(function(){ setLoading(false); });
      }
    }
  }, [spokenChar, pidx, playing]);

  // ── CROSS-DEVICE SYNC via Clerk metadata ──────────────────────────────────
  // On sign-in, fetch the server copy. If server has data, replace local state.
  // If server is empty but local has data, upload local as initial state.
  // After this initial sync, debounce any further changes and POST them.
  var [syncedFromServer, setSyncedFromServer] = useState(false);
  var [syncErr, setSyncErr] = useState("");  // Shown as a banner when sync fails (e.g. 8KB Clerk metadata limit hit)

  useEffect(function() {
    // Only sync for signed-in users (skip noAIMode unauthenticated users).
    if (!auth.isSignedIn || syncedFromServer) return;
    (async function() {
      try {
        var r = await authFetch("/api/user-data");
        if (!r.ok) return;
        var data = await r.json();
        var serverVocab = Array.isArray(data.vocab) ? data.vocab : [];
        var serverTips  = Array.isArray(data.tips)  ? data.tips  : [];

        if (serverVocab.length > 0 || serverTips.length > 0) {
          setVocab(serverVocab);
          setTips(serverTips);
        } else if (vocab.length > 0 || tips.length > 0) {
          await authFetch("/api/user-data", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ vocab: vocab, tips: tips }),
          });
        }
        setSyncedFromServer(true);
      } catch(e) {}
    })();
  }, [auth.isSignedIn]);

  // After initial sync, push subsequent changes (debounced 1.5s).
  useEffect(function() {
    if (!auth.isSignedIn || !syncedFromServer) return;
    var t = setTimeout(async function() {
      try {
        var r = await authFetch("/api/user-data", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ vocab: vocab, tips: tips }),
        });
        if (r.status === 413) {
          // 8KB Clerk metadata limit reached — show a visible banner.
          setSyncErr("Too many vocab words! Storage limit reached!");
        } else if (r.ok) {
          // Save succeeded — clear any previous error (user removed entries to get under the limit).
          if (syncErr) setSyncErr("");
        }
      } catch(e) {}
    }, 1500);
    return function(){ clearTimeout(t); };
  }, [vocab, tips, auth.isSignedIn, syncedFromServer]);

  useEffect(function() {
    var h = function(e) { if (popRef.current && !popRef.current.contains(e.target)) setPopup(null); };
    document.addEventListener("mousedown", h);
    return function() { document.removeEventListener("mousedown", h); };
  }, []);

  useEffect(function() {
    var find = function() {
      var raw = window.speechSynthesis.getVoices();
      if (!raw.length) return false;
      // In strict Chrome, hide local Windows Microsoft voices (e.g. "Microsoft
      // Pavel - Russian") — they sound robotic compared to Google's network
      // voices, which Chrome has built in. Other browsers (Edge, Brave, etc.)
      // see the full list. The filter is applied here once so both the picker
      // (which reads allVoices) and the auto-selector below share the same view.
      var all = isStrictChrome()
        ? raw.filter(function(v){ return !isLocalMsVoice(v); })
        : raw;
      setAllVoices(all);
      // Priority order:
      //   1. Local voices (work everywhere, predictable)
      //   2. Microsoft Edge "Online (Natural)" neural voices (high quality, reliable in Edge)
      //   3. Google network voices (high quality, reliable in Chrome on real sites — only
      //      flaky inside sandboxed iframes, which we no longer worry about post-deploy)
      //   4. Other network voices as a last resort
      var isMsNatural = function(v) {
        return /microsoft.*online.*natural/i.test(v.name) || /\(natural\)/i.test(v.name);
      };
      var isGoogle = function(v) { return /google/i.test(v.name); };
      var v =
           all.find(function(v) { return /katya|katja/i.test(v.name) && v.localService; })
        || all.find(function(v) { return v.lang === "ru-RU" && v.localService; })
        || all.find(function(v) { return v.lang.startsWith("ru") && v.localService; })
        // Microsoft Edge online neural voices — high quality, reliable in Edge
        || all.find(function(v) { return v.lang === "ru-RU" && isMsNatural(v); })
        || all.find(function(v) { return v.lang.startsWith("ru") && isMsNatural(v); })
        // Google Chrome's network voices — high quality, reliable on the deployed site
        || all.find(function(v) { return v.lang === "ru-RU" && isGoogle(v); })
        || all.find(function(v) { return v.lang.startsWith("ru") && isGoogle(v); })
        // Other network voices
        || all.find(function(v) { return v.lang === "ru-RU"; })
        || all.find(function(v) { return /katya|katja/i.test(v.name); })
        || all.find(function(v) { return v.lang.startsWith("ru"); });
      if (v) setVoice(v);
      return true;
    };
    if (!find()) window.speechSynthesis.onvoiceschanged = find;
  }, []);

  // Launch screen always shows a fresh "no book loaded" state. We deliberately
  // do NOT auto-restore the previous book from EPUB_CACHE on mode entry —
  // surfacing a half-remembered "Resume at chapter X" state on every visit was
  // confusing. The cache is still written during loadFile (so the same file
  // could be restored manually later), it just isn't read back on entry.
  // Bookmark (cbm) restoration is also disabled because it has nothing to
  // bookmark against when chapters is empty.

  // Persist bookmark whenever it changes (only meaningful with a loaded book).
  useEffect(function() {
    if (chapters.length > 0) storage && storage.set(EPUB_BM, String(cbm)).catch(function(){});
  }, [cbm]);

  useEffect(function() {
    if (!lsearch.trim() || !chapters.length) { setLres([]); return; }
    var q = lsearch.toLowerCase();
    var r = [];
    for (var i = 0; i < chapters.length && r.length < 50; i++) {
      if (chapters[i].text.toLowerCase().includes(q) || chapters[i].heading.toLowerCase().includes(q)) r.push(i);
    }
    setLres(r);
  }, [lsearch, chapters]);

  // Auto-scroll the currently-spoken word into view, but only when it's near
  // the edge of the reading pane (avoids jittery scroll on every word).
  useEffect(function() {
    if (spokenChar < 0) return;
    var el = document.querySelector(".rwhl");
    if (!el) return;
    var container = el.closest(".lit-left");
    if (!container) return;
    var er = el.getBoundingClientRect();
    var cr = container.getBoundingClientRect();
    var margin = 80;
    if (er.top < cr.top + margin || er.bottom > cr.bottom - margin) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [spokenChar]);

  // Auto-scroll the chat / lit-msgs to bottom when a new message arrives
  // or the typing indicator appears/disappears, so the latest content stays visible.
  useEffect(function() {
    if (msgsRef.current) {
      msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
    }
  }, [msgs.length, loading]);

  var api = async function(messages, sys, opts) {
    var run = async function() {
      var ctrl = new AbortController();
      var tid = setTimeout(function() { ctrl.abort(); }, 30000);
      try {
        // authFetch handles JWT injection and one auto-refresh on 401.
        var bodyObj = {
          messages: messages,
          system: sys || sysprompt(act, vocab, tips, level),
          max_tokens: 2048
        };
        // Forward "json" flag so the backend can put Gemini into strict JSON mode
        // (used by word-definition lookups). Default behavior unchanged.
        if (opts && opts.json) bodyObj.json = true;
        var r = await authFetch("/api/chat", {
          method:"POST", signal:ctrl.signal,
          headers: {"Content-Type":"application/json"},
          body:JSON.stringify(bodyObj),
        });
        clearTimeout(tid);
        var d = await r.json().catch(function(){ return {}; });
        if (r.status === 403 && d.error === "PENDING_APPROVAL") {
          setPendingApproval(true);
          throw new Error(d.message || "Your account is pending approval.");
        }
        if (r.status === 401) {
          // Both the cached AND fresh JWT got rejected — session is genuinely dead.
          throw new Error("Your session expired. Please sign out and sign back in.");
        }
        if (!r.ok) throw new Error(d.error || ("HTTP " + r.status));
        return d.text || "";
      } catch(e) { clearTimeout(tid); throw (e.name === "AbortError" ? new Error("Timeout") : e); }
    };
    try { return await run(); } catch(e) {
      // Don't retry on PENDING_APPROVAL — it's not a transient error.
      if (e.message && /pending approval/i.test(e.message)) throw e;
      // Don't retry on rate-limit / quota errors either — retrying just doubles
      // the load against an already-exhausted quota.
      if (e.message && /429|rate.?limit|quota|exhausted|Too many/i.test(e.message)) throw e;
      await new Promise(function(res){ setTimeout(res, 1500); });
      return await run();
    }
  };

  // Admin actions — fetch users + approve/reject. Only meaningful when isAdmin.
  // ── Forum + feedback handlers ────────────────────────────────────────────
  var loadForumThreads = async function() {
    setForumLoading(true); setForumErr("");
    try {
      var r = await authFetch("/api/forum");
      var d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed to load forum");
      setForumThreads(d.threads || []);
    } catch(e) { setForumErr(e.message || "Failed to load forum"); }
    finally { setForumLoading(false); }
  };

  var loadForumThread = async function(tid) {
    setForumLoading(true); setForumErr("");
    try {
      var r = await authFetch("/api/forum?thread=" + encodeURIComponent(tid));
      var d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed to load thread");
      setForumThread(d.thread || null);
    } catch(e) { setForumErr(e.message || "Failed to load thread"); }
    finally { setForumLoading(false); }
  };

  var openForum = function() {
    setForumOpen(true); setForumThread(null); setForumComposing(false);
    loadForumThreads();
  };

  var submitNewThread = async function() {
    if (forumBusy) return;
    var title = newTitle.trim();
    var bodyText = newBody.trim();
    if (!title || !bodyText) { setForumErr("Title and body required"); return; }
    setForumBusy(true); setForumErr("");
    try {
      var r = await authFetch("/api/forum", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ title: title, body: bodyText }),
      });
      var d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed to post");
      setNewTitle(""); setNewBody(""); setForumComposing(false);
      await loadForumThread(d.post.tid);   // jump into the newly created thread
      loadForumThreads();                  // refresh list in background
    } catch(e) { setForumErr(e.message || "Failed to post"); }
    finally { setForumBusy(false); }
  };

  var submitReply = async function() {
    if (forumBusy || !forumThread) return;
    var bodyText = replyBody.trim();
    if (!bodyText) return;
    setForumBusy(true); setForumErr("");
    try {
      var r = await authFetch("/api/forum", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ threadId: forumThread.tid, body: bodyText }),
      });
      var d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed to reply");
      setReplyBody("");
      // Optimistically append the new reply to the open thread.
      setForumThread(function(t) {
        if (!t) return t;
        return Object.assign({}, t, { posts: (t.posts || []).concat([d.post]) });
      });
      // Scroll to bottom of thread to show the new reply.
      requestAnimationFrame(function() {
        if (forumListRef.current) forumListRef.current.scrollTop = forumListRef.current.scrollHeight;
      });
    } catch(e) { setForumErr(e.message || "Failed to reply"); }
    finally { setForumBusy(false); }
  };

  var submitFeedback = async function() {
    if (feedbackBusy) return;
    var msg = feedbackBody.trim();
    if (!msg) return;
    setFeedbackBusy(true); setFeedbackMsg("");
    try {
      var r = await authFetch("/api/feedback", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ message: msg }),
      });
      var d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed to send feedback");
      setFeedbackMsg("Thanks! Feedback sent.");
      setFeedbackBody("");
      setTimeout(function(){ setFeedbackOpen(false); setFeedbackMsg(""); }, 1500);
    } catch(e) { setFeedbackMsg(e.message || "Failed to send"); }
    finally { setFeedbackBusy(false); }
  };

  var formatForumTs = function(ts) {
    if (!ts) return "";
    var d = new Date(ts), now = new Date();
    var sameDay = d.toDateString() === now.toDateString();
    if (sameDay) {
      var diffMin = Math.floor((now - d) / 60000);
      if (diffMin < 1) return "just now";
      if (diffMin < 60) return diffMin + " min ago";
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }
    var diffDays = Math.floor((now - d) / 86400000);
    if (diffDays === 1) return "yesterday";
    if (diffDays < 7) return diffDays + " days ago";
    return d.toLocaleDateString();
  };

  var loadAdminUsers = async function() {
    setAdminLoad(true); setAdminErr("");
    try {
      var r = await authFetch("/api/admin/users");
      var d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed to load users");
      setAdminUsers(d.users || []);
    } catch(e) {
      setAdminErr(e.message || "Failed to load users");
    } finally { setAdminLoad(false); }
  };

  var actOnUser = async function(userId, action) {
    setAdminBusy(function(b){ var n = Object.assign({}, b); n[userId] = action; return n; });
    try {
      var r = await authFetch("/api/admin/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: userId, action: action }),
      });
      var d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed");
      // Refresh the user list and surface email-status hint.
      await loadAdminUsers();
      if (action === "approve") {
        if (!d.emailSent) {
          setAdminErr("User approved, but email was NOT sent: " + (d.emailError || "Resend not configured. See AUTH_SETUP.md."));
        } else {
          setAdminErr(""); // success — clear any prior error
        }
      }
    } catch(e) {
      setAdminErr(e.message || "Failed");
    } finally {
      setAdminBusy(function(b){ var n = Object.assign({}, b); delete n[userId]; return n; });
    }
  };

  // Auto-load users when admin panel opens.
  useEffect(function() { if (showAdmin && isAdmin) loadAdminUsers(); }, [showAdmin, isAdmin]);

  // Upload a song to the library. Hits /api/admin/upload-song which commits
  // to GitHub → Vercel redeploys → song appears in picker after deploy.
  var uploadSong = async function() {
    if (upBusy) return;
    setUpErr("");
    setUpMsg("");
    var artist = upArtist.trim();
    var title  = upTitle.trim();
    var lyrics = upLyrics.trim();
    if (!artist) { setUpErr("Artist required"); return; }
    if (!title)  { setUpErr("Song title required"); return; }
    if (lyrics.length < 20) { setUpErr("Lyrics too short"); return; }
    setUpBusy(true);
    try {
      var r = await authFetch("/api/admin/upload-song", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ artist: artist, title: title, lyrics: lyrics }),
      });
      var d = await r.json().catch(function(){ return {}; });
      if (!r.ok) throw new Error(d.error || ("HTTP " + r.status));
      setUpMsg(
        d.isNewArtist
          ? "✓ Created new artist file \"" + d.artist + "\" with song #1: \"" + title + "\". Vercel will redeploy in ~1-2 min."
          : "✓ Appended song #" + d.songNumber + " (\"" + title + "\") to existing artist \"" + d.artist + "\". Vercel will redeploy in ~1-2 min."
      );
      // Clear title + lyrics so the admin can immediately add another song
      // from the same artist; preserve artist for convenience.
      setUpTitle("");
      setUpLyrics("");
    } catch(err) {
      setUpErr(err.message || "Upload failed");
    } finally {
      setUpBusy(false);
    }
  };

  // Upload a full book (EPUB/FB2/TXT/HTML). Reads the file as base64, sends to
  // /api/admin/upload-book which commits to public/books/<category-folder>/ on
  // GitHub.
  var uploadBook = async function() {
    if (upBusy) return;
    setUpErr("");
    setUpMsg("");
    var title  = upTitle.trim();
    var author = upBookAuthor.trim();
    var cat    = upBookCategory;
    var file   = upBookFile;
    if (!file) { setUpErr("Pick a file first"); return; }
    if (!title) { setUpErr("Title required"); return; }
    if (!cat)   { setUpErr("Category required"); return; }
    // 20 MB cap matches the backend limit; warn earlier so we don't waste a round-trip.
    if (file.size > 20 * 1024 * 1024) { setUpErr("File too large (max 20MB)"); return; }
    setUpBusy(true);
    try {
      // Read the file as base64. Use FileReader since File.arrayBuffer + Buffer
      // isn't available in the browser; readAsDataURL gives us "data:...;base64,XXX".
      var fileBase64 = await new Promise(function(resolve, reject) {
        var fr = new FileReader();
        fr.onload  = function(){
          var s = String(fr.result || "");
          var idx = s.indexOf(",");
          resolve(idx >= 0 ? s.slice(idx + 1) : s);
        };
        fr.onerror = function(){ reject(new Error("Could not read file")); };
        fr.readAsDataURL(file);
      });
      var r = await authFetch("/api/admin/upload-book", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename:   file.name,
          title:      title,
          author:     author,
          category:   cat,
          fileBase64: fileBase64,
        }),
      });
      var d = await r.json().catch(function(){ return {}; });
      if (!r.ok) throw new Error(d.error || ("HTTP " + r.status));
      setUpMsg(d.message || ("Book \"" + title + "\" uploaded — deploy in progress."));
      // Clear after success so admin can add another
      setUpBookFile(null);
      setUpTitle("");
      setUpBookAuthor("");
    } catch(err) {
      setUpErr(err.message || "Upload failed");
    } finally {
      setUpBusy(false);
    }
  };

  // Open the inline song-picker for a Song Lyrics artist. Reads song titles
  // from the book's `songs` array in index.json (populated by uploads). If
  // titles aren't pre-populated (e.g. older artist entries), fetch the .txt
  // and parse it to extract chapter headings.
  var openSongPicker = async function(book) {
    setSongPickerBook(book);
    setSongPickerErr("");
    setSongPickerList([]);
    // Fast path: pre-baked song titles in the manifest entry
    if (Array.isArray(book.songs) && book.songs.length > 0) {
      var titlesFromManifest = book.songs.map(function(s, i){
        var title = "";
        if (s && typeof s === "object" && typeof s.title === "string") title = s.title;
        return { title: title || ("Song " + (i + 1)), index: i };
      });
      if (titlesFromManifest.some(function(t){ return t.title && t.title.indexOf("Song ") !== 0; })) {
        setSongPickerList(titlesFromManifest);
        return;
      }
    }
    // Slow path: fetch + parse the file to extract titles
    setSongPickerLoad(true);
    try {
      var r = await fetch("/books/" + book.filename);
      if (!r.ok) throw new Error("HTTP " + r.status);
      var buf = await r.arrayBuffer();
      var result = await parseBook(buf, book.filename);
      var chs = result.chapters || [];
      // Apply the same splitting logic loadFile uses (heuristic, then legacy
      // numbered fallback if explicitly opted in). Skip the AI fallback here —
      // costs a token and the picker doesn't need perfection.
      if (book.category === "Song Lyrics" || book.splitByNumberedSections) {
        // Same priority as loadFile: trust the explicit flag first, then heuristic.
        var didSplit = false;
        if (book.splitByNumberedSections) {
          var byNum = resplitByNumberedSections(chs);
          if (byNum && byNum.length >= 1) { chs = byNum; didSplit = true; }
        }
        if (!didSplit || chs.length <= 1) {
          var smart = splitSongsHeuristic(chs, { minSongs: 2 });
          if (smart && smart.length >= 2) chs = smart;
        }
      }
      setSongPickerList(chs.map(function(ch, i){
        return { title: (ch.heading || "").trim() || ("Song " + (i + 1)), index: i };
      }));
    } catch(err) {
      setSongPickerErr(err.message || "Could not load song list");
    } finally {
      setSongPickerLoad(false);
    }
  };

  // User picked a specific song from the inline picker — load the book then
  // jump to that song's chapter index.
  var jumpToSong = async function(songIndex) {
    var book = songPickerBook;
    if (!book) return;
    setSongPickerBook(null);
    setSongPickerList([]);
    await loadPresetBook(book);
    // loadFile resets cidx via setCbm(0) but cidx itself stays. Force the jump.
    setCidx(songIndex);
    setPidx(0);
  };

  var startKeepalive = function() {
    if (keepAlive.current) clearInterval(keepAlive.current);
    // Chrome cuts off speechSynthesis after ~15 seconds. Pause+resume keeps it alive.
    keepAlive.current = setInterval(function() {
      if (!window.speechSynthesis || !window.speechSynthesis.speaking) {
        if (keepAlive.current) { clearInterval(keepAlive.current); keepAlive.current = null; }
        return;
      }
      window.speechSynthesis.pause();
      window.speechSynthesis.resume();
    }, 10000);
  };

  var stopKeepalive = function() {
    if (keepAlive.current) { clearInterval(keepAlive.current); keepAlive.current = null; }
  };

  var stopTTS = useCallback(function() {
    stopKeepalive();
    ttsQueue.current = [];  // halt the chunk chain
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    setPlaying(false); setSpkIdx(null); setSpokenChar(-1);
  }, []);

  var checkTTSAvailable = function() {
    if (!window.speechSynthesis) {
      setTtsErr("This browser does not support speechSynthesis.");
      return false;
    }
    var vs = window.speechSynthesis.getVoices();
    if (!vs.length) {
      setTtsErr("No voices available. Try clicking 🎙 Voice — if list is empty, your browser/OS has no installed voices.");
      return false;
    }
    return true;
  };

  var playText = useCallback(function(text, from) {
    if (from === undefined) from = 0;
    setTtsErr("");
    if (!checkTTSAvailable()) return;
    stopKeepalive();
    window.speechSynthesis.cancel();
    paraText.current = text;
    var slice = text.slice(from);
    if (!slice.trim()) return;

    // Split into ~200-char chunks at sentence boundaries. Google русский silently
    // fails on long utterances; even local voices benefit from shorter chunks
    // (less chance of the Chrome 15-sec-cutoff bug). Each chunk knows its global
    // char offset so word-boundary events map back to absolute positions.
    var chunks = chunkForTTS(text, from, 200);
    if (chunks.length === 0) return;
    ttsQueue.current = chunks.slice(); // copy so .shift() doesn't mutate caller's reference

    // playChunk pulls the next chunk from the queue and speaks it. When that
    // chunk ends naturally, it calls itself again to keep the chain going.
    var ssn = window.speechSynthesis;
    var playNext = function() {
      if (ttsQueue.current.length === 0) {
        stopKeepalive();
        setPlaying(false);
        charPos.current = 0;
        setSpokenChar(-1);
        return;
      }
      var chunk = ttsQueue.current.shift();
      var u = new SpeechSynthesisUtterance(chunk.text);
      u.lang = "ru-RU"; u.rate = 0.84;
      if (voice) u.voice = voice;
      u.onstart = function() { startKeepalive(); };
      u.onboundary = function(e) {
        if (e.name === "word") {
          var pos = chunk.start + e.charIndex;
          charPos.current = pos;
          setSpokenChar(pos);
        }
      };
      u.onend = function() {
        // Small inter-chunk delay smooths over the cancel/speak Chrome quirk
        // and gives the engine a beat to reset state between chunks.
        setTimeout(playNext, 30);
      };
      u.onerror = function(e) {
        var err = (e && e.error) || "unknown";
        if (err === "interrupted" || err === "canceled") return; // expected on stop
        ttsQueue.current = [];
        stopKeepalive();
        setSpokenChar(-1);
        setTtsErr("Speech error: " + err + ". Try clicking 🎙 Voice to pick a different voice.");
        setPlaying(false);
      };
      try {
        if (ssn.paused) ssn.resume();
        ssn.speak(u);
      } catch (ex) {
        ttsQueue.current = [];
        setTtsErr("speak() threw: " + (ex.message || ex));
        setPlaying(false);
      }
    };

    // Chrome quirk: speak() immediately after cancel() often fails silently —
    // wait a beat after the cancel before starting the chain.
    setTimeout(function() {
      setPlaying(true); charPos.current = from;
      playNext();
    }, 250);
  }, [voice]);

  var pauseTTS = useCallback(function() {
    stopKeepalive();
    ttsQueue.current = [];  // pause halts the chain; resuming would need a fresh playText call
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    setPlaying(false);
  }, []);

  var speakMsg = useCallback(function(text, idx) {
    setTtsErr("");
    if (!checkTTSAvailable()) return;
    stopKeepalive();
    window.speechSynthesis.cancel();
    if (spkIdx === idx) { setSpkIdx(null); return; }
    var ru = text.split("\n")
      .filter(function(l) { var t=l.trim(); return t && !/^\*{1,2}[^*]+\*{1,2}$/.test(t) && !/^📝/.test(t); })
      .join(" ")
      .replace(/\*\*[^*]+\*\*/g, function(m){ return m.replace(/\*\*/g,""); })
      .replace(/\[[^\]]+\]/g,"").replace(/\*[^*]+\*/g,"")
      .replace(/[a-zA-Z()/[\]{}|]/g,"").replace(/\s+/g," ").trim();
    if (!ru) return;
    setSpkIdx(idx);
    setTimeout(function() {
      var u = new SpeechSynthesisUtterance(ru);
      u.lang="ru-RU"; u.rate=0.84; if (voice) u.voice=voice;
      u.onstart = function(){ startKeepalive(); };
      u.onend = function(){ stopKeepalive(); setSpkIdx(null); };
      u.onerror = function(e){
        stopKeepalive();
        var err = (e && e.error) || "unknown";
        if (err !== "interrupted" && err !== "canceled") {
          setTtsErr("Speech error: " + err + ".");
        }
        setSpkIdx(null);
      };
      try {
        // Same Chrome quirk workarounds as playText: nudge the engine out of
        // any half-paused state before issuing the new utterance.
        if (window.speechSynthesis.paused) window.speechSynthesis.resume();
        window.speechSynthesis.speak(u);
      }
      catch(ex) { setTtsErr("speak() threw: " + (ex.message || ex)); setSpkIdx(null); }
    }, 250);
  }, [voice, spkIdx]);

  var runDiagnostics = function() {
    var logs = [];
    var addLog = function(line) {
      logs.push(line);
      setDiagLogs(logs.slice());
    };

    addLog("=== TTS DIAGNOSTIC ===");
    addLog("UA: " + navigator.userAgent);
    addLog("speechSynthesis available: " + (window.speechSynthesis ? "YES" : "NO"));
    if (!window.speechSynthesis) return;

    var ss = window.speechSynthesis;
    addLog("Voices count: " + ss.getVoices().length);
    addLog("State before tests — speaking:" + ss.speaking + " pending:" + ss.pending + " paused:" + ss.paused);

    // In sandboxed iframes, the browser sometimes silently drops audio output.
    // Three tests narrow down the cause:
    //   T1 = baseline (English, default voice) — does any TTS work at all?
    //   T2 = Russian language without voice override — does ru-RU work generically?
    //   T3 = Russian with the user's chosen voice — does that specific voice work?

    ss.cancel();

    var runTest = function(name, text, lang, useVoice, delay) {
      setTimeout(function() {
        addLog("--- " + name + ": speak('" + text + "', lang=" + lang + (useVoice && voice ? ", voice=" + voice.name : ", default voice") + ") ---");
        var t0 = Date.now();
        var u = new SpeechSynthesisUtterance(text);
        u.lang = lang; u.rate = 1.0;
        if (useVoice && voice) u.voice = voice;

        u.onstart = function() { addLog(name + " onstart @ +" + (Date.now()-t0) + "ms"); };
        u.onend   = function() { addLog(name + " onend   @ +" + (Date.now()-t0) + "ms"); };
        u.onerror = function(e) { addLog(name + " onerror @ +" + (Date.now()-t0) + "ms — error: " + ((e && e.error) || "unknown")); };

        try { ss.speak(u); addLog(name + " speak() returned cleanly"); }
        catch(ex) { addLog(name + " speak() THREW: " + (ex.message || ex)); }

        setTimeout(function() { addLog(name + " +100ms — speaking:" + ss.speaking + " pending:" + ss.pending); }, 100);
        setTimeout(function() { addLog(name + " +500ms — speaking:" + ss.speaking + " pending:" + ss.pending); }, 500);
      }, delay);
    };

    runTest("T1 (English default)", "Hello, this is a test.",  "en-US", false, 200);
    runTest("T2 (Russian default)", "Привет, это тест.",       "ru-RU", false, 4000);
    runTest("T3 (Russian + voice)", "Привет, это тест.",       "ru-RU", true,  8000);

    setTimeout(function() { addLog("=== DIAGNOSTIC COMPLETE === Copy this log and share it."); }, 12000);
  };

  var copyDiagLogs = function() {
    var text = diagLogs.join("\n");
    if (navigator.clipboard) navigator.clipboard.writeText(text).catch(function(){});
  };

  var fetchDef = async function(word) {
    // Ask the backend for strict JSON output. With responseMimeType set on the
    // Gemini side, the response is just `{...}` with no markdown fences, no
    // preamble, no trailing commentary. Lower temperature too (set server-side
    // when json=true) so the shape is predictable.
    var raw = await api(
      [{role:"user",content:defprompt(word)}],
      "You are a Russian-English dictionary. Return a single JSON object only. No markdown. No commentary.",
      { json: true }
    );
    var c = (raw || "").replace(/```[a-z]*\n?/gi,"").replace(/```/g,"").trim();
    var s = c.indexOf("{"), e2 = c.lastIndexOf("}");
    if (s === -1 || e2 === -1) throw new Error("Gemini returned no JSON object. Reply was: " + (c.slice(0, 80) || "(empty)"));
    var parsed;
    try { parsed = JSON.parse(c.slice(s, e2+1)); }
    catch (jerr) { throw new Error("Gemini returned malformed JSON: " + jerr.message); }
    // Validate the response has the field that matters most.
    if (!parsed || typeof parsed.translation !== "string" || !parsed.translation.trim()) {
      throw new Error("Gemini did not provide a translation for this word");
    }
    return parsed;
  };

  // In Read-without-AI mode, clicking a Russian word jumps TTS to that word and reads onward.
  var jumpTTS = function(charPosition) {
    var txt = (curChapter && curChapter.text) || "";
    if (!txt) return;
    playText(txt, charPosition);
  };

  var defWord = async function(word, e) {
    e.stopPropagation();
    if (noAIMode) return;  // No API calls in read-without-AI mode.
    var clean = word.replace(/[^а-яёА-ЯЁ]/g,"");
    if (!clean || clean.length < 2) return;
    var rect = e.currentTarget.getBoundingClientRect();
    var pw = Math.min(280, window.innerWidth-32);
    var left = rect.left;
    if (left+pw > window.innerWidth-16) left = window.innerWidth-pw-16;
    if (left < 16) left = 16;
    var top = window.innerHeight-rect.bottom > 220 ? rect.bottom+8 : rect.top-230;
    setPopXY({top:Math.max(8,top),left:left});
    setPopup({word:clean,data:null,loading:true,error:null,yo:null});
    try {
      var data = await fetchDef(clean);
      setPopup(function(p){ return p ? Object.assign({},p,{data:data,loading:false}) : null; });
    } catch(err) {
      var vars = yoVariants(clean);
      // Try the е↔ё variants automatically before giving up — but only on errors
      // that suggest the word itself was the problem (not rate limits / auth).
      var rawMsg = (err && err.message) || "Unknown error";
      var likelyRateLimit = /Too many|rate.?limit|quota|429|HTTP 429|exhausted/i.test(rawMsg);
      var likelyAuth      = /session|sign|approval|401|403/i.test(rawMsg);
      if (vars.length && !likelyRateLimit && !likelyAuth) {
        setPopup(function(p){ return p ? Object.assign({},p,{loading:false,yo:{orig:clean,vars:vars}}) : null; });
      } else {
        // Show a SHORT user-friendly message but the underlying cause too, so we
        // can tell rate-limit issues from JSON-parse issues from bad-word issues.
        var msg;
        if (likelyRateLimit)      msg = 'Daily AI limit reached — try again later, or raise the GEMINI_MODEL quota.';
        else if (likelyAuth)      msg = 'Sign-in required. Sign out and back in, then retry.';
        else                       msg = 'Could not define "' + clean + '" — ' + rawMsg;
        setPopup(function(p){ return p ? Object.assign({},p,{loading:false,error:msg}) : null; });
      }
    }
  };

  var defWithYo = async function(word) {
    setPopup(function(p){ return p ? Object.assign({},p,{loading:true,yo:null,error:null,word:word}) : null; });
    try {
      var data = await fetchDef(word);
      setPopup(function(p){ return p ? Object.assign({},p,{data:data,loading:false}) : null; });
    } catch(err) {
      setPopup(function(p){ return p ? Object.assign({},p,{loading:false,error:'Could not define "'+word+'"'}) : null; });
    }
  };

  // Pick a focus angle that hasn't been used in the last few sessions.
  var pickFocus = function() {
    var avoid = recentFoci.current;
    var available = QUESTION_FOCI.filter(function(f) { return avoid.indexOf(f.tag) === -1; });
    if (!available.length) { recentFoci.current = []; available = QUESTION_FOCI; }
    var pick = available[Math.floor(Math.random() * available.length)];
    recentFoci.current.push(pick.tag);
    if (recentFoci.current.length > 4) recentFoci.current.shift();
    return pick;
  };

  // Pull "❓1 Question text" lines out of an assistant message — used to remember
  // what we've already asked so we don't repeat next time.
  var extractQuestions = function(text) {
    var re = /❓\d+\s+([^\n]{6,200})/g;
    var qs = [];
    var m;
    while ((m = re.exec(text)) !== null) {
      var q = m[1].trim();
      if (q) qs.push(q);
    }
    return qs;
  };

  var loadQHist = async function() {
    try {
      var c = await storage.get(QHIST_KEY);
      if (c && c.value) return JSON.parse(c.value);
    } catch(e) {}
    return {};
  };

  var saveQHist = async function(hist) {
    try { await storage.set(QHIST_KEY, JSON.stringify(hist)); } catch(e) {}
  };

  // ── Per-page tutor-response cache ─────────────────────────────────────────
  // Save the AI's full reply so that flipping back to an already-visited page
  // shows the same questions without firing a new Gemini call. Saved/loaded via
  // the same storage shim as other state (works in browsers and Clerk metadata).
  // Cache key is "<title>|<author>|<chapterIdx>:<pageIdx>" with the book's
  // total chapter count appended as a soft fingerprint so two different books
  // that happen to share a title/author don't collide.
  var loadLitCache = async function() {
    try {
      var c = await storage.get(LIT_CACHE_KEY);
      if (c && c.value) return JSON.parse(c.value);
    } catch(e) {}
    return {};
  };
  var saveLitCache = async function(cache) {
    try {
      // LRU eviction: when over the cap, drop the oldest entries by timestamp.
      var keys = Object.keys(cache);
      if (keys.length > LIT_CACHE_MAX) {
        keys.sort(function(a, b){ return (cache[a].t || 0) - (cache[b].t || 0); });
        var drop = keys.slice(0, keys.length - LIT_CACHE_MAX);
        for (var i = 0; i < drop.length; i++) delete cache[drop[i]];
      }
      await storage.set(LIT_CACHE_KEY, JSON.stringify(cache));
    } catch(e) {}
  };
  var litCacheKey = function(meta, totalChapters, ci, pi, lvl) {
    var t = (meta && meta.title) || "untitled";
    var a = (meta && meta.author) || "unknown";
    return t + "|" + a + "|" + (totalChapters || 0) + "|" + ci + ":" + pi + "|" + (lvl || "B1");
  };

  var litAnalysis = async function(chs, i, pi, metaOverride, force) {
    if (typeof pi !== "number") pi = 0;
    var ch = chs[i] || {};
    var m = metaOverride || bookMeta;
    var sp = m.category === "Song Lyrics" || !!m.splitByNumberedSections;
    // Use the SAME pagination the renderer uses — 5 paragraphs OR ~1700 chars
    // per page, with sentence-boundary splits for giant single-paragraph chapters.
    // Single-page mode (song lyrics) shows the whole chapter as one page.
    var chPages = computePages(ch.text || "", { singlePage: sp });
    var page = chPages[Math.min(pi, chPages.length - 1)] || chPages[0];
    var snippet = page ? (ch.text || "").slice(page.startChar, page.endChar) : (ch.text || "").slice(0, 1700);
    if (snippet.length > 3500) snippet = snippet.slice(0, 3500);

    var focus = pickFocus();
    var pageCount = chPages.length;

    // ── Cache check ────────────────────────────────────────────────────────
    // If we already have a saved tutor reply for this (book, chapter, page),
    // reuse it instead of firing a new Gemini call. Big quota win, especially
    // when readers flip back and forth between pages or revisit a book.
    var cache = await loadLitCache();
    var cKey = litCacheKey(m, chs.length, i, pi, level);
    if (!force && cache[cKey] && cache[cKey].r) {
      setMsgs([{role:"assistant",content:cache[cKey].r}]);
      // Touch timestamp so this entry stays warm in LRU.
      cache[cKey].t = Date.now();
      saveLitCache(cache);
      return;
    }

    var hist = await loadQHist();
    var chKey = String(i) + ":" + pi;
    var prevQs = (hist[chKey] || []).slice(-12);

    try {
      var t = await api([{role:"user",content:"Go."}],
        litprompt(snippet, i, chs.length, m.title || "this book", m.author || "the author", focus, prevQs, pi, pageCount, level));
      setMsgs([{role:"assistant",content:t}]);

      // Save to cache so future visits to this page don't re-hit the API.
      cache[cKey] = { r: t, t: Date.now() };
      saveLitCache(cache);

      var newQs = extractQuestions(t);
      if (newQs.length) {
        hist[chKey] = (hist[chKey] || []).concat(newQs).slice(-25);
        saveQHist(hist);
      }
    } catch(err) {
      setMsgs([{role:"assistant",content:"❓ Что вы заметили в этом отрывке?"}]);
    }
  };

  var startChat = async function() {
    setStarted(true); setMsgs([]); setLoading(true); setPopup(null); stopTTS();
    try { var t = await api([{role:"user",content:"Start please."}]); setMsgs([{role:"assistant",content:t}]); }
    catch(err) { setMsgs([{role:"assistant",content:"*(Error: "+err.message+" — try again.)*"}]); }
    setLoading(false);
  };

  var startLit = async function(idx, chs, metaOverride) {
    var p = chs || chapters; if (!p || !p.length) return;
    var i = idx !== undefined ? idx : cbm;
    setCidx(i); setCbm(i); setPidx(0); setStarted(true); setMsgs([]); setLoading(true);
    setPopup(null); stopTTS(); setLview("read");
    charPos.current = 0; paraText.current = "";
    if (noAIMode) { setLoading(false); return; }
    await litAnalysis(p, i, 0, metaOverride); setLoading(false);
  };

  var navLit = async function(idx) {
    stopTTS(); charPos.current = 0; paraText.current = "";
    if (idx < 0 || idx >= chapters.length) return;
    setCidx(idx); setCbm(idx); setPidx(0); setMsgs([]); setLoading(true); setLview("read");
    if (noAIMode) { setLoading(false); return; }
    await litAnalysis(chapters, idx, 0); setLoading(false);
  };

  // Navigate to a new PAGE within the current chapter and refresh the tutor's
  // questions so they reflect what's on screen now. Used by the page arrows
  // and by the TTS-driven auto-advance. In noAIMode we just flip the page.
  var navPage = async function(newPidx) {
    if (newPidx < 0 || newPidx >= totalPages) return;
    stopTTS(); charPos.current = 0; paraText.current = "";
    setPidx(newPidx); setMsgs([]); setLoading(true); setLview("read");
    if (noAIMode) { setLoading(false); return; }
    await litAnalysis(chapters, cidx, newPidx); setLoading(false);
  };

  // ── Smart song-collection splitter ──────────────────────────────────────
  // Tries multiple deterministic patterns to find song boundaries in a song-
  // collection book. Returns an array of chapters (one per song) if any pattern
  // produces >= options.minSongs (default 3) plausible sections, otherwise null.
  // For Song Lyrics books we lower the threshold to 2 since even 2 songs is
  // valuable — for unknown books we keep 3 to avoid false-positive splits.
  var splitSongsHeuristic = function(chapters, options) {
    options = options || {};
    var minSongs = typeof options.minSongs === "number" ? options.minSongs : 3;
    if (!chapters || !chapters.length) {
      console.log("[songs:heuristic] no chapters passed in — bail");
      return null;
    }
    var fullText = chapters.map(function(ch){ return ch.text || ""; }).join("\n\n");
    if (fullText.length < 300) {
      console.log("[songs:heuristic] full text < 300 chars (" + fullText.length + ") — bail");
      return null;
    }
    var lines = fullText.split("\n");
    console.log("[songs:heuristic] starting — " + lines.length + " lines, " + fullText.length + " chars, minSongs=" + minSongs);

    var strategies = [
      {
        name: "standalone-numbered",
        // Just a digit (optionally with . or )), nothing else
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          return /^\(?\d{1,3}[.)]?\)?$/.test(t);
        },
        // For standalone-numbered, the title is on the NEXT non-blank line
        titleOffset: 1,
      },
      {
        name: "inline-numbered",
        // "1. Title" or "12) Title" — number then dot/paren then title text
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          return /^\d{1,3}[.)]\s+[А-ЯЁA-Z"«].{1,70}$/.test(t) && t.length < 80;
        },
        titleOffset: 0,
      },
      {
        name: "standalone-roman",
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          return /^[IVX]{1,5}\.?$/.test(t);
        },
        titleOffset: 1,
      },
      {
        name: "inline-roman",
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          return /^[IVX]{1,5}[.)]\s+[А-ЯЁA-Z"«].{1,70}$/.test(t) && t.length < 80;
        },
        titleOffset: 0,
      },
      {
        name: "all-caps-cyrillic",
        // Short ALL-CAPS Russian line, surrounded by blank lines.
        // Avoids matching things like "ПРОЩАЙ!" inside a lyric line.
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          if (t.length < 3 || t.length > 80) return false;
          if (!/^[А-ЯЁ][А-ЯЁ\s\-—–.,!?']{1,79}$/.test(t)) return false;
          if (!/[А-ЯЁ]{3,}/.test(t)) return false;  // need actual Cyrillic letters
          var prevBlank = i === 0 || !L[i-1].trim();
          var nextBlank = i + 1 >= L.length || !L[i+1].trim();
          return prevBlank && nextBlank;
        },
        titleOffset: 0,
      },
      {
        name: "title-case-cyrillic",
        // Short Title Case line alone, surrounded by blanks. Strict to avoid
        // matching sentences. Excludes lines ending in . , ; : ! ? (which
        // are likely sentences, not titles).
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          if (t.length < 3 || t.length > 60) return false;
          if (!/^[А-ЯЁ]/.test(t)) return false;
          if (/[.,;:!?]$/.test(t)) return false;
          // Reject sentence-like lines (many words)
          var words = t.split(/\s+/);
          if (words.length > 7) return false;
          // Must be alone on its line: blanks before AND after
          var prevBlank = i === 0 || !L[i-1].trim();
          var nextBlank = i + 1 >= L.length || !L[i+1].trim();
          return prevBlank && nextBlank;
        },
        titleOffset: 0,
      },
    ];

    var best = null;
    var bestName = "";

    for (var s = 0; s < strategies.length; s++) {
      var strat = strategies[s];
      var titleIdxs = [];
      for (var i = 0; i < lines.length; i++) {
        if (strat.isTitleLine(lines, i)) titleIdxs.push(i);
      }
      console.log("[songs:heuristic] " + strat.name + ": " + titleIdxs.length + " marker lines found"
        + (titleIdxs.length > 0 ? " at lines " + titleIdxs.slice(0, 8).join(",") + (titleIdxs.length > 8 ? "..." : "") : ""));
      // Heuristic validity checks
      if (titleIdxs.length < minSongs) {
        console.log("[songs:heuristic]   ↳ rejected: needs >= " + minSongs);
        continue;
      }
      // Sections shouldn't be too dense — if there's a title every 3 lines,
      // we're probably matching false positives (like ALL CAPS dialogue tags).
      var avgGap = lines.length / titleIdxs.length;
      if (avgGap < 6) {
        console.log("[songs:heuristic]   ↳ rejected: density too high (avgGap=" + avgGap.toFixed(1) + ")");
        continue;
      }

      var sections = [];
      for (var k = 0; k < titleIdxs.length; k++) {
        var start = titleIdxs[k];
        var end = k + 1 < titleIdxs.length ? titleIdxs[k+1] : lines.length;
        var heading = lines[start].trim();
        // For standalone-numbered/roman, the actual title is on the next
        // non-blank line after the marker
        if (strat.titleOffset === 1) {
          for (var n = start + 1; n < end && n < lines.length; n++) {
            if (lines[n].trim()) { heading = lines[n].trim(); break; }
          }
        }
        var bodyText = lines.slice(start, end).join("\n").trim();
        // Drop sections that are mostly empty / non-Russian — those are
        // probably false-positive matches (front matter, table of contents).
        var cyrCount = (bodyText.match(/[а-яёА-ЯЁ]/g) || []).length;
        if (cyrCount < 20) continue;
        sections.push({ heading: heading, text: bodyText });
      }
      console.log("[songs:heuristic]   ↳ " + sections.length + " valid sections after filtering");

      if (sections.length >= minSongs) {
        if (!best || sections.length > best.length) {
          best = sections;
          bestName = strat.name;
        }
      }
    }

    if (best) console.log("[songs] heuristic split via " + bestName + " → " + best.length + " songs");
    return best;
  };

  // Apply a regex pattern (from AI or other source) to split full text into
  // song chapters. Pattern matches a line that begins a new song.
  var splitByRegexPattern = function(fullText, patternStr) {
    try {
      var re = new RegExp(patternStr, "m");
      var lines = fullText.split("\n");
      var indices = [];
      for (var i = 0; i < lines.length; i++) {
        // Test against trimmed line (most patterns assume no leading whitespace)
        if (re.test(lines[i].trim())) indices.push(i);
      }
      if (indices.length < 3) return null;
      var result = [];
      for (var k = 0; k < indices.length; k++) {
        var start = indices[k];
        var end = k + 1 < indices.length ? indices[k+1] : lines.length;
        var text = lines.slice(start, end).join("\n").trim();
        var heading = lines[start].trim();
        var cyr = (text.match(/[а-яёА-ЯЁ]/g) || []).length;
        if (cyr < 20) continue;
        result.push({ heading: heading, text: text });
      }
      return result.length >= 3 ? result : null;
    } catch(e) { return null; }
  };

  // AI fallback: ask the model to identify the song-boundary pattern.
  // Cached per book filename so we only pay tokens once per book lifetime.
  var splitSongsAI = async function(chapters, fname) {
    if (!chapters || !chapters.length) return null;
    var fullText = chapters.map(function(ch){ return ch.text || ""; }).join("\n\n");
    if (fullText.length < 300) return null;

    var cacheKey = "gv_song_split_pattern_v1__" + (fname || "unknown");

    // Cache hit: skip the API call.
    try {
      var c = await storage.get(cacheKey);
      if (c && c.value) {
        console.log("[songs] using cached AI pattern for " + fname);
        var cached = splitByRegexPattern(fullText, c.value);
        if (cached && cached.length >= 3) return cached;
      }
    } catch(e) {}

    // Build a representative sample: head + middle + tail so the AI sees how
    // formatting looks throughout the book, not just the first few songs.
    var sample;
    if (fullText.length <= 6000) {
      sample = fullText;
    } else {
      var mid = Math.floor(fullText.length / 2);
      sample =
        fullText.slice(0, 3500) +
        "\n\n[... middle of book ...]\n\n" +
        fullText.slice(mid, mid + 1500) +
        "\n\n[... later in book ...]\n\n" +
        fullText.slice(-1500);
    }

    var prompt =
      "This is text from a Russian song-lyrics book. Songs need to be split apart. " +
      "Find the formatting pattern that marks the START of each song.\n\n" +
      "Return JSON only — no prose. Schema:\n" +
      '{ "regex": "<JS regex matching a line that starts a new song>", "examples": [up to 3 example titles] }\n\n' +
      "The regex is tested against TRIMMED lines (no surrounding whitespace) in multiline mode. " +
      "Don't include the / delimiters. Escape backslashes appropriately for JSON.\n\n" +
      "Examples of good patterns:\n" +
      '  "^\\\\d{1,3}\\\\.?$"           — standalone number like 1. or 23\n' +
      '  "^\\\\d{1,3}\\\\.\\\\s+\\\\S"    — inline numbered title like "1. Title"\n' +
      '  "^[IVX]{1,5}\\\\.?$"         — Roman numerals\n' +
      '  "^[А-ЯЁ\\\\s\\\\-]{3,60}$"     — ALL CAPS Cyrillic title alone on line\n\n' +
      "If you cannot find a reliable pattern, return: { \"regex\": \"\", \"examples\": [] }\n\n" +
      "BOOK TEXT:\n" + sample;

    try {
      console.log("[songs] calling AI to detect split pattern for " + fname);
      var resp = await api(
        [{ role: "user", content: prompt }],
        "You are a text-analysis assistant. You output only valid JSON.",
        { json: true }
      );
      var parsed;
      try { parsed = JSON.parse(resp); } catch(e) { parsed = null; }
      if (!parsed || !parsed.regex) {
        console.log("[songs] AI returned no usable pattern");
        return null;
      }
      console.log("[songs] AI suggested pattern: " + parsed.regex);
      var result = splitByRegexPattern(fullText, parsed.regex);
      if (result && result.length >= 3) {
        try { await storage.set(cacheKey, parsed.regex); } catch(e) {}
        console.log("[songs] AI split → " + result.length + " songs");
        return result;
      }
      console.log("[songs] AI pattern produced too few sections");
      return null;
    } catch(err) {
      console.log("[songs] AI split failed: " + (err.message || err));
      return null;
    }
  };

  // Re-split chapters by lines that contain only a digit (or "digit.")
  // Used for song-collection EPUBs like Tsoi, where each track number marks a new "chapter".
  // The first non-empty line after the number becomes the chapter heading (song title).
  var resplitByNumberedSections = function(chapters) {
    var fullText = chapters.map(function(ch){ return ch.text || ""; }).join("\n\n");
    var lines = fullText.split("\n");
    console.log("[songs:numbered] scanning " + lines.length + " lines for /^\\d{1,3}\\.?$/ markers");
    var out = [];
    var current = null;
    var awaitingTitle = false;
    var markerLines = [];
    for (var i = 0; i < lines.length; i++) {
      var t = lines[i].trim();
      if (/^\d{1,3}\.?$/.test(t)) {
        markerLines.push(i);
        // Track number found — start a new section
        if (current && (current.text || "").trim()) out.push(current);
        current = { heading: "", text: "" };
        awaitingTitle = true;
      } else if (current) {
        if (awaitingTitle && t) {
          current.heading = t;
          current.text = t + "\n";
          awaitingTitle = false;
        } else if (!awaitingTitle) {
          current.text += lines[i] + "\n";
        }
      }
    }
    if (current && (current.text || "").trim()) out.push(current);
    console.log("[songs:numbered] found " + markerLines.length + " markers at lines [" + markerLines.slice(0, 10).join(",") + (markerLines.length > 10 ? "..." : "") + "] → " + out.length + " sections");
    if (out.length > 0) {
      out.forEach(function(s, i){ console.log("  song " + (i+1) + ": \"" + (s.heading || "(no heading)") + "\""); });
    }
    return out.length ? out : chapters;
  };

  var loadFile = async function(buf, fname, opts) {
    setFErr("");
    opts = opts || {};
    try {
      var result = await parseBook(buf, fname);
      if (!result.chapters || result.chapters.length < 1) throw new Error("No chapters found in file.");
      var chs = result.chapters;
      // Song-collection mode: any book in the "Song Lyrics" category should
      // be split one-song-per-chapter, regardless of how the source EPUB
      // structured its spine. We use a tiered strategy:
      //   1. If the existing chapters already look like one-song-each (short,
      //      named, multiple of them), trust the source's split.
      //   2. Otherwise run the smart heuristic splitter — tries numbered,
      //      Roman numeral, ALL CAPS, Title Case patterns.
      //   3. If heuristics fail, ask the AI to find the boundary pattern.
      //   4. Last resort: the legacy resplitByNumberedSections (if the user
      //      explicitly set the flag in index.json).
      var isSongBook = opts.category === "Song Lyrics";
      console.log("[songs:load] file=" + fname + " category=" + opts.category + " flag=" + opts.splitByNumberedSections + " initial-chapters=" + chs.length);
      if (isSongBook) {
        // 1. EXPLICIT FORMAT FLAG WINS. Uploads always set `splitByNumberedSections: true`
        //    because we know the file format (numbered Tsoi-style). Trust it. This is the
        //    fast path for every uploaded artist file.
        if (opts.splitByNumberedSections) {
          console.log("[songs:load] explicit splitByNumberedSections flag set — trying numbered split first");
          var byNum = resplitByNumberedSections(chs);
          if (byNum && byNum.length > chs.length) {
            console.log("[songs:load] numbered split won: " + byNum.length + " sections (was " + chs.length + ")");
            chs = byNum;
          } else {
            console.log("[songs:load] numbered split did not improve count (" + (byNum ? byNum.length : 0) + " vs " + chs.length + ")");
          }
        }
        // 2. After (or in lieu of) the explicit flag, if we STILL have one big chapter,
        //    try smart splitting. This handles song books from external sources without
        //    the explicit flag, AND the case where splitByNumberedSections didn't find
        //    its markers (different format).
        if (chs.length <= 1) {
          var avgLen0 = chs.length ? (chs[0].text || "").length : 0;
          if (avgLen0 > 500) {
            console.log("[songs:load] still 1 chapter — running heuristic splitter");
            var smart = splitSongsHeuristic(chs, { minSongs: 2 });
            if (smart && smart.length >= 2) {
              console.log("[songs:load] heuristic won: " + smart.length + " sections");
              chs = smart;
            } else {
              console.log("[songs:load] heuristic failed → trying AI fallback");
              try {
                var aiResult = await splitSongsAI(chs, fname);
                if (aiResult && aiResult.length >= 2) {
                  console.log("[songs:load] AI won: " + aiResult.length + " sections");
                  chs = aiResult;
                } else {
                  console.log("[songs:load] AI also failed — file will be shown as one page");
                }
              } catch(aiErr) {
                console.log("[songs:load] AI fallback errored: " + (aiErr.message || aiErr));
              }
            }
          } else {
            console.log("[songs:load] file too short for smart splitting (" + avgLen0 + " chars)");
          }
        }
      } else if (opts.splitByNumberedSections) {
        // Non-song-category book with the legacy flag set: use original behavior.
        chs = resplitByNumberedSections(chs);
      } else {
        // Default for novels/stories/plays: re-split by in-text chapter markers
        // (Roman numerals, "Глава N", etc.). The author told us the chapter
        // boundaries by putting markers in the text — use those instead of
        // trusting spine items or TOC labels.
        var bymark = splitByMarkers(chs);
        if (bymark && bymark.length >= 2) {
          chs = bymark;
        } else if (chs.length > 1) {
          // No markers but we have multiple spine-based chapters. The user asked us not to
          // title chapters ourselves, so collapse to one chapter and let page navigation handle it.
          var merged = chs.map(function(c){ return c.text || ""; }).join("\n\n").trim();
          chs = [{ heading: "", text: merged }];
        } else if (chs.length === 1) {
          // Single chapter from spine — strip any auto-generated heading.
          var h = chs[0].heading || "";
          if (/^глава\s+\d+$/i.test(h.trim()) || /^chapter\s+\d+$/i.test(h.trim())) h = "";
          chs = [{ heading: h, text: chs[0].text || "" }];
        }
      }
      // Attach per-chapter YouTube URLs from the optional `songs` array on the
      // book entry. The array is indexed by chapter position (0-based), so the
      // user just lists URLs in song order in index.json. Missing/null entries
      // mean "no link for this song".
      if (Array.isArray(opts.songs)) {
        chs = chs.map(function(ch, i){
          var entry = opts.songs[i];
          var url = "";
          if (typeof entry === "string") url = entry;
          else if (entry && typeof entry === "object" && typeof entry.youtube === "string") url = entry.youtube;
          return url ? Object.assign({}, ch, { youtubeUrl: url }) : ch;
        });
      }

      var title = opts.title || result.title;
      var author = opts.author || result.author;
      // bookMeta carries title/author plus presentation flags the reader needs.
      // `category` drives single-page display mode (anything in "Song Lyrics"
      // shows one song per screen). `splitByNumberedSections` is the older
      // parsing flag — kept for backward compatibility and still triggers
      // single-page mode independently.
      var meta = {
        title: title,
        author: author,
        category: opts.category || "",
        splitByNumberedSections: !!opts.splitByNumberedSections,
      };
      setChapters(chs);
      setBookMeta(meta);
      setCbm(0);
      try {
        await storage.set(EPUB_CACHE, JSON.stringify({
          chapters: chs, title: title, author: author,
          category: opts.category || "",
          splitByNumberedSections: !!opts.splitByNumberedSections
        }));
        await storage.set(EPUB_BM, "0");
        await storage.delete(QHIST_KEY);
      } catch(e) {}
      startLit(0, chs, meta);
    } catch(err) { setFErr(err.message); }
  };

  // Download a preset book from the server and load it through the normal pipeline.
  var loadPresetBook = async function(book) {
    setFErr("");
    try {
      var r = await fetch("/books/" + book.filename);
      if (!r.ok) throw new Error("Could not load « " + book.filename + " »: HTTP " + r.status);
      var buf = await r.arrayBuffer();
      await loadFile(buf, book.filename, {
        splitByNumberedSections: !!book.splitByNumberedSections,
        title: book.title,
        author: book.author,
        category: book.category || "",
        // Optional per-chapter YouTube links (used by song collections). Array
        // indexed 0..N where each entry is a URL or null/missing.
        songs: Array.isArray(book.songs) ? book.songs : null,
      });
    } catch(err) { setFErr(err.message || "Failed to load preset book"); }
  };

  // Fetch the library manifest once on mount. Silent if missing — pre-loaded books are optional.
  useEffect(function() {
    fetch("/books/index.json")
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(list){ if (Array.isArray(list)) setPresetBooks(list); })
      .catch(function(){ /* no library, that's fine */ });
  }, []);

  // Fetch the grammar curriculum once on mount. The file lives in /public/grammar/
  // so it's served as a static asset; edits to the JSON take effect immediately
  // on next deploy without code changes.
  useEffect(function() {
    fetch("/grammar/curriculum.json")
      .then(function(r){ if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function(data){ setCurriculum(data); })
      .catch(function(err){ setGramErr("Couldn't load curriculum: " + (err.message || err)); });
  }, []);

  var send = async function() {
    if (!input.trim() || loading) return;
    var um = {role:"user",content:input.trim()};
    var next = msgs.concat([um]); setMsgs(next); setInput(""); setLoading(true);
    // Reset the auto-expanded textarea back to its compact starting height so
    // the next message starts from a clean 1-row state. Without this, the
    // textarea would stay at whatever height it grew to during typing.
    if (inputRef.current) inputRef.current.style.height = '';
    try {
      // Build a page-scoped snippet so follow-up messages stay locked to what's
      // on the user's screen (same scoping the AI got in the initial question).
      var sys;
      var qhistKey = String(cidx) + ":" + pidx;
      var qhistForUpdate = null;
      if (isLit && chapters.length > 0 && currentPage) {
        var litSnippet = (curChapter.text || "").slice(currentPage.startChar, currentPage.endChar);
        if (litSnippet.length > 3500) litSnippet = litSnippet.slice(0, 3500);
        // Pass prevQs so the AI knows how many questions have been asked and
        // doesn't repeat them — this is what enables the 6-question-per-song
        // session arc.
        qhistForUpdate = await loadQHist();
        var prevQs = (qhistForUpdate[qhistKey] || []).slice(-12);
        sys = litprompt(litSnippet, cidx, chapters.length, bookMeta.title || "this book", bookMeta.author || "the author", null, prevQs, pidx, totalPages, level);
      }
      var t = await api(next, sys);
      setMsgs(function(prev){ return prev.concat([{role:"assistant",content:t}]); });
      // If we're in literature mode, extract any newly-asked question from
      // the AI's reply and append it to qhist so the next turn knows the
      // count + can avoid duplicates.
      if (isLit && qhistForUpdate) {
        var newQs = extractQuestions(t);
        if (newQs.length) {
          qhistForUpdate[qhistKey] = (qhistForUpdate[qhistKey] || []).concat(newQs).slice(-25);
          saveQHist(qhistForUpdate);
        }
      }
    } catch(err) {
      setMsgs(function(prev){ return prev.concat([{role:"assistant",content:"*("+err.message+")*"}]); });
    }
    setLoading(false);
    if (inputRef.current) inputRef.current.focus();
  };

  var onKey = function(e) { if (e.key==="Enter" && !e.shiftKey){ e.preventDefault(); send(); } };

  var addV = function(ruOrEntry, en) {
    // Accepts either (ruString, enString) for legacy callers OR a full entry object:
    //   {ru, en, pos, aspect, grammar, example, exampleTranslation}
    var entry = (typeof ruOrEntry === "string")
      ? { ru: ruOrEntry, en: en || "" }
      : (ruOrEntry || {});
    var ru = (entry.ru || "").trim();
    if (!ru) return;
    if (vocab.find(function(v){ return v.ru === ru; })) return;
    var now = Date.now();
    setVocab(function(p){ return p.concat([Object.assign({}, entry, { ru: ru, id: now, created: now })]); });
  };
  var addT = function(tip) {
    if (!tips.find(function(t){ return t.tip===tip; })) {
      var now = Date.now();
      setTips(function(p){ return p.concat([{tip:tip,id:now,created:now}]); });
    }
  };
  // ── Vocab quiz generator ─────────────────────────────────────────────────
  // Builds an array of multiple-choice questions from the vocab list. For each
  // word (with an English meaning AND a part-of-speech tag), we pick 3 random
  // distractors from OTHER words with the same `pos`. If a word's pos group has
  // fewer than 3 valid siblings, that word is skipped (insufficient distractors).
  // Words without a `pos` tag are also skipped — verbs-vs-nouns mixing defeats
  // the pedagogy.
  var startQuiz = function() {
    // Group vocab by normalized pos. A word needs `en` (the English meaning to
    // quiz on) and `pos` (so we can find same-category distractors) to qualify.
    var groups = {};
    vocab.forEach(function(v){
      var p = (v.pos || "").toLowerCase().trim();
      if (!p) return;          // no pos → skipped entirely
      if (!v.en) return;       // no English meaning → can't quiz
      if (!groups[p]) groups[p] = [];
      groups[p].push(v);
    });

    var shuffle = function(arr) {
      var a = arr.slice();
      for (var i = a.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
      }
      return a;
    };

    var questions = [];
    var skipped = 0;
    vocab.forEach(function(v){
      var p = (v.pos || "").toLowerCase().trim();
      if (!p || !v.en) { skipped++; return; }
      var siblings = (groups[p] || []).filter(function(x){ return x.id !== v.id; });
      if (siblings.length < 3) { skipped++; return; }
      var distractors = shuffle(siblings).slice(0, 3).map(function(s){ return s.en; });
      questions.push({
        word: v.ru,
        correct: v.en,
        options: shuffle(distractors.concat([v.en])),
        pos: v.pos,
      });
    });

    if (questions.length === 0) {
      alert("You need more saved vocabulary! Add at least 4 words that share the same part of speech (e.g. 4 verbs), each with an English meaning and a part-of-speech tag.");
      return;
    }

    setQuizSkipNote(skipped > 0 ? skipped + " word(s) skipped (no part-of-speech tag or too few same-pos siblings)." : "");
    setQuizQuestions(shuffle(questions));
    setQuizIdx(0);
    setQuizSelected(null);
    setQuizScore(0);
    setQuizMenu(false);
    setQuizMode(true);
  };

  // ── Chat Practice: walk through saved vocab one word at a time ────────────
  // Switches to chat mode with topic "Vocabulary Practice". The AI uses each
  // saved word in context (a natural Russian sentence) and asks a question
  // about it. Different from the multiple-choice quiz — this is open-ended
  // conversational practice where the user constructs answers.
  var startVocabChat = async function() {
    if (vocab.length === 0) {
      alert("You need more saved vocabulary! Save at least one word before starting chat practice.");
      return;
    }
    setQuizMenu(false);
    setQuizMode(false);
    setTopic("Vocabulary Practice");
    setMode("chat");
    setTab("chat");
    setStarted(true);
    setMsgs([]);
    setLoading(true);
    stopTTS();
    try {
      // Pass the system prompt explicitly because setTopic hasn't propagated
      // to `act` yet on this render — api() would otherwise use the stale topic.
      var sys = vocabPracticePrompt(vocab, level);
      var t = await api([{role:"user",content:"Start please."}], sys);
      setMsgs([{role:"assistant",content:t}]);
    } catch(err) {
      setMsgs([{role:"assistant",content:"*(Error: "+err.message+")*"}]);
    }
    setLoading(false);
  };

  // Bookmarks for grammar curriculum topics. We only store the topic ID — when
  // the user clicks a saved card we re-render the full content from curriculum.json,
  // so edits to the curriculum are reflected in already-saved entries.
  var addTopic = function(topicId) {
    if (!topicId) return;
    setSavedTopics(function(p){ return p.indexOf(topicId) === -1 ? p.concat([topicId]) : p; });
  };
  var rmTopic = function(topicId) {
    setSavedTopics(function(p){ return p.filter(function(id){ return id !== topicId; }); });
  };

  // Format a timestamp (ms since epoch) as a friendly relative date string.
  var formatVocabDate = function(ts) {
    if (!ts || isNaN(ts)) return "";
    var d = new Date(ts);
    var now = new Date();
    var diffMs = now - d;
    var diffMins = Math.floor(diffMs / 60000);
    var diffHrs  = Math.floor(diffMs / 3600000);
    var diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1)  return "just now";
    if (diffMins < 60) return diffMins + " min ago";
    if (diffHrs  < 24 && now.getDate() === d.getDate()) {
      return "Today, " + d.getHours().toString().padStart(2,"0") + ":" + d.getMinutes().toString().padStart(2,"0");
    }
    if (diffDays < 2)  return "Yesterday";
    if (diffDays < 7)  return diffDays + " days ago";
    // Older: "11 May 2026"
    var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return d.getDate() + " " + months[d.getMonth()] + " " + d.getFullYear();
  };

  // Builds the canonical vocab entry from popup data:
  //   - nouns/adj/etc → lemma in nominative
  //   - verb without clear pair → infinitive
  //   - verb with pair → "imperfective / perfective" (or just "lemma / pair" if aspect unknown)
  var formatVocabEntry = function(data, fallback) {
    var fallbackRu = (fallback || "").trim();
    if (!data) return { ru: fallbackRu, en: "" };
    var lemma = (data.lemma || data.word || fallbackRu || "").trim();
    var pair  = (data.aspectPair || "").trim();
    var aspect = (data.aspect || "").toLowerCase();
    var ru;
    if (pair) {
      // Conventional dictionary order: imperfective / perfective.
      if (/imperf/.test(aspect))      ru = lemma + " / " + pair;
      else if (/^perf/.test(aspect))  ru = pair + " / " + lemma;
      else                            ru = lemma + " / " + pair;
    } else {
      ru = lemma;
    }
    return {
      ru: ru || fallbackRu,
      en: (data.translation || "").trim(),
      pos: (data.partOfSpeech || "").trim(),
      aspect: (data.aspect || "").trim(),
      grammar: (data.grammar || "").trim(),
      example: (data.example || "").trim(),
      exampleTranslation: (data.exampleTranslation || "").trim()
    };
  };

  var xBold = function(text) {
    var r = []; var re = /\*\*([^*\n(]{1,40})\(([^)]{1,60})\)\*\*/g; var m;
    while ((m = re.exec(text)) !== null) if (m[1].trim()) r.push({ru:m[1].trim(),en:m[2].trim()});
    return r;
  };
  var xTips = function(text) {
    var r = []; var re = /📝\s*TIP[:\s]+(.+)/g; var m;
    while ((m = re.exec(text)) !== null) if (m[1].trim()) r.push(m[1].trim());
    return r;
  };

  var renderLit = function(text) {
    var str = typeof text === "string" ? text : ((text && text.text) ? text.text : "");

    // Build tokens with absolute character positions in the original chapter text,
    // so we can match against onboundary events from speechSynthesis.
    var tokens = [];
    var tre = /[а-яёА-ЯЁ]+|[^а-яёА-ЯЁ]+/g;
    var tm;
    while ((tm = tre.exec(str)) !== null) {
      tokens.push({
        text: tm[0],
        start: tm.index,
        end: tm.index + tm[0].length,
        isRu: /[а-яёА-ЯЁ]/.test(tm[0][0])
      });
    }

    // ── Highlight matching ──
    // The TTS engine fires onboundary events that may land in whitespace, punctuation,
    // or be slightly off the start of a word. We compute the "active word" as the LAST
    // Russian token whose start ≤ spokenChar. The highlight then stays on a word from
    // the moment the engine reports its position until the next word's position arrives.
    // This prevents the shakiness/skipping you see when matching only on exact ranges.
    var activeStart = -1;
    if (noAIMode && spokenChar >= 0) {
      for (var ai = 0; ai < tokens.length; ai++) {
        if (tokens[ai].isRu && tokens[ai].start <= spokenChar) {
          activeStart = tokens[ai].start;
        } else if (tokens[ai].isRu && tokens[ai].start > spokenChar) {
          break;
        }
      }
      // Clear the highlight if the spoken position has run well past the last Russian word
      // (handles the moment between speech ending and onend firing).
      if (activeStart >= 0) {
        var lastRu = tokens.reduce(function(acc, t){ return t.isRu ? t : acc; }, null);
        if (lastRu && spokenChar > lastRu.end + 200) activeStart = -1;
      }
    }

    // Group tokens into paragraphs. For song books, EVERY newline creates a
    // new visual line (one lyric line per paragraph). For prose, only blank
    // lines (\n{2,}) separate paragraphs — single newlines are just word-wrap.
    var paraBreakRe = singlePageMode ? /\n+/g : /\n{2,}/g;
    var paragraphs = [[]];
    for (var ti = 0; ti < tokens.length; ti++) {
      var tok = tokens[ti];
      if (tok.isRu) {
        paragraphs[paragraphs.length-1].push(tok);
        continue;
      }
      var sub = tok.text, subStart = tok.start, lastIdx = 0;
      var brkRe = new RegExp(paraBreakRe.source, "g"), brk;
      while ((brk = brkRe.exec(sub)) !== null) {
        if (brk.index > lastIdx) {
          paragraphs[paragraphs.length-1].push({
            text: sub.slice(lastIdx, brk.index),
            start: subStart + lastIdx,
            end:   subStart + brk.index,
            isRu: false
          });
        }
        paragraphs.push([]);
        lastIdx = brk.index + brk[0].length;
      }
      if (lastIdx < sub.length) {
        paragraphs[paragraphs.length-1].push({
          text: sub.slice(lastIdx),
          start: subStart + lastIdx,
          end:   tok.end,
          isRu: false
        });
      }
    }

    return (function() {
      // Pull the non-empty paragraphs in the order they appear, matching how
      // computePages indexes them.
      var nonEmpty = paragraphs.filter(function(p){ return p.some(function(t){ return t.text.trim().length > 0; }); });
      if (!currentPage) return [];

      // Single-page mode (e.g. song lyrics): show the whole chapter, no slicing.
      if (currentPage.isSinglePage || currentPage.paraIndices === null) {
        return nonEmpty;
      }

      if (currentPage.isSplit) {
        // Giant single-paragraph chapter: the only paragraph is split across
        // multiple pages by sentence boundary. Render only the tokens that fall
        // within this page's char range.
        var giant = nonEmpty[0] || [];
        var sliced = giant.filter(function(tok) {
          return tok.start >= currentPage.startChar && tok.end <= currentPage.endChar;
        });
        return sliced.length > 0 ? [sliced] : [];
      }
      // Normal case: render the whole paragraphs that belong to this page.
      return currentPage.paraIndices.map(function(idx){ return nonEmpty[idx] || []; }).filter(function(p){ return p.length > 0; });
    })()
      .map(function(para, pi) {
        // Detect play-style speaker attribution at the start of a paragraph.
        // Russian plays commonly use Title Case names like "Маша. ..." or "Медведенко. ..."
        // (Chekhov, Ostrovsky, Tolstoy plays). Older drama uses ALL CAPS like "ЛУКА. ..." (Gorky).
        // Pattern: 1-3 Russian Title-Case or ALL-CAPS words, then . : — – or -, then space + dialogue.
        var paraText = para.map(function(t){ return t.text; }).join("");
        // Play-line detection: NAME punct dialogue. Skip for song books since
        // lines like "Владимирский централ - ветер северный" would otherwise
        // false-match as a speaker named "Владимирский централ".
        var speakerMatch = singlePageMode ? null
          : paraText.match(/^([А-ЯЁ][а-яёА-ЯЁ\-]+(?:\s+[А-ЯЁ][а-яёА-ЯЁ\-]+){0,2})\s*([.:—–\-])(\s+)/);
        var speakerNameEnd = -1, attribEnd = -1;
        // Guard against false positives — name must look like a name (≤40 chars) and there must be dialogue after.
        if (speakerMatch && speakerMatch[1].length <= 40 && paraText.length > speakerMatch[0].length + 3) {
          speakerNameEnd = (para[0] ? para[0].start : 0) + speakerMatch[1].length;
          attribEnd     = (para[0] ? para[0].start : 0) + speakerMatch[0].length;
        }

        return (
          <p key={pi} style={{marginBottom: singlePageMode ? "0.35em" : "1.2em"}}>
            {(function(){
              // If this paragraph is a play line, replace the punctuation between name and dialogue with an em-dash.
              if (speakerNameEnd > -1) {
                var elems = [];
                for (var i = 0; i < para.length; i++) {
                  var tk = para[i];
                  var hl = tk.isRu && tk.start === activeStart;
                  var inName = tk.end <= speakerNameEnd;
                  var inAttrib = tk.end <= attribEnd;

                  // Skip the original separator (.:—) and the whitespace right after.
                  if (inAttrib && !inName) continue;

                  if (tk.isRu) {
                    var clickPlay;
                    if (inName) {
                      clickPlay = undefined;
                    } else if (noAIMode) {
                      clickPlay = (function(pos){ return function(e){ e.stopPropagation(); jumpTTS(pos); }; })(tk.start);
                    } else {
                      clickPlay = (function(w){ return function(e){ defWord(w, e); }; })(tk.text);
                    }
                    elems.push(
                      <span key={i}
                        className={"rw" + (hl ? " rwhl" : "") + (inName ? " play-speaker" : "")}
                        onClick={clickPlay}
                        title={inName ? "" : (noAIMode ? "Click to read from here" : "Click to define")}>{tk.text}</span>
                    );
                    // Just after the speaker name finishes, insert the em-dash separator.
                    if (inName && (i+1 >= para.length || para[i+1].end > speakerNameEnd)) {
                      elems.push(<span key={"d"+i} className="play-dash">— </span>);
                    }
                  } else {
                    elems.push(<span key={i}>{tk.text.replace(/\n/g, " ")}</span>);
                  }
                }
                return elems;
              }
              // Regular paragraph rendering.
              return para.map(function(tk, i) {
                var hl = tk.isRu && tk.start === activeStart;
                if (tk.isRu) {
                  var clickReg = noAIMode
                    ? (function(pos){ return function(e){ e.stopPropagation(); jumpTTS(pos); }; })(tk.start)
                    : function(e){ defWord(tk.text, e); };
                  return (
                    <span key={i}
                      className={"rw" + (hl ? " rwhl" : "")}
                      onClick={clickReg}
                      title={noAIMode ? "Click to read from here" : "Click to define"}>{tk.text}</span>
                  );
                }
                return <span key={i}>{tk.text.replace(/\n/g, " ")}</span>;
              });
            })()}
          </p>
        );
      });
  };

  var renderBubble = function(text) {
    try {
      return text.split("\n").map(function(line, li) {
        var t = line.trim();
        var trm = t.match(/^\*{1,2}([^*]+)\*{1,2}$/);
        if (trm && !/[а-яёА-ЯЁ]{3,}/.test(trm[1])) return <div key={li} className="tline">{trm[1]}</div>;
        var tip = t.match(/^📝\s*TIP[:\s]+(.+)/);
        if (tip) return <div key={li} className="tipline">📝 {tip[1]}</div>;
        if (t.startsWith("❓")) return <div key={li} className="qline">{t}</div>;
        var toks = []; var rem = line; var ki = 0;
        while (rem.length > 0) {
          var bm = rem.match(/^\*\*([^*\n(]{1,40})\(([^)]{1,60})\)\*\*/);
          if (bm) {
            var bmRu = bm[1].trim();
            toks.push(<strong key={ki++} className="vw rw" onClick={(function(w){ return function(e){ defWord(w, e); }; })(bmRu)}>{bmRu}</strong>);
            rem = rem.slice(bm[0].length);
            continue;
          }
          if (rem.startsWith("**")) { rem=rem.slice(2); continue; }
          var cm = rem.match(/^\[([^\]]{1,60})\]/);
          if (cm) { toks.push(<span key={ki++} className="corr">[{cm[1]}]</span>); rem=rem.slice(cm[0].length); continue; }
          var rw = rem.match(/^[а-яёА-ЯЁ]+/);
          if (rw) {
            var rwWord = rw[0];
            toks.push(<span key={ki++} className="rw" onClick={(function(w){ return function(e){ defWord(w, e); }; })(rwWord)}>{rwWord}</span>);
            rem = rem.slice(rwWord.length);
            continue;
          }
          toks.push(<span key={ki++}>{rem[0]}</span>); rem=rem.slice(1);
        }
        return <div key={li} className="mline">{toks}</div>;
      });
    } catch(err) { return <div>{text}</div>; }
  };

  var renderMsg = function(msg, i) {
    if (msg.role==="user") return <div key={i} className="msg user"><div className="bub ubub">{msg.content}</div></div>;
    var tp=xTips(msg.content);
    return (
      <div key={i} className="msg ai">
        <div className="bub abub">{renderBubble(msg.content)}</div>
        <div className="acts">
          <button className={"spk"+(spkIdx===i?" spkon":"")} onClick={function(){ speakMsg(msg.content,i); }}>{spkIdx===i?"⏹ Stop":"🔊 Listen"}</button>
          {tp.map(function(t,j){
            var savedT = !!tips.find(function(x){ return x.tip === t; });
            return (
              <button key={j} className={"chip tc" + (savedT ? " chipsaved" : "")} disabled={savedT}
                onClick={function(){ if (!savedT) addT(t); }}
                title={savedT ? "Already saved" : "Save this tip"}>
                {savedT ? "✓ saved" : "📝 Save tip"}
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  // Voice picker panel — extracted into a helper so we can drop it into BOTH
  // the reading view (above the book text) and the chat view (above the input
  // bar). Same state (showVP, voice, allVoices) drives both call sites, so
  // picking a voice anywhere updates the entire app.
  var renderVoicePicker = function() {
    if (!showVP) return null;
    return (
      <div className="vpanel" style={{maxHeight: diagLogs.length > 0 ? 380 : 180}}>
        <div className="vphdr" style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:8}}>
          <span>Choose a Russian voice</span>
          <div style={{display:"flex",gap:6}}>
            {diagLogs.length > 0 && <button className="ttsbtn" style={{height:22,fontSize:11}} onClick={copyDiagLogs}>📋 Copy log</button>}
            <button className="ttsbtn" style={{height:22,fontSize:11}} onClick={runDiagnostics}>🩺 Diagnose</button>
          </div>
        </div>
        {diagLogs.length > 0 && (
          <div style={{maxHeight:180,overflowY:"auto",padding:"6px 28px",fontFamily:"monospace",fontSize:11,color:"rgba(210,197,175,.7)",background:"#0a0908",borderBottom:"1px solid rgba(210,197,175,.06)",lineHeight:1.5}}>
            {diagLogs.map(function(line,i){
              var color = line.indexOf("onerror") >= 0 || line.indexOf("THREW") >= 0 ? "#c87a6806a"
                       : line.indexOf("onstart") >= 0 ? "#82a882"
                       : line.indexOf("===") >= 0 ? "#c8a276" : "rgba(210,197,175,.7)";
              return <div key={i} style={{color:color,whiteSpace:"pre-wrap",wordBreak:"break-all"}}>{line}</div>;
            })}
          </div>
        )}
        <div className="vplist">
          {allVoices.length===0 && <div className="vpem">No voices found. Install a Russian voice in system settings.</div>}
          {allVoices.length>0 && allVoices.filter(function(v){ return v.lang.startsWith("ru")||/katya|katja|milena|yuri/i.test(v.name); }).length===0 && <div className="vpem">No Russian voices on this device.<br/>In Microsoft Edge you'll see Russian neural voices automatically — try opening the app in Edge. Or install a Russian voice in your system Speech settings.</div>}
          {(function() {
            var isRu = function(v) { return v.lang.startsWith("ru")||/katya|katja|milena|yuri/i.test(v.name); };
            var isMsNatural = function(v) {
              return /microsoft.*online.*natural/i.test(v.name) || /\(natural\)/i.test(v.name);
            };
            var isGoogle = function(v) { return /google/i.test(v.name); };
            // Tier each voice: 0 = local, 1 = high-quality network (MS Natural / Google),
            // 2 = other network. Google and MS Natural are both reliable on the deployed
            // site, so we group them together at the top of the network tier.
            var tier = function(v) {
              if (v.localService) return 0;
              if (isMsNatural(v) || isGoogle(v)) return 1;
              return 2;
            };
            var byQuality = function(a, b) { return tier(a) - tier(b); };
            var ruVoices = allVoices.filter(isRu).slice().sort(byQuality);
            return ruVoices;
          })()
            .map(function(v,i){
              var ru = true;  // We've already filtered — all voices in the list are Russian.
              var network = !v.localService;
              // Microsoft Edge's Online Natural neural voices AND Chrome's Google network
              // voices are both high-quality neural — flag them positively, not as warnings.
              var isMsNatural = /microsoft.*online.*natural/i.test(v.name) || /\(natural\)/i.test(v.name);
              var isGoogle = /google/i.test(v.name);
              var isHighQualityNetwork = isMsNatural || isGoogle;
              var labelText, labelColor, rowOpacity;
              if (!network) {
                labelText = " · local ✓";
                labelColor = null;
                rowOpacity = null;
              } else if (isHighQualityNetwork) {
                labelText = " · neural ★";
                labelColor = "#c8a276";
                rowOpacity = null;
              } else {
                labelText = " · network ⚠";
                labelColor = "#c87a68";
                rowOpacity = 0.55;
              }
              return (
                <button key={i} className={"vprow"+(voice&&voice.name===v.name?" sel":"")}
                  style={rowOpacity ? {opacity: rowOpacity} : null}
                  onClick={function(){
                    setVoice(v); stopTTS(); setTtsErr("");
                    // Speak a short test phrase so the user immediately knows if the voice works.
                    setTimeout(function() {
                      var u = new SpeechSynthesisUtterance("Привет! Я твой голос.");
                      u.lang = "ru-RU"; u.voice = v; u.rate = 0.9;
                      u.onerror = function(e) {
                        var err = (e && e.error) || "unknown";
                        if (err !== "interrupted" && err !== "canceled") {
                          var hint = (network && !isHighQualityNetwork) ? " — pick a voice marked « local » or « neural ★ » instead" : "";
                          setTtsErr("Voice « " + v.name + " » failed: " + err + hint);
                        }
                      };
                      try { window.speechSynthesis.speak(u); }
                      catch(ex) { setTtsErr("speak() threw: " + (ex.message || ex)); }
                    }, 80);
                  }}>
                  <span className={"vpn"+(ru?" vpnru":"")}>{v.name}</span>
                  <span className="vpl" style={labelColor ? {color:labelColor} : null}>{v.lang}{labelText}</span>
                </button>
              );
          })}
        </div>
      </div>
    );
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,400&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        html,body{height:100%;background:#1a1611;color:#d2c5af;font-family:'Crimson Pro',serif;overflow:hidden}
        /* Lock the app to the viewport: full width, viewport height. Inner panels
           (book text, chat messages) scroll within their own bounds — the page
           itself never scrolls. Uses 100dvh (dynamic viewport height) so mobile
           browsers with collapsing chrome behave correctly; falls back to 100vh
           for older browsers. */
        .app{height:100vh;height:100dvh;background:#1a1611;display:flex;flex-direction:column;width:100%;overflow:hidden}
        .app::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background:radial-gradient(ellipse at 15% 0%,rgba(150,80,60,.06) 0%,transparent 50%),radial-gradient(ellipse at 85% 100%,rgba(80,90,130,.05) 0%,transparent 50%)}
        .hdr{padding:16px 28px 12px;border-bottom:1px solid rgba(210,197,175,.1);display:flex;align-items:center;justify-content:space-between;gap:16px;position:relative;z-index:10}
        .logo{display:flex;align-items:baseline;gap:10px}
        .lru{font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:#c8a276}
        .lsub{font-size:11px;color:rgba(210,197,175,.35);letter-spacing:2.5px;text-transform:uppercase}
        .tbadge{background:rgba(200,162,118,.1);border:1px solid rgba(200,162,118,.25);color:#c8a276;padding:6px 14px;border-radius:20px;font-size:13px;cursor:pointer;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        /* Persistent CEFR level selector pinned in the header. Compact pill style
           that matches the Topic badge. The label sits to the left of the dropdown. */
        .level-wrap{display:flex;align-items:center;gap:6px}
        .level-lbl{font-size:10px;color:rgba(210,197,175,.4);text-transform:uppercase;letter-spacing:1.5px;font-weight:600}
        .level-pill{background:rgba(200,162,118,.1);border:1px solid rgba(200,162,118,.25);color:#c8a276;padding:5px 10px;border-radius:14px;font-size:13px;font-family:'Crimson Pro',serif;cursor:pointer;width:auto;outline:none}
        .level-pill:hover{background:rgba(200,162,118,.18)}
        .level-pill option{background:#221e17}
        @media(max-width:600px){.level-lbl{display:none}.level-pill{padding:4px 8px;font-size:12px}}
        .tbadge:hover{background:rgba(200,162,118,.18)}
        .tabs{display:flex;border-bottom:1px solid rgba(210,197,175,.1);padding:0 28px;position:relative;z-index:10}
        .tab{padding:11px 20px;background:none;border:none;color:rgba(210,197,175,.4);font-family:'Crimson Pro',serif;font-size:14px;cursor:pointer;border-bottom:2px solid transparent;position:relative;top:1px;transition:color .2s}
        .tab.on{color:#c8a276;border-bottom-color:#c8a276}
        .tab:hover:not(.on){color:rgba(210,197,175,.7)}
        .bdg{background:#9d4630;color:#fff;font-size:10px;border-radius:10px;padding:1px 5px;margin-left:4px;vertical-align:middle}
        .bdg.g{background:#5a8556}
        .main{flex:1;display:flex;flex-direction:column;position:relative;z-index:1;min-height:0}
        .ss{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:48px 28px;text-align:center;gap:22px}
        .sico{font-size:54px;line-height:1}
        .sti{font-family:'Playfair Display',serif;font-size:30px;color:#d2c5af;font-weight:400}
        .sde{color:rgba(210,197,175,.5);font-size:16px;max-width:500px;line-height:1.6}
        .tsel{width:100%;max-width:500px;display:flex;flex-direction:column;gap:12px;text-align:left}
        .slbl{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:rgba(210,197,175,.35)}
        select,input[type="text"],textarea{width:100%;background:rgba(210,197,175,.06);border:1px solid rgba(210,197,175,.16);color:#d2c5af;padding:12px 16px;border-radius:10px;font-family:'Crimson Pro',serif;font-size:16px;outline:none;transition:border-color .2s}
        select{appearance:none;cursor:pointer} select option{background:#221e17}
        ::placeholder{color:rgba(210,197,175,.28)}
        input:focus,textarea:focus,select:focus{border-color:rgba(200,162,118,.5)}
        .btn-p{background:linear-gradient(135deg,#9d4630,#82362a);color:#fff;border:none;padding:14px 32px;border-radius:10px;font-family:'Playfair Display',serif;font-size:17px;cursor:pointer;width:100%;box-shadow:0 4px 20px rgba(157,70,48,.3);transition:opacity .2s}
        .btn-p:hover:not(:disabled){opacity:.88} .btn-p:disabled{opacity:.4;cursor:default}
        .btn-g{background:rgba(210,197,175,.07);color:rgba(210,197,175,.6);border:1px solid rgba(210,197,175,.15);padding:12px 24px;border-radius:10px;font-family:'Crimson Pro',serif;font-size:15px;cursor:pointer;width:100%;transition:background .2s}
        .btn-g:hover{background:rgba(210,197,175,.12)}
        .chat-wrap{flex:1;display:flex;flex-direction:column;min-height:0}
        .msgs{flex:1;overflow-y:auto;padding:20px 28px 8px;display:flex;flex-direction:column;gap:12px}
        .msg{display:flex;flex-direction:column;gap:6px}
        .msg.user{align-items:flex-end} .msg.ai{align-items:flex-start}
        .bub{max-width:72%;padding:14px 18px;font-size:16px;line-height:1.7}
        .abub{background:rgba(210,197,175,.065);border:1px solid rgba(210,197,175,.11);border-radius:4px 16px 16px 16px}
        .ubub{background:rgba(157,70,48,.2);border:1px solid rgba(157,70,48,.28);border-radius:16px 4px 16px 16px}
        .mline{display:block;margin-bottom:3px;line-height:1.7}
        .tline{color:rgba(210,197,175,.5);font-size:14px;margin-top:6px;display:block;line-height:1.65;padding-top:5px;border-top:1px solid rgba(210,197,175,.08)}
        .tipline{color:rgba(128,168,128,.85);font-size:13.5px;border-left:2px solid rgba(128,168,128,.35);padding-left:8px;margin-top:7px;display:block;line-height:1.5}
        .qline{color:#c8a276;font-size:15px;margin-top:10px;display:block;line-height:1.6;padding:8px 12px;background:rgba(200,162,118,.07);border-radius:8px;border-left:2px solid rgba(200,162,118,.4)}
        .vw{color:#c8a276} .corr{color:#87a8c4}
        .vw.rw{color:#c8a276;border-bottom:1px dotted rgba(200,162,118,.5)}
        .vw.rw:hover{color:#ece1cb;border-bottom-color:#ece1cb;background:rgba(200,162,118,.18);border-radius:2px}
        .rw{cursor:pointer;border-bottom:1px dotted rgba(210,197,175,.18);transition:color .15s,background .12s}
        .rw:hover{color:#c8a276;border-bottom-color:#c8a276}
        .rwhl{background:rgba(200,162,118,.18);color:#ece1cb;border-bottom-color:#c8a276;border-radius:3px;padding:1px 2px}
        .acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:2px}
        .spk{padding:5px 12px;border-radius:20px;font-size:13px;cursor:pointer;font-family:'Crimson Pro',serif;background:rgba(210,197,175,.07);border:1px solid rgba(210,197,175,.2);color:rgba(210,197,175,.7);transition:all .15s}
        .spk:hover{background:rgba(210,197,175,.14)} .spkon{background:rgba(157,70,48,.18);border-color:rgba(157,70,48,.35);color:#c87a6806a}
        .chip{padding:5px 12px;border-radius:20px;font-size:12px;cursor:pointer;font-family:'Crimson Pro',serif;border:1px solid;transition:background .15s}
        .vc{background:rgba(200,162,118,.09);border-color:rgba(200,162,118,.28);color:#c8a276} .vc:hover:not(:disabled){background:rgba(200,162,118,.18)}
        .tc{background:rgba(128,168,128,.08);border-color:rgba(128,168,128,.25);color:rgba(128,168,128,.9)} .tc:hover:not(:disabled){background:rgba(128,168,128,.15)}
        .chip:disabled,.chipsaved{cursor:default;opacity:.7}
        .chipsaved{background:rgba(128,168,128,.15)!important;border-color:rgba(128,168,128,.4)!important;color:rgba(150,190,150,.95)!important}
        .typing{display:flex;align-items:center;gap:5px;padding:12px 16px;background:rgba(210,197,175,.065);border:1px solid rgba(210,197,175,.11);border-radius:4px 16px 16px 16px;width:fit-content}
        .dot{width:6px;height:6px;background:rgba(210,197,175,.4);border-radius:50%;animation:bounce 1.2s ease-in-out infinite}
        .dot:nth-child(2){animation-delay:.2s} .dot:nth-child(3){animation-delay:.4s}
        @keyframes bounce{0%,80%,100%{transform:translateY(0);opacity:.4}40%{transform:translateY(-5px);opacity:1}}
        .ibar{padding:12px 28px 16px;border-top:1px solid rgba(210,197,175,.09);display:flex;gap:10px;align-items:flex-end;background:#1a1611;z-index:10}
        .ibar textarea{flex:1;resize:none;min-height:44px;max-height:120px;padding:10px 14px;border-radius:22px;font-size:15px;line-height:1.5}
        .isend{background:linear-gradient(135deg,#9d4630,#82362a);color:#fff;border:none;width:44px;height:44px;border-radius:50%;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:opacity .15s}
        .isend:hover:not(:disabled){opacity:.85} .isend:disabled{opacity:.35;cursor:default}
        .inew{background:rgba(210,197,175,.06);color:rgba(210,197,175,.5);border:1px solid rgba(210,197,175,.15);padding:0 16px;border-radius:22px;font-size:13px;cursor:pointer;font-family:'Crimson Pro',serif;height:44px;white-space:nowrap;transition:all .15s}
        .inew:hover{background:rgba(210,197,175,.12);color:#d2c5af}
        .lit-wrap{flex:1;display:flex;flex-direction:column;min-height:0;overflow:hidden}
        .lit-top{display:flex;align-items:center;gap:8px;padding:8px 28px;border-bottom:1px solid rgba(210,197,175,.1);flex-shrink:0;background:#1a1611}
        .ltab{padding:6px 14px;border-radius:16px;background:none;border:1px solid rgba(210,197,175,.14);color:rgba(210,197,175,.45);font-family:'Crimson Pro',serif;font-size:13px;cursor:pointer;transition:all .15s}
        .ltab.on{background:rgba(200,162,118,.12);border-color:rgba(200,162,118,.3);color:#c8a276}
        .ltab:hover:not(.on){background:rgba(210,197,175,.06)}
        .lprog{margin-left:auto;display:flex;align-items:center;gap:10px}
        .lpct{font-size:12px;color:rgba(210,197,175,.35)}
        .lpbar{width:80px;height:3px;background:rgba(210,197,175,.1);border-radius:2px;overflow:hidden}
        .lpfill{height:100%;background:#c8a276;border-radius:2px;transition:width .3s}
        .ttsbar{display:flex;align-items:center;gap:10px;padding:7px 28px;background:#1e1a14;border-bottom:1px solid rgba(210,197,175,.08);flex-shrink:0}
        .ttsplay{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#9d4630,#82362a);border:none;color:#fff;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:opacity .15s}
        .ttsplay:hover{opacity:.85}
        .ttspause{width:32px;height:32px;border-radius:50%;background:rgba(157,70,48,.2);border:1px solid rgba(157,70,48,.4);color:#c87a6806a;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}
        .ttslab{flex:1;font-size:12px;color:rgba(210,197,175,.4);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .ttsbtn{background:none;border:1px solid rgba(210,197,175,.15);color:rgba(210,197,175,.4);height:26px;border-radius:8px;font-size:12px;cursor:pointer;padding:0 10px;transition:all .15s}
        .ttsbtn:hover{background:rgba(210,197,175,.08);color:rgba(210,197,175,.7)}
        /* Grammar reference page (📚 Grammar mode) */
        .gramref{flex:1;display:flex;flex-direction:column;min-height:0}
        .gramref-hdr{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 28px;background:#1e1a14;border-bottom:1px solid rgba(210,197,175,.08);flex-shrink:0}
        .gramref-body{flex:1;overflow-y:auto;padding:32px 28px 60px;max-width:780px;width:100%;margin:0 auto;line-height:1.55}
        .gramref-body section h2{margin-top:4px}
        .gramref-body section:first-of-type{margin-top:8px}
        .gramref-nav{display:flex;gap:10px;margin-top:32px;padding-top:24px;border-top:1px solid rgba(210,197,175,.08)}
        .gramref-nav .btn-g{font-size:13px;padding:10px 14px;text-align:center}
        @media (max-width:600px){.gramref-body{padding:24px 18px 60px}.gramref-hdr{padding:10px 18px}.gramref-nav{flex-direction:column}}
        .vpanel{background:#1e1a14;border-bottom:1px solid rgba(210,197,175,.08);max-height:180px;display:flex;flex-direction:column;flex-shrink:0}
        .vphdr{padding:7px 28px 4px;border-bottom:1px solid rgba(210,197,175,.06);font-size:12px;color:rgba(210,197,175,.35)}
        .vplist{overflow-y:auto;padding:4px 28px}
        .vprow{width:100%;background:none;border:none;border-bottom:1px solid rgba(210,197,175,.05);padding:7px 0;display:flex;align-items:center;justify-content:space-between;cursor:pointer;gap:10px;transition:background .15s}
        .vprow:hover,.vprow.sel{background:rgba(200,162,118,.06)}
        .vpn{font-size:14px;color:#d2c5af;font-family:'Crimson Pro',serif;text-align:left}
        .vpnru{color:#c8a276} .vpl{font-size:11px;color:rgba(210,197,175,.28)}
        .vpem{font-size:13px;color:rgba(210,197,175,.3);padding:14px 0;text-align:center}
        .lit-body{flex:1;display:flex;min-height:0;overflow:hidden}
        .lit-left{flex:1;overflow-y:auto;padding:24px 28px;border-right:1px solid rgba(210,197,175,.08)}
        /* Book text gets a comfortable reading width even when the column is very
           wide on big monitors — humans don't enjoy reading lines that span
           1000+ pixels. Center the content. */
        .lit-left > *{max-width:760px;margin-left:auto;margin-right:auto}
        .lit-right{width:460px;flex-shrink:0;display:flex;flex-direction:column;min-height:0}
        @media(max-width:900px){
          .lit-body{flex-direction:column}
          .lit-left{
            border-right:none;
            border-bottom:none;
            max-height:none;
            flex:1;
            /* Leave room at the bottom for the floating two-row nav + chat panel.
               Nav is now ~108px tall: page row (~46) + chapter row (~26) + gaps + padding. */
            padding-bottom:calc(40vh + 120px);
          }
          /* In read-without-AI mode there's no chat panel, so only leave room for the nav bar. */
          .lit-left.noai{
            padding-bottom:calc(128px + env(safe-area-inset-bottom));
          }
          .lit-right{
            width:100%;
            max-width:1000px;
            position:fixed;
            bottom:0;
            left:0;
            right:0;
            margin:0 auto;
            height:40vh;
            background:rgba(26,22,17,.96);
            -webkit-backdrop-filter:blur(10px);
            backdrop-filter:blur(10px);
            border-top:1px solid rgba(210,197,175,.12);
            z-index:50;
            padding-bottom:env(safe-area-inset-bottom);
          }
          /* Pin the Previous / 📌 / Next bar directly above the floating chat,
             with rounded top corners so the two together feel like a unified bottom sheet. */
          .lnav{
            position:fixed;
            bottom:40vh;
            left:0;
            right:0;
            max-width:1000px;
            margin:0 auto;
            z-index:51;
            border-top:none;
            background:rgba(26,22,17,.94);
            -webkit-backdrop-filter:blur(10px);
            backdrop-filter:blur(10px);
            border-radius:14px 14px 0 0;
            box-shadow:0 -8px 28px rgba(0,0,0,.45);
          }
          /* Read-without-AI: no chat panel below, so pin to the absolute bottom of the viewport
             with safe-area padding for the iPhone home indicator. */
          .lnav.noai{
            bottom:0;
            border-radius:14px 14px 0 0;
            padding-bottom:calc(12px + env(safe-area-inset-bottom));
          }
        }
        .lhdr{font-size:11px;color:rgba(210,197,175,.3);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px}
        .lch-heading{font-family:'Playfair Display',serif;font-size:20px;color:#c8a276;margin-bottom:14px}
        .ltxt{font-size:17.5px;line-height:1.85;color:#d2c5af;font-family:'Crimson Pro',serif;word-wrap:break-word;overflow-wrap:break-word;letter-spacing:.005em}
        .play-speaker{color:#c8a276;font-weight:600;letter-spacing:.04em;border-bottom:none !important;cursor:default !important}
        .play-speaker:hover{color:#c8a276 !important;background:none !important}
        .play-dash{color:rgba(210,197,175,.45);padding:0 6px;font-weight:300}
        .lit-msgs{flex:0 1 auto;max-height:50%;overflow-y:auto;padding:14px 20px 8px;display:flex;flex-direction:column;gap:10px}
        .lit-ibar{position:relative;padding:10px 20px 14px;border-top:1px solid rgba(210,197,175,.08);background:#1a1611;flex:1 1 auto;min-height:0;display:flex;flex-direction:column}
        .lit-ibar textarea{flex:1;width:100%;resize:none;min-height:80px;max-height:none;padding:14px 60px 14px 16px;border-radius:14px;font-size:16px;line-height:1.55}
        .lit-ibar .isend{position:absolute;bottom:22px;right:28px;box-shadow:0 4px 14px rgba(0,0,0,.4)}
        .lnav{display:flex;flex-direction:column;gap:6px;padding:10px 28px 12px;border-top:1px solid rgba(210,197,175,.08);flex-shrink:0;background:#1a1611}
        .lnav-row{display:flex;gap:8px;justify-content:center;align-items:stretch}
        .lnav-row-sm{margin-top:2px}
        .lnb{flex:1;padding:10px;border-radius:10px;border:1px solid rgba(210,197,175,.14);background:rgba(210,197,175,.05);color:rgba(210,197,175,.55);font-family:'Crimson Pro',serif;font-size:14px;cursor:pointer;transition:all .15s;text-align:center}
        .lnb:hover:not(:disabled){background:rgba(210,197,175,.1);color:#d2c5af} .lnb:disabled{opacity:.22;cursor:default}
        .lnb.p{background:linear-gradient(135deg,#9d4630,#82362a);border-color:transparent;color:#fff} .lnb.p:hover{opacity:.9}
        .lbm{padding:10px 14px;border-radius:10px;border:1px solid rgba(200,162,118,.25);background:rgba(200,162,118,.07);color:#c8a276;font-size:15px;cursor:pointer;transition:background .15s}
        .lbm:hover{background:rgba(200,162,118,.15)}
        .lnb-sm{flex:1;padding:7px 12px;border-radius:8px;border:1px solid rgba(200,162,118,.3);background:rgba(200,162,118,.08);color:#c8a276;font-family:'Crimson Pro',serif;font-size:13px;cursor:pointer;transition:all .15s;text-align:center}
        .lnb-sm:hover:not(:disabled){background:rgba(200,162,118,.18);border-color:rgba(200,162,118,.5)}
        .lnb-sm:disabled{opacity:.35;cursor:default}
        .navpanel{flex:1;overflow-y:auto;padding:16px 28px;display:flex;flex-direction:column;gap:8px}
        .lcard{padding:12px 14px;border-radius:10px;background:rgba(210,197,175,.04);border:1px solid rgba(210,197,175,.09);cursor:pointer;transition:all .15s}
        .lcard:hover{background:rgba(210,197,175,.08)} .lcard.cur{border-color:rgba(200,162,118,.4);background:rgba(200,162,118,.07)}
        .lcn{font-size:10px;color:rgba(210,197,175,.28);letter-spacing:1px;margin-bottom:4px}
        .lchead{font-size:14px;color:#c8a276;font-family:'Playfair Display',serif;margin-bottom:3px}
        .lcp{font-size:13px;color:rgba(210,197,175,.55);line-height:1.4}
        .lem{text-align:center;color:rgba(210,197,175,.28);padding:32px;font-size:14px}
        .lsbar{padding:12px 28px;border-bottom:1px solid rgba(210,197,175,.08)}
        .pover{position:fixed;inset:0;z-index:200;background:rgba(0,0,0,.15)}
        .pop{position:fixed;z-index:201;background:#23201a;border:1px solid rgba(210,197,175,.2);border-radius:14px;padding:16px 18px 18px;box-shadow:0 12px 40px rgba(0,0,0,.6);animation:pf .15s ease}
        @keyframes pf{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
        .pcl{position:absolute;top:10px;right:12px;background:none;border:none;color:rgba(210,197,175,.35);font-size:18px;cursor:pointer}
        .pcl:hover{color:rgba(210,197,175,.7)}
        .pw{font-family:'Playfair Display',serif;font-size:22px;color:#c8a276;margin-bottom:2px;padding-right:24px}
        .ppos{font-size:11px;color:rgba(210,197,175,.35);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px}
        .ptr{font-size:18px;color:#d2c5af;margin-bottom:7px}
        .pgr{font-size:13px;color:rgba(135,168,196,.8);margin-bottom:7px;background:rgba(135,168,196,.08);border-radius:8px;padding:5px 10px}
        .pex{font-size:13px;color:rgba(210,197,175,.5);border-top:1px solid rgba(210,197,175,.08);padding-top:7px;line-height:1.5}
        .pext{font-size:12px;color:rgba(210,197,175,.3);margin-top:3px}
        .pload{color:rgba(210,197,175,.4);font-size:14px;text-align:center;padding:14px 0}
        .perr{color:#c87a68;font-size:13px}
        .psave{margin-top:12px;width:100%;border:1px solid rgba(200,162,118,.28);background:rgba(200,162,118,.09);color:#c8a276;padding:10px;border-radius:10px;font-size:14px;cursor:pointer;font-family:'Crimson Pro',serif;transition:background .15s}
        .psave:hover{background:rgba(200,162,118,.2)}
        .yobtn{width:100%;background:rgba(210,197,175,.06);border:1px solid rgba(210,197,175,.15);color:#d2c5af;padding:9px;border-radius:10px;font-size:15px;cursor:pointer;font-family:'Crimson Pro',serif;transition:background .15s;text-align:left;margin-bottom:4px}
        .yobtn:hover{background:rgba(210,197,175,.12)}
        .panel{flex:1;padding:28px;overflow-y:auto;display:flex;flex-direction:column;gap:14px}
        .phdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px}
        .pti{font-family:'Playfair Display',serif;font-size:20px;color:#d2c5af}
        .ab{border:1px solid rgba(200,162,118,.28);background:rgba(200,162,118,.08);color:#c8a276;padding:7px 16px;border-radius:20px;font-size:13px;cursor:pointer;font-family:'Crimson Pro',serif;transition:background .15s}
        .ab:hover{background:rgba(200,162,118,.18)}
        .ab.g{border-color:rgba(128,168,128,.28);background:rgba(128,168,128,.07);color:rgba(128,168,128,.9)} .ab.g:hover{background:rgba(128,168,128,.15)}
        .empty{text-align:center;color:rgba(210,197,175,.3);font-size:15px;padding:48px 0;line-height:1.7}
        .ilist{display:flex;flex-direction:column;gap:8px}
        .icard{background:rgba(210,197,175,.04);border:1px solid rgba(210,197,175,.09);border-radius:12px;padding:13px 16px;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;transition:background .15s}
        .icard:hover{background:rgba(210,197,175,.07)}
        .icont{display:flex;flex-direction:column;gap:3px;flex:1;min-width:0}
        .ipri{font-size:17px;color:#d2c5af;font-family:'Playfair Display',serif}
        .ipos{font-size:11px;color:rgba(200,162,118,.7);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:1px}
        .isec{font-size:14px;color:rgba(210,197,175,.75)}
        .igr{font-size:12px;color:rgba(135,168,196,.7);background:rgba(135,168,196,.06);border-radius:6px;padding:3px 8px;align-self:flex-start;margin-top:3px}
        .iex{font-size:13px;color:rgba(210,197,175,.5);font-style:italic;margin-top:6px;padding-top:6px;border-top:1px solid rgba(210,197,175,.06);line-height:1.5}
        .iext{font-style:normal;font-size:12px;color:rgba(210,197,175,.35);margin-top:2px}
        .rmb{background:rgba(157,70,48,.1);border:1px solid rgba(157,70,48,.25);color:rgba(200,128,112,.75);font-size:18px;cursor:pointer;padding:0;width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:all .15s}
        .rmb:hover{background:rgba(157,70,48,.3);border-color:rgba(157,70,48,.5);color:#fff}
        .mover{position:fixed;inset:0;background:rgba(26,22,17,.85);z-index:100;display:flex;align-items:center;justify-content:center;padding:24px}
        .modal{background:#1f1c16;border:1px solid rgba(210,197,175,.14);border-radius:16px;padding:28px;width:100%;max-width:480px;display:flex;flex-direction:column;gap:16px}
        .mti{font-family:'Playfair Display',serif;font-size:22px;color:#d2c5af}
        .mact{display:flex;gap:10px;justify-content:flex-end;margin-top:4px}
        .mcanc{background:none;border:1px solid rgba(210,197,175,.18);color:rgba(210,197,175,.55);padding:10px 20px;border-radius:10px;font-size:15px;cursor:pointer;font-family:'Crimson Pro',serif;transition:all .15s}
        .mcanc:hover{color:#d2c5af;border-color:rgba(210,197,175,.35)}
        .mconf{background:linear-gradient(135deg,#9d4630,#82362a);color:#fff;border:none;padding:10px 20px;border-radius:10px;font-size:15px;cursor:pointer;font-family:'Crimson Pro',serif;transition:opacity .15s}
        .mconf:hover{opacity:.85} .mconf.g{background:linear-gradient(135deg,#5a8556,#4a6845)}

        /* First-visit landing screen */
        .land{position:fixed;inset:0;z-index:9999;background:#1a1611;display:flex;align-items:flex-start;justify-content:center;padding:32px 32px 60px;overflow-y:auto}
        .land::before{content:'';position:fixed;inset:0;pointer-events:none;background:radial-gradient(ellipse at 20% 10%,rgba(150,80,60,.10) 0%,transparent 55%),radial-gradient(ellipse at 80% 90%,rgba(80,90,130,.08) 0%,transparent 55%)}
        .land-card{position:relative;max-width:580px;width:100%;text-align:center;display:flex;flex-direction:column;gap:28px;align-items:center;padding:24px}
        .land-icon{font-size:56px;margin-bottom:-4px}
        .land-title{font-family:'Playfair Display',serif;font-size:54px;font-weight:700;color:#c8a276;letter-spacing:-1px;line-height:1}
        .land-sub{font-size:12px;letter-spacing:3px;text-transform:uppercase;color:rgba(210,197,175,.45);margin-top:-12px}
        .land-tagline{font-family:'Crimson Pro',serif;font-style:italic;font-size:18px;color:rgba(210,197,175,.75);max-width:440px;line-height:1.5}
        .land-tips{background:rgba(200,162,118,.06);border:1px solid rgba(200,162,118,.18);border-radius:14px;padding:22px 26px;text-align:left;width:100%;max-width:440px;display:flex;flex-direction:column;gap:14px;margin-top:8px}
        .land-features{background:rgba(80,120,90,.04);border:1px solid rgba(120,160,130,.16);border-radius:14px;padding:22px 26px;text-align:left;width:100%;max-width:440px;display:flex;flex-direction:column;gap:12px;margin-top:8px}
        .land-features-title{font-family:'Playfair Display',serif;font-size:14px;color:#a8c2a8;letter-spacing:2px;text-transform:uppercase;text-align:center;margin-bottom:4px}
        .land-feat{display:flex;gap:12px;align-items:flex-start;font-size:14px;line-height:1.5;color:#d2c5af}
        .land-feat-icon{flex-shrink:0;font-size:18px;line-height:1.4;width:26px;text-align:center}
        .land-feat strong{color:#c8a276;font-weight:600}
        .land-tips-title{font-family:'Playfair Display',serif;font-size:14px;color:#c8a276;letter-spacing:2px;text-transform:uppercase;text-align:center;margin-bottom:4px}
        .land-tip{display:flex;gap:12px;align-items:flex-start;font-size:15px;line-height:1.5;color:#d2c5af}
        .land-tip-num{flex-shrink:0;width:24px;height:24px;border-radius:50%;background:rgba(200,162,118,.15);border:1px solid rgba(200,162,118,.3);color:#c8a276;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;margin-top:1px}
        .land-tip strong{color:#c8a276;font-weight:600}
        .land-begin{background:linear-gradient(135deg,#9d4630,#82362a);color:#fff;border:none;padding:16px 48px;border-radius:12px;font-size:18px;font-family:'Crimson Pro',serif;cursor:pointer;transition:opacity .15s,transform .1s;letter-spacing:1px;margin-top:8px;box-shadow:0 6px 20px rgba(0,0,0,.3)}
        .land-begin:hover{opacity:.92;transform:translateY(-1px)}
        .land-begin:active{transform:translateY(0)}
        @media (max-width:520px){
          .land-title{font-size:42px}
          .land-tagline{font-size:16px}
          .land-tips,.land-features{padding:18px 20px}
          .land-tip{font-size:14px}
          .land-feat{font-size:13px}
        }

        /* Sign-in / sign-out auth UI */
        .auth-page{min-height:100vh;background:#1a1611;display:flex;align-items:center;justify-content:center;padding:32px;position:relative}
        .auth-page::before{content:'';position:fixed;inset:0;pointer-events:none;background:radial-gradient(ellipse at 20% 10%,rgba(150,80,60,.10) 0%,transparent 55%),radial-gradient(ellipse at 80% 90%,rgba(80,90,130,.08) 0%,transparent 55%)}
        .auth-card{position:relative;display:flex;flex-direction:column;align-items:center;gap:20px;max-width:440px;width:100%}
        .auth-brand{text-align:center;margin-bottom:8px}
        .auth-brand-icon{font-size:44px}
        .auth-brand-title{font-family:'Playfair Display',serif;font-size:42px;font-weight:700;color:#c8a276;line-height:1;margin-top:8px}
        .auth-brand-sub{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:rgba(210,197,175,.45);margin-top:6px}
        .userbtn-wrap{display:flex;align-items:center}

        /* Pending-approval screen */
        .pending{min-height:100vh;background:#1a1611;display:flex;align-items:center;justify-content:center;padding:32px;position:relative}
        .pending::before{content:'';position:fixed;inset:0;pointer-events:none;background:radial-gradient(ellipse at 20% 10%,rgba(150,80,60,.10) 0%,transparent 55%),radial-gradient(ellipse at 80% 90%,rgba(80,90,130,.08) 0%,transparent 55%)}
        .pending-card{position:relative;max-width:480px;text-align:center;display:flex;flex-direction:column;gap:20px;align-items:center}
        .pending-icon{font-size:56px}
        .pending-title{font-family:'Playfair Display',serif;font-size:32px;color:#c8a276;line-height:1.2}
        .pending-msg{font-size:16px;line-height:1.6;color:rgba(210,197,175,.78);max-width:400px}
        .pending-email{font-size:13px;color:rgba(210,197,175,.5);background:rgba(200,162,118,.08);padding:8px 16px;border-radius:8px;border:1px solid rgba(200,162,118,.2)}
        .pending-userbtn{margin-top:8px}

        /* Admin panel overlay */
        .adm-over{position:fixed;inset:0;background:rgba(26,22,17,.92);z-index:200;display:flex;align-items:flex-start;justify-content:center;padding:24px;overflow-y:auto}
        .adm-modal{background:#1f1c16;border:1px solid rgba(210,197,175,.14);border-radius:16px;width:100%;max-width:760px;display:flex;flex-direction:column;gap:0;margin:32px 0}

        /* Forum styles */
        .forum-modal{max-width:680px;max-height:88vh}
        .forum-back{background:none;border:none;color:#c8a276;font-size:22px;cursor:pointer;padding:0 8px 0 0;line-height:1}
        .forum-thr-title{font-size:16px;color:#d2c5af;font-weight:normal}
        .forum-list{display:flex;flex-direction:column;gap:8px;padding:14px 18px}
        .forum-thread-card{padding:12px 14px;border:1px solid rgba(210,197,175,.1);border-radius:10px;background:rgba(210,197,175,.04);cursor:pointer;transition:all .15s}
        .forum-thread-card:hover{background:rgba(210,197,175,.08);border-color:rgba(200,162,118,.3)}
        .forum-thread-title{font-family:'Crimson Pro',serif;color:#d2c5af;font-size:16px;margin-bottom:4px}
        .forum-thread-meta{font-family:'Crimson Pro',serif;color:rgba(210,197,175,.5);font-size:12px;display:flex;gap:6px;align-items:center;flex-wrap:wrap}
        .forum-compose{padding:18px;display:flex;flex-direction:column;gap:10px}
        .forum-compose input,.forum-compose textarea{background:rgba(210,197,175,.06);border:1px solid rgba(210,197,175,.16);border-radius:8px;padding:10px 12px;font-family:'Crimson Pro',serif;color:#d2c5af;font-size:14px;outline:none}
        .forum-compose input:focus,.forum-compose textarea:focus{border-color:rgba(200,162,118,.5);background:rgba(210,197,175,.08)}
        .forum-compose textarea{resize:vertical;min-height:120px;line-height:1.5}
        .forum-compose-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:4px}
        .forum-thread-body{display:flex;flex-direction:column;gap:10px;padding:14px 18px;overflow-y:auto}
        .forum-post{background:rgba(210,197,175,.04);border:1px solid rgba(210,197,175,.1);border-radius:10px;padding:10px 14px;max-width:85%;align-self:flex-start}
        .forum-post.mine{align-self:flex-end;background:rgba(200,162,118,.1);border-color:rgba(200,162,118,.28)}
        .forum-post-head{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:4px}
        .forum-post-author{font-family:'Crimson Pro',serif;font-size:12px;color:#c8a276;letter-spacing:.5px}
        .forum-post-ts{font-family:'Crimson Pro',serif;font-size:11px;color:rgba(210,197,175,.4);font-style:italic}
        .forum-post-body{font-family:'Crimson Pro',serif;color:#d2c5af;font-size:14px;line-height:1.5;white-space:pre-wrap;word-break:break-word}
        .forum-reply{display:flex;gap:8px;padding:10px 14px;border-top:1px solid rgba(210,197,175,.08);align-items:flex-end}
        .forum-reply textarea{flex:1;background:rgba(210,197,175,.04);border:1px solid rgba(210,197,175,.14);border-radius:8px;padding:8px 12px;font-family:'Crimson Pro',serif;color:#d2c5af;font-size:14px;resize:none;min-height:36px;max-height:120px;outline:none;line-height:1.4}
        .forum-reply textarea:focus{border-color:rgba(200,162,118,.4)}

        /* Feedback styles */
        .feedback-modal{max-width:520px}
        .feedback-body{padding:16px 20px;display:flex;flex-direction:column;gap:10px}
        .feedback-help{font-family:'Crimson Pro',serif;color:rgba(210,197,175,.6);font-size:13px;margin:0;font-style:italic}
        .feedback-body textarea{background:rgba(210,197,175,.06);border:1px solid rgba(210,197,175,.16);border-radius:8px;padding:10px 12px;font-family:'Crimson Pro',serif;color:#d2c5af;font-size:14px;outline:none;resize:vertical;min-height:140px;line-height:1.5}
        .feedback-body textarea:focus{border-color:rgba(200,162,118,.5);background:rgba(210,197,175,.08)}
        .feedback-msg{font-family:'Crimson Pro',serif;font-size:13px;padding:6px 0}
        .feedback-msg.ok{color:#a8c2a8}
        .feedback-msg.err{color:#d97a6b}

        @media (max-width:560px){
          .forum-modal,.feedback-modal{max-width:100%;height:100vh;max-height:100vh;border-radius:0;margin:0}
          .forum-post{max-width:100%}
        }
        .adm-head{padding:22px 28px 18px;border-bottom:1px solid rgba(210,197,175,.1);display:flex;align-items:center;justify-content:space-between;gap:16px}
        .adm-title{font-family:'Playfair Display',serif;font-size:24px;color:#c8a276}
        .adm-x{background:none;border:none;color:rgba(210,197,175,.6);font-size:24px;cursor:pointer;padding:0;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:8px;transition:all .15s}
        .adm-x:hover{background:rgba(210,197,175,.08);color:#d2c5af}
        .adm-body{padding:20px 28px;display:flex;flex-direction:column;gap:12px;max-height:65vh;overflow-y:auto}
        .adm-empty{text-align:center;padding:32px;color:rgba(210,197,175,.5);font-style:italic}
        .adm-row{display:flex;align-items:center;gap:14px;padding:14px 16px;background:#23201a;border:1px solid rgba(210,197,175,.08);border-radius:12px}
        .adm-avatar{width:40px;height:40px;border-radius:50%;background:#1a1611 center/cover no-repeat;flex-shrink:0;border:1px solid rgba(210,197,175,.15)}
        .adm-info{flex:1;min-width:0}
        .adm-name{font-size:15px;color:#d2c5af;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .adm-email{font-size:13px;color:rgba(210,197,175,.55);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .adm-status{font-size:11px;letter-spacing:1px;text-transform:uppercase;padding:3px 10px;border-radius:6px;flex-shrink:0}
        .adm-status.approved{background:rgba(90,133,86,.18);color:#9ec896;border:1px solid rgba(90,133,86,.3)}
        .adm-status.rejected{background:rgba(157,70,48,.18);color:#c87a68;border:1px solid rgba(157,70,48,.3)}
        .adm-status.pending{background:rgba(200,162,118,.12);color:#c8a276;border:1px solid rgba(200,162,118,.25)}
        .adm-status.admin{background:rgba(135,168,196,.15);color:#a3c0d8;border:1px solid rgba(135,168,196,.3)}
        .adm-actions{display:flex;gap:8px;flex-shrink:0}
        .adm-btn{padding:7px 14px;border:none;border-radius:8px;font-size:13px;font-family:'Crimson Pro',serif;cursor:pointer;transition:opacity .15s;font-weight:600}
        .adm-btn:disabled{opacity:.5;cursor:wait}
        .adm-btn.approve{background:linear-gradient(135deg,#5a8556,#4a6845);color:#fff}
        .adm-btn.reject{background:rgba(157,70,48,.15);border:1px solid rgba(157,70,48,.4);color:#c87a68}
        .adm-btn.reject:hover:not(:disabled){background:rgba(157,70,48,.3)}
        .adm-err{margin:0 28px 16px;padding:12px 16px;background:rgba(157,70,48,.18);border:1px solid rgba(157,70,48,.35);color:#c87a68;border-radius:10px;font-size:13px}
        .adm-foot{padding:16px 28px;border-top:1px solid rgba(210,197,175,.08);display:flex;justify-content:space-between;align-items:center}
        .adm-refresh{background:none;border:1px solid rgba(210,197,175,.18);color:rgba(210,197,175,.7);padding:8px 16px;border-radius:8px;font-size:13px;cursor:pointer;font-family:'Crimson Pro',serif}
        .adm-refresh:hover{color:#d2c5af;border-color:rgba(210,197,175,.4)}
        .adm-trigger{background:rgba(135,168,196,.12);border:1px solid rgba(135,168,196,.3);color:#a3c0d8;padding:6px 12px;border-radius:8px;font-size:12px;cursor:pointer;font-family:'Crimson Pro',serif;display:flex;align-items:center;gap:6px}
        .adm-trigger:hover{background:rgba(135,168,196,.2)}
        @media (max-width:520px){
          .adm-row{flex-wrap:wrap}
          .adm-actions{width:100%;justify-content:flex-end}
        }
      `}</style>

      {/* Sign-in screen: shown to anyone not signed in. AI features require login,
          so there's no "Read without AI" bypass here anymore — everyone signs in. */}
      {!auth.isSignedIn && (
        <div className="auth-page">
          <div className="auth-card">
            <div className="auth-brand">
              <div className="auth-brand-icon" style={{color:"#c8a276"}}><Pushkin size={56}/></div>
              <div className="auth-brand-title">Говорим</div>
              <div className="auth-brand-sub">Russian Practice</div>
            </div>
            <SignIn routing="hash" />
            <div style={{fontSize:12,color:"rgba(210,197,175,.4)",textAlign:"center",maxWidth:400,lineHeight:1.5,marginTop:8}}>
              Russian reading + AI tutor. Approval required after sign-up.
            </div>
          </div>
        </div>
      )}

      {/* Main app: shown only when signed in. */}
      {auth.isSignedIn && (
        <>
      {pendingApproval ? (
        <div className="pending">
          <div className="pending-card">
            <div className="pending-icon">⏳</div>
            <div className="pending-title">Waiting for approval</div>
            <div className="pending-msg">
              Thanks for signing up! Your account is pending approval. You'll receive an email at the address below once you've been approved — usually within a day.
            </div>
            <div className="pending-email">{currentEmail}</div>
            <div className="pending-userbtn"><UserButton afterSignOutUrl="/" /></div>
          </div>
        </div>
      ) : (
      <>
      {/* ── Forum overlay ─────────────────────────────────────────────── */}
      {forumOpen && (
        <div className="adm-over" onClick={function(e){ if (e.target.className === "adm-over") setForumOpen(false); }}>
          <div className="adm-modal forum-modal">
            <div className="adm-head">
              <div className="adm-title">
                {forumThread ? (
                  <button className="forum-back" onClick={function(){ setForumThread(null); loadForumThreads(); }}>←</button>
                ) : (
                  <span>📝 Forum</span>
                )}
                {forumThread && <span className="forum-thr-title">{forumThread.title}</span>}
              </div>
              <button className="adm-x" onClick={function(){ setForumOpen(false); setForumThread(null); setForumComposing(false); }}>×</button>
            </div>
            {forumErr && <div className="adm-err">{forumErr}</div>}

            {/* New-thread compose form */}
            {forumComposing && !forumThread && (
              <div className="forum-compose">
                <input type="text" placeholder="Title" maxLength={80} value={newTitle}
                  onChange={function(e){ setNewTitle(e.target.value); }} />
                <textarea placeholder="What's on your mind?" maxLength={1000} value={newBody}
                  onChange={function(e){ setNewBody(e.target.value); }} />
                <div className="forum-compose-actions">
                  <button className="adm-btn" onClick={function(){ setForumComposing(false); setNewTitle(""); setNewBody(""); }}>Cancel</button>
                  <button className="adm-btn approve" onClick={submitNewThread} disabled={forumBusy || !newTitle.trim() || !newBody.trim()}>
                    {forumBusy ? "Posting…" : "Post thread"}
                  </button>
                </div>
              </div>
            )}

            {/* Thread list */}
            {!forumThread && !forumComposing && (
              <div className="adm-body forum-list">
                {forumLoading && <div className="adm-empty">Loading…</div>}
                {!forumLoading && forumThreads.length === 0 && <div className="adm-empty">No threads yet. Start one!</div>}
                {!forumLoading && forumThreads.map(function(t){
                  return (
                    <div key={t.tid} className="forum-thread-card" onClick={function(){ loadForumThread(t.tid); }}>
                      <div className="forum-thread-title">{t.title}</div>
                      <div className="forum-thread-meta">
                        <span>{t.author.name}</span>
                        <span>·</span>
                        <span>{formatForumTs(t.lastTs || t.ts)}</span>
                        <span>·</span>
                        <span>{t.replies === 0 ? "no replies" : (t.replies + " " + (t.replies === 1 ? "reply" : "replies"))}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Single thread view */}
            {forumThread && (
              <>
                <div className="adm-body forum-thread-body" ref={forumListRef}>
                  {(forumThread.posts || []).map(function(p, i){
                    var isMine = p.author && p.author.id === user.id;
                    return (
                      <div key={i} className={"forum-post" + (isMine ? " mine" : "")}>
                        <div className="forum-post-head">
                          <span className="forum-post-author">{p.author && p.author.name}</span>
                          <span className="forum-post-ts">{formatForumTs(p.ts)}</span>
                        </div>
                        <div className="forum-post-body">{p.body}</div>
                      </div>
                    );
                  })}
                </div>
                <div className="forum-reply">
                  <textarea placeholder="Write a reply…" maxLength={1000} value={replyBody}
                    onChange={function(e){ setReplyBody(e.target.value); }}
                    onKeyDown={function(e){ if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submitReply(); } }} />
                  <button className="adm-btn approve" onClick={submitReply} disabled={forumBusy || !replyBody.trim()}>
                    {forumBusy ? "…" : "Reply"}
                  </button>
                </div>
              </>
            )}

            {/* Footer: "New thread" CTA when on the list */}
            {!forumThread && !forumComposing && (
              <div className="adm-foot">
                <button className="adm-btn approve" onClick={function(){ setForumComposing(true); setForumErr(""); }}>+ New thread</button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Feedback modal ────────────────────────────────────────────── */}
      {feedbackOpen && (
        <div className="adm-over" onClick={function(e){ if (e.target.className === "adm-over") { setFeedbackOpen(false); setFeedbackMsg(""); } }}>
          <div className="adm-modal feedback-modal">
            <div className="adm-head">
              <div className="adm-title">💬 Send feedback</div>
              <button className="adm-x" onClick={function(){ setFeedbackOpen(false); setFeedbackMsg(""); }}>×</button>
            </div>
            <div className="feedback-body">
              <p className="feedback-help">This goes straight to my email. Bugs, suggestions, requests — anything.</p>
              <textarea placeholder="What's up?" maxLength={2000} value={feedbackBody}
                onChange={function(e){ setFeedbackBody(e.target.value); }} />
              {feedbackMsg && <div className={"feedback-msg" + (/thanks/i.test(feedbackMsg) ? " ok" : " err")}>{feedbackMsg}</div>}
            </div>
            <div className="adm-foot">
              <button className="adm-btn" onClick={function(){ setFeedbackOpen(false); setFeedbackBody(""); setFeedbackMsg(""); }}>Cancel</button>
              <button className="adm-btn approve" onClick={submitFeedback} disabled={feedbackBusy || !feedbackBody.trim()}>
                {feedbackBusy ? "Sending…" : "Send"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showAdmin && isAdmin && (
        <div className="adm-over" onClick={function(e){ if (e.target.className === "adm-over") setShowAdmin(false); }}>
          <div className="adm-modal">
            <div className="adm-head">
              <div className="adm-title">👥 Manage Users</div>
              <button className="adm-x" onClick={function(){ setShowAdmin(false); }}>×</button>
            </div>
            {adminErr && <div className="adm-err">{adminErr}</div>}
            <div className="adm-body">
              {adminLoad && <div className="adm-empty">Loading users…</div>}
              {!adminLoad && adminUsers.length === 0 && <div className="adm-empty">No users yet.</div>}
              {!adminLoad && adminUsers.map(function(u){
                var status = u.isAdmin ? "admin" : (u.approved ? "approved" : (u.rejected ? "rejected" : "pending"));
                var label  = u.isAdmin ? "Admin" : (u.approved ? "Approved" : (u.rejected ? "Rejected" : "Pending"));
                var name   = (u.firstName + " " + u.lastName).trim() || u.email || "(no name)";
                var busy   = adminBusy[u.id];
                return (
                  <div key={u.id} className="adm-row">
                    <div className="adm-avatar" style={{backgroundImage:u.imageUrl?'url("'+u.imageUrl+'")':'none'}}/>
                    <div className="adm-info">
                      <div className="adm-name">{name}</div>
                      <div className="adm-email">{u.email}</div>
                    </div>
                    <div className={"adm-status "+status}>{label}</div>
                    {!u.isAdmin && (
                      <div className="adm-actions">
                        {!u.approved && (
                          <button className="adm-btn approve" disabled={!!busy} onClick={function(){ actOnUser(u.id, "approve"); }}>
                            {busy === "approve" ? "…" : "Approve"}
                          </button>
                        )}
                        {!u.rejected && u.approved && (
                          <button className="adm-btn reject" disabled={!!busy} onClick={function(){ actOnUser(u.id, "reject"); }}>
                            {busy === "reject" ? "…" : "Revoke"}
                          </button>
                        )}
                        {!u.approved && !u.rejected && (
                          <button className="adm-btn reject" disabled={!!busy} onClick={function(){ actOnUser(u.id, "reject"); }}>
                            {busy === "reject" ? "…" : "Reject"}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="adm-foot">
              <span style={{fontSize:12,color:"rgba(210,197,175,.5)"}}>{adminUsers.length} {adminUsers.length === 1 ? "user" : "users"}</span>
              <button className="adm-refresh" onClick={loadAdminUsers} disabled={adminLoad}>Refresh</button>
            </div>
          </div>
        </div>
      )}
      {showUpload && isAdmin && (
        <div className="adm-over" onClick={function(e){ if (e.target.className === "adm-over") setShowUpload(false); }}>
          <div className="adm-modal" style={{maxWidth:640}}>
            <div className="adm-head">
              <div className="adm-title">📤 Upload</div>
              <button className="adm-x" onClick={function(){ setShowUpload(false); }}>×</button>
            </div>
            <div className="adm-body" style={{padding:20,display:"flex",flexDirection:"column",gap:14}}>
              {/* Mode tabs */}
              <div style={{display:"flex",gap:0,borderBottom:"1px solid rgba(210,197,175,.15)"}}>
                <button onClick={function(){ setUpMode("song"); setUpErr(""); setUpMsg(""); }}
                  style={{flex:1,padding:"10px 14px",background:upMode==="song"?"rgba(200,162,118,.12)":"transparent",color:upMode==="song"?"#c8a276":"rgba(210,197,175,.6)",border:"none",borderBottom:upMode==="song"?"2px solid #c8a276":"2px solid transparent",cursor:"pointer",fontFamily:"'Crimson Pro',serif",fontSize:14,fontWeight:upMode==="song"?600:400}}>
                  🎵 Song (paste lyrics)
                </button>
                <button onClick={function(){ setUpMode("book"); setUpErr(""); setUpMsg(""); }}
                  style={{flex:1,padding:"10px 14px",background:upMode==="book"?"rgba(200,162,118,.12)":"transparent",color:upMode==="book"?"#c8a276":"rgba(210,197,175,.6)",border:"none",borderBottom:upMode==="book"?"2px solid #c8a276":"2px solid transparent",cursor:"pointer",fontFamily:"'Crimson Pro',serif",fontSize:14,fontWeight:upMode==="book"?600:400}}>
                  📚 Book (upload file)
                </button>
              </div>

              {upMode === "song" && (
                <div style={{fontSize:12,opacity:.6,lineHeight:1.5}}>
                  Pasted lyrics get appended to a per-artist file under <code style={{background:"rgba(0,0,0,.3)",padding:"1px 5px",borderRadius:3}}>public/books/lyrics/&lt;artist&gt;.txt</code>.
                  Vercel redeploys after each upload — your new song appears in the picker in ~1-2 min.
                </div>
              )}
              {upMode === "book" && (
                <div style={{fontSize:12,opacity:.6,lineHeight:1.5}}>
                  Upload an EPUB, FB2, TXT, or HTML file. Max 20MB. The file gets committed to <code style={{background:"rgba(0,0,0,.3)",padding:"1px 5px",borderRadius:3}}>public/books/&lt;category&gt;/</code> and added to the manifest.
                </div>
              )}

              {upErr && <div className="adm-err">{upErr}</div>}
              {upMsg && (
                <div style={{padding:"8px 12px",background:"rgba(138,171,124,.15)",border:"1px solid rgba(138,171,124,.4)",borderRadius:4,color:"#a8c89a",fontSize:13}}>
                  ✓ {upMsg}
                </div>
              )}

              {upMode === "song" && (
                <>
                  <div>
                    <label style={{display:"block",marginBottom:5,fontSize:13,opacity:.75,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Artist</label>
                    <input type="text" value={upArtist} onChange={function(e){ setUpArtist(e.target.value); }}
                      placeholder="e.g. Виктор Цой"
                      disabled={upBusy}
                      style={{width:"100%",padding:"9px 12px",background:"rgba(0,0,0,.3)",border:"1px solid rgba(210,197,175,.2)",color:"#d2c5af",borderRadius:4,fontSize:14,fontFamily:"inherit",boxSizing:"border-box"}}/>
                  </div>
                  <div>
                    <label style={{display:"block",marginBottom:5,fontSize:13,opacity:.75,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Song title</label>
                    <input type="text" value={upTitle} onChange={function(e){ setUpTitle(e.target.value); }}
                      placeholder="e.g. Группа крови"
                      disabled={upBusy}
                      style={{width:"100%",padding:"9px 12px",background:"rgba(0,0,0,.3)",border:"1px solid rgba(210,197,175,.2)",color:"#d2c5af",borderRadius:4,fontSize:14,fontFamily:"inherit",boxSizing:"border-box"}}/>
                  </div>
                  <div>
                    <label style={{display:"block",marginBottom:5,fontSize:13,opacity:.75,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Lyrics (Russian)</label>
                    <textarea value={upLyrics} onChange={function(e){ setUpLyrics(e.target.value); }}
                      placeholder="Paste the song lyrics here..."
                      rows={12}
                      disabled={upBusy}
                      style={{width:"100%",padding:"9px 12px",background:"rgba(0,0,0,.3)",border:"1px solid rgba(210,197,175,.2)",color:"#d2c5af",borderRadius:4,fontSize:14,fontFamily:"inherit",resize:"vertical",lineHeight:1.55,boxSizing:"border-box"}}/>
                    <div style={{fontSize:11,opacity:.45,marginTop:4,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>
                      {upLyrics.length} chars · {(upLyrics.match(/[а-яёА-ЯЁ]/g) || []).length} Cyrillic letters
                    </div>
                  </div>
                  <div style={{display:"flex",gap:10,alignItems:"center",marginTop:4}}>
                    <button onClick={uploadSong} disabled={upBusy || !upArtist.trim() || !upTitle.trim() || upLyrics.trim().length < 20}
                      style={{padding:"10px 22px",background:"#c8a276",color:"#1a1612",border:"none",borderRadius:4,fontWeight:600,fontSize:14,cursor:upBusy?"wait":"pointer",opacity:(upBusy || !upArtist.trim() || !upTitle.trim() || upLyrics.trim().length < 20)?.5:1,fontFamily:"'Crimson Pro',serif"}}>
                      {upBusy ? "Uploading..." : "Upload song"}
                    </button>
                    <button onClick={function(){ setUpTitle(""); setUpLyrics(""); setUpMsg(""); setUpErr(""); }} disabled={upBusy}
                      style={{padding:"10px 16px",background:"transparent",color:"#d2c5af",border:"1px solid rgba(210,197,175,.25)",borderRadius:4,fontSize:13,cursor:"pointer",fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>
                      Clear song
                    </button>
                  </div>
                </>
              )}

              {upMode === "book" && (
                <>
                  <div>
                    <label style={{display:"block",marginBottom:5,fontSize:13,opacity:.75,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Book file</label>
                    <input type="file" accept=".epub,.fb2,.txt,.html,.htm,.xhtml"
                      onChange={function(e){
                        var f = e.target.files && e.target.files[0];
                        setUpBookFile(f || null);
                        // Auto-fill title from filename if empty
                        if (f && !upTitle.trim()) {
                          var stem = f.name.replace(/\.[^.]+$/, "").replace(/[_-]/g, " ");
                          setUpTitle(stem);
                        }
                      }}
                      disabled={upBusy}
                      style={{width:"100%",padding:"9px 12px",background:"rgba(0,0,0,.3)",border:"1px solid rgba(210,197,175,.2)",color:"#d2c5af",borderRadius:4,fontSize:14,fontFamily:"inherit",boxSizing:"border-box"}}/>
                    {upBookFile && (
                      <div style={{fontSize:11,opacity:.55,marginTop:4,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>
                        {upBookFile.name} · {Math.round(upBookFile.size / 1024)} KB
                      </div>
                    )}
                  </div>
                  <div>
                    <label style={{display:"block",marginBottom:5,fontSize:13,opacity:.75,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Title</label>
                    <input type="text" value={upTitle} onChange={function(e){ setUpTitle(e.target.value); }}
                      placeholder="e.g. Анна Каренина"
                      disabled={upBusy}
                      style={{width:"100%",padding:"9px 12px",background:"rgba(0,0,0,.3)",border:"1px solid rgba(210,197,175,.2)",color:"#d2c5af",borderRadius:4,fontSize:14,fontFamily:"inherit",boxSizing:"border-box"}}/>
                  </div>
                  <div>
                    <label style={{display:"block",marginBottom:5,fontSize:13,opacity:.75,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Author <span style={{opacity:.5}}>(optional)</span></label>
                    <input type="text" value={upBookAuthor} onChange={function(e){ setUpBookAuthor(e.target.value); }}
                      placeholder="e.g. Лев Толстой"
                      disabled={upBusy}
                      style={{width:"100%",padding:"9px 12px",background:"rgba(0,0,0,.3)",border:"1px solid rgba(210,197,175,.2)",color:"#d2c5af",borderRadius:4,fontSize:14,fontFamily:"inherit",boxSizing:"border-box"}}/>
                  </div>
                  <div>
                    <label style={{display:"block",marginBottom:5,fontSize:13,opacity:.75,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Category</label>
                    <select value={upBookCategory} onChange={function(e){ setUpBookCategory(e.target.value); }} disabled={upBusy}
                      style={{width:"100%",padding:"9px 12px",background:"rgba(0,0,0,.3)",border:"1px solid rgba(210,197,175,.2)",color:"#d2c5af",borderRadius:4,fontSize:14,fontFamily:"inherit",boxSizing:"border-box"}}>
                      <option value="Novel">Novel</option>
                      <option value="Plays">Plays</option>
                      <option value="Short Stories">Short Stories</option>
                      <option value="Poetry">Poetry</option>
                    </select>
                  </div>
                  <div style={{display:"flex",gap:10,alignItems:"center",marginTop:4}}>
                    <button onClick={uploadBook} disabled={upBusy || !upBookFile || !upTitle.trim()}
                      style={{padding:"10px 22px",background:"#c8a276",color:"#1a1612",border:"none",borderRadius:4,fontWeight:600,fontSize:14,cursor:upBusy?"wait":"pointer",opacity:(upBusy || !upBookFile || !upTitle.trim())?.5:1,fontFamily:"'Crimson Pro',serif"}}>
                      {upBusy ? "Uploading..." : "Upload book"}
                    </button>
                    <button onClick={function(){ setUpBookFile(null); setUpTitle(""); setUpBookAuthor(""); setUpMsg(""); setUpErr(""); }} disabled={upBusy}
                      style={{padding:"10px 16px",background:"transparent",color:"#d2c5af",border:"1px solid rgba(210,197,175,.25)",borderRadius:4,fontSize:13,cursor:"pointer",fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>
                      Clear
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
      {!seenLanding && (
        <div className="land">
          <div className="land-card">
            <div className="land-icon" style={{color:"#c8a276"}}><Pushkin size={68}/></div>
            <div>
              <div className="land-title">Говорим</div>
              <div className="land-sub">Russian Practice</div>
            </div>
            <div className="land-tagline">
              Read, listen, and converse in Russian — with an AI tutor that adapts to your level.
            </div>

            <div className="land-features">
              <div className="land-features-title">What you can do</div>
              <div className="land-feat"><span className="land-feat-icon">💬</span><div><strong>Chat</strong> — Pick a topic, hear interesting facts, answer probing questions in Russian.</div></div>
              <div className="land-feat"><span className="land-feat-icon">📖</span><div><strong>Read</strong> — Load any EPUB, FB2, TXT, or HTML book. Get chapter-by-chapter comprehension questions.</div></div>
              <div className="land-feat"><span className="land-feat-icon">🔊</span><div><strong>Listen</strong> — Word-by-word TTS using natural Russian voices, with synchronized highlighting.</div></div>
              <div className="land-feat"><span className="land-feat-icon">✏️</span><div><strong>Define</strong> — Tap any Russian word for translation, lemma, aspect pairs, and example sentences.</div></div>
              <div className="land-feat"><span className="land-feat-icon">📚</span><div><strong>Build a library</strong> — Save vocab and grammar tips; they sync across all your devices.</div></div>
              <div className="land-feat"><span className="land-feat-icon">🎭</span><div><strong>Plays formatted nicely</strong> — Character names highlighted, dialogue cleanly separated.</div></div>
            </div>

            <div className="land-tips">
              <div className="land-tips-title">For the best experience</div>
              <div className="land-tip">
                <span className="land-tip-num">1</span>
                <span>Open the app in <strong>Google Chrome</strong> on a computer or Android. Chrome ships with high-quality Russian voices built in.<br/><span style={{opacity:.7,fontStyle:"italic",fontSize:13}}>On iPhone, use Safari with Russian Premium voices downloaded under Settings → Accessibility → Spoken Content → Voices.</span></span>
              </div>
              <div className="land-tip">
                <span className="land-tip-num">2</span>
                <span>On any Russian text, tap <strong>🎙 Voice</strong>. In the picker, choose <strong>Google русский</strong> — it's the most natural-sounding option in Chrome and the one we recommend.</span>
              </div>
              <div className="land-tip">
                <span className="land-tip-num">3</span>
                <span>If you don't see <strong>Google русский</strong> listed, pick any voice marked <strong>★ neural</strong> or <strong>✓ local</strong> — those are the next best options.</span>
              </div>
            </div>

            <button className="land-begin" onClick={dismissLanding}>Begin →</button>
          </div>
        </div>
      )}

      <div className="app">
        <header className="hdr">
          <div
            className="logo"
            role="button"
            tabIndex={0}
            title="Back to home"
            onClick={function(){
              // Reset all the state that defines "where you are" so the user
              // lands on the home screen (the chat/read/grammar mode picker).
              // We do NOT clear `chapters` — if the user was reading a book,
              // they can pick "Read" again and resume where they left off.
              setMode("");
              setStarted(false);
              setMsgs([]);
              setGramTopicId("");
              setGramLevel("");
              setGramSearch("");
              setShowVP(false);
              setTab("chat");
              stopTTS();
            }}
            onKeyDown={function(e){ if (e.key === "Enter" || e.key === " ") { e.currentTarget.click(); } }}
            style={{cursor:"pointer"}}>
            <span className="lru">Говорим</span><span className="lsub">Russian Practice</span>
          </div>
          <div style={{display:"flex",alignItems:"center",gap:12}}>
            <div className="level-wrap" title="Russian proficiency level. Adapts AI questions to your skill. Changes apply immediately to chat and reading-mode analysis.">
              <span className="level-lbl">Level</span>
              <select className="level-pill" value={level} onChange={function(e){ setLevel(e.target.value); }}>
                {LEVELS.map(function(l){ return <option key={l.code} value={l.code}>{l.label}</option>; })}
              </select>
            </div>
            {started && <button className="tbadge" onClick={function(){ setShowTopic(true); }}>{isLit ? ("📖 " + (bookMeta.title || "Book")) : ("💬 "+act)}</button>}
            {auth.isSignedIn && <button className="adm-trigger" onClick={openForum} title="Community forum">📝 Forum</button>}
            {auth.isSignedIn && <button className="adm-trigger" onClick={function(){ setFeedbackOpen(true); }} title="Send feedback">💬 Feedback</button>}
            {isAdmin && <button className="adm-trigger" onClick={function(){ setShowAdmin(true); }} title="Manage user approvals">👥 Users</button>}
            {isAdmin && <button className="adm-trigger" onClick={function(){ setShowUpload(true); setUpErr(""); setUpMsg(""); }} title="Upload a song to the library">📤 Upload</button>}
            {auth.isSignedIn && <div className="userbtn-wrap"><UserButton afterSignOutUrl="/" /></div>}
          </div>
        </header>

        {!noAIMode && (
        <div className="tabs">
          {["chat","vocab","grammar"].map(function(t){
            return (
              <button key={t} className={"tab"+(tab===t?" on":"")} onClick={function(){ setTab(t); }}>
                {t==="chat"?"Conversation":t==="vocab"?"Vocabulary":"Grammar"}
                {t==="vocab"&&vocab.length>0&&<span className="bdg">{vocab.length}</span>}
                {t==="grammar"&&tips.length>0&&<span className="bdg g">{tips.length}</span>}
              </button>
            );
          })}
        </div>
        )}
        {ttsErr && (
          <div style={{padding:"8px 28px",background:"rgba(157,70,48,.18)",borderBottom:"1px solid rgba(157,70,48,.35)",color:"#c87a68",fontSize:13,display:"flex",alignItems:"center",gap:10}}>
            <span style={{flex:1}}>🔊 {ttsErr}</span>
            <button onClick={function(){ setTtsErr(""); }} style={{background:"none",border:"none",color:"#c87a68",cursor:"pointer",fontSize:18,padding:0}}>×</button>
          </div>
        )}

        {syncErr && (
          <div style={{padding:"8px 28px",background:"rgba(157,70,48,.18)",borderBottom:"1px solid rgba(157,70,48,.35)",color:"#c87a68",fontSize:13,display:"flex",alignItems:"center",gap:10}}>
            <span style={{flex:1}}>⚠️ {syncErr} <span style={{opacity:.75,fontStyle:"italic"}}>Remove a few entries from the Vocabulary tab to keep syncing.</span></span>
            <button onClick={function(){ setSyncErr(""); }} style={{background:"none",border:"none",color:"#c87a68",cursor:"pointer",fontSize:18,padding:0}}>×</button>
          </div>
        )}

        {tab==="chat" && (
          <div className="main">
            {!started && !mode && (
              <div className="ss">
                <div className="sico" style={{color:"#c8a276"}}><Pushkin size={64}/></div>
                <h1 className="sti">Говорим</h1>
                <p className="sde">Choose how you want to practice today.</p>
                <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:14}}>
                  <button className="btn-p" onClick={function(){ setMode("chat"); }} style={{textAlign:"left",padding:"18px 22px"}}>
                    <div style={{fontSize:22,marginBottom:4}}>💬 Chat</div>
                    <div style={{fontSize:13,opacity:.85,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Pick a topic, hear interesting facts, answer probing questions.</div>
                  </button>
                  <button className="btn-p" onClick={function(){ setMode("read"); }} style={{textAlign:"left",padding:"18px 22px"}}>
                    <div style={{fontSize:22,marginBottom:4}}>📖 Read</div>
                    <div style={{fontSize:13,opacity:.85,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Load any Russian book file, then practice with comprehension questions.</div>
                  </button>
                  <button className="btn-p" onClick={function(){ setMode("grammar"); }} style={{textAlign:"left",padding:"18px 22px"}}>
                    <div style={{fontSize:22,marginBottom:4}}>📚 Grammar</div>
                    <div style={{fontSize:13,opacity:.85,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Pick your level and a topic. Quick reference pages with rules and examples.</div>
                  </button>
                </div>
              </div>
            )}

            {!started && mode === "chat" && (
              <div className="ss">
                <div className="sico">💬</div>
                <h1 className="sti">Давайте поговорим</h1>
                <p className="sde">Choose a topic and start a natural Russian conversation.</p>
                <div className="tsel">
                  <span className="slbl">Topic</span>
                  <select value={topic} onChange={function(e){ setTopic(e.target.value); setCustom(""); }}>
                    {TOPICS.map(function(t){ return <option key={t}>{t}</option>; })}
                  </select>
                </div>
                <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:8}}>
                  <button className="btn-p" onClick={startChat}>Начать разговор →</button>
                  <button className="btn-g" onClick={function(){ setMode(""); }}>← Back</button>
                </div>
              </div>
            )}

            {!started && mode === "read" && (
              <div className="ss">
                <div className="sico">📖</div>
                <h1 className="sti">{chapters.length > 0 ? bookMeta.title : "Open a Russian book"}</h1>
                <p className="sde">{chapters.length > 0 ? bookMeta.author : "Load EPUB, FB2, TXT, or HTML from your device. Supports books from Project Gutenberg, Litres, Flibusta, etc. Cached after first load."}</p>
                <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:10}}>
                  {chapters.length > 0 ? (
                    <>
                      {cbm > 0 && <button className="btn-p" onClick={function(){ startLit(cbm); }}>📌 Resume at chapter {cbm+1}</button>}
                      <button className={cbm>0?"btn-g":"btn-p"} onClick={function(){ startLit(0); }}>{cbm>0?"Start from beginning":"Начать читать →"}</button>
                      <FileBtn label="Open an ebook" onLoad={loadFile}/>
                      <button onClick={async function(){
                        setChapters([]); setCidx(0); setCbm(0); setBookMeta({title:"",author:""});
                        try { await storage.delete(EPUB_CACHE); } catch(e) {}
                        try { await storage.delete(EPUB_BM); } catch(e) {}
                        try { await storage.delete(QHIST_KEY); } catch(e) {}
                      }} style={{background:"none",border:"none",color:"rgba(210,197,175,.4)",fontSize:11,fontStyle:"italic",fontFamily:"'Crimson Pro',serif",cursor:"pointer",padding:"4px",marginTop:4,textDecoration:"underline",textDecorationColor:"rgba(210,197,175,.2)",alignSelf:"center"}}>clear cached book</button>
                    </>
                  ) : (
                    <FileBtn label="Open an ebook" onLoad={loadFile}/>
                  )}

                  {/* Pre-loaded library — dropdown of books shipped with the app,
                      grouped into categories (Novel, Song Lyrics, Poetry, Short Stories,
                      then "Other" for anything uncategorized). For Song Lyrics
                      entries the dropdown selection routes to an inline song picker
                      so users can pick a specific song instead of starting at #1. */}
                  {presetBooks.length > 0 && (
                    <div style={{marginTop:18,paddingTop:18,borderTop:"1px solid rgba(210,197,175,.1)"}}>
                      <div style={{fontSize:11,letterSpacing:2,textTransform:"uppercase",color:"rgba(210,197,175,.45)",marginBottom:10,textAlign:"center"}}>Or pick from the library</div>
                      <select
                        defaultValue=""
                        onChange={function(e){
                          var idx = e.target.value;
                          if (idx === "") return;
                          var book = presetBooks[parseInt(idx,10)];
                          if (book && book.category === "Song Lyrics") {
                            openSongPicker(book);
                          } else {
                            loadPresetBook(book);
                          }
                          e.target.value = "";  // reset so picking again triggers onChange
                        }}>
                        <option value="" disabled>📖 Choose a book…</option>
                        {(function() {
                          // Group books by category, preserving the index into presetBooks
                          // so the onChange lookup still resolves correctly. Categories
                          // render in this fixed order; "Other" catches anything missing
                          // or unrecognized.
                          var CATEGORIES = ["Novel", "Plays", "Song Lyrics", "Poetry", "Short Stories"];
                          var buckets = {};
                          CATEGORIES.forEach(function(c){ buckets[c] = []; });
                          buckets["Other"] = [];
                          presetBooks.forEach(function(book, idx) {
                            var cat = (book && book.category) || "";
                            var bucket = CATEGORIES.indexOf(cat) !== -1 ? cat : "Other";
                            buckets[bucket].push({ book: book, idx: idx });
                          });
                          return CATEGORIES.concat(["Other"]).map(function(cat) {
                            var entries = buckets[cat];
                            if (!entries.length) return null;
                            return (
                              <optgroup key={cat} label={cat}>
                                {entries.map(function(entry) {
                                  var book = entry.book;
                                  var label = (book.title || book.filename) + (book.author && book.author !== book.title ? " — " + book.author : "");
                                  return <option key={entry.idx} value={entry.idx}>{label}</option>;
                                })}
                              </optgroup>
                            );
                          });
                        })()}
                      </select>

                      {/* Inline song picker — shown after picking a Song Lyrics
                          artist from the dropdown. Lists the artist's individual
                          songs so you can jump straight to one. */}
                      {songPickerBook && (
                        <div style={{marginTop:14,padding:14,background:"rgba(0,0,0,.25)",border:"1px solid rgba(210,197,175,.15)",borderRadius:6}}>
                          <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",marginBottom:10}}>
                            <div style={{fontFamily:"'Crimson Pro',serif",fontSize:15}}>
                              🎵 <span style={{fontStyle:"italic"}}>{songPickerBook.title}</span> · pick a song
                            </div>
                            <button onClick={function(){ setSongPickerBook(null); setSongPickerList([]); setSongPickerErr(""); }}
                              style={{background:"transparent",color:"rgba(210,197,175,.55)",border:"none",cursor:"pointer",fontSize:18,padding:"0 4px"}}>×</button>
                          </div>
                          {songPickerLoad && (
                            <div style={{fontSize:13,opacity:.6,padding:"6px 0",fontStyle:"italic"}}>Loading song list…</div>
                          )}
                          {songPickerErr && (
                            <div style={{fontSize:13,color:"#c87a68",padding:"6px 0"}}>{songPickerErr}</div>
                          )}
                          {!songPickerLoad && !songPickerErr && songPickerList.length === 0 && (
                            <div style={{fontSize:13,opacity:.6,padding:"6px 0",fontStyle:"italic"}}>No songs found.</div>
                          )}
                          {songPickerList.length > 0 && (
                            <div style={{maxHeight:320,overflowY:"auto",display:"flex",flexDirection:"column",gap:2}}>
                              {songPickerList.map(function(s){
                                return (
                                  <button key={s.index} onClick={function(){ jumpToSong(s.index); }}
                                    style={{textAlign:"left",padding:"8px 12px",background:"transparent",color:"#d2c5af",border:"1px solid rgba(210,197,175,.1)",borderRadius:4,cursor:"pointer",fontSize:14,fontFamily:"'Crimson Pro',serif",display:"flex",justifyContent:"space-between",alignItems:"center"}}
                                    onMouseEnter={function(e){ e.currentTarget.style.background = "rgba(200,162,118,.1)"; e.currentTarget.style.borderColor = "rgba(200,162,118,.3)"; }}
                                    onMouseLeave={function(e){ e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = "rgba(210,197,175,.1)"; }}>
                                    <span><span style={{opacity:.4,marginRight:8}}>{s.index + 1}.</span>{s.title}</span>
                                    <span style={{opacity:.4,fontSize:12}}>▶</span>
                                  </button>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {fErr && <p style={{color:"#c87a68",fontSize:13,lineHeight:1.5}}>{fErr}</p>}
                  <button className="btn-g" onClick={function(){ setMode(""); }}>← Back</button>
                </div>
              </div>
            )}

            {/* ── Grammar reference (📚 Grammar) ────────────────────────────
                Three sub-states, gated entirely by local state — no `started`:
                  1. No level picked    → show level dropdown + intro
                  2. Level picked, no topic → show topic dropdown for that level
                  3. Topic picked → show the reference page for that topic
                Picking a level keeps the user inside grammar mode; picking the
                "← Back" buttons walks back one step at a time. */}
            {mode === "grammar" && !gramTopicId && (
              <div className="ss">
                <div className="sico" style={{color:"#c8a276"}}>📚</div>
                <h1 className="sti">Grammar Reference</h1>
                <p className="sde">Pick your level, then choose a topic. Rules and examples on every page.</p>

                {gramErr && <p style={{color:"#c87a68",fontSize:13,lineHeight:1.5,maxWidth:500}}>{gramErr}</p>}

                {curriculum && (
                  <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:14}}>
                    {/* Cross-level search — when this has text, it replaces the level/topic
                        dropdowns with a flat list of matching topics from every level.
                        Matches against title, subtitle, all bullets, and example text. */}
                    <div style={{position:"relative"}}>
                      <input
                        type="text"
                        value={gramSearch}
                        onChange={function(e){ setGramSearch(e.target.value); }}
                        placeholder="🔍 Search all levels (e.g. 'case', 'aspect', 'motion')"
                        style={{width:"100%",padding:"10px 36px 10px 14px",fontSize:14,background:"rgba(210,197,175,.05)",border:"1px solid rgba(210,197,175,.15)",borderRadius:8,color:"#d2c5af",fontFamily:"'Crimson Pro',serif"}}
                      />
                      {gramSearch && (
                        <button
                          onClick={function(){ setGramSearch(""); }}
                          title="Clear search"
                          style={{position:"absolute",right:6,top:"50%",transform:"translateY(-50%)",background:"none",border:"none",color:"rgba(210,197,175,.5)",cursor:"pointer",fontSize:18,padding:"2px 8px"}}>×</button>
                      )}
                    </div>

                    {gramSearch.trim() ? (function() {
                      // Search active — show flat result list across all levels.
                      var q = gramSearch.trim().toLowerCase();
                      var matches = curriculum.topics.filter(function(t) {
                        if ((t.title || "").toLowerCase().indexOf(q) !== -1) return true;
                        if ((t.subtitle || "").toLowerCase().indexOf(q) !== -1) return true;
                        var sections = t.sections || [];
                        for (var si = 0; si < sections.length; si++) {
                          var sec = sections[si];
                          if ((sec.heading || "").toLowerCase().indexOf(q) !== -1) return true;
                          var items = sec.items || [];
                          for (var ii = 0; ii < items.length; ii++) {
                            var item = items[ii];
                            if (typeof item === "string") {
                              if (item.toLowerCase().indexOf(q) !== -1) return true;
                            } else if (item) {
                              if ((item.ru || "").toLowerCase().indexOf(q) !== -1) return true;
                              if ((item.en || "").toLowerCase().indexOf(q) !== -1) return true;
                            }
                          }
                        }
                        return false;
                      });
                      // Sort by level so results group naturally (A1 → C2).
                      var levelOrder = curriculum.levels.map(function(L){ return L.code; });
                      matches.sort(function(a, b) {
                        return levelOrder.indexOf(a.level) - levelOrder.indexOf(b.level);
                      });
                      return (
                        <>
                          <span className="slbl">
                            {matches.length === 0 ? "No matches" : matches.length + " result" + (matches.length === 1 ? "" : "s") + " across all levels"}
                          </span>
                          {matches.length > 0 && (
                            <div style={{display:"flex",flexDirection:"column",gap:1,background:"rgba(210,197,175,.04)",border:"1px solid rgba(210,197,175,.1)",borderRadius:8,overflow:"hidden",maxHeight:340,overflowY:"auto"}}>
                              {matches.map(function(t) {
                                return (
                                  <button
                                    key={t.id}
                                    onClick={function(){ setGramTopicId(t.id); }}
                                    style={{textAlign:"left",background:"none",border:"none",borderBottom:"1px solid rgba(210,197,175,.06)",padding:"12px 14px",cursor:"pointer",color:"#d2c5af",fontFamily:"'Crimson Pro',serif",display:"flex",alignItems:"flex-start",gap:12,transition:"background .12s"}}
                                    onMouseEnter={function(e){ e.currentTarget.style.background = "rgba(200,162,118,.06)"; }}
                                    onMouseLeave={function(e){ e.currentTarget.style.background = "none"; }}>
                                    <span style={{fontSize:11,fontWeight:600,letterSpacing:1.5,color:"#c8a276",background:"rgba(200,162,118,.12)",padding:"3px 7px",borderRadius:4,flexShrink:0,marginTop:1}}>{t.level}</span>
                                    <span style={{display:"flex",flexDirection:"column",gap:2,flex:1,minWidth:0}}>
                                      <span style={{fontSize:15,fontWeight:500,color:"#d2c5af"}}>{t.title}</span>
                                      {t.subtitle && <span style={{fontSize:12,fontStyle:"italic",color:"rgba(210,197,175,.55)",lineHeight:1.45}}>{t.subtitle}</span>}
                                    </span>
                                  </button>
                                );
                              })}
                            </div>
                          )}
                          {matches.length === 0 && (
                            <p style={{fontSize:13,fontStyle:"italic",color:"rgba(210,197,175,.5)",textAlign:"center",padding:"12px 0"}}>
                              Nothing matched "{gramSearch}". Try a different word, or clear the search to browse by level.
                            </p>
                          )}
                        </>
                      );
                    })() : (
                      // No search — show the normal level/topic dropdown picker.
                      <div className="tsel" style={{margin:0}}>
                        <span className="slbl">Your level</span>
                        <select value={gramLevel} onChange={function(e){ setGramLevel(e.target.value); }}>
                          <option value="" disabled>— select a CEFR level —</option>
                          {curriculum.levels.map(function(L) {
                            return <option key={L.code} value={L.code}>{L.name}</option>;
                          })}
                        </select>
                        {gramLevel && (function() {
                          var L = curriculum.levels.find(function(x){ return x.code === gramLevel; });
                          var topicsHere = curriculum.topics.filter(function(t){ return t.level === gramLevel; });
                          return (
                            <>
                              {L && L.description && (
                                <p style={{fontSize:13,fontStyle:"italic",color:"rgba(210,197,175,.55)",margin:"4px 2px 0",fontFamily:"'Crimson Pro',serif",lineHeight:1.5}}>{L.description}</p>
                              )}
                              <span className="slbl" style={{marginTop:14}}>Topic ({topicsHere.length} available)</span>
                              <select
                                value=""
                                onChange={function(e){
                                  var id = e.target.value;
                                  if (id) setGramTopicId(id);
                                  e.target.value = "";
                                }}>
                                <option value="" disabled>📖 Choose a topic…</option>
                                {topicsHere.map(function(t) {
                                  return <option key={t.id} value={t.id}>{t.title}</option>;
                                })}
                              </select>
                            </>
                          );
                        })()}
                      </div>
                    )}
                  </div>
                )}

                {!curriculum && !gramErr && <p style={{color:"rgba(210,197,175,.55)",fontStyle:"italic"}}>Loading curriculum…</p>}

                <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:8,marginTop:18}}>
                  <button className="btn-g" onClick={function(){ setMode(""); setGramLevel(""); setGramSearch(""); }}>← Back</button>
                </div>
              </div>
            )}

            {mode === "grammar" && gramTopicId && curriculum && (function() {
              var topic = curriculum.topics.find(function(t){ return t.id === gramTopicId; });
              if (!topic) {
                return (
                  <div className="ss">
                    <p style={{color:"#c87a68"}}>Topic not found.</p>
                    <button className="btn-g" onClick={function(){ setGramTopicId(""); }}>← Back to topics</button>
                  </div>
                );
              }
              // Topics in the same level, used for "Next topic" navigation.
              var siblings = curriculum.topics.filter(function(t){ return t.level === topic.level; });
              var thisIdx = siblings.findIndex(function(t){ return t.id === topic.id; });
              var prev = thisIdx > 0 ? siblings[thisIdx - 1] : null;
              var next = thisIdx < siblings.length - 1 ? siblings[thisIdx + 1] : null;

              return (
                <div className="gramref">
                  <div className="gramref-hdr">
                    <button className="ttsbtn" onClick={function(){ setGramTopicId(""); }}>← All {topic.level} topics</button>
                    <div style={{display:"flex",alignItems:"center",gap:10}}>
                      {(function(){
                        var saved = savedTopics.indexOf(topic.id) !== -1;
                        return (
                          <button
                            className="ttsbtn"
                            title={saved ? "Already saved — click to remove from Grammar tab" : "Save to Grammar tab for quick review"}
                            onClick={function(){ saved ? rmTopic(topic.id) : addTopic(topic.id); }}
                            style={saved ? {color:"#9ab28e",borderColor:"rgba(154,178,142,.4)"} : null}>
                            {saved ? "✓ Saved" : "📚 Save topic"}
                          </button>
                        );
                      })()}
                      <span style={{color:"rgba(210,197,175,.4)",fontSize:12,letterSpacing:1.5,textTransform:"uppercase"}}>{topic.level}</span>
                    </div>
                  </div>

                  <div className="gramref-body">
                    <h1 style={{fontFamily:"'Playfair Display',serif",fontSize:32,fontWeight:700,color:"#c8a276",marginBottom:6,lineHeight:1.15}}>{topic.title}</h1>
                    {topic.subtitle && <p style={{fontStyle:"italic",fontSize:16,color:"rgba(210,197,175,.65)",marginBottom:24,fontFamily:"'Crimson Pro',serif",lineHeight:1.5}}>{topic.subtitle}</p>}

                    {(topic.sections || []).map(function(sec, si) {
                      return (
                        <section key={si} style={{marginBottom:22}}>
                          {sec.heading && <h2 style={{fontFamily:"'Playfair Display',serif",fontSize:14,fontWeight:700,color:"rgba(210,197,175,.5)",textTransform:"uppercase",letterSpacing:2,marginBottom:10,paddingBottom:6,borderBottom:"1px solid rgba(210,197,175,.08)"}}>{sec.heading}</h2>}
                          {sec.type === "bullets" && (
                            <ul style={{listStyle:"none",padding:0,margin:0,display:"flex",flexDirection:"column",gap:8}}>
                              {(sec.items || []).map(function(item, ii) {
                                return (
                                  <li key={ii} style={{paddingLeft:18,position:"relative",lineHeight:1.55,fontSize:15}}>
                                    <span style={{position:"absolute",left:0,top:0,color:"#c8a276"}}>•</span>
                                    {item}
                                  </li>
                                );
                              })}
                            </ul>
                          )}
                          {sec.type === "examples" && (
                            <div style={{display:"flex",flexDirection:"column",gap:14}}>
                              {(sec.items || []).map(function(ex, ii) {
                                var ru = typeof ex === "string" ? ex : (ex.ru || "");
                                var en = typeof ex === "string" ? "" : (ex.en || "");
                                return (
                                  <div key={ii} style={{borderLeft:"2px solid rgba(200,162,118,.35)",paddingLeft:14,display:"flex",flexDirection:"column",gap:3}}>
                                    <div style={{display:"flex",alignItems:"flex-start",gap:8}}>
                                      <span style={{fontSize:16,lineHeight:1.45,flex:1}}>{ru}</span>
                                      {ru && (
                                        <button
                                          className="ttsbtn"
                                          style={{height:22,fontSize:11,flexShrink:0}}
                                          onClick={function(){ speakMsg(ru, "gram-" + topic.id + "-" + si + "-" + ii); }}
                                          title="Listen">
                                          🔊
                                        </button>
                                      )}
                                    </div>
                                    {en && <span style={{fontStyle:"italic",fontSize:13,color:"rgba(210,197,175,.55)",fontFamily:"'Crimson Pro',serif",lineHeight:1.5}}>{en}</span>}
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </section>
                      );
                    })}

                    <div className="gramref-nav">
                      <button
                        className="btn-g"
                        style={{flex:1,opacity: prev ? 1 : 0.35, cursor: prev ? "pointer" : "default"}}
                        disabled={!prev}
                        onClick={function(){ if (prev) { setGramTopicId(prev.id); window.scrollTo(0,0); } }}>
                        {prev ? "← " + prev.title : "← Previous"}
                      </button>
                      <button
                        className="btn-g"
                        style={{flex:1,opacity: next ? 1 : 0.35, cursor: next ? "pointer" : "default"}}
                        disabled={!next}
                        onClick={function(){ if (next) { setGramTopicId(next.id); window.scrollTo(0,0); } }}>
                        {next ? next.title + " →" : "Next →"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })()}

            {started && isLit && (
              <div className="lit-wrap">
                <div className="lit-top">
                  <button className={"ltab"+(lview==="read"?" on":"")} onClick={function(){ setLview("read"); }}>📖 Read</button>
                  <button className={"ltab"+(lview==="nav"?" on":"")} onClick={function(){ setLview("nav"); }}>🗂 Chapters</button>
                  <button className={"ltab"+(lview==="search"?" on":"")} onClick={function(){ setLview("search"); }}>🔍 Search</button>
                  <div className="lprog">
                    <span className="lpct">
                      {singlePageMode
                        ? <>Song {cidx+1}/{chapters.length} · {pct}%</>
                        : <>Ch. {cidx+1}/{chapters.length} · Page {pidx+1}/{totalPages} · {pct}%</>}
                    </span>
                    <div className="lpbar"><div className="lpfill" style={{width:pct+"%"}}/></div>
                  </div>
                </div>

                {lview==="read" && (
                  <>
                    <div className="ttsbar">
                      {!playing
                        ? <button className="ttsplay" onClick={function(){ paraText.current=curChapter.text||""; playText(paraText.current,charPos.current); }}>▶</button>
                        : <button className="ttspause" onClick={pauseTTS}>⏸</button>
                      }
                      <span className="ttslab">{playing?"Reading…":charPos.current>0?(voice&&voice.name||"Voice")+" — paused":voice?(voice.name+" — click ▶"):"No Russian voice found"}</span>
                      {charPos.current>0 && <button className="ttsbtn" onClick={function(){ stopTTS(); charPos.current=0; paraText.current=""; }}>⏹</button>}
                      <button className="ttsbtn" onClick={function(){ setShowVP(function(v){ return !v; }); }}>🎙 Voice</button>
                    </div>

                    {renderVoicePicker()}

                    <div className="lit-body">
                      <div className={"lit-left" + (noAIMode ? " noai" : "")}>
                        {/* Book title shown small above the chapter heading so the reader always knows
                            which book they're in, even after navigating mid-chapter. */}
                        {bookMeta.title && (
                          <div style={{fontFamily:"'Crimson Pro',serif",fontStyle:"italic",fontSize:13,color:"rgba(210,197,175,.45)",marginBottom:4,letterSpacing:.3}}>
                            {bookMeta.title}{bookMeta.author ? " — " + bookMeta.author : ""}
                          </div>
                        )}
                        <div className="lhdr">
                          {singlePageMode
                            ? <>Song {cidx+1} of {chapters.length} · click any word to define</>
                            : <>Chapter {cidx+1} of {chapters.length} · click any word to define</>}
                        </div>
                        {curChapter.heading && (
                          <div className="lch-heading" style={{display:"flex",alignItems:"center",gap:12,flexWrap:"wrap"}}>
                            <span>{curChapter.heading}</span>
                            {curChapter.youtubeUrl && (
                              <a href={curChapter.youtubeUrl} target="_blank" rel="noopener noreferrer"
                                title="Listen on YouTube"
                                style={{fontSize:12,color:"rgba(210,197,175,.7)",textDecoration:"none",padding:"4px 10px",border:"1px solid rgba(210,197,175,.25)",borderRadius:4,fontFamily:"'Inter',sans-serif"}}>
                                🎵 Listen on YouTube ↗
                              </a>
                            )}
                          </div>
                        )}
                        <div className="ltxt">{renderLit(curChapter.text)}</div>
                      </div>
                      {!noAIMode && (
                      <div className="lit-right">
                        <div className="lit-msgs" ref={msgsRef}>
                          {msgs.map(function(m,i){ return renderMsg(m,i); })}
                          {loading && <div className="msg ai"><div className="typing"><div className="dot"/><div className="dot"/><div className="dot"/></div></div>}
                        </div>
                        <div className="lit-ibar">
                          <button
                            className="inew"
                            title="Generate fresh questions for this page (costs an API call)"
                            disabled={loading || noAIMode}
                            onClick={async function() {
                              if (!chapters.length) return;
                              setLoading(true);
                              await litAnalysis(chapters, cidx, pidx, undefined, true);
                              setLoading(false);
                            }}>↻</button>
                          <textarea ref={inputRef} value={input}
                            onChange={function(e){
                              setInput(e.target.value);
                              // Auto-expand the textarea so the user always sees what they're typing
                              // without scrolling inside the box. Reset to auto first so shrinking
                              // (when content is deleted) works too, then size to fit content up
                              // to a 240px cap (after which content scrolls inside).
                              e.target.style.height = 'auto';
                              e.target.style.height = Math.min(e.target.scrollHeight, 240) + 'px';
                            }}
                            onKeyDown={onKey} placeholder="Напиши свой ответ…" disabled={loading}/>
                          <button className="isend" onClick={send} disabled={loading||!input.trim()}>↑</button>
                        </div>
                      </div>
                      )}
                    </div>

                    <div className={"lnav" + (noAIMode ? " noai" : "")}>
                      <div className="lnav-row">
                        {pidx > 0 && <button className="lnb" onClick={function(){ navPage(pidx - 1); }} disabled={loading}>← Page</button>}
                        <button className="lbm" onClick={function(){ setCbm(cidx); }}>📌</button>
                        {pidx < totalPages - 1 && <button className="lnb p" onClick={function(){ navPage(pidx + 1); }} disabled={loading}>Page →</button>}
                      </div>
                      {chapters.length > 1 && (
                        <div className="lnav-row lnav-row-sm">
                          {cidx > 0 && <button className="lnb-sm" onClick={function(){ navLit(cidx-1); }} disabled={loading}>← {singlePageMode ? "Previous song" : "Previous chapter"}</button>}
                          {cidx < chapters.length - 1 && <button className="lnb-sm" onClick={function(){ navLit(cidx+1); }} disabled={loading}>{singlePageMode ? "Next song" : "Next chapter"} →</button>}
                        </div>
                      )}
                    </div>
                  </>
                )}

                {lview==="nav" && (
                  <div className="navpanel">
                    {chapters.map(function(ch,i){
                      return (
                        <div key={i} className={"lcard"+(i===cidx?" cur":"")} onClick={function(){ setLview("read"); navLit(i); }}>
                          <div className="lcn">{i+1}{i===cbm?" 📌":""}{i===cidx?" ◀":""}</div>
                          <div className="lchead">{ch.heading}</div>
                          <div className="lcp">{ch.text.slice(0,80)}…</div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {lview==="search" && (
                  <>
                    <div className="lsbar">
                      <input type="text" placeholder={"Search " + (bookMeta.title || "book") + "…"} value={lsearch} onChange={function(e){ setLsearch(e.target.value); }}/>
                    </div>
                    <div className="navpanel">
                      {!lsearch && <div className="lem">Type to search the full text.</div>}
                      {lsearch && !lres.length && <div className="lem">No results for «{lsearch}»</div>}
                      {lres.map(function(i){
                        return (
                          <div key={i} className={"lcard"+(i===cidx?" cur":"")} onClick={function(){ setLsearch(""); setLview("read"); navLit(i); }}>
                            <div className="lcn">{i+1}{i===cbm?" 📌":""}</div>
                            <div className="lchead">{chapters[i].heading}</div>
                            <div className="lcp">{chapters[i].text.slice(0,100)}…</div>
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>
            )}

            {started && !isLit && (
              <div className="chat-wrap">
                <div className="msgs">
                  {msgs.map(function(m,i){ return renderMsg(m,i); })}
                  {loading && <div className="msg ai"><div className="typing"><div className="dot"/><div className="dot"/><div className="dot"/></div></div>}
                </div>
                {/* Voice picker panel — same control as in the reading view. Sits above
                    the input bar so toggling 🎙 Voice opens it between the conversation
                    and the textarea. The picker drives the same `voice` state used by
                    the 🔊 Listen button on each AI message. */}
                {renderVoicePicker()}
                <div className="ibar">
                  <button className="inew" onClick={startChat}>↺ New</button>
                  <button className="inew" title="Choose a voice for 🔊 Listen" onClick={function(){ setShowVP(function(v){ return !v; }); }}>🎙</button>
                  <textarea ref={inputRef} value={input} onChange={function(e){ setInput(e.target.value); }} onKeyDown={onKey} placeholder="Type in Russian or English…" rows={1} disabled={loading}/>
                  <button className="isend" onClick={send} disabled={loading||!input.trim()}>↑</button>
                </div>
              </div>
            )}
          </div>
        )}

        {tab==="vocab" && (
          <div className="panel">
            {quizMode ? (
              // ── Quiz view ──────────────────────────────────────────────
              <>
                <div className="phdr">
                  <span className="pti">📝 Vocab Quiz</span>
                  <button className="ab" onClick={function(){ setQuizMode(false); setQuizMenu(true); }}>← Back</button>
                </div>
                {quizQuestions.length === 0 ? (
                  <div style={{padding:"40px 20px",textAlign:"center"}}>
                    <p style={{color:"rgba(210,197,175,.7)",fontSize:15,lineHeight:1.6,maxWidth:480,margin:"0 auto"}}>{quizSkipNote}</p>
                    <button className="btn-g" style={{marginTop:24,maxWidth:280}} onClick={function(){ setQuizMode(false); }}>Back to vocab list</button>
                  </div>
                ) : quizIdx >= quizQuestions.length ? (
                  // Final score screen
                  <div style={{padding:"40px 20px",textAlign:"center"}}>
                    <div style={{fontSize:48,marginBottom:12}}>{quizScore === quizQuestions.length ? "🎉" : quizScore >= quizQuestions.length * 0.7 ? "👏" : "📚"}</div>
                    <h2 style={{fontFamily:"'Playfair Display',serif",fontSize:26,color:"#c8a276",marginBottom:8}}>Quiz Complete!</h2>
                    <p style={{fontSize:20,color:"#d2c5af",marginBottom:6}}>You got <strong style={{color:"#c8a276"}}>{quizScore}</strong> of <strong>{quizQuestions.length}</strong> correct.</p>
                    <p style={{fontSize:14,color:"rgba(210,197,175,.5)",marginBottom:28}}>{Math.round(quizScore / quizQuestions.length * 100)}%</p>
                    {quizSkipNote && <p style={{fontSize:12,color:"rgba(210,197,175,.4)",fontStyle:"italic",marginBottom:20,maxWidth:440,margin:"0 auto 20px"}}>{quizSkipNote}</p>}
                    <div style={{display:"flex",gap:10,justifyContent:"center",flexWrap:"wrap"}}>
                      <button className="btn-p" style={{maxWidth:200}} onClick={startQuiz}>Retake quiz</button>
                      <button className="btn-g" style={{maxWidth:200}} onClick={function(){ setQuizMode(false); setQuizMenu(false); }}>Back to vocab list</button>
                    </div>
                  </div>
                ) : (
                  // Current question
                  <div style={{padding:"20px 4px"}}>
                    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:18,fontSize:13,color:"rgba(210,197,175,.5)"}}>
                      <span>Question {quizIdx + 1} of {quizQuestions.length}</span>
                      <span>Score: {quizScore} / {quizIdx + (quizSelected !== null ? 1 : 0)}</span>
                    </div>
                    {/* The Russian word being quizzed */}
                    <div style={{textAlign:"center",marginBottom:8}}>
                      <span style={{fontSize:12,color:"rgba(210,197,175,.45)",textTransform:"uppercase",letterSpacing:1.5}}>{quizQuestions[quizIdx].pos}</span>
                    </div>
                    <div style={{fontSize:42,fontFamily:"'Playfair Display',serif",color:"#c8a276",textAlign:"center",marginBottom:30,fontWeight:600}}>
                      {quizQuestions[quizIdx].word}
                    </div>
                    {/* Multiple choice options */}
                    <div style={{display:"flex",flexDirection:"column",gap:10,maxWidth:560,margin:"0 auto"}}>
                      {quizQuestions[quizIdx].options.map(function(opt, i) {
                        var isCorrect = opt === quizQuestions[quizIdx].correct;
                        var isPicked  = opt === quizSelected;
                        var bg = "rgba(210,197,175,.05)", brd = "rgba(210,197,175,.16)", col = "#d2c5af";
                        if (quizSelected !== null) {
                          if (isCorrect)      { bg = "rgba(90,133,86,.18)";  brd = "rgba(90,133,86,.6)";  col = "#9dbf99"; }
                          else if (isPicked)  { bg = "rgba(157,70,48,.18)";  brd = "rgba(157,70,48,.6)";  col = "#c87a68"; }
                          else                { col = "rgba(210,197,175,.4)"; }
                        }
                        return (
                          <button key={i} disabled={quizSelected !== null} onClick={function(){
                            setQuizSelected(opt);
                            if (isCorrect) setQuizScore(function(s){ return s + 1; });
                          }} style={{background:bg,border:"1px solid "+brd,color:col,padding:"14px 18px",borderRadius:10,fontSize:16,fontFamily:"'Crimson Pro',serif",cursor: quizSelected !== null ? "default" : "pointer", textAlign:"left", transition:"all .15s"}}>
                            <span style={{display:"inline-block",width:20,color:"rgba(210,197,175,.45)",fontFamily:"'Inter',sans-serif",fontSize:13}}>{String.fromCharCode(65 + i)}.</span>
                            {opt}
                          </button>
                        );
                      })}
                    </div>
                    {quizSelected !== null && (
                      <div style={{marginTop:24,textAlign:"center"}}>
                        <button className="btn-p" style={{maxWidth:280}} onClick={function(){
                          setQuizIdx(function(i){ return i + 1; });
                          setQuizSelected(null);
                        }}>
                          {quizIdx + 1 < quizQuestions.length ? "Next →" : "See results"}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : quizMenu ? (
              // ── Review choice menu (Multiple Choice vs Chat Practice) ──
              <>
                <div className="phdr">
                  <span className="pti">📝 Review Vocabulary</span>
                  <button className="ab" onClick={function(){ setQuizMenu(false); }}>← Back to list</button>
                </div>
                <div style={{padding:"24px 16px",display:"flex",flexDirection:"column",gap:14,maxWidth:560,margin:"0 auto"}}>
                  <p style={{color:"rgba(210,197,175,.65)",fontSize:14,textAlign:"center",margin:"0 0 8px"}}>How would you like to practice your {vocab.length} saved {vocab.length === 1 ? "word" : "words"}?</p>
                  {/* Multiple Choice Quiz option */}
                  <button onClick={startQuiz}
                    style={{background:"rgba(200,162,118,.08)",border:"1px solid rgba(200,162,118,.3)",color:"#d2c5af",padding:"18px 20px",borderRadius:12,cursor:"pointer",textAlign:"left",fontFamily:"'Crimson Pro',serif",transition:"all .15s"}}
                    onMouseOver={function(e){ e.currentTarget.style.background = "rgba(200,162,118,.14)"; }}
                    onMouseOut={function(e){ e.currentTarget.style.background = "rgba(200,162,118,.08)"; }}>
                    <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:6}}>
                      <span style={{fontSize:24}}>📝</span>
                      <span style={{fontSize:18,fontWeight:600,color:"#c8a276",fontFamily:"'Playfair Display',serif"}}>Multiple Choice Quiz</span>
                    </div>
                    <p style={{fontSize:13,color:"rgba(210,197,175,.55)",margin:0,lineHeight:1.5}}>Quick recall test. Each question shows a Russian word with 4 English meaning options (from same-pos vocabulary).</p>
                  </button>
                  {/* Chat Practice option */}
                  <button onClick={startVocabChat}
                    style={{background:"rgba(90,133,86,.08)",border:"1px solid rgba(90,133,86,.3)",color:"#d2c5af",padding:"18px 20px",borderRadius:12,cursor:"pointer",textAlign:"left",fontFamily:"'Crimson Pro',serif",transition:"all .15s"}}
                    onMouseOver={function(e){ e.currentTarget.style.background = "rgba(90,133,86,.14)"; }}
                    onMouseOut={function(e){ e.currentTarget.style.background = "rgba(90,133,86,.08)"; }}>
                    <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:6}}>
                      <span style={{fontSize:24}}>💬</span>
                      <span style={{fontSize:18,fontWeight:600,color:"#9dbf99",fontFamily:"'Playfair Display',serif"}}>Chat Practice</span>
                    </div>
                    <p style={{fontSize:13,color:"rgba(210,197,175,.55)",margin:0,lineHeight:1.5}}>Open-ended conversation. The AI uses each saved word in a Russian sentence and asks a question about it — you reply naturally.</p>
                  </button>
                </div>
              </>
            ) : (
              // ── Normal vocab list view ─────────────────────────────────
              <>
                <div className="phdr">
                  <span className="pti">My Vocabulary</span>
                  <div style={{display:"flex",gap:8}}>
                    {vocab.length > 0 && <button className="ab" onClick={function(){ setQuizMenu(true); }} title="Quiz yourself or practice these words in chat">📝 Review vocab</button>}
                    <button className="ab" onClick={function(){ setNRu(""); setNEn(""); setShowWord(true); }}>+ Add word</button>
                  </div>
                </div>
                {vocab.length===0 ? <p className="empty">No words saved yet.<br/>Click any Russian word to define and save it.</p>
                  : <div className="ilist">{vocab.map(function(v){
                    var posLine = [v.pos, v.aspect].filter(Boolean).join(" · ");
                    var stamp = formatVocabDate(v.created || v.id);
                    return (
                      <div key={v.id} className="icard">
                        <div className="icont">
                          <span className="ipri">{v.ru}</span>
                          {posLine && <span className="ipos">{posLine}</span>}
                          {v.en && <span className="isec">{v.en}</span>}
                          {v.grammar && <span className="igr">{v.grammar}</span>}
                          {v.example && (
                            <div className="iex">
                              «&nbsp;{v.example}&nbsp;»
                              {v.exampleTranslation && <div className="iext">{v.exampleTranslation}</div>}
                            </div>
                          )}
                          {stamp && <span style={{fontSize:11,color:"rgba(210,197,175,.35)",fontStyle:"italic",fontFamily:"'Crimson Pro',serif",marginTop:6,display:"block"}}>Added {stamp}</span>}
                        </div>
                        <button className="rmb" title="Remove from vocabulary" onClick={function(){ setVocab(function(p){ return p.filter(function(x){ return x.id!==v.id; }); }); }}>×</button>
                      </div>
                    );
                  })}</div>}
              </>
            )}
          </div>
        )}

        {tab==="grammar" && (
          <div className="panel">
            {/* Saved curriculum topics: cards that click to open the reference page.
                Empty by default — only appears once the user has bookmarked something. */}
            {savedTopics.length > 0 && curriculum && (
              <>
                <div className="phdr"><span className="pti">Saved Topics</span></div>
                <div className="ilist" style={{marginBottom:20}}>
                  {savedTopics.map(function(id) {
                    var topic = curriculum.topics.find(function(t){ return t.id === id; });
                    if (!topic) return null; // ID exists but topic was removed from curriculum
                    return (
                      <div key={id} className="icard" style={{cursor:"pointer"}}
                        onClick={function(){ setMode("grammar"); setGramTopicId(id); setStarted(false); setMsgs([]); stopTTS(); setTab("chat"); }}>
                        <div className="icont" style={{flex:1}}>
                          <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:2}}>
                            <span style={{fontSize:10,letterSpacing:1.5,padding:"2px 6px",border:"1px solid rgba(210,197,175,.25)",borderRadius:3,color:"rgba(210,197,175,.6)"}}>{topic.level}</span>
                            <span className="ipri" style={{fontSize:15,color:"#c8a276"}}>📚 {topic.title}</span>
                          </div>
                          {topic.subtitle && <span style={{fontSize:13,fontStyle:"italic",color:"rgba(210,197,175,.55)",fontFamily:"'Crimson Pro',serif"}}>{topic.subtitle}</span>}
                        </div>
                        <button className="rmb" title="Remove from Grammar tab" onClick={function(e){ e.stopPropagation(); rmTopic(id); }}>×</button>
                      </div>
                    );
                  })}
                </div>
              </>
            )}

            <div className="phdr"><span className="pti">Grammar Tips</span><button className="ab g" onClick={function(){ setNTip(""); setShowTip(true); }}>+ Add tip</button></div>
            {tips.length===0 ? <p className="empty">No tips saved yet.<br/>Click 📝 Save tip under any tutor message, or use 📚 Grammar to bookmark a curriculum topic.</p>
              : <div className="ilist">{tips.map(function(t){
                return (
                  <div key={t.id} className="icard">
                    <div className="icont"><span className="ipri" style={{fontSize:15}}>📝 {t.tip}</span></div>
                    <button className="rmb" onClick={function(){ setTips(function(p){ return p.filter(function(x){ return x.id!==t.id; }); }); }}>×</button>
                  </div>
                );
              })}</div>}
          </div>
        )}

        {showTopic && (
          <div className="mover" onClick={function(){ setShowTopic(false); }}>
            <div className="modal" onClick={function(e){ e.stopPropagation(); }}>
              <span className="mti">{isLit ? ("📖 " + (bookMeta.title || "Reading")) : "💬 Change Topic"}</span>
              {!isLit && (
                <>
                  <span className="slbl">Topic</span>
                  <select value={topic} onChange={function(e){ setTopic(e.target.value); setCustom(""); }}>
                    {TOPICS.map(function(t){ return <option key={t}>{t}</option>; })}
                  </select>
                </>
              )}
              <div className="mact">
                <button className="mcanc" onClick={function(){ setShowTopic(false); }}>Cancel</button>
                {!isLit && <button className="mconf" onClick={function(){ setShowTopic(false); setStarted(false); setMsgs([]); stopTTS(); }}>Switch topic</button>}
                <button className="mconf" onClick={function(){ setShowTopic(false); setStarted(false); setMode(""); setMsgs([]); stopTTS(); }}>← Back to start</button>
              </div>
            </div>
          </div>
        )}

        {showWord && (
          <div className="mover" onClick={function(){ setShowWord(false); }}>
            <div className="modal" onClick={function(e){ e.stopPropagation(); }}>
              <span className="mti">Add Word</span>
              <input type="text" placeholder="Russian word" value={nRu} onChange={function(e){ setNRu(e.target.value); }}/>
              <input type="text" placeholder="English translation (optional)" value={nEn} onChange={function(e){ setNEn(e.target.value); }}/>
              <div className="mact">
                <button className="mcanc" onClick={function(){ setShowWord(false); }}>Cancel</button>
                <button className="mconf" onClick={function(){ if(nRu.trim()) addV(nRu.trim(),nEn.trim()); setShowWord(false); }}>Save</button>
              </div>
            </div>
          </div>
        )}

        {showTip && (
          <div className="mover" onClick={function(){ setShowTip(false); }}>
            <div className="modal" onClick={function(e){ e.stopPropagation(); }}>
              <span className="mti">Add Grammar Tip</span>
              <input type="text" placeholder="e.g. Genitive case after negation" value={nTip} onChange={function(e){ setNTip(e.target.value); }}/>
              <div className="mact">
                <button className="mcanc" onClick={function(){ setShowTip(false); }}>Cancel</button>
                <button className="mconf g" onClick={function(){ if(nTip.trim()) addT(nTip.trim()); setShowTip(false); }}>Save</button>
              </div>
            </div>
          </div>
        )}

        {popup && (
          <div className="pover" onClick={function(){ setPopup(null); }}>
            <div className="pop" ref={popRef} style={{top:popXY.top,left:popXY.left,width:Math.min(280,window.innerWidth-32)}} onClick={function(e){ e.stopPropagation(); }}>
              <button className="pcl" onClick={function(){ setPopup(null); }}>×</button>

              {/* Header shows the canonical form once data has loaded.
                   Pre-load (or on error) we show what the user clicked. */}
              {(function() {
                var entry = formatVocabEntry(popup.data, popup.word);
                var headline = entry.ru || popup.word;
                var clicked = (popup.word || "").trim();
                var lemma = popup.data && popup.data.lemma;
                var showClickedHint = !!(lemma && clicked && lemma !== clicked && !(/\s\/\s/.test(headline)));
                return (
                  <>
                    <div className="pw">{headline}</div>
                    {showClickedHint && (
                      <div style={{fontSize:11,color:"rgba(210,197,175,.4)",marginBottom:6,marginTop:-2}}>
                        you clicked: {clicked}
                      </div>
                    )}
                  </>
                );
              })()}

              {popup.loading && <div className="pload">Looking up…</div>}
              {popup.error && <div className="perr">{popup.error}</div>}

              {popup.yo && (
                <div style={{display:"flex",flexDirection:"column",gap:4,marginTop:8}}>
                  <div className="ppos" style={{marginBottom:8}}>е or ё? Tap the right spelling:</div>
                  <button className="yobtn" onClick={function(){ defWithYo(popup.yo.orig); }}>{popup.yo.orig} (keep е)</button>
                  {popup.yo.vars.map(function(v,i){ return <button key={i} className="yobtn" onClick={function(){ defWithYo(v); }}>{v} (with ё)</button>; })}
                </div>
              )}

              {!popup.loading && !popup.error && !popup.yo && popup.data && (
                <>
                  <div className="ppos">{popup.data.partOfSpeech}{popup.data.aspect ? " · " + popup.data.aspect : ""}</div>
                  <div className="ptr">{popup.data.translation}</div>
                  {popup.data.grammar && <div className="pgr">{popup.data.grammar}</div>}
                  {popup.data.example && <div className="pex">{popup.data.example}{popup.data.exampleTranslation&&<div className="pext">{popup.data.exampleTranslation}</div>}</div>}
                </>
              )}

              {/* Save uses the formatted entry: nominative for nouns, infinitive (with aspect pair) for verbs.
                   Also persists pos/grammar/example into the vocab list. */}
              {(function() {
                var entry = formatVocabEntry(popup.data, popup.word);
                return (
                  <button className="psave" onClick={function(){
                    if (entry.ru) addV(entry);
                    setPopup(null);
                  }}>+ Save « {entry.ru || popup.word} » to vocabulary</button>
                );
              })()}
            </div>
          </div>
        )}
      </div>
      </>
      )}
      </>
      )}
    </>
  );
}

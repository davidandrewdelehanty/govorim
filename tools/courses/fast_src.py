# -*- coding: utf-8 -*-
"""The FSI Russian FAST Course (Foreign Service Institute, 1994; a US
Government work in the public domain), lessons 2–11: the dialogues, their
variants, each lesson's useful words and expressions, and the cultural notes
that open each lesson, as printed in the three student volumes — corrected by
hand from an OCR of the scans at fsi-languages.yojik.eu and
livelingua.com. Lesson 1 teaches the alphabet, which the app covers elsewhere.

A dialogue turn is "WHO|Russian|English"; WHO is А (the American), Р (the
Russian), К (Katya, in one variant) or empty where the book prints no letter.
The recordings (tools/pd_courses/fast_build.py) are cut from the FSI tapes
by the words heard on them, so every Russian line here is one the tape reads."""

LESSONS = []

LESSONS.append({
    "n": 2, "ru": "География", "en": "Geography",
    "intro": [
        "Россия Russia covers more than 6.5 million square miles or, roughly speaking, an area more than twice the size "
        "of the United States. The Ural Mountains divide the country into a European (western) half and an Asian "
        "(eastern) half. To the west, Russia shares borders with Belarus, Ukraine, Latvia and Estonia. Southern Russia "
        "extends to the Caucasus Mountains, which form the frontier with Georgia and Azerbaijan. In the east, that "
        "portion of Russia known as Сибирь Siberia stretches from the Arctic Ocean in the north to Kazakhstan, Mongolia "
        "and China in the south.",
        "The southern portion of Russia is composed primarily of flat, treeless plains known as степь steppe. Siberia "
        "itself is comprised of a northern belt of permanently frozen, treeless plains тундра and, more southerly, vast "
        "evergreen forests тайга. Санкт-Петербург St. Petersburg, founded by Пётр Великий Peter the Great on the Gulf "
        "of Finland as a “window to the West”, has been nicknamed the “brain” of Russia, thanks to its regular, "
        "grid-like pattern of city planning. Москва Moscow, on the other hand, is often referred to as the “soul”, "
        "thanks to its more chaotic growth over the years and a more “Russian” look.",
    ],
    "sets": [{
        "title": "Россия и Ближнее Зарубежье", "en": "Russia and the Near Abroad",
        "lines": [
            "|Россия. Москва — столица России. В России живут русские.|Russia. Moscow is the capital of Russia. Russians live in Russia.",
            "|Украина. Киев — столица Украины. В Украине живут украинцы.|Ukraine. Kiev is the capital of Ukraine. Ukrainians live in Ukraine.",
            "|Латвия. Рига — столица Латвии. В Латвии живут латыши.|Latvia. Riga is the capital of Latvia. Latvians live in Latvia.",
            "|Литва. Вильнюс — столица Литвы. В Литве живут литовцы.|Lithuania. Vilnius is the capital of Lithuania. Lithuanians live in Lithuania.",
            "|Эстония. Таллин — столица Эстонии. В Эстонии живут эстонцы.|Estonia. Tallinn is the capital of Estonia. Estonians live in Estonia.",
            "|Молдавия. Кишинёв — столица Молдавии. В Молдавии живут молдаване.|Moldavia. Kishinev is the capital of Moldavia. Moldavians live in Moldavia.",
            "|Белоруссия. Минск — столица Белоруссии. В Белоруссии живут белорусы.|Belorussia. Minsk is the capital of Belorussia. Belorussians live in Belorussia.",
            "|Грузия. Тбилиси — столица Грузии. В Грузии живут грузины.|Georgia. Tbilisi is the capital of Georgia. Georgians live in Georgia.",
            "|Армения. Ереван — столица Армении. В Армении живут армяне.|Armenia. Yerevan is the capital of Armenia. Armenians live in Armenia.",
            "|Азербайджан. Баку — столица Азербайджана. В Азербайджане живут азербайджанцы.|Azerbaijan. Baku is the capital of Azerbaijan. Azerbaijanis live in Azerbaijan.",
            "|Узбекистан. Ташкент — столица Узбекистана. В Узбекистане живут узбеки.|Uzbekistan. Tashkent is the capital of Uzbekistan. Uzbeks live in Uzbekistan.",
            "|Казахстан. Алма-Ата — столица Казахстана. В Казахстане живут казахи.|Kazakhstan. Alma-Ata is the capital of Kazakhstan. Kazakhs live in Kazakhstan.",
            "|Туркмения. Ашхабад — столица Туркмении. В Туркмении живут туркмены.|Turkmenia. Ashkhabad is the capital of Turkmenia. Turkmens live in Turkmenia.",
            "|Таджикистан. Душанбе — столица Таджикистана. В Таджикистане живут таджики.|Tajikistan. Dushanbe is the capital of Tajikistan. Tajiks live in Tajikistan.",
            "|Киргизия. Бишкек — столица Киргизии. В Киргизии живут киргизы.|Kirghizia. Bishkek is the capital of Kirghizia. Kirghiz live in Kirghizia.",
        ],
    }],
    "words": [
        ("в", "in, inside"), ("восток; на востоке", "east; in the east"), ("вот", "here"), ("Где?", "Where?"),
        ("город", "city, town"), ("Добро пожаловать!", "Welcome!"), ("жить", "to live"),
        ("я живу, вы живёте, они живут", "I live, you live, they live"), ("запад; на западе", "west; in the west"),
        ("какой, какое, какая", "what kind of; which; which one"), ("кто", "who"), ("Кто это?", "Who is that?"),
        ("на", "on; at; in"), ("он, она, оно, они", "he; she; it; they"), ("Покажите…", "Show…"),
        ("погода", "weather"), ("север", "north"), ("столица", "capital"), ("что", "what"),
        ("Что это?", "What is this/that?"), ("юг", "south"),
    ],
})

LESSONS.append({
    "n": 3, "ru": "Знакомство", "en": "Getting Acquainted",
    "intro": [
        "There is no secret to greeting people in Russian. It can be as simple as Здравствуйте/Здравствуй! Like "
        "“Hello” in English, you can use this greeting at any time of the day and with nearly anyone. Keep in mind, "
        "however, that you will use this expression only once in the day. If you meet again later, you should greet "
        "each other using a different expression. You may use Доброе утро! Good morning! Добрый день! Good afternoon! "
        "or Добрый вечер! Good evening! depending on the time of day. More informal greetings such as Привет! Hi! or "
        "the very slangy Салют! Hey! are also possible, but you should be careful when, and with whom you use these.",
        "As we do in English, you might ask someone you know how he/she is doing: Как поживаете? How are you? Как "
        "дела? How are things (going)? Possible responses are Хорошо Fine; Нормально As usual; Ничего O.K. Unlike "
        "Americans, whose response to these questions is often nothing more than a polite “Fine, thanks.” Russians may "
        "take the time to tell you the whole truth!",
        "До свидания Good bye! (literally: “Until our next meeting.”) will work in all situations when saying good-bye. "
        "You may also use: Всего хорошего; Всего доброго! All the best. Пока! See ya! or Bye! is more casual and you "
        "should be careful when you use it, and with whom.",
        "If you need to address a stranger, or get their attention for whatever reason, you should remember the "
        "following: all strangers (except for children) should be addressed as Вы. Women in general are Девушка! "
        "(Miss!) — unless this is obviously inappropriate. Men in general are Молодой человек! (Young man!) unless, "
        "again, this is obviously inappropriate. In those situations where these are inappropriate, simply use: "
        "Простите, пожалуйста… Pardon me, please… Будьте добры… Be so kind… Скажите, пожалуйста… Tell me, please…",
    ],
    "sets": [
        {"title": "Hello!", "lines": [
            "|Здравствуйте!|Hello!", "|Доброе утро!|Good morning!", "|Добрый день!|Good afternoon!",
            "|Добрый вечер!|Good evening!", "|Привет!|Hi!"]},
        {"title": "How are you?", "lines": [
            "|Как поживаете?|How are you?", "|Как живёте?|How’s life?", "|Как дела?|How are things (going)?"]},
        {"title": "When things are going well", "lines": ["|Спасибо, хорошо.|Fine, thanks.", "|Прекрасно!|Excellent."]},
        {"title": "When things are OK", "lines": ["|Ничего.|O.K.", "|Так себе.|So-so."]},
        {"title": "When things are going badly", "lines": ["|Плохо.|Badly.", "|Неважно.|Not so well."]},
        {"title": "Good-bye", "lines": [
            "|До свидания!|Good-bye!", "|Спокойной ночи!|Good night!", "|Пока!|Bye!", "|До завтра!|See you tomorrow!",
            "|Всего хорошего!|All the best!", "|Всего доброго!|All the best!"]},
        {"title": "Getting someone’s attention", "lines": [
            "|Девушка!|Miss!", "|Молодой человек!|Young man!", "|Простите, пожалуйста…|Pardon me, please…",
            "|Будьте добры…|Be so kind…", "|Скажите, пожалуйста…|Tell me, please…"]},
    ],
    "dialogs": [
        {"kind": "dialog", "n": 1, "title": "Познакомьтесь, пожалуйста!", "en": "Please get acquainted!", "turns": [
            "Р|Здравствуйте. Давайте познакомимся. Меня зовут Владимир Николаевич.|Hello. Let me introduce myself. My name is Vladimir Nikolaevich.",
            "А|Очень приятно. Меня зовут Джон Мартинез. А как ваша фамилия?|Pleased to meet you. My name is John Martinez. What is your last name?",
            "Р|Моя фамилия Петров. Рад познакомиться. А это моя жена, Екатерина Васильевна. Познакомьтесь, пожалуйста.|My last name is Petrov. Pleased to meet you. And this is my wife, Yekaterina Vasil’evna. Please get acquainted.",
            "А|Очень рад познакомиться, Екатерина Васильевна.|Very pleased to meet you, Yekaterina Vasil’evna.",
        ]},
        {"kind": "variant", "n": 1, "turns": [
            "Р|Здравствуйте. Давайте познакомимся. Меня зовут Анна Александровна.|Hello. Let me introduce myself. My name is Anna Aleksandrovna.",
            "А|Очень приятно. Меня зовут Синди Петерсон. А как ваша фамилия?|Pleased to meet you. My name is Cindy Peterson. What is your last name?",
            "Р|Моя фамилия Морозова. Рада познакомиться. А это мой муж, Максим Дмитриевич. Познакомьтесь, пожалуйста.|My last name is Morozova. Pleased to meet you. And this is my husband, Maxim Dmitrievich. Please get acquainted.",
            "А|Очень рада познакомиться, Максим Дмитриевич.|Very pleased to meet you, Maxim Dmitrievich.",
        ]},
    ],
    "words": [
        ("вечер", "evening"), ("день", "day"), ("имя", "first name"), ("ночь", "night"),
        ("познакомиться", "to get acquainted"), ("утро", "morning"), ("хорошо", "good"), ("фамилия", "last name"),
        ("Всего доброго!", "All the best!"), ("Всего хорошего!", "All the best!"),
        ("Давайте познакомимся!", "Let’s get acquainted!"), ("Доброе утро!", "Good morning!"),
        ("Добрый день!", "Good afternoon!"), ("До свидания!", "Good-bye!"), ("Здравствуйте!", "Hello! How do you do!"),
        ("Извините (простите)…", "Excuse me…"), ("Как вас зовут?", "What is your name?"),
        ("Как ваше имя?", "What is your name?"), ("Как дела?", "How are you? How are things?"),
        ("Как живёте?", "How are you?"), ("Меня зовут…", "My name is…"), ("Моя фамилия…", "My last name is…"),
        ("Скажите, пожалуйста…", "Tell me, please…"), ("Что нового?", "What’s new?"),
    ],
})

LESSONS.append({
    "n": 4, "ru": "Семья", "en": "Family",
    "intro": [
        "A typical Russian family in a major city consists of the parents, one child and often a grandmother or "
        "grandfather or even both. While urban families are more likely to have just one child, it is not unusual to "
        "see large families in the rural areas. In the cities as well as in the country, parents will often live with "
        "their adult, married children and help raise the grandchildren. This extended family provides a certain "
        "degree of stability and security to the children and alleviates the necessity of arranging for day-care "
        "outside the home. The economic situation in Russia and the Former Soviet Union dictates today (and has "
        "historically) that both parents work to support the family. However, some things have changed and are "
        "continuing to change; you can now find mothers who do not work outside the home, though the concept of a "
        "“house-husband” is still foreign to Russians.",
        "The use of words which indicate relationships between family members is somewhat fluid. Children will often "
        "refer to adults (their parents’ acquaintances and strangers alike) as тётя Aunt or дядя Uncle. You may also "
        "hear people refer to elderly individuals, with whom they are not acquainted, as бабушка Grandma or дедушка "
        "Grandpa. The form of address will always be Вы in these cases. Though there are terms for cousins: "
        "двоюродный брат (for males) and двоюродная сестра (for females), Russians will often simply use брат or "
        "сестра.",
    ],
    "dialogs": [
        {"kind": "dialog", "n": 1, "title": "О семье", "en": "About the family",
         "setting": "A Russian and an American are discussing their families.", "turns": [
            "Р|Вы женаты?|Are you married?",
            "А|Да, женат. / Нет, не женат.|Yes, I’m married. / No, I’m not married.",
            "Р|У вас есть дети?|Do you have any children?",
            "А|Да, у меня сын и дочь.|Yes, I have a son and a daughter.",
        ]},
        {"kind": "variant", "n": 1, "turns": [
            "Р|Скажите, Линда, вы замужем?|Tell me, Linda, are you married?",
            "А|Да, замужем. / Нет, не замужем.|Yes, I’m married. / No, I’m not married.",
            "Р|У вас есть дети?|Do you have any children?",
            "А|У меня один сын.|I have one son.",
        ]},
        {"kind": "dialog", "n": 2, "turns": [
            "Р|Скажите, пожалуйста, у вас семья большая или маленькая?|Tell me, please, is your family large or small?",
            "А|Маленькая, только мама и я. А у вас?|It’s small, just my mother and I. And yours?",
            "Р|У меня большая — родители, два брата, две сестры, бабушка и дедушка.|Mine’s large: my parents, two brothers, two sisters, a grandmother and a grandfather.",
            "А|У меня тоже есть дедушка и бабушка. Они живут в Вашингтоне.|I have grandparents, too. They live in Washington.",
        ]},
        {"kind": "variant", "n": 2, "turns": [
            "Р|Скажите, пожалуйста, у вас большая семья?|Tell me, please, do you have a large family?",
            "А|Да, мать, отец, брат и сестра. А у вас?|Yes, my mother, father, brother, sister. And you?",
            "Р|Моя семья небольшая — родители и я.|My family’s not large. Just my parents and I.",
        ]},
    ],
    "words": [
        ("бабушка", "grandmother"), ("большой, большая, большое, большие", "big, large"),
        ("брат (братья)", "brother (brothers)"), ("внук", "grandson"), ("внучка", "granddaughter"),
        ("дедушка", "grandfather"), ("дети", "children"), ("дочь", "daughter"), ("дядя", "uncle"), ("жена", "wife"),
        ("женат", "married (referring to a man)"), ("замужем", "married (referring to a woman)"),
        ("маленький, маленькая, маленькое, маленькие", "small, little"), ("мать", "mother"),
        ("мой, моя, моё, мои", "my"), ("муж", "husband"), ("отец", "father"), ("племянник", "nephew"),
        ("племянница", "niece"), ("родители", "parents"), ("семья", "family"), ("сестра", "sister"), ("сын", "son"),
        ("тётя", "aunt"), ("Вы женаты?", "Are you married? (asked of men)"),
        ("Вы замужем?", "Are you married? (asked of women)"), ("Познакомьтесь…", "Get acquainted…"),
        ("Скажите, пожалуйста…", "Tell me, please…"), ("У вас есть…?", "Do you have…?"), ("У меня есть…", "I have…"),
        ("У меня нет…", "I don’t have…"),
    ],
    "numbers": [("один, одна, одно", "one"), ("два, две", "two"), ("три", "three"), ("четыре", "four"), ("пять", "five"),
                ("шесть", "six"), ("семь", "seven"), ("восемь", "eight"), ("девять", "nine"), ("десять", "ten")],
})

LESSONS.append({
    "n": 5, "ru": "Где вы работаете?", "en": "Where Do You Work?",
    "intro": [
        "Many of your acquaintances in your new country will be interested in getting to know you better. One of the "
        "things they’ll be asking will be Где вы работаете? “What do you do for a living? Where do you work?” Don’t be "
        "surprised if you’re asked questions, especially having to do with how much you are paid, which Americans "
        "would find inappropriate. During the Soviet period, wage scales were standard and common knowledge "
        "throughout the Soviet Union. A bus driver in Moscow was supposed to make as much as one in Irkutsk; a "
        "university professor in Kiev had the same salary as his counterpart in Gorky.",
        "In those years, manual labor was more highly valued (and better paid) than those professions which demanded "
        "more brain and less brawn. With the break-up of the Soviet Union and the disappearance of the communist "
        "state, the nature and scope of many professions have been altered. And as the country moves toward a market "
        "economy, new professions are appearing (мэнеджеры, банкиры, бизнесмены and others) which enjoy varying "
        "degrees of popularity and respect.",
    ],
    "dialogs": [
        {"kind": "dialog", "n": 1, "title": "Где вы работаете?", "en": "Where do you work?", "turns": [
            "Р|Скажите, пожалуйста, где вы работаете?|Tell me, please, where do you work?",
            "А|В американском посольстве.|In the American Embassy.",
            "Р|Кто вы по специальности?|What do you do? (What is your profession?)",
            "А|По специальности я экономист. Я очень люблю свою специальность. А кто вы?|I am an economist. I really like my profession. And what do you do?",
            "Р|Я инженер-механик. Работаю на авиационном заводе.|I am a mechanical engineer. I work at an aviation factory.",
        ]},
        {"kind": "variant", "n": 1, "turns": [
            "Р|Скажите, пожалуйста, где вы работаете?|Tell me, please, where do you work?",
            "А|Я работаю в Министерстве иностранных дел (в МИДе).|I work at the Ministry of Foreign Affairs.",
            "Р|А кто вы по специальности?|What do you do?",
            "А|Я секретарь, работаю в информационном отделе.|I am a secretary. I work in the information division.",
            "Р|Вы любите свою работу?|Do you like your work?",
            "А|Да, конечно. Очень люблю.|Yes, of course. I like it very much.",
        ]},
    ],
    "words": [
        ("администратор", "administrator"), ("военный атташе", "defense attaché"), ("дипломат", "diplomat"),
        ("инженер (-механик)", "engineer (mechanical)"), ("консул", "consul"), ("любить", "to love, to like"),
        ("я люблю, он любит, вы любите", "I love, he loves, you love"), ("министерство", "department, ministry"),
        ("отдел", "section"), ("посол", "ambassador"), ("посольство", "embassy"), ("работать", "to work"),
        ("я работаю, он работает, вы работаете", "I work, he works, you work"), ("работа", "work, job"),
        ("секретарь", "secretary"), ("специальность", "area of specialization"), ("Конечно!", "Of course! Certainly!"),
        ("Кто вы по специальности?", "What do you do?"), ("Где вы работаете?", "Where do you work?"),
        ("Где американское посольство?", "Where is the American Embassy?"),
        ("Вы любите свою работу?", "Do you like your job?"),
    ],
    "numbers": [("одиннадцать", "eleven"), ("двенадцать", "twelve"), ("тринадцать", "thirteen"),
                ("четырнадцать", "fourteen"), ("пятнадцать", "fifteen"), ("шестнадцать", "sixteen"),
                ("семнадцать", "seventeen"), ("восемнадцать", "eighteen"), ("девятнадцать", "nineteen"),
                ("двадцать", "twenty")],
})

LESSONS.append({
    "n": 6, "ru": "Где вы живёте?", "en": "Where Do You Live?",
    "intro": [
        "«В гостях хорошо, а дома лучше» as the Russians say: “There’s no place like home”. And this is true even if "
        "home is in the taiga in Siberia, down along the Volga or beyond the Ural mountains. Russians in the major "
        "metropolitan areas and the larger cities live in high-rise apartment buildings, whereas those in the rural "
        "areas tend to live in single-family homes. A drive through провинция the provinces will reward you with "
        "glimpses of those homes which are usually wooden, single-story and often brightly painted and decorated. "
        "Quite a contrast to the concrete monsters in the major urban areas!",
        "Housing, whether in terms of quality or quantity, has always been a problem in Russia and continues to be so "
        "today. The recent move toward privatization has made it possible for some Russians to buy their apartments "
        "from the government; others must continue to live in government-owned and subsidized housing. But many "
        "Russians still find themselves in situations where multiple families have individual rooms in a коммуналка "
        "communal apartment and others must live in cramped quarters with their extended families.",
    ],
    "dialogs": [
        {"kind": "dialog", "n": 1, "title": "Где вы живёте?", "en": "Where do you live?", "turns": [
            "Р|Линда, я переехал на новую квартиру.|Linda, I moved to a new apartment.",
            "А|Поздравляю! А где ваша новая квартира?|Congratulations! Where is your new apartment?",
            "Р|Недалеко от станции метро «Проспект Мира».|Not far from the Metro Station “Prospect Mira”.",
            "А|А какой у вас адрес?|What is your address?",
            "Р|Проспект Мира, дом 2, квартира 5.|Prospect Mira, building 2, apartment 5.",
        ]},
        {"kind": "variant", "n": 1, "turns": [
            "Р|Катя, я переехал в новый дом.|Katya, I moved to a new house.",
            "К|Поздравляю! А где ваш новый дом?|Congratulations! Where is your new house?",
            "Р|Далеко, в новом районе, в Росинке.|It’s far away, in a new district, in Rosinka.",
            "К|А какой у вас адрес?|What’s your address?",
            "Р|Росинка, 720.|720 Rosinka.",
        ]},
        {"kind": "dialog", "n": 2, "turns": [
            "Р|Линда, скажите, пожалуйста, где вы сейчас живёте?|Linda, please tell me, where are you living now?",
            "А|Сейчас я живу в Росинке, недалеко от Москвы.|I live in Rosinka now, not far from Moscow.",
            "Р|А где вы жили в Америке?|And where did you live in America?",
            "А|Я жила в штате Мэриленд.|I lived in Maryland.",
            "Р|Вы жили в доме или в квартире?|Did you live in a house or in an apartment?",
            "А|Я жила в доме.|I lived in a house.",
        ]},
        {"kind": "variant", "n": 2, "turns": [
            "Р|Марк, скажите, пожалуйста, где вы сейчас живёте?|Mark, tell me please, where do you live now?",
            "А|Сейчас я живу на Ленинском проспекте, недалеко от центра города.|I live on Leninskiy Prospect now, not far from the center of the city.",
            "Р|А где вы жили в Америке?|And where did you live in America?",
            "А|Я жил в Нью-Йорке.|I lived in New York.",
            "Р|Вы жили в доме или в квартире?|Did you live in a house or an apartment?",
            "А|Я жил в квартире.|I lived in an apartment.",
        ]},
    ],
    "words": [
        ("адрес", "address"), ("бульвар", "boulevard, avenue"), ("далеко", "far, far away"), ("дом", "house, home"),
        ("квартира", "apartment"), ("недалеко", "not far, not far away"), ("новый, новая, новое, новые", "new"),
        ("переехать", "to move"), ("переулок", "lane, side street"), ("проспект", "avenue"),
        ("район", "district, area"), ("улица", "street"), ("штат", "state (in the United States)"),
        ("Я переехал(а).", "I moved."), ("Поздравляю!", "Congratulations!"), ("Где вы живёте?", "Where do you live?"),
        ("Где вы жили?", "Where did you live?"), ("Какой у вас адрес?", "What is your address?"),
        ("Вы живёте в доме?", "Do you live in a house?"), ("Вы живёте в квартире?", "Do you live in an apartment?"),
        ("Я жил(а) в штате…", "I lived in the state of…"),
    ],
    "numbers": [("двадцать", "twenty"), ("двадцать один", "twenty-one"), ("двадцать два", "twenty-two"),
                ("тридцать", "thirty"), ("тридцать три", "thirty-three"), ("сорок", "forty"),
                ("сорок пять", "forty-five"), ("пятьдесят", "fifty"), ("пятьдесят семь", "fifty-seven"),
                ("шестьдесят", "sixty"), ("шестьдесят девять", "sixty-nine"), ("семьдесят", "seventy"),
                ("восемьдесят", "eighty"), ("девяносто", "ninety"), ("сто", "one hundred"),
                ("сто один", "one hundred and one"), ("сто два", "one hundred and two")],
})

LESSONS.append({
    "n": 7, "ru": "Покупки", "en": "Shopping",
    "intro": [
        "Thanks to the inroads capitalism has made into Russia, shopping is less of a chore than it ever used to be. "
        "During the Soviet period, when various goods would disappear from the state-owned stores, usually with little "
        "or no warning and for no apparent reasons, the foreign community (with its валюта hard currency) nearly "
        "always had everything it needed or wanted, thanks to the stores known as Берёзка which were off-limits to "
        "Soviet citizens. Today, however, Moscow and St. Petersburg and to a lesser extent the capitals of the Newly "
        "Independent States are inundated with stores which sell those same goods openly and at prices which are on "
        "a par with those in Western Europe and the US.",
        "Today there are very few things which you will be unable to purchase in Moscow or St. Petersburg. Whether it "
        "is a Cadillac Seville or Arrow shirts, you can be pretty certain that somewhere in the city there’s somebody "
        "selling just what you need. The big problem today is not whether or not you CAN buy something, but WHERE "
        "you’re going to find it in the forest of new stores that has replaced the simple берёзки. (The prices in the "
        "dialogues are those of 1994, in the roubles of the day.)",
    ],
    "dialogs": [
        {"kind": "dialog", "n": 1, "title": "В магазине «Подарки»", "en": "In the “Gifts” store",
         "setting": "An American is buying a матрёшка wooden nesting doll at «Подарки» “Gifts”.", "turns": [
            "А|Девушка!|Miss!",
            "Р|Да. Что вы хотите?|Yes. What do you want?",
            "А|Покажите, пожалуйста, матрёшку.|Show me a matryoshka, please.",
            "Р|Какую матрёшку вам показать? Вот эту?|Which one do you want me to show you? This one?",
            "А|Да, пожалуйста, эту. Сколько она стоит?|Yes, please, this one. How much is it?",
            "Р|Тридцать пять тысяч рублей.|35,000 roubles.",
            "А|Сколько?|How much?",
            "Р|Тридцать пять тысяч рублей. Платите в кассу.|35,000 roubles. Pay at the register.",
        ]},
        {"kind": "variant", "n": 1, "turns": [
            "А|Молодой человек!|Young man!",
            "Р|Да…|Yes?..",
            "А|Я хочу купить платок.|I want to buy a shawl.",
            "Р|Какой платок вам показать? Вот этот?|Which one would you like me to show you? This one?",
            "А|Да, пожалуйста, этот. Сколько он стоит?|Yes, please, this one. How much is it?",
            "Р|Семьдесят тысяч рублей.|70,000 roubles.",
            "А|Сколько?|How much?",
            "Р|Семьдесят тысяч рублей. Платите в кассу.|70,000 roubles. Pay at the register.",
        ]},
        {"kind": "dialog", "n": 2, "title": "На Центральном рынке", "en": "At the Central Market",
         "setting": "The American is going to the market.", "turns": [
            "А|Девушка, почём яблоки?|Miss, how much are the apples?",
            "Р|Три тысячи рублей килограмм.|3,000 roubles a kilogram.",
            "А|Дайте два килограмма.|Give me two kilograms.",
            "Р|Вот, пожалуйста.|Here you go.",
            "А|Спасибо.|Thank you.",
        ]},
        {"kind": "variant", "n": 2, "turns": [
            "А|Молодой человек! Сколько стоит кило апельсинов?|Young man! How much is a kilo of oranges?",
            "Р|Шесть тысяч рублей.|6,000 roubles.",
            "А|Дайте, пожалуйста, три кило.|Please give me three kilos.",
            "Р|Вот, пожалуйста.|Here you go.",
            "А|Спасибо.|Thanks.",
        ]},
        {"kind": "dialog", "n": 3, "title": "В гастрономе", "en": "In the grocery store",
         "setting": "The American is in a гастроном grocery store, at the dairy counter.", "turns": [
            "А|Скажите, пожалуйста, у вас есть молоко?|Please tell me, do you have any milk?",
            "Р|Утром было, а сейчас уже нет.|We had some this morning, but now we’re all out.",
            "А|А творог есть?|How about cottage cheese?",
            "Р|Творог есть.|We have cottage cheese.",
            "А|А сколько стоит творог?|How much is the cottage cheese?",
            "Р|Восемьсот рублей килограмм.|800 roubles per kilogram.",
            "А|Взвесьте, пожалуйста, полкило.|Please weigh half a kilo.",
            "Р|Четыреста рублей. Платите в кассу.|Pay the cashier 400 roubles.",
            "А|Хорошо.|O.K.",
            "-|У кассы|At the cash register",
            "А|Четыреста рублей, пожалуйста.|400 roubles, please.",
            "Р|В какой отдел?|Which section?",
            "А|В молочный.|Dairy.",
            "Р|Пожалуйста.|Here you go.",
            "А|Спасибо.|Thank you.",
            "-|В молочном|At the dairy counter",
            "А|Вот чек, пожалуйста.|Here’s my receipt.",
            "Р|Пожалуйста, ваш творог.|And here’s your cottage cheese.",
        ]},
        {"kind": "dialog", "n": 4, "title": "В гастрономе", "en": "In the grocery store",
         "setting": "The American is now at the deli counter.", "turns": [
            "А|Скажите, пожалуйста, у вас есть докторская колбаса?|Please tell me, do you have “Doctorskaya” sausage?",
            "Р|Да, есть. Вам сколько?|Yes. How much do you want?",
            "А|Дайте, пожалуйста, триста грамм.|Give me 300 grams, please.",
            "Р|Что ещё?|What else?",
            "А|Это всё.|That’s it.",
            "Р|Пятьсот рублей. Платите в кассу.|That’s 500 roubles. Pay at the register.",
        ]},
        {"kind": "variant", "n": 4, "turns": [
            "А|Простите, у вас есть белый хлеб?|Excuse me. Do you have any white bread?",
            "Р|Конечно есть. Какой вам?|Of course we do. What kind would you like?",
            "А|Дайте, пожалуйста, батон.|Give me a baguette, please.",
            "Р|Пожалуйста. Что ещё?|Here you are. What else?",
            "А|И буханку чёрного хлеба.|And a loaf of black bread.",
            "Р|Пожалуйста. Две тысячи четыреста рублей. Платите в кассу.|Here you go. That’ll be 2,400 roubles. Pay at the register.",
        ]},
        {"kind": "dialog", "n": 5, "title": "В комиссионном магазине", "en": "In the consignment store",
         "setting": "On our last shopping trip we’re going to a комиссионный магазин consignment store or second-hand store, "
                    "a good place to buy antiques, samovars, lithographs, silver, etc.", "turns": [
            "А|Я хочу купить самовар.|I want to buy a samovar.",
            "Р|У нас есть разные самовары. Посмотрите, пожалуйста.|We have all different kinds of samovars. Take a look.",
            "А|Покажите этот маленький.|Show me that little one.",
            "Р|Это очень хороший старый тульский самовар.|This is a very good old samovar, made in Tula.",
            "А|Да, он мне нравится! Сколько он стоит?|Oh yes, I like it! How much is it?",
            "Р|Четыреста тысяч рублей.|Four hundred thousand roubles.",
            "А|А самовары можно вывозить из страны?|Can samovars be exported?",
            "Р|Да, конечно можно.|Yes, of course.",
            "А|Прекрасно! Я беру.|Great! I’ll take it.",
        ]},
    ],
    "words": [
        ("бусы", "beads"), ("бутылка", "bottle"), ("гастроном", "grocery store"), ("деньги", "money"),
        ("игрушка", "toy"), ("карандаш", "pencil"), ("картина", "painting"), ("касса", "cash register"),
        ("книга", "book"), ("колбаса", "sausage"), ("кольцо", "ring"), ("купить", "to buy"), ("магазин", "store"),
        ("матрёшка", "Russian wooden nesting doll"), ("молоко", "milk"), ("молочный", "milk (adj.)"),
        ("обувь", "shoes (footwear)"), ("одежда", "clothes"), ("платить", "to pay"), ("платок", "shawl, scarf"),
        ("подарок", "present, gift"), ("показать", "to show"), ("понимать", "to understand"), ("портфель", "briefcase"),
        ("продукты", "groceries"), ("рубль (рубля, рублей)", "rouble (roubles)"), ("ручка", "pen"),
        ("рынок (на рынке)", "farmer’s market"), ("сейчас", "now"), ("серьги", "earrings"), ("серый", "grey"),
        ("сколько?", "how much? how many?"), ("сумка", "bag, purse"), ("творог", "cottage cheese"), ("ткани", "fabrics"),
        ("туфли", "shoes"), ("уже", "already"), ("утром", "in the morning"), ("хлеб", "bread"), ("хотеть", "to want"),
        ("я хочу, он хочет, вы хотите", "I want, he wants, you want"), ("часы", "watch"), ("шапка", "hat"),
        ("штука", "piece"), ("этот, это, эта, эти", "this, these"), ("ювелирный", "jewelry (adj.)"), ("янтарь", "amber"),
        ("Дайте, пожалуйста…", "Give me, please…"), ("Девушка!", "Miss!"), ("Молодой человек!", "Young man!"),
        ("Платите в кассу.", "Pay at the cash register."), ("Покажите, пожалуйста…", "Show me, please…"),
        ("Сколько стоит…?", "How much does… cost?"), ("Что вы хотите?", "What do you want?"),
        ("У вас есть…?", "Do you have…?"),
    ],
    "numbers": [("сто", "one hundred"), ("двести", "two hundred"), ("триста", "three hundred"),
                ("четыреста", "four hundred"), ("пятьсот", "five hundred"), ("шестьсот", "six hundred"),
                ("семьсот", "seven hundred"), ("восемьсот", "eight hundred"), ("девятьсот", "nine hundred"),
                ("тысяча", "one thousand"), ("две, три, четыре тысячи", "two, three, four thousand"),
                ("пять тысяч", "five thousand")],
})

LESSONS.append({
    "n": 8, "ru": "В ресторане", "en": "In a Restaurant",
    "intro": [
        "«Щи да каша, пища наша» “A loaf of bread, a jug of wine…” If only it were that simple! Food: how to get it, "
        "how to cook it and finally, how to eat it, has occupied the thoughts of Russians in everything from classic "
        "works of literature to everyday life. Open Gogol’s famous novel «Мёртвые души» Dead Souls to almost any page, "
        "and you’ll be greeted with detailed descriptions of all kinds of culinary delights as experienced by the "
        "intrepid Chichikov. Even the casual reader of Russian literature or the viewer of Russian painting will find "
        "that food has played an integral part in Russian life down through the years, across class lines and in and "
        "out of the arts.",
        "Moscow and St. Petersburg alike now boast a large number of restaurants which cater to nearly every cuisine "
        "and taste imaginable. As with stores, some of these are foreign-owned, some are joint ventures and still "
        "others belong wholly to Russians. In any case, you will find that together with variety comes "
        "unpredictability: high-priced isn’t always a guarantee of high-quality; high-quality one day does not "
        "guarantee it the next… Though a service charge of 15% is usually included in most restaurant checks, you may "
        "also tip the usual 15%–20%. Either leave it on the table when you leave or use the phrase Сдачи не надо Keep "
        "the change. You usually pay your server, and not at the door.",
    ],
    "dialogs": [
        {"kind": "dialog", "n": 1, "title": "В ресторане", "en": "In a restaurant", "turns": [
            "А|Скажите, пожалуйста, этот столик свободен?|Pardon me, is this table free?",
            "Р|Да, садитесь, пожалуйста. Вот меню.|Yes. Please, have a seat. Here’s a menu.",
            "А|Спасибо.|Thank you.",
            "Р|Что будете заказывать?|What will you be ordering?",
        ]},
        {"kind": "variant", "n": 1, "turns": [
            "А|У вас есть свободный стол?|Do you have any free tables?",
            "Р|Да, пожалуйста, вот этот.|Yes, this one is free.",
            "А|Принесите, пожалуйста, меню.|Bring me a menu, please.",
            "Р|Одну минуту, сейчас принесу.|Just a minute. I’ll get it for you.",
        ]},
        {"kind": "dialog", "n": 2, "title": "В ресторане", "en": "In a restaurant", "turns": [
            "А|Девушка, примите, пожалуйста, заказ.|Excuse me, Miss! Could you please take my order?",
            "Р|Я вас слушаю.|I’m listening.",
            "А|На закуску принесите, пожалуйста, чёрную икру.|For an appetizer, please bring me some black caviar.",
            "Р|Чёрной икры нет. Есть только красная.|There’s no black caviar, just red.",
            "А|Хорошо. Принесите красную.|OK. Bring me the red.",
            "Р|Что вы хотите на первое?|What would you like for the first course?",
            "А|На первое борщ.|I would like some borshch.",
            "Р|А что на второе?|And what about the main course?",
            "А|На второе котлеты по-киевски с гарниром.|I would like Chicken Kiev and vegetables.",
            "Р|Сладкое будете заказывать?|Are you going to order dessert?",
            "А|Принесите мороженое и кофе.|Ice cream and some coffee.",
            "Р|Что ещё?|What else?",
            "А|Это всё. Спасибо.|That’s all, thank you.",
        ]},
        {"kind": "dialog", "n": 3, "title": "Принесите счёт", "en": "Bring the check",
         "setting": "The American is paying for a meal in a restaurant.", "turns": [
            "А|Девушка, принесите, пожалуйста, чек.|Miss, bring the check, please.",
            "Р|Одну минуту. Вам вместе или отдельно?|Just a minute. Do you want one check or separate checks?",
            "А|Вместе, пожалуйста.|One check, please.",
            "Р|Вот ваш счёт.|Here you go.",
            "А|Пожалуйста, получите. Сдачи не надо.|Thanks. Keep the change.",
        ]},
    ],
    "words": [
        ("блюдо", "dish; course"), ("блюдце", "saucer"), ("вместе", "together"), ("вилка", "fork"),
        ("гарнир", "side dishes"), ("грязный, грязное, грязная, грязные", "dirty; soiled"),
        ("другой, другое, другая, другие", "another (one); other"), ("завтрак", "breakfast"),
        ("заказывать/заказать", "to order"), ("закуски", "hors d’oeuvres"), ("занят", "occupied"),
        ("кружка", "(beer) mug"), ("ложка", "spoon"), ("нож", "knife"), ("обед", "lunch/dinner"),
        ("официант/официантка", "waiter/waitress"), ("отдельно", "separately, individually"),
        ("первое", "first course"), ("повар/шеф-повар", "chef (cook)"), ("порция", "portion, serving"),
        ("рюмка", "wine glass"), ("салфетка", "napkin"), ("свободен", "free, unoccupied, vacant"),
        ("сладкое/десерт", "dessert"), ("стакан", "(water) glass"), ("стол, столик", "table"), ("счёт", "check, bill"),
        ("тарелка", "plate"), ("ужин", "supper"), ("чашка", "cup"), ("чек", "check, receipt, bill"),
        ("Я хочу заказать столик.", "I would like to reserve a table."), ("Это всё.", "That’s all."),
        ("Этот столик свободен?", "Is this table free?"), ("Этот столик занят.", "This table is occupied."),
        ("Примите заказ.", "Take our order."), ("У вас есть…?", "Do you have…?"),
        ("Принесите, пожалуйста…", "Please bring…"), ("Что ещё?", "What else?"), ("Больше ничего.", "Nothing else."),
        ("Сколько с меня?", "How much do I owe you?"), ("Получите, пожалуйста.", "Here you go. (when paying)"),
        ("Сдачи не надо.", "Keep the change."),
    ],
})

LESSONS.append({
    "n": 9, "ru": "Транспорт", "en": "Transportation",
    "intro": [
        "Many of you may decide to take your car with you to Moscow, St. Petersburg or to one of the other posts in "
        "the Former Soviet Union. The ГАИ (Государственная автоинспекция) are the Russian traffic cops (not to be "
        "confused with the милиция police). Always wear your seat belt. Not only is this a good safety practice, but "
        "you may be pulled over by a traffic cop and fined if you’re not wearing one. The speed limit in the city is "
        "60 kph (35 mph). Speed limits outside the city vary from 90–120 kph (55–65 mph). There is no “right turn on "
        "red”. Look for turn signs at all intersections which will indicate which turns are permitted.",
        "The dialogues take you through the Moscow metro, with its Кольцевая линия Ring Line and its переходы "
        "transfers, and onto the buses, where in 1994 a талон ticket bought in a книжечка booklet was punched in the "
        "компостер on board.",
    ],
    "dialogs": [
        {"kind": "dialog", "n": 1, "title": "Как доехать до…?", "en": "How do I get to…?", "turns": [
            "А|Скажите, пожалуйста, как доехать до американского посольства?|Could you please tell me how to get to the American Embassy?",
            "Р|Вы хотите ехать на метро?|Do you want to take the metro?",
            "А|Да, конечно.|Of course.",
            "Р|Вам нужно доехать до станции «Краснопресненская». Это третья станция. Оттуда вы можете дойти пешком до посольства.|You have to take it to the station called “Krasnopresnenskaya”. It’s the third one. From there you can walk to the Embassy.",
            "А|Спасибо большое!|Thank you very much.",
            "Р|Не за что.|Don’t mention it.",
        ]},
        {"kind": "variant", "n": 1, "v": 1,
         "setting": "The American has just arrived by train from St. Petersburg. He/She’s at the Ленинградский вокзал "
                    "(Metro «Комсомольская») and needs to get to the hotel «Метрополь».", "turns": [
            "А|Простите, пожалуйста, как доехать до гостиницы «Метрополь»?|Excuse me, please. How do I get to the hotel “Metropol”?",
            "Р|Отсюда очень просто. Вам нужно доехать до станции «Охотный ряд». Потом пешком до гостиницы.|It’s easy from here. You need to get to the station called “Okhotny ryad”. Then you can walk to the hotel.",
            "А|«Охотный ряд»? Это какая станция?|“Okhotny ryad”? Which station is that?",
            "Р|Это третья станция.|It’s the third one.",
            "А|Понятно. Спасибо.|Got it. Thanks.",
            "Р|Пожалуйста.|Don’t mention it.",
        ]},
        {"kind": "variant", "n": 1, "v": 2,
         "setting": "The American has left the Embassy, is at metro «Краснопресненская» and would like to get out to the "
                    "“flea market” at Измайловский парк.", "turns": [
            "А|Скажите, пожалуйста, как доехать до станции «Измайловский парк»?|Could you please tell me how to get to “Izmailovsky Park”?",
            "Р|Вам нужно доехать по «Кольцу» до станции «Курская» и там сделать пересадку.|You need to take the “Ring” line to station “Kurskaya” and transfer there.",
            "А|Спасибо. А потом?|Thanks. And then what?",
            "Р|А потом до станции «Измайловский парк».|Then take it to “Izmailovsky Park”.",
        ]},
        {"kind": "dialog", "n": 2, "title": "Какая следующая станция?", "en": "What’s the next station?", "turns": [
            "А|Извините, какая следующая станция?|Excuse me, what’s the next station?",
            "Р|«Беговая».|“Begovaya”.",
            "А|А скоро будет «Краснопресненская»?|Is “Krasnopresnenskaya” coming up soon?",
            "Р|«Краснопресненскую» уже проехали.|We already passed “Krasnopresnenskaya”.",
            "А|Что же мне делать?|What should I do?",
            "Р|Вам надо выйти на следующей станции и ехать в обратную сторону.|You need to get off at the next station and go back.",
            "А|Спасибо.|Thanks.",
        ]},
        {"kind": "dialog", "n": 3, "title": "Вы сейчас выходите?", "en": "Are you getting off now?", "turns": [
            "А|Вы сейчас выходите?|Are you getting off now?",
            "Р|Это какая станция?|What station is this?",
            "А|«Кропоткинская».|“Kropotkinskaya”.",
            "Р|Нет, не выхожу.|No, I’m not.",
            "А|Тогда разрешите пройти.|Then let me through.",
            "Р|Пожалуйста.|Go ahead.",
            "А|Спасибо.|Thanks.",
        ]},
        {"kind": "dialog", "n": 4, "title": "Где здесь переход?", "en": "Where’s the transfer?", "turns": [
            "А|Скажите, пожалуйста, это переход на «Кольцевую линию»?|Excuse me, is this the transfer to the Ring Line?",
            "Р|Нет, это выход в город.|No, this is the exit to the city.",
            "А|А где здесь переход?|Then where’s the transfer?",
            "Р|Переход на «Кольцевую линию» направо.|The transfer to the Ring Line is to the right.",
        ]},
        {"kind": "dialog", "n": 5, "title": "Как дойти до американского посольства?", "en": "How do I get to the American Embassy?",
         "setting": "The American is in the «Краснопресненская» metro and now needs to get to the Embassy.", "turns": [
            "А|Простите, как дойти до американского посольства?|Excuse me, how do I get to the American Embassy?",
            "Р|Это очень просто. Вам надо выйти из метро на Новинский бульвар и пройти два квартала.|It’s very simple. You have to go out of the metro onto Novinsky Boulevard and go two blocks.",
            "А|В какую сторону?|In which direction?",
            "Р|Направо. Вы увидите большое жёлтое здание с американским флагом. Это и есть посольство.|Right. You’ll see a big yellow building with an American flag. That’s the Embassy.",
            "А|Большое спасибо.|Thank you very much.",
            "Р|Не за что.|Don’t mention it.",
        ]},
        {"kind": "variant", "n": 5,
         "setting": "The American has just come out of the «Кропоткинская» metro and needs to get to the Canadian Embassy.", "turns": [
            "А|Вы не скажете, как дойти до канадского посольства?|Could you tell me how to get to the Canadian Embassy?",
            "Р|Вам нужно пройти три квартала, потом повернуть направо. Там будет канадское посольство.|You have to go three blocks and then turn right. The Canadian Embassy will be right there.",
            "А|Значит, прямо, а потом налево?|So, straight and then to the left?",
            "Р|Нет, нет! Прямо, а потом направо.|No, no! Straight and then right.",
            "А|Понял, направо. Спасибо.|I understand, right. Thanks.",
            "Р|Пожалуйста.|You’re welcome.",
        ]},
        {"kind": "dialog", "n": 6, "title": "На остановке автобуса", "en": "At the bus stop", "turns": [
            "А|Вы не знаете, какой автобус идёт в центр?|Do you know which bus goes downtown?",
            "Р|А куда именно?|Where exactly?",
            "А|Я еду в Большой театр.|I’m going to the Bolshoy Theater.",
            "Р|Вам нужно сесть на автобус номер 122 и доехать до остановки «Большой театр».|You need to take bus #122 to the stop marked “Bolshoy Teatr”.",
            "А|Спасибо.|Thank you.",
            "Р|Не за что.|Don’t mention it.",
        ]},
        {"kind": "variant", "n": 6, "turns": [
            "А|Простите, этот автобус идёт до станции метро «Аэропорт»?|Excuse me, does this bus go to the metro station “Aeroport”?",
            "Р|Нет. Вам в другую сторону. Ваша остановка там, напротив. Видите?|No. You have to go in the opposite direction. Your stop is over there, across the street. Do you see it?",
            "А|Да, вижу. Спасибо.|Yes, I do. Thank you.",
            "Р|Пожалуйста.|Don’t mention it.",
        ]},
        {"kind": "dialog", "n": 7, "title": "В автобусе", "en": "On the bus",
         "setting": "«Талоны продаются только на остановках!» Tickets are sold only at the stops!", "turns": [
            "А|Простите, у вас есть книжечки?|Excuse me, do you have any books of tickets?",
            "Р|Есть.|Yes, we do.",
            "А|Сколько стоит?|How much are they?",
            "Р|Шесть тысяч.|Six thousand roubles.",
            "А|Дайте, пожалуйста, одну.|Give me a book, please.",
            "Р|Пожалуйста.|Here you go.",
        ]},
        {"kind": "dialog", "n": 8, "turns": [
            "А|Простите, где пробить талон?|Pardon me, where do I validate this ticket?",
            "Р|Вон там компостер.|The punch is over there.",
            "А|Передайте, пожалуйста.|Could you pass my ticket over there, please?",
        ]},
        {"kind": "dialog", "n": 9, "turns": [
            "А|Вы выходите на следующей?|Are you getting off at the next stop?",
            "Р|Нет, не выхожу.|No, I’m not.",
            "А|Разрешите пройти.|Then let me through, please.",
            "Р|Пожалуйста.|Go ahead.",
        ]},
        {"kind": "dialog", "n": 10, "turns": [
            "А|Молодой человек, какая следующая остановка?|Young man, what’s the next stop?",
            "Р|«Аптека».|“Apteka”.",
            "А|Вы выходите на следующей?|Are you getting off at the next stop?",
            "Р|Да, выхожу.|Yes, I am.",
        ]},
    ],
    "words": [
        ("билет", "ticket"), ("вверх", "up (direction)"), ("вниз", "down (direction)"), ("вход", "entrance"),
        ("выход", "exit"), ("выходить, выйти", "to exit, go out"), ("гостиница", "hotel"), ("делать", "to do, to make"),
        ("доехать до…", "to get to, to get as far as"), ("жетон", "token"), ("за угол (Куда?)", "around the corner (direction)"),
        ("за углом (Где?)", "around the corner (location)"), ("квартал", "block"), ("книжечка", "booklet"),
        ("Кольцевая линия", "Ring Line"), ("куда?", "where? (direction)"), ("на углу", "on the corner"),
        ("налево", "to the left, on the left"), ("направо", "to the right, on the right"),
        ("напротив", "opposite, across"), ("обратный", "back, reverse"), ("объезд", "detour"), ("отсюда", "from here"),
        ("передать", "to pass, hand over"), ("пересадка", "transfer"), ("переход", "crosswalk; transfer"),
        ("пешком", "on foot"), ("повернуть", "to turn"), ("подземный переход", "underground passage, crosswalk"),
        ("потом", "then, after"), ("пробить", "to punch (a ticket)"), ("проехать", "to pass, drive through"),
        ("проход", "passage"), ("прямо", "straight ahead"), ("скоро", "soon"), ("следующий, -ая, -ее, -ие", "next"),
        ("стоянка такси", "taxi stand"), ("талон", "ticket"), ("туда", "there (direction), that way"),
        ("Как дойти до…?", "How do I get to…? (on foot)"), ("Как доехать до…?", "How do I get to…? (by car)"),
        ("Какая следующая станция?", "What’s the next station?"), ("Какая следующая остановка?", "What’s the next stop?"),
        ("Вы (сейчас) выходите?", "Are you getting off?"), ("Разрешите пройти.", "Please let me through."),
        ("Не за что.", "Don’t mention it."),
    ],
})

LESSONS.append({
    "n": 10, "ru": "В гостинице", "en": "In a Hotel",
    "intro": [
        "As in most countries, when traveling in Russia you should make hotel reservations ahead of time. There are "
        "no “motels”, as we in the US understand that word, where you have a chance of getting accommodations without "
        "reservations. In the major cities (Moscow, St. Petersburg and the capitals of the NIS countries), there are "
        "many Western-owned and operated hotels which offer all the comforts and services we are accustomed to. When "
        "you arrive, tell the desk clerk that you have a reservation: Для меня забронирован номер. I have a "
        "reservation.",
        "When checking in, you’ll be asked to show your passport for registration purposes. In the large cities, the "
        "desk clerk will give you a пропуск/карта гостя room card (with your name and room number on it) together "
        "with your ключ room key. Keep this card handy as often you’ll be asked to show it to the doorman to get in, "
        "especially if you return late in the evening. In hotels in the smaller cities when you go out, you will "
        "probably be asked to leave your key with the woman responsible for your floor. She’ll ask you to show your "
        "room card when you return and want to pick up your key. This procedure is less common, however, in the "
        "larger cities, though you will have a дежурная floor lady. These are good people to get to know.",
    ],
    "dialogs": [
        {"kind": "dialog", "n": 1, "title": "Я еду в командировку", "en": "I’m going on a business trip",
         "setting": "An American calls a travel agency to reserve a hotel room.", "turns": [
            "Р|«Американ Экспресс». Соколова слушает.|“American Express”. Sokolova here.",
            "А|Здравствуйте. Это говорит Джон Смит из американского посольства.|Hello. This is John Smith from the American Embassy.",
            "Р|Доброе утро. Чем могу помочь?|Good morning. How can I help you?",
            "А|Во вторник я еду в командировку в Санкт-Петербург. Я хочу забронировать номер в гостинице.|On Tuesday I’m going to St. Petersburg on a business trip. I want to reserve a hotel room.",
            "Р|Пожалуйста. Рекомендую вам гостиницу «Европейская». Она в самом центре города, и номера там очень удобные.|Fine. I can recommend the “Evropeiskaya”. It’s right in the center of town, and the rooms are very nice.",
            "А|Хорошо. Это меня устраивает.|That suits me just fine.",
            "Р|Так, вам номер на одного?|Good. Will you need a single?",
            "А|Да, пожалуйста, на одного. Я один.|Yes, a single. I’m travelling alone.",
            "Р|Хорошо. А на сколько суток вам нужен номер?|Fine. And how long will you be staying?",
            "А|На трое суток. Скажите, сколько будет стоить номер?|Three days. How much will the room cost?",
            "Р|Сто тысяч рублей в сутки, завтрак включён.|100,000 roubles a night, breakfast included.",
            "А|Прекрасно. Спасибо большое.|Wonderful! Thanks a lot!",
            "Р|Не за что. Счастливого пути!|Don’t mention it. Bon voyage!",
        ]},
        {"kind": "variant", "n": 1, "turns": [
            "Р|«Интурист». Жуковский слушает.|“Intourist”. Zhukovsky speaking.",
            "К|Добрый день. Это говорит Линда Дэйвис из канадского посольства.|Hello. This is Linda Davis from the Canadian Embassy.",
            "Р|Здравствуйте. Чем могу помочь?|Hello. How can I help you?",
            "К|В среду я еду в командировку в Ялту. Мне надо забронировать номер в гостинице.|On Wednesday I’m leaving for Yalta on business. I need to make a hotel reservation.",
            "Р|Пожалуйста. Рекомендую вам гостиницу «Жемчуг». Она совсем новая, и номера там очень хорошие.|Fine. I can recommend the “Zhemchug”. It’s brand new and the rooms are very nice.",
            "К|Хорошо, это меня устраивает.|Good. That suits me fine.",
            "Р|Вам какой номер нужен? На одного?|What kind of room do you need? A single?",
            "К|Нет, на двоих. Я еду с мужем.|No, a double. I’m going with my husband.",
            "Р|Хорошо. А на сколько суток вам нужен номер?|Fine. How long will you be staying?",
            "К|На трое суток. Скажите, сколько будет стоить номер?|Three days. How much will the room cost?",
            "Р|Двести тысяч рублей в сутки, завтрак включён.|200,000 roubles a night, breakfast included.",
            "К|Очень хорошо. Спасибо.|Very good. Thank you.",
            "Р|Пожалуйста. Счастливого пути!|You’re welcome. Bon voyage!",
        ]},
        {"kind": "dialog", "n": 2, "title": "В гостинице", "en": "In the hotel",
         "setting": "The American has just arrived at the hotel and is checking in.", "turns": [
            "А|Добрый вечер. Для меня забронирован номер. Меня зовут Джон Смит.|Good evening. You have a reservation for me under the name of John Smith.",
            "Р|Как вы сказали? Смит? Сейчас посмотрю. Да, да. Есть. Номер на двоих, на пятом этаже.|Did you say Smith? I’ll take a look. Yes, here it is. A double, on the fifth floor.",
            "А|Нет, это неправильно. Для меня забронирован номер на одного.|No, that’s not right. I made a reservation for a single.",
            "Р|Ах, да. Простите, я ошиблась. Совершенно правильно. Номер на одного, на пятом этаже. Сколько вы у нас пробудете?|Oh, yes. I’m sorry. I made a mistake. You’re absolutely right. A single, on the fifth floor. How long will you be staying?",
            "А|Трое суток.|Three days.",
            "Р|Прошу вас заполнить эту анкету. И, пожалуйста, оставьте ваш паспорт для регистрации. Завтра утром вы можете его получить обратно.|Please fill out this form. And you’ll have to leave your passport for registration. You can pick it up tomorrow morning.",
            "А|Где? Тут?|Where? Here?",
            "Р|Нет, в паспортном столе на третьем этаже. Простите, вы забыли расписаться.|No, in the passport office on the third floor. Excuse me, but you forgot to sign.",
            "А|Извините, я не понимаю. Что значит «расписаться»?|I’m sorry, but I don’t understand. What does «расписаться» mean?",
            "Р|Вы должны написать вашу фамилию вот здесь.|You need to sign your last name right here.",
            "А|Понимаю. Вот, пожалуйста, анкета и паспорт.|I got it. Okay, here’s the form and my passport.",
            "Р|Вот ваш ключ. Ваш номер на пятом этаже, вы можете подняться на лифте.|Here’s your key. Your room is on the fifth floor. You can take the elevator up.",
            "А|А чемоданы?|What about my suitcases?",
            "Р|Оставьте их здесь. Чемоданы доставят вам в номер.|Leave them here. They’ll be brought up to your room.",
        ]},
        {"kind": "variant", "n": 2, "setting": "An American couple has just arrived at their hotel.", "turns": [
            "А|Здравствуйте. Для нас забронирован номер на имя Дэйвис.|Hello. You have a reservation for us under the name of Davis.",
            "Р|Дэйвис? Да, да. Есть. Для вас есть номер на двоих, на девятом этаже. Пожалуйста, заполните эту анкету.|Davis? Yes, here it is. You have a double on the ninth floor. Please fill out this form.",
            "А|Можно заполнить на английском?|May I do it in English?",
            "Р|Да, конечно. Распишитесь здесь и оставьте ваши паспорта для регистрации.|Of course. Sign here and leave me your passports for registration.",
            "А|Вот, пожалуйста, анкета и паспорта.|Here’s the form and our passports.",
            "Р|Вот ваш ключ. Ваш номер на девятом этаже. Вы можете подняться на лифте.|Here’s your key. Your room is on the ninth floor. You can take the elevator up.",
            "А|Спасибо. А где лифт?|Thank you. And where’s the elevator?",
            "Р|Лифт вон там. Оставьте чемоданы здесь. Их вам доставят в номер.|The elevator’s over there. Leave your suitcases here. Someone will bring them up to your room.",
        ]},
        {"kind": "dialog", "n": 3, "title": "Разговор с дежурной", "en": "Talking to the floor lady", "turns": [
            "А|Девушка, номер 503 в какую сторону?|Miss, which way is room 503?",
            "Р|503? Направо.|503? To the right.",
            "А|Направо? Спасибо.|To the right? Thank you.",
            "Р|Пожалуйста. Если вам что-нибудь будет нужно, обращайтесь ко мне.|You’re welcome. If you need anything, just ask me.",
        ]},
        {"kind": "dialog", "n": 4, "title": "Разговор с горничной", "en": "Talking to the maid", "turns": [
            "А|Девушка, извините. Вы работаете на этом этаже?|Miss, excuse me. Do you work on this floor?",
            "Р|Да, пожалуйста. Чем могу помочь?|Yes. How can I help you?",
            "А|Вы знаете, у меня в номере нет туалетной бумаги.|You know, there’s no toilet paper in my bathroom.",
            "Р|В каком вы номере?|What’s your room number?",
            "А|В номере 503.|Room 503.",
            "Р|Хорошо. Сейчас принесу.|Okay. I’ll bring some right away.",
            "А|Спасибо большое.|Thanks a lot.",
        ]},
        {"kind": "variant", "n": 4, "v": 1, "turns": [
            "А|Девушка, извините. Можно отдать в стирку рубашки?|Miss, excuse me. Can I get these shirts washed?",
            "Р|Конечно. Положите ваши вещи в этот пакет и оставьте его на кровати. Я потом его заберу.|Of course. Put your things in this bag and leave it on the bed. I’ll pick it up later.",
            "А|Спасибо. Когда мои вещи будут готовы?|Thanks. When will my things be ready?",
            "Р|Сегодня вечером. Я вам всё принесу.|This evening. I’ll bring everything up to you.",
        ]},
        {"kind": "variant", "n": 4, "v": 2, "turns": [
            "Р|Простите, пожалуйста. Вы сейчас уходите? Можно убрать ваш номер?|Excuse me, are you going out? May I clean your room now?",
            "А|Да, да. Я сейчас ухожу. Вы знаете, ночью мне было холодно. Можно попросить ещё одно одеяло?|Go ahead. I’m on my way out. You know, I was cold last night. May I ask you for another blanket?",
            "Р|Пожалуйста. Сейчас принесу.|Certainly. I’ll bring it right away.",
            "А|Спасибо.|Thanks.",
        ]},
        {"kind": "variant", "n": 4, "v": 3, "turns": [
            "А|Девушка, холодильник в номере не работает.|Miss, the refrigerator in my room doesn’t work.",
            "Р|Какой ваш номер?|What’s your room number?",
            "А|503.|503.",
            "Р|503? Я сейчас пришлю мастера.|503? I’ll send the repairman up.",
            "А|Спасибо. Мне его подождать?|Thanks. Shall I wait for him?",
            "Р|Нет, не надо.|No, that’s not necessary.",
        ]},
        {"kind": "dialog", "n": 5, "title": "Разговоры с дежурной", "en": "Talking to the floor lady", "turns": [
            "А|Девушка, можно у вас попросить чаю?|Miss, could I ask you for some tea?",
            "Р|Пожалуйста. Минут через 15 я вам принесу в номер. Какой ваш номер?|Sure. I’ll bring it to your room in about 15 minutes. What’s your room number?",
            "А|503.|503.",
            "Р|Хорошо. Вам с сахаром? Печенье хотите?|Okay. Do you take it with sugar? Would you like some cookies?",
            "А|Спасибо, без сахара. Но принесите, пожалуйста, печенье.|No sugar, please. But bring me some cookies.",
            "Р|Сейчас всё сделаю и принесу.|I’ll bring everything right away.",
            "А|Большое спасибо.|Thanks very much.",
            "Р|Не за что.|Don’t mention it.",
        ]},
        {"kind": "variant", "n": 5, "v": 1, "turns": [
            "А|Девушка, вам оставить ключ?|Miss, should I leave you my key?",
            "Р|Пожалуйста, оставьте. Вот ваша карточка. Вы надолго уходите?|Please. Here’s your guest card. Will you be gone long?",
            "А|Да. Я буду только вечером.|Yes. I won’t be back until this evening.",
            "Р|Хорошо. До вечера.|Okay. See you this evening.",
        ]},
        {"kind": "variant", "n": 5, "v": 2, "turns": [
            "А|Девушка, завтра мне надо встать рано. Разбудите меня в шесть, пожалуйста.|Miss, I have to get up early tomorrow. Please wake me up at 6:00.",
            "Р|Хорошо. Вам позвонят в шесть. Какой ваш номер?|Okay. You’ll have a wake-up call at 6:00. What’s your room number?",
            "А|503. Вы не забудете?|503. You won’t forget, will you?",
            "Р|Конечно не забуду. Сейчас всё сделаю.|Of course not. I’ll take care of it right away.",
            "А|Спасибо большое.|Thanks very much.",
            "Р|Не за что.|No problem.",
        ]},
    ],
    "words": [
        ("анкета", "form, blank"), ("ванная", "bathroom"), ("вешалка", "(clothes) hanger, hook"), ("вещь", "thing"),
        ("горничная", "maid"), ("гостиница", "hotel"), ("готов, готова, готовы", "ready"),
        ("дежурная, дежурный", "floor attendant, concierge"), ("душ", "shower"), ("забронировать", "to reserve"),
        ("заполнить (анкету)", "to fill out (a form)"), ("ключ от номера", "room key"), ("Когда?", "When?"),
        ("командировка", "business trip"), ("мыло", "soap"), ("номер", "hotel room"), ("одеяло", "blanket"),
        ("подушка", "pillow"), ("полотенце", "towel"), ("помогать/помочь", "to help"), ("помощь", "help"),
        ("почта (на почте)", "post office (at the post office)"), ("правильно", "correctly; correct"),
        ("пропуск", "pass, room card"), ("расписаться", "to sign (one’s name)"), ("сутки", "24 hours, a day"),
        ("туалетная бумага", "toilet paper"), ("устраивать", "to suit"), ("чемодан", "suitcase"),
        ("этаж (на этаже)", "floor (on a floor)"),
        ("Я хочу забронировать номер.", "I want to reserve a room."), ("Это меня устраивает.", "This/That suits me."),
        ("Можно заполнить на английском?", "May I fill it out in English?"), ("Можно попросить…?", "May I ask you for…?"),
        ("Сколько будет стоить номер?", "How much will the room cost?"),
        ("Разбудите меня в шесть часов.", "Wake me up at 6."),
        ("В ванной нет горячей воды.", "There is no hot water in the bathroom."), ("Чем могу помочь?", "How can I help you?"),
        ("В котором часу?", "At what time? When?"), ("В какую сторону?", "Which way?"), ("Не за что.", "Don’t mention it."),
        ("Счастливого пути!", "Have a nice trip! Bon voyage!"),
    ],
})

LESSONS.append({
    "n": 11, "ru": "Телефон", "en": "The Telephone",
    "intro": [
        "There are no tricks to using the telephone in Russia, especially today when more and more phone lines are "
        "being laid, when satellite links are becoming more and more common and when more Russians have telephones "
        "than at any time in the recent past. As for “telephone etiquette”, there is really very little that is "
        "different from what we in the West are used to. You will encounter varying degrees of politeness and "
        "rudeness on the phone, just as you will here.",
        "You will need to do the following to make phone calling as easy as possible: 1) memorize a certain number "
        "of common phrases which you will use frequently when calling and when answering calls; 2) understand other "
        "phrases which you will hear but not actively use; and 3) be able to write down telephone numbers and other "
        "information as it is being given to you over the phone. This lesson will help you do precisely that.",
    ],
    "dialogs": [
        {"kind": "dialog", "n": 1, "title": "Простите, кто говорит?", "en": "Who may I say is calling?", "turns": [
            "А|Алло. Слушаю.|Hello.",
            "Р|Здравствуйте. Можно Смита к телефону?|Hello. May I speak to Mr. Smith, please?",
            "А|Простите, кто говорит?|Who may I say is calling?",
            "Р|Шкарникова.|Shkarnikova.",
            "А|Повторите, пожалуйста, по буквам.|Could you spell that, please?",
            "Р|Шура — Катя — Аня — Рита — Нина — Ирина — Катя — Ольга — Вера — Аня.|Shura — Katya — Anya — Rita — Nina — Irina — Katya — Olga — Vera — Anya.",
            "А|Понятно. Шкарникова. Одну минуту. Сейчас позову.|I got it. Shkarnikova. Just a minute. I’ll call him.",
        ]},
        {"kind": "dialog", "n": 2, "title": "Какой у вас телефон?", "en": "What’s your phone number?", "turns": [
            "А|Алло. Слушаю. Это Марк Смит.|Hello. This is Mark Smith speaking.",
            "Р|Позовите, пожалуйста, госпожу Дэйвис.|May I speak to Ms. Davis, please?",
            "А|Её сейчас нет. Что-нибудь передать?|She’s not here right now. May I take a message?",
            "Р|Передайте ей, что звонил Иванов. Мой номер телефона 230-41-45.|Tell her that Ivanov called. My number is 230-41-45.",
            "А|Скажите, пожалуйста, по цифрам.|Could you give that to me number by number, please?",
            "Р|2-3-0-4-1-4-5.|2-3-0-4-1-4-5.",
        ]},
        {"kind": "dialog", "n": 3, "title": "Вы не туда попали", "en": "You have the wrong number", "turns": [
            "А|Алло. Слушаю.|Hello.",
            "Р|Можно Иванова к телефону?|May I speak to Ivanov?",
            "А|Вы не туда попали. Иванов здесь не работает.|You have the wrong number. There’s no Ivanov here.",
            "Р|Извините, я ошибся.|Excuse me, I must have dialed the wrong number.",
        ]},
        {"kind": "variant", "n": 3, "turns": [
            "А|Алло.|Hello.",
            "Р|Здравствуйте. Можно Веру Ивановну к телефону?|Hello. May I speak to Vera Ivanovna, please?",
            "А|Веру Ивановну? Какой номер вы набрали?|Vera Ivanovna? What number did you dial?",
            "Р|147-83-30.|147-83-30.",
            "А|Это не тот номер.|You have the wrong number.",
            "Р|Простите, я ошиблась.|I’m sorry. I dialed the wrong number.",
        ]},
        {"kind": "dialog", "n": 4, "title": "Плохо слышно", "en": "A bad connection", "turns": [
            "А|Алло. Смит слушает.|Hello. Smith here.",
            "Р|Можно к телефону Линду Дэйвис?|May I speak to Linda Davis?",
            "А|Простите, вас не слышно. Перезвоните, пожалуйста.|I’m sorry, I can’t hear you. Please hang up and call back.",
        ]},
        {"kind": "variant", "n": 4, "turns": [
            "Р|Алло. Курочкин слушает.|Hello. Kurochkin here.",
            "А|Здравствуйте. Можно Журавлёва к телефону?|Hello. May I speak to Mr. Zhuravlyov, please?",
            "Р|Кого? Плохо слышно. Кого позвать?|To whom? We have a bad connection. Whom do you want?",
            "А|Журавлёва.|Mr. Zhuravlyov.",
            "Р|Вас не слышно. Перезвоните.|I can’t hear you. Hang up and call back.",
        ]},
        {"kind": "dialog", "n": 5, "title": "Нас разъединили", "en": "We were disconnected", "turns": [
            "А|Алло. Линда Дэйвис слушает.|Hello. Linda Davis speaking.",
            "Р|Здравствуйте, Линда. Это говорит Иванов из…|Hello, Linda. This is Ivanov from…",
            "А|Алло? Алло?|Hello? Hello?",
            "-|The line has gone dead. Linda waits a moment and then hangs up. In a minute the phone rings again.|",
            "А|Алло?|Hello?",
            "Р|Линда? Это говорит Иванов из клуба «Спартак». Видимо, нас разъединили.|Linda? This is Ivanov from the “Spartak” club. It seems we were disconnected.",
            "А|Ничего. Это бывает.|No problem. That happens.",
        ]},
        {"kind": "variant", "n": 5, "turns": [
            "Р|Пчёлкина слушает.|Pcholkina speaking.",
            "А|Здравствуйте. Это говорит Марк Смит из…|Hello. This is Mark Smith from…",
            "Р|Алло? Алло?|Hello? Hello?",
            "Р|Алло. Пчёлкина слушает.|Hello. Pcholkina speaking.",
            "А|Людмила Николаевна, это говорит Марк Смит из американского посольства. Нас разъединили.|Ludmila Nikolaevna, this is Mark Smith from the American Embassy. We got disconnected.",
            "Р|Ничего. Это бывает.|No problem. That happens.",
        ]},
        {"kind": "dialog", "n": 6, "title": "Приходите к нам в гости", "en": "Come over and visit us", "turns": [
            "А|Здравствуйте, Коля. Это говорит Линда.|Hello, Kolya! This is Linda.",
            "Р|Здравствуйте, Линда. Рад слышать ваш голос.|Hello, Linda. Glad to hear your voice.",
            "А|Коля, в субботу у мужа день рождения. Я хочу пригласить вас к нам в гости. Надеюсь, вы свободны.|Kolya, this Saturday is my husband’s birthday. I want to invite you over. I hope you’re free.",
            "Р|Я свободен и буду очень рад вас видеть. В котором часу прийти?|I’m free, and I’ll be happy to see you. What time should I come?",
            "А|В семь.|At 7:00.",
            "Р|Большое спасибо за приглашение. До скорого.|Thanks a lot for the invitation. See you soon.",
            "А|До свидания.|Bye.",
        ]},
        {"kind": "dialog", "n": 7, "title": "У нас будет новоселье", "en": "We’re having a housewarming", "turns": [
            "А|Алло.|Hello.",
            "Р|Здравствуйте, Линда! Это Миша.|Hello, Linda. This is Misha.",
            "А|Миша! Рада слышать ваш голос. Что нового?|Misha! How nice to hear your voice! What’s new?",
            "Р|Много. Мы наконец получили новую квартиру!|Plenty! We finally got a new apartment!",
            "А|Поздравляю! Когда будет новоселье?|Congratulations! When’s the housewarming?",
            "Р|В эту субботу. Приглашаем вас с мужем. Запишите наш новый адрес.|This Saturday. You and your husband are invited. Here’s the new address.",
            "А|Минутку, я возьму ручку.|Hang on, I’ll get a pen.",
            "Р|Улица Веснина, дом 4, квартира 23.|Vesnina Street, building 4, apartment 23.",
            "А|Прекрасно! До субботы!|Great! See you Saturday!",
        ]},
        {"kind": "dialog", "n": 8, "title": "У нас сегодня встреча", "en": "We have a meeting today",
         "setting": "Mark Smith has an appointment with an official from the Ministry of Foreign Affairs. The gentleman’s "
                    "secretary is calling to cancel and reschedule.", "turns": [
            "А|Алло. Марк Смит слушает.|Hello. This is Mark Smith.",
            "Р|Здравствуйте. Вас беспокоит Алла Сергеевна из Министерства иностранных дел. Я звоню по поручению Плотникова, Виктора Степановича.|Hello. This is Alla Sergeevna from the Ministry of Foreign Affairs. I’m calling for Victor Stepanovich Plotnikov.",
            "А|Да, да. У нас сегодня встреча.|Oh, yes. We have a meeting today.",
            "Р|К сожалению, Виктор Степанович не может встретиться с вами сегодня. Он хочет перенести встречу на пятое.|Unfortunately, Victor Stepanovich can’t meet with you today. He wants to change the meeting to the 5th.",
            "А|Хорошо. Это меня устраивает.|Okay. That’s good for me.",
            "Р|Спасибо. До свидания.|Thank you and good bye.",
        ]},
        {"kind": "variant", "n": 8, "turns": [
            "Р|Алло. Слушаю вас.|Hello.",
            "А|Здравствуйте. Это говорит Линда Дэйвис из американского посольства.|Hello. This is Linda Davis from the American Embassy.",
            "Р|Да, да. Наталья Петровна вас ждёт сегодня в три.|Oh, yes. Natalya Petrovna is expecting you at 3:00 today.",
            "А|К сожалению, я не могу прийти сегодня. Наталья Петровна будет свободна завтра?|Unfortunately I can’t make it today. Is Natalya Petrovna free tomorrow?",
            "Р|Да, она может встретиться с вами завтра в три.|Yes, she can see you tomorrow at 3:00.",
            "А|Спасибо. До свидания.|Thanks. Good bye.",
        ]},
        {"kind": "dialog", "n": 9, "title": "Когда открывается магазин?", "en": "When does the store open?", "turns": [
            "Р|Алло? Магазин «Русский сувенир». Слушаю.|Hello. “Russian Souvenir”. Can I help you?",
            "А|Скажите, пожалуйста, когда открывается ваш магазин?|Can you tell me what time your store opens?",
            "Р|Магазин открыт ежедневно с десяти до семи. Перерыв на обед с двух до трёх.|Our store is open daily from 10:00 to 7:00. We close for lunch from 2:00 to 3:00.",
            "А|Спасибо.|Thanks.",
        ]},
        {"kind": "dialog", "n": 10, "title": "Я хочу заказать столик", "en": "I’d like to reserve a table", "turns": [
            "Р|Ресторан «Боярский зал». Слушаю.|The “Boyarsky zal”. May I help you?",
            "А|Добрый вечер. Я хочу заказать столик на субботу, на семь часов.|Good evening. I’d like to make a reservation for this Saturday at 7:00.",
            "Р|Хорошо. Сколько вас будет?|Fine. How many in your party?",
            "А|Только двое.|Just two.",
            "Р|Ваша фамилия?|And your name?",
            "А|Смит.|Smith.",
            "Р|Хорошо, господин Смит. Ждём вас в субботу, в семь часов.|Very good, Mr. Smith. We’ll see you on Saturday at 7:00.",
            "А|Спасибо. До свидания.|Thanks. Good-bye.",
        ]},
        {"kind": "dialog", "n": 11, "title": "В гостинице", "en": "In the hotel", "turns": [
            "Р|Алло. Добрый вечер.|Hello. Good evening.",
            "А|Добрый вечер. Я хочу заказать ужин в номер.|Good evening. I’d like to order room service for supper.",
            "Р|Хорошо. Меню у вас есть?|Fine. Do you have a menu?",
            "А|Да. Принесите, пожалуйста, сырники со сметаной и чай.|Yes, I do. Please send up sirniki with sour cream and tea.",
            "Р|А ваш номер?|Your room number, please.",
            "А|612 (шестьсот двенадцать).|612.",
            "Р|Сейчас вам принесут.|It’ll be right up.",
            "А|Спасибо.|Thanks.",
        ]},
        {"kind": "dialog", "n": 12, "title": "Вызов скорой", "en": "Calling an ambulance", "turns": [
            "Р|Скорая.|Ambulance.",
            "А|Приезжайте скорее! У нас тяжело больной.|Come immediately! We have a very sick person here!",
            "Р|Что с ним?|What’s the matter with him?",
            "А|Плохо с сердцем.|He has chest pains.",
            "Р|Адрес?|What’s the address?",
            "А|Улица Дмитрия Ульянова, 22, квартира 167.|22 Dmitry Ulyanov Street, apartment 167.",
            "Р|Район?|District?",
            "А|Севастопольский.|Sevastopol’sky.",
            "Р|Фамилия?|Last name?",
            "А|Щербаков.|Shcherbakov.",
            "Р|Возраст?|Age?",
            "А|65 (шестьдесят пять).|65.",
            "Р|Выезжаем. Ждите.|We’re on our way. Wait for us.",
        ]},
    ],
    "words": [
        ("вешать/повесить (трубку)", "to hang up (the receiver)"), ("встреча", "meeting; appointment"),
        ("говорить/сказать", "to speak, to say"), ("звонить/позвонить", "to call (up), to phone"),
        ("записать", "to write, jot down"), ("класть/положить", "to put (something) down"), ("медленнее", "slower"),
        ("медленно", "slowly"), ("набрать (номер)", "to dial"), ("номер (телефона)", "telephone number"),
        ("перезвонить", "to call back; to redial"), ("повторить", "to repeat"),
        ("позвать", "to call, summon (call someone to the phone)"), ("пожар", "fire"), ("попросить", "to request, ask"),
        ("приглашение", "invitation"), ("скорая (помощь)", "ambulance"), ("слушать", "to listen"), ("слышать", "to hear"),
        ("справочная", "directory assistance; information"), ("цифра", "number, figure"),
        ("Большое спасибо за приглашение.", "Thanks a lot for the invitation."),
        ("Вы не туда попали.", "You’ve got the wrong number."), ("Запишите…", "Write down…"),
        ("Запишите мой телефон.", "Write down my phone number."), ("К сожалению…", "Unfortunately…"),
        ("Когда открывается магазин?", "When does the store open?"), ("Когда закрывается магазин?", "When does the store close?"),
        ("Можно?", "May I?"), ("Нас разъединили.", "We were disconnected."),
        ("Нас двое (трое, четверо).", "There are 2 (3, 4) in our party."), ("Не вешайте трубку.", "Don’t hang up."),
        ("Не кладите трубку.", "Don’t hang up."), ("Плохо слышно.", "We’ve got a bad connection."),
        ("по цифрам", "one number at a time"), ("Повторите, пожалуйста.", "Please repeat that."),
        ("Что нового?", "What’s new?"), ("Это бывает.", "It happens."), ("Это меня устраивает.", "That suits me."),
    ],
})

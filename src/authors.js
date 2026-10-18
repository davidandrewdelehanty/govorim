import IMAGE_MAP from "./image-map.json";
// Authors on the library shelves: the catalogue's author string (surname and
// initials, as the FB2s spell it) -> a display name, life years and a portrait.
// Portraits are Wikidata's image (P18) for each writer, hotlinked from Wikimedia
// Commons; the few that are not public domain carry their credit. An author
// with no file gets a monogram tile instead. Built 17 Oct 2026.
export var AUTHORS = {
  "Чехов А.П.": {"name": "Антон Чехов", "years": "1860–1904", "file": "Anton Chekhov with bow-tie sepia image.jpg"},
  "Бунин И.А.": {"name": "Иван Бунин", "years": "1870–1953", "file": "Ivan Bunin (sepia).jpg"},
  "Тургенев И.С.": {"name": "Иван Тургенев", "years": "1818–1883", "file": "Turgenev by Repin.jpg"},
  "Горький М.": {"name": "Максим Горький", "years": "1868–1936", "file": "Maxim Gorky LOC Restored edit1.jpg"},
  "Толстой Л.Н.": {"name": "Лев Толстой", "years": "1828–1910", "file": "L.N.Tolstoy Prokudin-Gorsky.jpg"},
  "Пушкин А.С.": {"name": "Александр Пушкин", "years": "1799–1837", "file": "Kiprensky Pushkin.jpg"},
  "Достоевский Ф.М.": {"name": "Фёдор Достоевский", "years": "1821–1881", "file": "Vasily Perov - Портрет Ф.М.Достоевского - Google Art Project.jpg"},
  "Булгаков М.А.": {"name": "Михаил Булгаков", "years": "1891–1940", "file": "Михаил-Булгаков.jpg"},
  "Лермонтов М.Ю.": {"name": "Михаил Лермонтов", "years": "1814–1841", "file": "Mikhail lermontov.jpg"},
  "Маяковский В.В.": {"name": "Владимир Маяковский", "years": "1893–1930", "file": "Majakovszkij.jpg"},
  "Есенин С.А.": {"name": "Сергей Есенин", "years": "1895–1925", "file": "Sergey Yesenin 2.jpg"},
  "Тютчев Ф.И.": {"name": "Фёдор Тютчев", "years": "1803–1873", "file": "Tiutchev.jpg"},
  "Куприн А.И.": {"name": "Александр Куприн", "years": "1870–1938", "file": "Kuprin.jpg"},
  "Андреев Л.Н.": {"name": "Леонид Андреев", "years": "1871–1919", "file": "1912c Leonid Andreyev Autochrome self-portrait.jpg"},
  "Некрасов Н.А.": {"name": "Николай Некрасов", "years": "1821–1878", "file": "Nikolay Nekrasov 2cr.jpg"},
  "Блок А.А.": {"name": "Александр Блок", "years": "1880–1921", "file": "Alexander Blok.jpeg"},
  "Афанасьев А.Н.": {"name": "Александр Афанасьев", "years": "1826–1871", "file": "Afanasev.jpg"},
  "Фет А.А.": {"name": "Афанасий Фет", "years": "1820–1892", "file": "Fet by Repin.jpg"},
  "Крылов И.А.": {"name": "Иван Крылов", "years": "1769–1844", "file": "Eggink-Portrait of Ivan Krylov.jpg"},
  "Гоголь Н.В.": {"name": "Николай Гоголь", "years": "1809–1852", "file": "N.Gogol by F.Moller (1840, Tretyakov gallery).jpg"},
  "Салтыков-Щедрин М.Е.": {"name": "Михаил Салтыков-Щедрин", "years": "1826–1889", "file": "Kramskoj - saltykov-schedrin.jpg"},
  "Лесков Н.С.": {"name": "Николай Лесков", "years": "1831–1895", "file": "Serov Leskov.jpg"},
  "Толстой А.К.": {"name": "Алексей К. Толстой", "years": "1817–1875", "file": "Brullov AKTolstoy.jpg"},
  "Островский А.Н.": {"name": "Александр Островский", "years": "1823–1886", "file": "Alexander Ostrovsky by Vasily Perov.jpg"},
  "Ленин В.И.": {"name": "Владимир Ленин", "years": "1870–1924", "file": "Vladímir Lenin (fotografía coloreada).jpg"},
  "Короленко В.Г.": {"name": "Владимир Короленко", "years": "1853–1921", "file": "Vladimir Korolenko bw.jpg"},
  "Жуковский В.А.": {"name": "Василий Жуковский", "years": "1783–1852", "file": "Zhukovsky 1815.jpg"},
  "Цветаева М.И.": {"name": "Марина Цветаева", "years": "1892–1941", "file": "Марина Цветаева (1925) (cropped).jpg"},
  "Гаршин В.М.": {"name": "Всеволод Гаршин", "years": "1855–1888", "file": "Илья Репин - Портрет Всеволод Михайлович Гаршин.jpg"},
  "Диккенс Ч.": {"name": "Чарльз Диккенс", "years": "1812–1870", "file": "Dickens Gurney head.jpg"},
  "Замятин Е.И.": {"name": "Евгений Замятин", "years": "1884–1937", "file": "Zamjatin.jpg"},
  "Гайдар А.П.": {"name": "Аркадий Гайдар", "years": "1904–1941", "file": "Гайдар, Аркадий Петрович 001.png"},
  "Никитин И.С.": {"name": "Иван Никитин", "years": "1824–1861", "file": "PGRS 2 066 Nikitin - crop.jpg"},
  "Брюсов В.Я.": {"name": "Валерий Брюсов", "years": "1873–1924", "file": "Valery Bryusov c. 1900.jpg"},
  "Купер Дж. Ф.": {"name": "Джеймс Фенимор Купер", "years": "1789–1851", "file": "James Fenimore Cooper by Jarvis.jpg"},
  "Лондон Дж.": {"name": "Джек Лондон", "years": "1876–1916", "file": "Jack London young.jpg"},
  "Сталин И.В.": {"name": "Иосиф Сталин", "years": "1878–1953", "file": "Joseph Stalin official portrait.jpg"},
  "Грин А.С.": {"name": "Александр Грин", "years": "1880–1932", "file": "Александр Грин.jpg"},
  "Толстой А.Н.": {"name": "Алексей Н. Толстой", "years": "1882–1945", "file": "ANTolstoy.jpg"},
  "Державин Г.Р.": {"name": "Гавриил Державин", "years": "1743–1816", "file": "Derzhavin by Borovikovsky (1811, Pushkin museum).jpg"},
  "Твен М.": {"name": "Марк Твен", "years": "1835–1910", "file": "MarkTwain.LOC.jpg"},
  "Марриет Ф.": {"name": "Фредерик Марриет", "years": "1792–1848", "file": "Frederick Marryat by John Simpson.jpg"},
  "Сологуб Ф.К.": {"name": "Фёдор Сологуб", "years": "1863–1927", "file": "Sologub-1909.jpg"},
  "Карамзин Н.М.": {"name": "Николай Карамзин", "years": "1766–1826", "file": "Karamzin by Tropinin (1818, Tretyakov gallery).jpg"},
  "Одоевский В.Ф.": {"name": "Владимир Одоевский", "years": "1803–1869", "file": "Vladimir Odoyevsky 1.jpg"},
  "Аверченко А.Т.": {"name": "Аркадий Аверченко", "years": "1881–1925", "file": "Arkady Averchenko 7.gif"},
  "Кольцов А.В.": {"name": "Алексей Кольцов", "years": "1809–1842", "file": "Koltsov AV.jpg"},
  "Майков А.Н.": {"name": "Аполлон Майков", "years": "1821–1897", "file": "Apollon Maykov.jpg"},
  "Полонский Я.П.": {"name": "Яков Полонский", "years": "1819–1898", "file": "Yakov Polonskiy.jpg"},
  "Бальмонт К.Д.": {"name": "Константин Бальмонт", "years": "1867–1942", "file": "Konstantin Balmont by Valentin Serov 1905.jpg"},
  "Волошин М.А.": {"name": "Максимилиан Волошин", "years": "1877–1932", "file": "Maximilan Voloshin.jpg"},
  "Уэллс Г.": {"name": "Герберт Уэллс", "years": "1866–1946", "file": "H.G. Wells by Beresford.jpg"},
  "Мамин-Сибиряк Д.Н.": {"name": "Дмитрий Мамин-Сибиряк", "years": "1852–1912", "file": "Dmitry Narkisovich Mamin-Sibiryak.jpg"},
  "Беляев А.Р.": {"name": "Александр Беляев", "years": "1884–1942", "file": "1915. Alex Belayev.jpg"},
  "Анненский И.Ф.": {"name": "Иннокентий Анненский", "years": "1855–1909", "file": "Innokenty Annensky (cropped).jpg"},
  "Хлебников В.": {"name": "Велимир Хлебников", "years": "1885–1922", "file": "Chlebnikow.jpg"},
  "Стивенсон Р. Л.": {"name": "Роберт Льюис Стивенсон", "years": "1850–1894", "file": "Robert Louis Stevenson by Henry Walter Barnett bw.jpg"},
  "Герцен А.И.": {"name": "Александр Герцен", "years": "1812–1870", "file": "Herzen ge.png"},
  "Гончаров И.А.": {"name": "Иван Гончаров", "years": "1812–1891", "file": "Ivan Goncharov.jpg"},
  "Гарин-Михайловский Н.Г.": {"name": "Николай Гарин-Михайловский", "years": "1852–1906", "file": "Nikolay Mikhaylovsky.jpg"},
  "Вересаев В.В.": {"name": "Викентий Вересаев", "years": "1867–1945", "file": "Vikenty Vikentyevich Veresaev.jpg"},
  "Тэффи Н.А.": {"name": "Тэффи", "years": "1872–1952", "file": "Teffi Choumoff.jpg"},
  "Тынянов Ю.Н.": {"name": "Юрий Тынянов", "years": "1894–1943", "file": "Tiynyanov yuriyi.jpg"},
  "Батюшков К.Н.": {"name": "Константин Батюшков", "years": "1787–1855", "file": "Batushkov by Utkin.JPG"},
  "Рылеев К.Ф.": {"name": "Кондратий Рылеев", "years": "1795–1826", "file": "Rylejew.jpg"},
  "Северянин И.": {"name": "Игорь Северянин", "years": "1887–1941", "file": "Igor Severyanin.jpg"},
  "Ходасевич В.Ф.": {"name": "Владислав Ходасевич", "years": "1886–1939", "file": "Khodasevich 1.jpg"},
  "Багрицкий Э.Г.": {"name": "Эдуард Багрицкий", "years": "1895–1934", "file": "E. Bagritskiy by anonymous (1920-1930s, Akhmatova's museum).jpg"},
  "Скотт В.": {"name": "Вальтер Скотт", "years": "1771–1832", "file": "Sir Henry Raeburn - Portrait of Sir Walter Scott.jpg"},
  "Киплинг Р.": {"name": "Редьярд Киплинг", "years": "1865–1936", "file": "Kipling nd.jpg"},
  "Майн Рид Т.": {"name": "Майн Рид", "years": "1818–1883", "file": "Portrait of Thomas Mayne Reid, circa 1850 (cropped).jpg"},
  "Бульвер-Литтон Э.": {"name": "Эдвард Бульвер-Литтон", "years": "1803–1873", "file": "Edward George Earle Lytton Bulwer Lytton, 1st Baron Lytton by Henry William Pickersgill.jpg"},
  "Мережковский Д.С.": {"name": "Дмитрий Мережковский", "years": "1865–1941", "file": "Merezhkovskiy in NNovgorod.jpg"},
  "Аксаков С.Т.": {"name": "Сергей Аксаков", "years": "1791–1859", "file": "Perov Axakov.jpg"},
  "Помяловский Н.Г.": {"name": "Николай Помяловский", "years": "1835–1863", "file": "Nikolai Pomyalovsky by Nikolai Nevrev.jpg"},
  "Белый А.": {"name": "Андрей Белый", "years": "1880–1934", "file": "Andrei Bely in Brussels (1912).jpg"},
  "Шмелёв И.С.": {"name": "Иван Шмелёв", "years": "1873–1950", "file": "И.С. Шмелев.jpg"},
  "Суриков И.З.": {"name": "Иван Суриков", "years": "1841–1880", "file": "Ivan surikov.jpg"},
  "Козлов И.И.": {"name": "Иван Козлов", "years": "1779–1840", "file": "Ivan Ivanovich Kozlov portrait.jpg"},
  "Языков Н.М.": {"name": "Николай Языков", "years": "1803–1846", "file": "Nikolay Mikhailovich Yazykov.jpg"},
  "Козьма Прутков": {"name": "Козьма Прутков", "years": "1803–1863", "file": "Kozma Prutkov by L M Zhemchuzhnikov.jpg"},
  "Поварнин С.И.": {"name": "Сергей Поварнин", "years": "1870–1952", "file": "Povarnin.jpg", "credit": "Photo: unknown, CC BY-SA 2.5"},
  "Виппер Р.Ю.": {"name": "Роберт Виппер", "years": "1859–1954", "file": "Wipper Robert Yurievich.gif"},
  "Конрад Дж.": {"name": "Джозеф Конрад", "years": "1857–1924", "file": "Joseph Conrad-remastered to black and white.png"},
  "Теккерей У.": {"name": "Уильям Теккерей", "years": "1811–1863", "file": "William Makepeace Thackeray by Jesse Harrison Whitehurst-crop.jpg"},
  "Конан Дойл А.": {"name": "Артур Конан Дойл", "years": "1859–1930", "file": "Arthur Conan Doyle by Walter Benington, 1914.png"},
  "Арцыбашев М.П.": {"name": "Михаил Арцыбашев", "years": "1878–1927", "file": "Mikhail Petrovich Artsybashev.jpg"},
  "Грибоедов А.С.": {"name": "Александр Грибоедов", "years": "1795–1829", "file": "Ivan Nikolayevich Kramskoi - Portrait of Alexander Sergeyevich Griboyedov, 1873.jpg"},
  "Брежнев Л.И.": {"name": "Леонид Брежнев", "years": "1906–1982", "file": "Leonid Brezjnev, leider van de Sovjet-Unie, Bestanddeelnr 925-6564.jpg"},
  "Островский Н.А.": {"name": "Николай Островский", "years": "1904–1936", "file": "N Ostrovskiy.jpg"},
  "Фонвизин Д.И.": {"name": "Денис Фонвизин", "years": "1745–1792", "file": "Armand-Charles Caraffe, Denis Fonvizin, c. 1784–1785, Pushkin House Ж-95; from goskatalog.ru.jpg"},
  "Погорельский А.": {"name": "Антоний Погорельский", "years": "1787–1836", "file": "BrullovP-TPEROV.jpg"},
  "Писемский А.Ф.": {"name": "Алексей Писемский", "years": "1821–1881", "file": "Pisemsky by Repin.jpg"},
  "Успенский Г.И.": {"name": "Глеб Успенский", "years": "1843–1902", "file": "1884 Yaroshenko Portrait Schriftsteller G.I. Uspenskoje anagoria.JPG"},
  "Фурманов Д.А.": {"name": "Дмитрий Фурманов", "years": "1891–1926", "file": "Фурманов, Дмитрий Андреевич 001.png"},
  "Ломоносов М.В.": {"name": "Михаил Ломоносов", "years": "1711–1765", "file": "M.V. Lomonosov by L.Miropolskiy after G.C.Prenner (1787, RAN).jpg"},
  "Баратынский Е.А.": {"name": "Евгений Баратынский", "years": "1800–1844", "file": "PGRS 2 008 Baratynsky - crop.jpg"},
  "Дельвиг А.А.": {"name": "Антон Дельвиг", "years": "1798–1831", "file": "PGRS 2 029 Delvig - crop.jpg"},
  "Апухтин А.Н.": {"name": "Алексей Апухтин", "years": "1840–1893", "file": "Apukhtin AN.jpg"},
  "Вяземский П.А.": {"name": "Пётр Вяземский", "years": "1792–1878", "file": "P.F. Sokolov 007.jpg"},
  "Огарёв Н.П.": {"name": "Николай Огарёв", "years": "1813–1877", "file": "GRW219 Ogaryov.jpg"},
  "Дефо Д.": {"name": "Даниель Дефо", "years": "1660–1731", "file": "Daniel Defoe Kneller Style.jpg"},
  "Джером Дж. К.": {"name": "Джером К. Джером", "years": "1859–1927", "file": "Jerome K. Jerome 02.jpg"},
  "Голсуорси Дж.": {"name": "Джон Голсуорси", "years": "1867–1933", "file": "John Galsworthy 2.jpg"},
  "Кэрролл Л.": {"name": "Льюис Кэрролл", "years": "1832–1898", "file": "LewisCarrollSelfPhoto.jpg"},
  "Бичер-Стоу Г.": {"name": "Гарриет Бичер-Стоу", "years": "1811–1896", "file": "Beecher-Stowe.jpg"},
  "Ерофеев В.В.": {"name": "Венедикт Ерофеев", "years": "1938–1990"},
  "Драгунский В.Ю.": {"name": "Виктор Драгунский", "years": "1913–1972", "file": "Viktor Dragunsky (1934).jpg"},
  "Пастернак Б.Л.": {"name": "Борис Пастернак", "years": "1890–1960", "file": "Boris Pasternak 1958 photo.jpg"},
  "Костюченко Е.Г.": {"name": "Елена Костюченко", "years": "1987–", "file": "Elena Kostyuchenko 2011-10-28.jpg", "credit": "Photo: Side by Side Film Festival, CC BY-SA 3.0"},
  "Навальный А.А.": {"name": "Алексей Навальный", "years": "1976–2024", "file": "Alexey Navalny 2018 (cropped).png", "credit": "Photo: Navalny's Team, CC BY 3.0"},
  "Шолохов М.А.": {"name": "Михаил Шолохов", "years": "1905–1984", "file": "Михаил Александрович Шолохов.jpg"},
  "Киз Д.": {"name": "Дэниел Киз", "years": "1927–2014"},
  "Радищев А.Н.": {"name": "Александр Радищев", "years": "1749–1802", "file": "Radishchev color.jpg"},
  "Ершов П.П.": {"name": "Пётр Ершов", "years": "1815–1869", "file": "Пётр Ершов.jpg"},
  "Гладков Ф.В.": {"name": "Фёдор Гладков", "years": "1883–1958", "file": "The Soviet Union 1963 CPA 2812 stamp (Writers and poets of our Motherland. Feodor Gladkov (1883-1958), a Soviet and Russian socialist realist writer).jpg"},
  "Чернышевский Н.Г.": {"name": "Николай Чернышевский", "years": "1828–1889", "file": "Nikolaj G. Černyševskij 1888.jpg"},
  "Слепцов В.А.": {"name": "Василий Слепцов", "years": "1836–1878", "file": "Vasily Sleptsov 2 (cropped).jpg"},
  "Решетников Ф.М.": {"name": "Фёдор Решетников", "years": "1841–1871", "file": "Fyodor Mikhailovich Reshetnikov 1.jpg"},
  "Боборыкин П.Д.": {"name": "Пётр Боборыкин", "years": "1836–1921", "file": "Pyotr D. Boborykin.jpeg"},
  "Серафимович А.С.": {"name": "Александр Серафимович", "years": "1863–1949", "file": "Alexander Serafimovich.jpg"},
  "Бабель И.Э.": {"name": "Исаак Бабель", "years": "1894–1940", "file": "Isaac Babel.jpg"},
  "Неверов А.С.": {"name": "Александр Неверов", "years": "1886–1923", "file": "Alexandr Neverov 1925.jpg"},
  "Плещеев А.Н.": {"name": "Алексей Плещеев", "years": "1825–1893", "file": "Plesheev AN (cropped).jpg"},
  "Надсон С.Я.": {"name": "Семён Надсон", "years": "1862–1887", "file": "Semyon Yakovlevich Nadson.jpg"},
  "Случевский К.К.": {"name": "Константин Случевский", "years": "1837–1904", "file": "Случевский Константин Константинович.jpg"},
  "Гиппиус З.Н.": {"name": "Зинаида Гиппиус", "years": "1869–1945", "file": "Gippius 1910s.jpg"},
  "Кузмин М.А.": {"name": "Михаил Кузмин", "years": "1872–1936", "file": "Kuzmin.jpg"},
  "Саша Чёрный": {"name": "Саша Чёрный", "years": "1880–1932", "file": "Sasha cherny.jpg"},
  "Вахтеров В.П.": {"name": "Василий Вахтеров", "years": "1853–1924", "file": "Vasily Porfirievich Vakhterov.jpg", "credit": "Photo: Iliaz, CC BY-SA 3.0"},
  "Богораз-Тан В.Г.": {"name": "Владимир Богораз-Тан", "years": "1865–1936", "file": "Тан Богораз.jpg"},
  "Щерба Л.В.": {"name": "Лев Щерба", "years": "1880–1944", "file": "Щерба Лев Владимирович (конверт).jpg",
    // The only free portrait is the one printed on a 1979 Soviet envelope:
    // show just the portrait, not the envelope (fractions of the image).
    "crop": [0.081, 0.140, 0.331, 0.613]},
  "Олкотт Л. М.": {"name": "Луиза Мэй Олкотт", "years": "1832–1888", "file": "Louisa May Alcott, c. 1870 - Warren's Portraits, Boston.jpg"},
  "Драйзер Т.": {"name": "Теодор Драйзер", "years": "1871–1945", "file": "Theodore Dreiser.jpg"},
  "Гарди Т.": {"name": "Томас Гарди", "years": "1840–1928", "file": "Thomashardy restored.jpg"},
  "Бёрнетт Ф. Х.": {"name": "Фрэнсис Бёрнетт", "years": "1849–1924", "file": "Frances Burnett.jpg"},
  "Беллами Э.": {"name": "Эдвард Беллами", "years": "1850–1898", "file": "Edward Bellamy - photograph c.1889.jpg"},
  "Хаггард Г. Р.": {"name": "Генри Райдер Хаггард", "years": "1856–1925", "file": "Henry Rider Haggard 03.jpg"},
  "Стокер Б.": {"name": "Брэм Стокер", "years": "1847–1912", "file": "Bram Stoker 1906.jpg"},
  "Уайльд О.": {"name": "Оскар Уайльд", "years": "1854–1900", "file": "Oscar Wilde by Napoleon Sarony. Three-quarter-length photograph, seated.jpg"},
  "Троллоп Э.": {"name": "Энтони Троллоп", "years": "1815–1882", "file": "Anthony Trollope 1.jpg"},
  "Молотов В.М.": {"name": "Вячеслав Молотов", "years": "1890–1986", "file": "V.M. Molotov TASS Portrait Trim Edit.jpg"},
  "Горбачёв М.С.": {"name": "Михаил Горбачёв", "years": "1931–2022", "file": "GorbachevMS.jpg", "credit": "Photo: Leo Medvedev, CC BY-SA 4.0"},
  "Ильф И. и Петров Е.": {"name": "Ильф и Петров", "file": "Ilf Petrov.jpg"}
};
// Not people, or people Commons has no picture of, drawn from elsewhere.
// Ребельский has no portrait anywhere free; his own 1929 title page stands
// in. The two Bibles get the title page of the Ostrog Bible (1581), the
// first complete printed Bible in Church Slavonic.
AUTHORS["Ребельский И.В."] = { name: "Иван Ребельский", img: "/books/textbooks/rebelsky-azbuka/cover.webp" };
// Plato as Raphael painted him in «Афинская школа» (1509–1511), cropped
// to the head from the Plato-and-Aristotle detail.
AUTHORS["Платон"] = { name: "Платон", years: "ок. 428–348 до н. э.", file: "Sanzio 01 Plato Aristotle.jpg",
  crop: [0.08, 0.0, 0.44, 0.367] };
AUTHORS["Аристотель"] = { name: "Аристотель", years: "384–322 до н. э.", file: "Sanzio 01 Plato Aristotle.jpg",
  crop: [0.48, 0.0, 0.84, 0.367] };
AUTHORS["Ницше Ф."] = { name: "Фридрих Ницше", years: "1844–1900", file: "Nietzsche187a.jpg" };
AUTHORS["Макиавелли Н."] = { name: "Никколо Макиавелли", years: "1469–1527", file: "Portrait of Niccolò Machiavelli by Santi di Tito.jpg" };
AUTHORS["Шопенгауэр А."] = { name: "Артур Шопенгауэр", years: "1788–1860", file: "Arthur Schopenhauer by J Schäfer, 1859b.jpg" };
AUTHORS["Эпиктет"] = { name: "Эпиктет", years: "ок. 50–138", file: "Epictetus.jpg" };
AUTHORS["Гомер"] = { name: "Гомер", years: "VIII в. до н. э.", file: "Homer British Museum.jpg" };
AUTHORS["Эзоп"] = { name: "Эзоп", years: "VI в. до н. э.", file: "Velázquez - Esopo (Museo del Prado, 1639-41).jpg" };
AUTHORS["Серафим Саровский"] = { name: "Серафим Саровский", years: "1754–1833", file: "Saint Serafim Of Sarov Portrait Painted During His Life.jpg" };
AUTHORS["Аввакум Петров"] = { name: "Протопоп Аввакум", years: "1620–1682", file: "Avvakum by Pyotr Yevgenyevich Myasoyedov.jpg" };
AUTHORS["Нестор Летописец"] = { name: "Нестор Летописец", years: "ок. 1056–1114", file: "Нестор-летописец.jpg" };
AUTHORS["Странник"] = { name: "Странник", years: "XIX в.", file: "Перов Странник(ГТГ).jpg" };
AUTHORS["Иоанн Лествичник"] = { name: "Иоанн Лествичник", years: "ок. 579–649", file: "The Ladder of Divine Ascent Monastery of St Catherine Sinai 12th century.jpg" };
AUTHORS["Мандельштам О.Э."] = { name: "Осип Мандельштам", years: "1891–1938", file: "Osip Mandelstam Russian writer.jpg" };
AUTHORS["Гумилёв Н.С."] = { name: "Николай Гумилёв", years: "1886–1921", file: "Ngumil.jpg" };
AUTHORS["Сервантес М."] = { name: "Мигель де Сервантес", years: "1547–1616", file: "Cervantes Jáuregui.jpg" };
AUTHORS["Дюма А."] = { name: "Александр Дюма", years: "1802–1870", file: "Alexander Dumas père par Nadar - Google Art Project.jpg" };
AUTHORS["Верн Ж."] = { name: "Жюль Верн", years: "1828–1905", file: "Félix Nadar 1820-1910 portraits Jules Verne.jpg" };
AUTHORS["Данте А."] = { name: "Данте Алигьери", years: "1265–1321", file: "Sandro Botticelli - Portrait of Dante - WGA02802.jpg" };
AUTHORS["Андерсен Х.К."] = { name: "Ханс Кристиан Андерсен", years: "1805–1875", file: "HCA 1869 by Thora Hallager.jpg" };
AUTHORS["Гримм Я. и В."] = { name: "Братья Гримм", years: "1785–1863, 1786–1859", file: "Grimm.jpg" };
AUTHORS["Бальзак О."] = { name: "Оноре де Бальзак", years: "1799–1850", file: "Honoré de Balzac (1842) Detail.jpg" };
AUTHORS["Стендаль"] = { name: "Стендаль", years: "1783–1842", file: "Stendhal.jpg" };
AUTHORS["Гёте И.В."] = { name: "Иоганн Вольфганг Гёте", years: "1749–1832", file: "Goethe (Stieler 1828).jpg" };
AUTHORS["Гофман Э.Т.А."] = { name: "Эрнст Теодор Амадей Гофман", years: "1776–1822", file: "E.T.A. Hoffmann Selbstportrait.jpg" };
AUTHORS["Шиллер Ф."] = { name: "Фридрих Шиллер", years: "1759–1805", file: "Anton Graff - Friedrich Schiller.jpg" };
AUTHORS["Уитмен У."] = { name: "Уолт Уитмен", years: "1819–1892", file: "Walt Whitman - George Collins Cox.jpg" };
AUTHORS["Чаадаев П.Я."] = { name: "Пётр Чаадаев", years: "1794–1856", file: "Chaadaev portrait.jpeg" };
AUTHORS["Соловьёв В.С."] = { name: "Владимир Соловьёв", years: "1853–1900", file: "VS Solovyov.jpg" };
AUTHORS["Бердяев Н.А."] = { name: "Николай Бердяев", years: "1874–1948", file: "NBerdyaev.jpg" };
AUTHORS["Шестов Л."] = { name: "Лев Шестов", years: "1866–1938", file: "Si Léon Chestov noong 1927.jpg" };
AUTHORS["Розанов В.В."] = { name: "Василий Розанов", years: "1856–1919", file: "Vasily Rozanov.jpg" };
AUTHORS["Фёдоров Н.Ф."] = { name: "Николай Фёдоров", years: "1829–1903", file: "Pasternak fedorov.jpg" };
AUTHORS["Кропоткин П.А."] = { name: "Пётр Кропоткин", years: "1842–1921", file: "Kropotkin1.jpg" };
AUTHORS["Бакунин М.А."] = { name: "Михаил Бакунин", years: "1814–1876", file: "Bakunin Nadar.jpg" };
AUTHORS["Леонтьев К.Н."] = { name: "Константин Леонтьев", years: "1831–1891", file: "Leont'ev.jpg" };
AUTHORS["Religious Texts"] = { name: "Библия", file: "Ostrog Bible, title page, 1581.jpg" };

export function authorInfo(key) {
  return AUTHORS[String(key || "").trim()] || null;
}
// The picture for an author entry: a page of our own, or a Commons file.
export function authorSrc(info, width) {
  if (!info) return "";
  if (info.img) return info.img;
  return info.file ? authorPhoto(info.file, info.crop ? 1200 : width) : "";
}
// A crop as CSS background geometry: the chosen box fills the tile.
export function authorCropStyle(info, width) {
  const c = info && info.crop;
  if (!c) return null;
  const w = c[2] - c[0], h = c[3] - c[1];
  return {
    // Our copy on top, the Commons original underneath: if the copy is
    // missing, the original shows through instead of an empty tile.
    backgroundImage: "url(\"" + authorSrc(info, width) + "\")" +
      (info.file && IMAGE_MAP[info.file]
        ? ", url(\"https://commons.wikimedia.org/wiki/Special:FilePath/" + encodeURIComponent(info.file) + "?width=960\")"
        : ""),
    backgroundSize: (100 / w) + "% " + (100 / h) + "%",
    backgroundPosition: (w < 1 ? c[0] / (1 - w) * 100 : 0) + "% " + (h < 1 ? c[1] / (1 - h) * 100 : 0) + "%",
    backgroundRepeat: "no-repeat",
  };
}
export function authorPhoto(file, width) {
  // Our own copy, made by tools/localize_images.py, when there is one.
  if (IMAGE_MAP[file]) return IMAGE_MAP[file];
  return "https://commons.wikimedia.org/wiki/Special:FilePath/" + encodeURIComponent(file) + "?width=" + (width || 400);
}

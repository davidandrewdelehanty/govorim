# Video chapter boundaries — what needs re-timing

Every book whose chapters are cut out of one long video. A narrator speaks at a steady rate, so each
segment should hold about as many **words per minute** as the rest of that book. Where one chapter's
figure jumps, its start or end is in the wrong place:

- **above** the book's pace → the segment is too SHORT for its text (its start is too late, or its end too early)
- **below** the book's pace → the segment is too LONG (it has swallowed part of a neighbour)

Boundaries are shared: moving the end of chapter N moves the start of N+1. Fix them in order, top to bottom.

Values live in `private/books/index.json` under each book's `videos` block, as whole seconds.

| Priority | Book | Chapters | Book's pace | Worst chapter | Video |
|---|---|---|---|---|---|
| FIX | Герой нашего времени | 7 | 108 w/min | ch0 +299% | https://youtu.be/aA87bXjXt60 |
| FIX | Жизнь Василия Фивейского | 11 | 100 w/min | ch1 +285% | https://youtu.be/ORRu81GTCUM |
| FIX | Отцы и дети | 28 | 110 w/min | ch2 +232% | https://youtu.be/0rA3zDZvy4M |
| FIX | Поликушка | 15 | 102 w/min | ch1 +199% | https://youtu.be/ofRpAAHHkLU |
| FIX | Казаки | 42 | 116 w/min | ch31 +146% | https://youtu.be/iyPsxqSj-zQ |
| FIX | Кавказский пленник | 4 | 110 w/min | ch3 +123% | https://youtu.be/wYUfDsgWb_4 |
| FIX | Вечный муж | 17 | 122 w/min | ch16 +97% | https://youtu.be/Ozls9E3_3pk |
| FIX | Гроза (спектакль) | 5 | 89 w/min | ch4 +81% | https://youtu.be/fdNthke_Enw |
| FIX | Палата № 6 | 19 | 113 w/min | ch14 +71% | https://youtu.be/ev7W9zrO-SI |
| FIX | Дьявол | 23 | 108 w/min | ch2 +64% | https://youtu.be/zAqYP1qDPLA |
| FIX | Учение Христа, изложенное для детей | 9 | 150 w/min | ch8 -53% | https://youtu.be/fCz4aRA10g0 |
| FIX | Власть тьмы (спектакль) | 5 | 105 w/min | ch3 +52% | https://youtu.be/c6CRrtUF4Nw |
| FIX | Мелкий бес | 78 | 115 w/min | ch54 +137% | https://youtu.be/iPcr6aHcHok |
| FIX | Дядюшкин сон | 15 | 114 w/min | ch10 +46% | https://youtu.be/Q3SXgeVah0k |
| FIX | Чайка | 4 | 113 w/min | ch0 -45% | https://youtu.be/Cf8HIMJG3yQ |
| FIX | Отрочество | 27 | 118 w/min | ch16 -42% | https://youtu.be/n3Wsnd8h9_s |
| FIX | Братья Карамазовы | 98 | 99 w/min | ch15 +41% | https://youtu.be/U5blK3O_Ivs |
| FIX | Библия. Синодальный перевод | 276 | 146 w/min | ch186 -38% | https://youtu.be/n_ci23ZwOGY |
| CHECK | Яма | 39 | 104 w/min | ch15 +29% | https://youtu.be/HOlVMJc59DI |
| CHECK | Красный смех | 19 | 111 w/min | ch6 -60% | https://youtu.be/Io5The4PKHE |
| CHECK | Юность | 45 | 115 w/min | ch8 -27% | https://youtu.be/BOIXjt-_2UI |
| CHECK | Тарас Бульба | 12 | 113 w/min | ch2 +26% | https://youtu.be/CJMvJ8av-fk |
| CHECK | На дне (спектакль) | 4 | 98 w/min | ch3 +25% | https://youtu.be/uO_GRxCPbu0 |
| CHECK | Накануне | 35 | 118 w/min | ch9 -25% | https://youtu.be/ttJEPOe0ndw |
| CHECK | Новь | 29 | 118 w/min | ch8 +24% | https://youtu.be/Sdxmls9hcL0 |
| CHECK | Мать | 58 | 127 w/min | ch13 +21% | https://youtu.be/yhzpV9H4dPM |
| CHECK | Белые ночи | 5 | 131 w/min | ch5 -19% | https://youtu.be/hwSBw4BZJeo |
| CHECK | Вишнёвый сад (спектакль) | 4 | 80 w/min | ch1 -18% | https://youtu.be/eCFnvdfRzDY |
| CHECK | Крейцерова соната | 29 | 111 w/min | ch0 -17% | https://youtu.be/7TY6XFtFSOQ |
| CHECK | Мёртвые души | 11 | 113 w/min | ch0 +16% | https://youtu.be/yx-95Wr-P5U |
| CHECK | Дым | 12 | 111 w/min | ch2 -16% | https://youtu.be/ypv0CvWL3Kk |
| CHECK | Мужики | 9 | 124 w/min | ch8 -15% | https://youtu.be/8q0TTfdCnlU |


## Герой нашего времени  
`geroy-nashego-vremeni` · 7 segments · this book reads at about 108 words a minute

Video: https://youtu.be/aA87bXjXt60

_Showing the 2 chapters that are off pace and their neighbours, of 7._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:00:58 | 0:01:55 | 1 min | 409 | 431 | +299% | segment too short — start later? end earlier? |
| 1 | Глава 2 | 0:01:55 | 1:49:31 | 108 min | 11019 | 102 | -5% | ok |

## Жизнь Василия Фивейского  
`zhizn-vasiliya-fiveyskogo` · 11 segments · this book reads at about 100 words a minute

Video: https://youtu.be/ORRu81GTCUM

_Showing the 9 chapters that are off pace and their neighbours, of 11._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:00:12 | 0:12:13 | 12 min | 1206 | 100 | -0% | ok |
| 1 | Глава 2 | 0:12:13 | 0:16:16 | 4 min | 1565 | 386 | +285% | segment too short — start later? end earlier? |
| 2 | Глава 3 | 0:10:58 | 0:16:01 | 5 min | 531 | 105 | +5% | ok |
| 4 | Глава 5 | 0:00:08 | 0:19:47 | 20 min | 1975 | 101 | +0% | ok |
| 5 | Глава 6 | 0:00:12 | 0:16:30 | 16 min | 2731 | 168 | +67% | segment too short — start later? end earlier? |
| 6 | Глава 7 | 0:00:11 | 0:21:13 | 21 min | 2112 | 100 | +0% | ok |
| 7 | Глава 8 | 0:00:11 | 0:27:35 | 27 min | 2484 | 91 | -10% | ok |
| 9 | Глава 10 | 0:00:11 | 0:17:29 | 17 min | 1413 | 82 | -19% | segment too long — swallowing a neighbour |
| 10 | Глава 11 | 0:00:10 | 0:21:31 | 21 min | 2069 | 97 | -3% | ok |

## Отцы и дети  
`ottsy-i-deti` · 28 segments · this book reads at about 110 words a minute

Video: https://youtu.be/0rA3zDZvy4M

_Showing the 9 chapters that are off pace and their neighbours, of 28._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Глава 2 | 0:09:54 | 0:13:48 | 4 min | 489 | 125 | +14% | ok |
| 2 | Глава 3 | 0:13:48 | 0:17:53 | 4 min | 1497 | 367 | +232% | segment too short — start later? end earlier? |
| 3 | Глава 4 | 0:17:53 | 0:28:42 | 11 min | 1158 | 107 | -3% | ok |
| 7 | Глава 8 | 1:07:20 | 1:23:55 | 17 min | 1934 | 117 | +6% | ok |
| 8 | Глава 9 | 1:23:55 | 1:33:50 | 10 min | 838 | 85 | -23% | segment too long — swallowing a neighbour |
| 9 | Глава 10 | 1:33:50 | 2:02:34 | 29 min | 3412 | 119 | +8% | ok |
| 10 | Глава 11 | 2:02:34 | 2:16:53 | 14 min | 1098 | 77 | -31% | segment too long — swallowing a neighbour |
| 11 | Глава 12 | 2:16:53 | 2:26:05 | 9 min | 1353 | 147 | +33% | segment too short — start later? end earlier? |
| 12 | Глава 13 | 2:26:05 | 2:40:33 | 14 min | 1634 | 113 | +2% | ok |

## Поликушка  
`polikushka` · 15 segments · this book reads at about 102 words a minute

Video: https://youtu.be/ofRpAAHHkLU

_Showing the 14 chapters that are off pace and their neighbours, of 15._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:00:22 | 0:17:47 | 17 min | 1331 | 76 | -25% | segment too long — swallowing a neighbour |
| 1 | Глава 2 | 0:17:47 | 0:21:59 | 4 min | 1283 | 305 | +199% | segment too short — start later? end earlier? |
| 2 | Глава 3 | 0:21:59 | 0:30:32 | 9 min | 976 | 114 | +12% | ok |
| 3 | Глава 4 | 0:30:32 | 0:36:16 | 6 min | 488 | 85 | -17% | segment too long — swallowing a neighbour |
| 4 | Глава 5 | 0:36:16 | 0:51:02 | 15 min | 1593 | 108 | +6% | ok |
| 5 | Глава 6 | 0:51:02 | 0:59:48 | 9 min | 602 | 69 | -33% | segment too long — swallowing a neighbour |
| 6 | Глава 7 | 0:59:48 | 1:08:17 | 8 min | 1257 | 148 | +45% | segment too short — start later? end earlier? |
| 7 | Глава 8 | 1:08:17 | 1:22:30 | 14 min | 1307 | 92 | -10% | ok |
| 8 | Глава 9 | 1:22:30 | 1:31:45 | 9 min | 634 | 69 | -33% | segment too long — swallowing a neighbour |
| 9 | Глава 10 | 1:31:45 | 1:36:23 | 5 min | 1202 | 259 | +154% | segment too short — start later? end earlier? |
| 10 | Глава 11 | 1:36:23 | 1:45:30 | 9 min | 931 | 102 | +0% | ok |
| 12 | Глава 13 | 1:53:36 | 2:05:48 | 12 min | 1425 | 117 | +14% | ok |
| 13 | Глава 14 | 2:05:48 | 2:17:26 | 12 min | 769 | 66 | -35% | segment too long — swallowing a neighbour |
| 14 | Глава 15 | 2:17:26 | 2:39:26 | 22 min | 2807 | 128 | +25% | segment too short — start later? end earlier? |

## Казаки  
`kazaki` · 42 segments · this book reads at about 116 words a minute

Video: https://youtu.be/iyPsxqSj-zQ

_Showing the 21 chapters that are off pace and their neighbours, of 42._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:03:13 | 0:12:11 | 9 min | 1209 | 135 | +16% | segment too short — start later? end earlier? |
| 1 | Глава 2 | 0:12:11 | 0:33:55 | 22 min | 2078 | 96 | -17% | segment too long — swallowing a neighbour |
| 2 | Глава 3 | 0:33:55 | 0:42:00 | 8 min | 783 | 97 | -16% | segment too long — swallowing a neighbour |
| 3 | Глава 4 | 0:42:00 | 0:54:30 | 12 min | 1193 | 95 | -18% | segment too long — swallowing a neighbour |
| 4 | Глава 5 | 0:54:30 | 1:06:22 | 12 min | 1149 | 97 | -16% | segment too long — swallowing a neighbour |
| 5 | Глава 6 | 1:06:22 | 1:20:02 | 14 min | 1425 | 104 | -10% | ok |
| 10 | Глава 11 | 2:05:58 | 2:17:01 | 11 min | 1176 | 106 | -8% | ok |
| 11 | Глава 12 | 2:17:01 | 2:22:26 | 5 min | 739 | 136 | +18% | segment too short — start later? end earlier? |
| 12 | Глава 13 | 2:22:26 | 2:38:04 | 16 min | 1879 | 120 | +4% | ok |
| 13 | Глава 14 | 2:38:04 | 2:43:30 | 5 min | 666 | 123 | +6% | ok |
| 14 | Глава 15 | 2:43:30 | 2:56:31 | 13 min | 1007 | 77 | -33% | segment too long — swallowing a neighbour |
| 15 | Глава 16 | 2:56:31 | 3:06:14 | 10 min | 1513 | 156 | +34% | segment too short — start later? end earlier? |
| 16 | Глава 17 | 3:06:14 | 3:14:14 | 8 min | 847 | 106 | -9% | ok |
| 21 | Глава 22 | 4:01:02 | 4:12:59 | 12 min | 1547 | 129 | +12% | ok |
| 22 | Глава 23 | 4:12:59 | 4:23:52 | 11 min | 1016 | 93 | -19% | segment too long — swallowing a neighbour |
| 23 | Глава 24 | 4:23:52 | 4:38:48 | 15 min | 2114 | 142 | +22% | segment too short — start later? end earlier? |
| 24 | Глава 25 | 4:38:48 | 4:46:21 | 8 min | 904 | 120 | +3% | ok |
| 29 | Глава 30 | 5:20:45 | 5:27:03 | 6 min | 728 | 116 | -0% | ok |
| 30 | Глава 31 | 5:27:03 | 5:37:11 | 10 min | 766 | 76 | -35% | segment too long — swallowing a neighbour |
| 31 | Глава 32 | 5:37:11 | 5:40:11 | 3 min | 856 | 285 | +146% | segment too short — start later? end earlier? |
| 32 | Глава 33 | 5:40:11 | 5:53:05 | 13 min | 1609 | 125 | +8% | ok |

## Кавказский пленник  
`kavkazskiy-plennik` · 4 segments · this book reads at about 110 words a minute

Video: https://youtu.be/wYUfDsgWb_4

_Showing the 2 chapters that are off pace and their neighbours, of 4._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 2 | Глава 3 | 0:16:23 | 0:28:48 | 12 min | 1309 | 105 | -4% | ok |
| 3 | Глава 4 | 0:28:48 | 0:31:14 | 2 min | 595 | 245 | +123% | segment too short — start later? end earlier? |

## Вечный муж  
`vechnyy-muzh` · 17 segments · this book reads at about 122 words a minute

Video: https://youtu.be/Ozls9E3_3pk

_Showing the 2 chapters that are off pace and their neighbours, of 17._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 15 | Глава 16 | 5:21:32 | 5:41:53 | 20 min | 2570 | 126 | +3% | ok |
| 16 | Глава 17 | 5:41:53 | 5:52:00 | 10 min | 2440 | 241 | +97% | segment too short — start later? end earlier? |

## Гроза (спектакль)  
`groza-spektakl` · 5 segments · this book reads at about 89 words a minute

Video: https://youtu.be/fdNthke_Enw

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:00:00 | 0:48:10 | 48 min | 4303 | 89 | +0% | ok |
| 1 | Глава 2 | 0:48:10 | 1:11:46 | 24 min | 2798 | 119 | +33% | segment too short — start later? end earlier? |
| 2 | Глава 3 | 1:11:46 | 1:52:34 | 41 min | 3500 | 86 | -4% | ok |
| 3 | Глава 4 | 1:52:34 | 2:26:26 | 34 min | 2148 | 63 | -29% | segment too long — swallowing a neighbour |
| 4 | Глава 5 | 2:26:26 | 2:40:32 | 14 min | 2286 | 162 | +81% | segment too short — start later? end earlier? |

## Палата № 6  
`palata-6` · 19 segments · this book reads at about 113 words a minute

Video: https://youtu.be/ev7W9zrO-SI

_Showing the 9 chapters that are off pace and their neighbours, of 19._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 9 | Глава 10 | 1:12:54 | 1:27:39 | 15 min | 1687 | 114 | +1% | ok |
| 10 | Глава 11 | 1:27:39 | 1:31:16 | 4 min | 487 | 135 | +19% | segment too short — start later? end earlier? |
| 11 | Глава 12 | 1:31:16 | 1:41:02 | 10 min | 1007 | 103 | -9% | ok |
| 12 | Глава 13 | 1:41:02 | 1:44:14 | 3 min | 520 | 162 | +43% | segment too short — start later? end earlier? |
| 13 | Глава 14 | 1:44:14 | 1:53:50 | 10 min | 857 | 89 | -21% | segment too long — swallowing a neighbour |
| 14 | Глава 15 | 1:53:50 | 1:58:11 | 4 min | 843 | 194 | +71% | segment too short — start later? end earlier? |
| 15 | Глава 16 | 1:58:11 | 2:07:10 | 9 min | 1065 | 119 | +5% | ok |
| 17 | Глава 18 | 2:12:48 | 2:21:07 | 8 min | 937 | 113 | -1% | ok |
| 18 | Глава 19 | 2:21:07 | 2:24:17 | 3 min | 292 | 92 | -19% | segment too long — swallowing a neighbour |

## Дьявол  
`dyavol` · 23 segments · this book reads at about 108 words a minute

Video: https://youtu.be/zAqYP1qDPLA

_Showing the 13 chapters that are off pace and their neighbours, of 23._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Глава 2 | 0:00:55 | 0:09:10 | 8 min | 761 | 92 | -15% | ok |
| 2 | Глава 3 | 0:09:10 | 0:11:04 | 2 min | 337 | 177 | +64% | segment too short — start later? end earlier? |
| 3 | Глава 4 | 0:11:04 | 0:23:32 | 12 min | 1292 | 104 | -4% | ok |
| 9 | Глава 10 | 0:54:50 | 1:01:48 | 7 min | 739 | 106 | -2% | ok |
| 10 | Глава 11 | 1:01:48 | 1:05:30 | 4 min | 467 | 126 | +16% | segment too short — start later? end earlier? |
| 11 | Глава 12 | 1:05:30 | 1:10:57 | 5 min | 534 | 98 | -10% | ok |
| 15 | Глава 16 | 1:31:06 | 1:36:50 | 6 min | 658 | 115 | +6% | ok |
| 16 | Глава 17 | 1:36:50 | 1:44:06 | 7 min | 667 | 92 | -15% | segment too long — swallowing a neighbour |
| 17 | Глава 18 | 1:44:06 | 1:50:36 | 6 min | 763 | 117 | +8% | ok |
| 19 | Глава 20 | 1:54:04 | 1:57:48 | 4 min | 417 | 112 | +3% | ok |
| 20 | Глава 21 | 1:57:48 | 2:04:34 | 7 min | 623 | 92 | -15% | segment too long — swallowing a neighbour |
| 21 | Глава 22 | 2:04:34 | 2:08:49 | 4 min | 340 | 80 | -26% | segment too long — swallowing a neighbour |
| 22 | Глава 23 | 2:08:49 | 2:15:04 | 6 min | 651 | 104 | -4% | ok |

## Учение Христа, изложенное для детей  
`uchenie-khrista-izlozhennoe-dlya-detey` · 9 segments · this book reads at about 150 words a minute

Video: https://youtu.be/fCz4aRA10g0

_Showing the 2 chapters that are off pace and their neighbours, of 9._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 7 | Глава 8 | 1:27:26 | 1:44:34 | 17 min | 2774 | 162 | +8% | ok |
| 8 | Глава 9 | 1:44:34 | 2:21:35 | 37 min | 2613 | 71 | -53% | segment too long — swallowing a neighbour |

## Власть тьмы (спектакль)  
`vlast-tmy-spektakl` · 5 segments · this book reads at about 105 words a minute

Video: https://youtu.be/c6CRrtUF4Nw

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:00:00 | 0:50:12 | 50 min | 4485 | 89 | -15% | ok |
| 1 | Глава 2 | 0:50:12 | 1:14:44 | 25 min | 3381 | 138 | +32% | segment too short — start later? end earlier? |
| 2 | Глава 3 | 1:14:44 | 2:17:32 | 63 min | 4118 | 66 | -37% | segment too long — swallowing a neighbour |
| 3 | Глава 4 | 2:17:32 | 2:44:05 | 27 min | 4213 | 159 | +52% | segment too short — start later? end earlier? |
| 4 | Глава 5 | 2:44:05 | 3:19:22 | 35 min | 3689 | 105 | +0% | ok |

## Мелкий бес  
`melkiy-bes` · 78 segments · this book reads at about 115 words a minute

Video: https://youtu.be/3CIe0i5_fXs

_Showing the 44 chapters that are off pace and their neighbours, of 78._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 3 | Глава 4 | 0:00:24 | 0:14:43 | 14 min | 1750 | 122 | +6% | ok |
| 4 | Глава 5 | 0:00:46 | 0:20:02 | 19 min | 2555 | 133 | +15% | segment too short — start later? end earlier? |
| 5 | Глава 6 | 0:00:05 | 0:25:48 | 26 min | 2970 | 115 | +0% | ok |
| 12 | Глава 13 | 0:00:12 | 0:18:49 | 19 min | 2206 | 118 | +3% | ok |
| 13 | Глава 14 | 0:18:49 | 0:20:28 | 2 min | 220 | 133 | +16% | segment too short — start later? end earlier? |
| 14 | Глава 15 | 0:20:28 | 0:23:41 | 3 min | 370 | 115 | -0% | ok |
| 19 | Глава 20 | 0:00:06 | 0:08:51 | 9 min | 1023 | 117 | +1% | ok |
| 20 | Глава 21 | 0:08:51 | 0:17:54 | 9 min | 879 | 97 | -16% | segment too long — swallowing a neighbour |
| 21 | Глава 22 | 0:00:05 | 0:19:17 | 19 min | 2304 | 120 | +4% | ok |
| 30 | Глава 31 | 0:09:09 | 0:13:04 | 4 min | 442 | 113 | -2% | ok |
| 31 | Глава 32 | 0:13:04 | 0:13:17 | 0 min | 45 | 208 | +80% | segment too short — start later? end earlier? |
| 32 | Глава 33 | 0:13:17 | 0:19:27 | 6 min | 687 | 111 | -3% | ok |
| 36 | Глава 37 | 0:00:39 | 0:17:48 | 17 min | 2101 | 123 | +6% | ok |
| 37 | Глава 38 | 0:17:48 | 0:20:47 | 3 min | 272 | 91 | -21% | segment too long — swallowing a neighbour |
| 38 | Глава 39 | 0:20:47 | 0:26:38 | 6 min | 791 | 135 | +17% | segment too short — start later? end earlier? |
| 39 | Глава 40 | 0:00:55 | 0:06:15 | 5 min | 667 | 125 | +9% | ok |
| 44 | Глава 45 | 0:04:48 | 0:12:18 | 8 min | 800 | 107 | -7% | ok |
| 47 | Глава 48 | 0:07:00 | 0:10:05 | 3 min | 411 | 133 | +16% | segment too short — start later? end earlier? |
| 48 | Глава 49 | 0:10:05 | 0:22:32 | 12 min | 1458 | 117 | +2% | ok |
| 49 | Глава 50 | 0:00:06 | 0:18:17 | 18 min | 1924 | 106 | -8% | ok |
| 50 | Глава 51 | 0:18:17 | 0:21:26 | 3 min | 451 | 143 | +24% | segment too short — start later? end earlier? |
| 51 | Глава 52 | 0:00:06 | 0:02:33 | 2 min | 218 | 89 | -23% | segment too long — swallowing a neighbour |
| 52 | Глава 53 | 0:02:33 | 0:06:45 | 4 min | 452 | 108 | -7% | ok |
| 53 | Глава 54 | 0:06:45 | 0:16:08 | 9 min | 1052 | 112 | -3% | ok |
| 54 | Глава 55 | 0:16:08 | 0:16:17 | 0 min | 41 | 273 | +137% | segment too short — start later? end earlier? |
| 55 | Глава 56 | 0:16:17 | 0:19:56 | 4 min | 405 | 111 | -4% | ok |
| 58 | Глава 59 | 0:04:04 | 0:10:10 | 6 min | 662 | 109 | -6% | ok |
| 59 | Глава 60 | 0:10:10 | 0:20:57 | 11 min | 1037 | 96 | -17% | segment too long — swallowing a neighbour |
| 60 | Глава 61 | 0:20:57 | 0:24:10 | 3 min | 414 | 129 | +12% | ok |
| 68 | Глава 69 | 0:19:09 | 0:21:08 | 2 min | 226 | 114 | -1% | ok |
| 69 | Глава 70 | 0:21:08 | 0:23:10 | 2 min | 158 | 78 | -33% | segment too long — swallowing a neighbour |
| 70 | Глава 71 | 0:23:10 | 0:25:36 | 2 min | 326 | 134 | +16% | segment too short — start later? end earlier? |
| 71 | Глава 72 | 0:00:24 | 0:12:06 | 12 min | 1339 | 114 | -1% | ok |
| 72 | Глава 73 | 0:12:06 | 0:12:23 | 0 min | 77 | 272 | +136% | segment too short — start later? end earlier? |
| 73 | Глава 74 | 0:12:23 | 0:13:45 | 1 min | 136 | 100 | -14% | ok |
| 75 | Глава 76 | 0:03:11 | 0:16:31 | 13 min | 1576 | 118 | +3% | ok |
| 76 | Глава 77 | 0:16:31 | 0:18:01 | 2 min | 223 | 149 | +29% | segment too short — start later? end earlier? |
| 77 | Глава 78 | 0:18:01 | 0:18:33 | 1 min | 27 | 51 | -56% | segment too long — swallowing a neighbour |
| 78 | Глава 79 | 0:18:33 | 0:20:33 | 2 min | 275 | 138 | +19% | segment too short — start later? end earlier? |
| 79 | Глава 80 | 0:20:33 | 0:21:21 | 1 min | 95 | 119 | +3% | ok |
| 80 | Глава 81 | 0:00:07 | 0:12:29 | 12 min | 1430 | 116 | +0% | ok |
| 81 | Глава 82 | 0:12:29 | 0:14:34 | 2 min | 144 | 69 | -40% | segment too long — swallowing a neighbour |
| 82 | Глава 83 | 0:14:34 | 0:15:49 | 1 min | 213 | 170 | +48% | segment too short — start later? end earlier? |
| 83 | Глава 84 | 0:00:05 | 0:14:39 | 15 min | 1581 | 109 | -6% | ok |

## Дядюшкин сон  
`dyadyushkin-son` · 15 segments · this book reads at about 114 words a minute

Video: https://youtu.be/Q3SXgeVah0k

_Showing the 8 chapters that are off pace and their neighbours, of 15._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:00:16 | 0:13:39 | 13 min | 1518 | 113 | -0% | ok |
| 1 | Глава 2 | 0:13:39 | 0:30:49 | 17 min | 1329 | 77 | -32% | segment too long — swallowing a neighbour |
| 2 | Глава 3 | 0:30:49 | 0:52:19 | 22 min | 3154 | 147 | +29% | segment too short — start later? end earlier? |
| 3 | Глава 4 | 0:52:19 | 1:23:48 | 31 min | 3576 | 114 | +0% | ok |
| 8 | Глава 9 | 3:10:40 | 3:42:35 | 32 min | 3751 | 118 | +3% | ok |
| 9 | Глава 10 | 3:42:35 | 4:10:07 | 28 min | 2335 | 85 | -25% | segment too long — swallowing a neighbour |
| 10 | Глава 11 | 4:10:07 | 4:25:29 | 15 min | 2543 | 165 | +46% | segment too short — start later? end earlier? |
| 11 | Глава 12 | 4:25:29 | 4:45:42 | 20 min | 2318 | 115 | +1% | ok |

## Чайка  
`chayka` · 4 segments · this book reads at about 113 words a minute

Video: https://youtu.be/Cf8HIMJG3yQ

_Showing the 2 chapters that are off pace and their neighbours, of 4._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Действующие лица | 0:00:18 | 0:01:28 | 1 min | 73 | 63 | -45% | segment too long — swallowing a neighbour |
| 1 | Действие первое | 0:01:28 | 0:35:44 | 34 min | 3962 | 116 | +2% | ok |

## Отрочество  
`otrochestvo` · 27 segments · this book reads at about 118 words a minute

Video: https://youtu.be/n3Wsnd8h9_s

_Showing the 8 chapters that are off pace and their neighbours, of 27._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 10 | Глава 11 | 1:23:02 | 1:33:13 | 10 min | 1331 | 131 | +10% | ok |
| 11 | Глава 12 | 1:33:13 | 1:38:53 | 6 min | 513 | 91 | -23% | segment too long — swallowing a neighbour |
| 12 | Глава 13 | 1:38:53 | 1:42:14 | 3 min | 540 | 161 | +36% | segment too short — start later? end earlier? |
| 13 | Глава 14 | 1:42:14 | 1:48:14 | 6 min | 767 | 128 | +8% | ok |
| 15 | Глава 16 | 1:58:41 | 2:09:22 | 11 min | 1310 | 123 | +4% | ok |
| 16 | Глава 17 | 2:09:22 | 2:18:18 | 9 min | 611 | 68 | -42% | segment too long — swallowing a neighbour |
| 17 | Глава 18 | 2:18:18 | 2:27:13 | 9 min | 1321 | 148 | +25% | segment too short — start later? end earlier? |
| 18 | Глава 19 | 2:27:13 | 2:34:25 | 7 min | 932 | 129 | +9% | ok |

## Братья Карамазовы  
`bratya-karamazovy` · 98 segments · this book reads at about 99 words a minute

Video: https://youtu.be/U5blK3O_Ivs

_Showing the 14 chapters that are off pace and their neighbours, of 98._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 5 | ЧАСТЬ ПЕРВАЯ — КНИГА ПЕРВАЯ — V Старцы | 1:16:30 | 1:47:13 | 31 min | 3352 | 109 | +10% | ok |
| 6 | ЧАСТЬ ПЕРВАЯ — КНИГА ВТОРАЯ — I Приехали в монастырь | 1:47:13 | 2:01:23 | 14 min | 1626 | 115 | +15% | segment too short — start later? end earlier? |
| 7 | ЧАСТЬ ПЕРВАЯ — КНИГА ВТОРАЯ — II Старый шут | 2:01:23 | 2:30:19 | 29 min | 3118 | 108 | +8% | ok |
| 14 | ЧАСТЬ ПЕРВАЯ — КНИГА ТРЕТЬЯ — I В лакейской | 5:22:58 | 5:43:09 | 20 min | 1986 | 98 | -1% | ok |
| 15 | ЧАСТЬ ПЕРВАЯ — КНИГА ТРЕТЬЯ — II Лизавета смердящая | 5:43:09 | 5:53:58 | 11 min | 1517 | 140 | +41% | segment too short — start later? end earlier? |
| 16 | ЧАСТЬ ПЕРВАЯ — КНИГА ТРЕТЬЯ — III Исповедь горячего сердца. В стихах | 5:53:58 | 6:30:39 | 37 min | 2918 | 80 | -20% | segment too long — swallowing a neighbour |
| 17 | ЧАСТЬ ПЕРВАЯ — КНИГА ТРЕТЬЯ — IV Исповедь горячего сердца. В анекдотах | 6:30:39 | 7:01:09 | 30 min | 2801 | 92 | -8% | ok |
| 53 | ЧАСТЬ ТРЕТЬЯ — КНИГА ВОСЬМАЯ — I Кузьма Самсонов | 2:33:23 | 3:14:16 | 41 min | 4033 | 99 | -1% | ok |
| 54 | ЧАСТЬ ТРЕТЬЯ — КНИГА ВОСЬМАЯ — II Лягавый | 3:14:16 | 3:50:43 | 36 min | 2448 | 67 | -32% | segment too long — swallowing a neighbour |
| 55 | ЧАСТЬ ТРЕТЬЯ — КНИГА ВОСЬМАЯ — III Золотые прииски | 3:50:43 | 4:30:04 | 39 min | 4123 | 105 | +5% | ok |
| 64 | ЧАСТЬ ТРЕТЬЯ — КНИГА ДЕВЯТАЯ — IV Мытарство второе | 1:14:59 | 1:40:25 | 25 min | 2545 | 100 | +1% | ok |
| 65 | ЧАСТЬ ТРЕТЬЯ — КНИГА ДЕВЯТАЯ — V Третье мытарство | 1:40:25 | 2:10:26 | 30 min | 3715 | 124 | +25% | segment too short — start later? end earlier? |
| 66 | ЧАСТЬ ТРЕТЬЯ — КНИГА ДЕВЯТАЯ — VI Прокурор поймал Митю | 2:10:26 | 2:45:01 | 35 min | 2717 | 79 | -21% | segment too long — swallowing a neighbour |
| 67 | ЧАСТЬ ТРЕТЬЯ — КНИГА ДЕВЯТАЯ — VII Великая тайна Мити. Освистали | 2:45:01 | 3:24:34 | 40 min | 4055 | 103 | +3% | ok |

## Библия. Синодальный перевод  
`bibliya-sinodalnyy-perevod` · 276 segments · this book reads at about 146 words a minute

Video: https://youtu.be/C8HHcfTHq38

_Showing the 26 chapters that are off pace and their neighbours, of 276._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 8 | Бытие 9 | 0:25:22 | 0:28:45 | 3 min | 509 | 150 | +3% | ok |
| 9 | Бытие 10 | 0:28:45 | 0:31:35 | 3 min | 346 | 122 | -16% | segment too long — swallowing a neighbour |
| 10 | Бытие 11 | 0:31:35 | 0:34:46 | 3 min | 462 | 145 | -0% | ok |
| 34 | Бытие 35 | 2:11:25 | 2:15:09 | 4 min | 529 | 142 | -3% | ok |
| 35 | Бытие 36 | 2:15:09 | 2:20:18 | 5 min | 619 | 120 | -18% | segment too long — swallowing a neighbour |
| 36 | Бытие 37 | 2:20:18 | 2:25:18 | 5 min | 739 | 148 | +1% | ok |
| 151 | Числа 35 | 2:41:14 | 2:46:09 | 5 min | 718 | 146 | +0% | ok |
| 152 | Числа 36 | 2:46:09 | 2:49:03 | 3 min | 304 | 105 | -28% | segment too long — swallowing a neighbour |
| 153 | Второзаконие 1 | 0:00:08 | 0:06:21 | 6 min | 952 | 153 | +5% | ok |
| 164 | Второзаконие 12 | 0:52:34 | 0:58:03 | 5 min | 762 | 139 | -5% | ok |
| 165 | Второзаконие 13 | 0:58:03 | 1:01:14 | 3 min | 370 | 116 | -20% | segment too long — swallowing a neighbour |
| 166 | Второзаконие 14 | 1:01:14 | 1:04:56 | 4 min | 548 | 148 | +2% | ok |
| 176 | Второзаконие 24 | 1:36:35 | 1:40:02 | 3 min | 538 | 156 | +7% | ok |
| 177 | Второзаконие 25 | 1:40:02 | 1:42:38 | 3 min | 316 | 122 | -17% | segment too long — swallowing a neighbour |
| 178 | Второзаконие 26 | 1:42:38 | 1:46:00 | 3 min | 509 | 151 | +4% | ok |
| 185 | Второзаконие 33 | 2:19:21 | 2:23:27 | 4 min | 523 | 128 | -13% | ok |
| 186 | Второзаконие 34 | 2:23:27 | 2:25:50 | 2 min | 217 | 91 | -38% | segment too long — swallowing a neighbour |
| 187 | Матфея 1 | 0:00:09 | 0:03:03 | 3 min | 362 | 125 | -14% | ok |
| 229 | Марка 15 | 1:10:41 | 1:15:31 | 5 min | 680 | 141 | -4% | ok |
| 230 | Марка 16 | 1:15:31 | 1:18:24 | 3 min | 321 | 111 | -24% | segment too long — swallowing a neighbour |
| 231 | Луки 1 | 0:00:10 | 0:07:58 | 8 min | 1139 | 146 | +0% | ok |
| 270 | Иоанна 16 | 1:15:54 | 1:19:41 | 4 min | 597 | 158 | +8% | ok |
| 271 | Иоанна 17 | 1:19:41 | 1:22:44 | 3 min | 518 | 170 | +16% | segment too short — start later? end earlier? |
| 272 | Иоанна 18 | 1:22:44 | 1:27:46 | 5 min | 731 | 145 | -0% | ok |
| 274 | Иоанна 20 | 1:33:08 | 1:37:03 | 4 min | 584 | 149 | +2% | ok |
| 275 | Иоанна 21 | 1:37:03 | 1:41:29 | 4 min | 549 | 124 | -15% | segment too long — swallowing a neighbour |

## Яма  
`yama` · 39 segments · this book reads at about 104 words a minute

Video: https://youtu.be/JnsE7Acq8lo

_Showing the 6 chapters that are off pace and their neighbours, of 39._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 9 | Глава 10 | 0:00:04 | 0:18:46 | 19 min | 2034 | 109 | +4% | ok |
| 10 | Глава 11 | 0:00:04 | 0:00:48 | 1 min | 60 | 82 | -21% | segment too long — swallowing a neighbour |
| 11 | Глава 12 | 0:00:48 | 0:44:23 | 44 min | 4238 | 97 | -7% | ok |
| 14 | Глава 15 | 0:00:06 | 0:32:30 | 32 min | 3344 | 103 | -1% | ok |
| 15 | Глава 16 | 0:04:13 | 0:16:51 | 13 min | 1694 | 134 | +29% | segment too short — start later? end earlier? |
| 16 | Глава 17 | 0:00:04 | 0:09:32 | 9 min | 1013 | 107 | +3% | ok |

## Красный смех  
`krasnyy-smekh` · 19 segments · this book reads at about 111 words a minute

Video: https://youtu.be/Io5The4PKHE

_Showing the 9 chapters that are off pace and their neighbours, of 19._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:00:32 | 0:14:06 | 14 min | 1179 | 87 | -22% | segment too long — swallowing a neighbour |
| 1 | Глава 2 | 0:14:06 | 0:21:16 | 7 min | 1009 | 141 | +27% | segment too short — start later? end earlier? |
| 2 | Глава 3 | 0:21:16 | 0:21:33 | 0 min | 28 | 99 | -11% | ok |
| 5 | Глава 6 | 0:57:35 | 1:12:58 | 15 min | 1680 | 109 | -1% | ok |
| 6 | Глава 7 | 1:12:58 | 1:13:55 | 1 min | 42 | 44 | -60% | segment too long — swallowing a neighbour |
| 7 | Глава 8 | 1:13:55 | 1:20:57 | 7 min | 893 | 127 | +15% | ok |
| 15 | Глава 15 | 2:09:49 | 2:21:19 | 12 min | 1267 | 110 | -1% | ok |
| 16 | Глава 16 | 2:21:19 | 2:21:29 | 0 min | 8 | 48 | -57% | segment too long — swallowing a neighbour |
| 17 | Глава 17 | 2:21:29 | 2:31:15 | 10 min | 1074 | 110 | -1% | ok |

## Юность  
`yunost` · 45 segments · this book reads at about 115 words a minute

Video: https://youtu.be/BOIXjt-_2UI

_Showing the 9 chapters that are off pace and their neighbours, of 45._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 7 | Глава 8 | 0:48:21 | 0:54:36 | 6 min | 732 | 117 | +2% | ok |
| 8 | Глава 9 | 0:54:36 | 1:02:54 | 8 min | 696 | 84 | -27% | segment too long — swallowing a neighbour |
| 9 | Глава 10 | 1:02:54 | 1:12:38 | 10 min | 1349 | 139 | +21% | segment too short — start later? end earlier? |
| 10 | Глава 11 | 1:12:38 | 1:20:07 | 7 min | 843 | 113 | -2% | ok |
| 23 | Глава 24 | 3:20:35 | 3:34:18 | 14 min | 1357 | 99 | -14% | ok |
| 24 | Глава 25 | 3:34:18 | 3:47:48 | 14 min | 1215 | 90 | -22% | segment too long — swallowing a neighbour |
| 25 | Глава 26 | 3:47:48 | 3:57:24 | 10 min | 1219 | 127 | +11% | ok |
| 26 | Глава 27 | 3:57:24 | 4:07:49 | 10 min | 1419 | 136 | +19% | segment too short — start later? end earlier? |
| 27 | Глава 28 | 4:07:49 | 4:19:18 | 11 min | 1277 | 111 | -3% | ok |

## Тарас Бульба  
`taras-bulba` · 12 segments · this book reads at about 113 words a minute

Video: https://youtu.be/CJMvJ8av-fk

_Showing the 4 chapters that are off pace and their neighbours, of 12._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:00:51 | 0:30:12 | 29 min | 3486 | 119 | +5% | ok |
| 1 | Глава 2 | 0:30:12 | 1:04:10 | 34 min | 3117 | 92 | -19% | segment too long — swallowing a neighbour |
| 2 | Глава 3 | 1:04:10 | 1:21:43 | 18 min | 2495 | 142 | +26% | segment too short — start later? end earlier? |
| 3 | Глава 4 | 1:21:43 | 1:45:11 | 23 min | 2697 | 115 | +2% | ok |

## На дне (спектакль)  
`na-dne-spektakl` · 4 segments · this book reads at about 98 words a minute

Video: https://youtu.be/uO_GRxCPbu0

_Showing the 3 chapters that are off pace and their neighbours, of 4._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 2 | Глава 3 | 0:48:23 | 1:32:52 | 44 min | 4003 | 90 | -9% | ok |
| 3 | Глава 4 | 1:32:52 | 2:13:31 | 41 min | 5008 | 123 | +25% | segment too short — start later? end earlier? |
| 4 | Глава 5 | 2:13:31 | 2:46:45 | 33 min | 3161 | 95 | -3% | ok |

## Накануне  
`nakanune` · 35 segments · this book reads at about 118 words a minute

Video: https://youtu.be/ttJEPOe0ndw

_Showing the 10 chapters that are off pace and their neighbours, of 35._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 8 | Глава 9 | 1:31:00 | 1:41:48 | 11 min | 1137 | 105 | -11% | ok |
| 9 | Глава 10 | 1:41:48 | 1:56:12 | 14 min | 1286 | 89 | -25% | segment too long — swallowing a neighbour |
| 10 | Глава 11 | 1:56:12 | 2:06:57 | 11 min | 1209 | 112 | -5% | ok |
| 11 | Глава 12 | 2:06:57 | 2:19:12 | 12 min | 1181 | 96 | -19% | segment too long — swallowing a neighbour |
| 12 | Глава 13 | 2:19:12 | 2:26:12 | 7 min | 711 | 102 | -14% | ok |
| 13 | Глава 14 | 2:26:12 | 2:38:57 | 13 min | 1182 | 93 | -22% | segment too long — swallowing a neighbour |
| 14 | Глава 15 | 2:38:57 | 3:07:55 | 29 min | 3184 | 110 | -7% | ok |
| 17 | Глава 18 | 3:35:26 | 3:49:11 | 14 min | 1470 | 107 | -10% | ok |
| 18 | Глава 19 | 3:49:11 | 3:56:15 | 7 min | 970 | 137 | +16% | segment too short — start later? end earlier? |
| 19 | Глава 20 | 3:56:15 | 4:03:24 | 7 min | 819 | 115 | -3% | ok |

## Новь  
`nov` · 29 segments · this book reads at about 118 words a minute

Video: https://youtu.be/Sdxmls9hcL0

_Showing the 10 chapters that are off pace and their neighbours, of 29._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 7 | Глава 8 | 1:53:03 | 3:37:33 | 104 min | 11677 | 112 | -5% | ok |
| 8 | Глава 9 | 3:37:33 | 3:57:27 | 20 min | 2913 | 146 | +24% | segment too short — start later? end earlier? |
| 9 | Глава 10 | 3:57:27 | 4:13:15 | 16 min | 1861 | 118 | -0% | ok |
| 10 | Глава 11 | 4:13:15 | 4:29:28 | 16 min | 1676 | 103 | -12% | ok |
| 11 | Глава 12 | 4:29:28 | 4:44:48 | 15 min | 1489 | 97 | -18% | segment too long — swallowing a neighbour |
| 12 | Глава 13 | 4:44:48 | 5:28:17 | 43 min | 6068 | 140 | +18% | segment too short — start later? end earlier? |
| 13 | Глава 14 | 5:28:17 | 6:07:56 | 40 min | 4778 | 121 | +2% | ok |
| 26 | Глава 27 | 10:26:05 | 10:40:30 | 14 min | 1633 | 113 | -4% | ok |
| 27 | Глава 28 | 10:40:30 | 11:02:10 | 22 min | 1968 | 91 | -23% | segment too long — swallowing a neighbour |
| 28 | Глава 29 | 11:02:10 | 11:22:45 | 21 min | 2822 | 137 | +16% | segment too short — start later? end earlier? |

## Мать  
`mat` · 58 segments · this book reads at about 127 words a minute

Video: https://youtu.be/yhzpV9H4dPM

_Showing the 3 chapters that are off pace and their neighbours, of 58._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 12 | Часть первая — XIII | 2:10:41 | 2:19:51 | 9 min | 1015 | 111 | -13% | ok |
| 13 | Часть первая — XIV | 2:19:51 | 2:29:03 | 9 min | 1415 | 154 | +21% | segment too short — start later? end earlier? |
| 14 | Часть первая — XV | 2:29:03 | 2:48:07 | 19 min | 2673 | 140 | +10% | ok |

## Белые ночи  
`belye-nochi` · 5 segments · this book reads at about 131 words a minute

Video: https://youtu.be/hwSBw4BZJeo

_Showing the 2 chapters that are off pace and their neighbours, of 5._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 4 | Ночь четвёртая | 1:45:08 | 2:09:02 | 24 min | 3124 | 131 | +0% | ok |
| 5 | Утро | 2:09:02 | 2:16:03 | 7 min | 740 | 105 | -19% | segment too long — swallowing a neighbour |

## Вишнёвый сад (спектакль)  
`vishnevyy-sad-spektakl` · 4 segments · this book reads at about 80 words a minute

Video: https://youtu.be/eCFnvdfRzDY

_Showing the 3 chapters that are off pace and their neighbours, of 4._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:00:00 | 0:47:53 | 48 min | 4249 | 89 | +11% | ok |
| 1 | Глава 2 | 0:47:53 | 1:34:37 | 47 min | 3061 | 65 | -18% | segment too long — swallowing a neighbour |
| 2 | Глава 3 | 1:34:37 | 2:14:25 | 40 min | 3216 | 81 | +1% | ok |

## Крейцерова соната  
`kreytserova-sonata` · 29 segments · this book reads at about 111 words a minute

Video: https://youtu.be/7TY6XFtFSOQ

_Showing the 2 chapters that are off pace and their neighbours, of 29._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:00:32 | 0:01:24 | 1 min | 80 | 92 | -17% | segment too long — swallowing a neighbour |
| 1 | Глава 2 | 0:01:24 | 0:14:49 | 13 min | 1609 | 120 | +8% | ok |

## Мёртвые души  
`myortvye-dushi` · 11 segments · this book reads at about 113 words a minute

Video: https://youtu.be/yx-95Wr-P5U

_Showing the 2 chapters that are off pace and their neighbours, of 11._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 0 | Глава 1 | 0:05:42 | 0:34:44 | 29 min | 3798 | 131 | +16% | segment too short — start later? end earlier? |
| 1 | Глава 2 | 0:34:44 | 1:30:31 | 56 min | 6348 | 114 | +1% | ok |

## Дым  
`dym` · 12 segments · this book reads at about 111 words a minute

Video: https://youtu.be/ypv0CvWL3Kk

_Showing the 3 chapters that are off pace and their neighbours, of 12._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Глава 2 | 0:09:45 | 0:18:08 | 8 min | 953 | 114 | +2% | ok |
| 2 | Глава 3 | 0:18:08 | 0:32:39 | 15 min | 1358 | 94 | -16% | segment too long — swallowing a neighbour |
| 3 | Глава 4 | 0:32:39 | 0:56:57 | 24 min | 2525 | 104 | -6% | ok |

## Мужики  
`muzhiki` · 9 segments · this book reads at about 124 words a minute

Video: https://youtu.be/8q0TTfdCnlU

_Showing the 2 chapters that are off pace and their neighbours, of 9._

| Ch | Section | Start | End | Length | Words | W/min | Off pace | Verdict |
|---|---|---|---|---|---|---|---|---|
| 7 | Глава 8 | 1:00:40 | 1:09:32 | 9 min | 1124 | 127 | +2% | ok |
| 8 | Глава 9 | 1:09:32 | 1:17:53 | 8 min | 873 | 105 | -15% | segment too long — swallowing a neighbour |

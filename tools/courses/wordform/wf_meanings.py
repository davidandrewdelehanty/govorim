# -*- coding: utf-8 -*-
"""Which documented meaning goes in which module.

Every reference points at a numbered meaning that a dictionary gives for the prefix or suffix, together with the words that
dictionary lists for that meaning — nothing here assigns a meaning to a word:
  ("ru", morpheme, n, label)  meaning n of the morpheme's entry in the Russian Wiktionary (Значение), with its example words;
                              the label is a plain English rendering of that entry's own wording, shown beside the Russian.
  ("en", key, n)              meaning n of the English Wiktionary entry for the prefix/suffix, with its example words.
  ("t1", prefix, word)        the English Wiktionary etymology of that one word glosses its prefix (e.g. убрать: у- “away”).
  ("rule", suffix)            a suffix with a single meaning in both Wiktionaries: every word Wiktionary's etymologies build
                              with it has that meaning.
Only the grouping of meanings into modules, and the module titles, are editorial.
"""

PREFIX_GROUPS = [["в", "во"], ["вз", "вс", "взо"], ["воз", "вос"], ["вы"], ["до"], ["за"], ["из", "ис", "изо"], ["на"],
                 ["над", "надо"], ["о", "об", "обо"], ["от", "ото"], ["пере"], ["по"], ["под", "подо"], ["пре"], ["пред", "предо"],
                 ["при"], ["про"], ["раз", "рас", "разо"], ["с", "со"], ["у"], ["полу"], ["без", "бес"], ["сверх"]]

PREFIX_MEANINGS = [
    ("m01-in-out-up", "Moving in, out and up", [
        ("ru", "в-", 0, "movement into something"),
        ("en", "в", 0),
        ("ru", "вы-", 1, "movement from inside to outside"),
        ("en", "вы", 0),
        ("en", "вз", 0),
        ("ru", "воз-", 0, "direction of the action upwards"),
    ]),
    ("m02-arrive-leave", "Arriving and leaving", [
        ("en", "при", 0),
        ("t1", "при-", "приходить"),
        ("ru", "у-", 0, "moving away from, leaving a place by the action of the base verb"),
        ("en", "у", 0),
        ("t1", "у-", "убрать"),
    ]),
    ("m03-approach-reach", "Approaching, moving off, reaching", [
        ("en", "под", 1),
        ("en", "от", 0),
        ("ru", "от-", 1, "moving away, removing, separating"),
        ("ru", "из-", 0, "movement, removal out of somewhere"),
        ("ru", "до-", 0, "completing an action, reaching a goal"),
        ("en", "до", 0),
    ]),
    ("m04-across-past", "Across, through and past", [
        ("en", "пере", 1),
        ("ru", "про-", 0, "direction through something"),
        ("en", "про", 0),
        ("ru", "про-", 2, "movement past and beyond something"),
        ("en", "про", 2),
        ("en", "пре", 0),
    ]),
    ("m05-around", "Around and near", [
        ("ru", "о-", 2, "going round, movement around something"),
        ("en", "о", 2),
        ("ru", "о-", 14, "surrounding; something circular"),
        ("ru", "о-", 8, "nearness, closeness"),
        ("en", "о", 3),
    ]),
    ("m06-down-together-apart", "Down, together and apart", [
        ("ru", "с-", 1, "movement from above downwards"),
        ("en", "с", 1),
        ("ru", "о-", 1, "completed falling, movement downwards"),
        ("ru", "с-", 0, "movement from different sides to one point"),
        ("ru", "с-", 3, "joint or mutual action, joining"),
        ("en", "раз", 1),
        ("ru", "раз-", 1, "spreading out, separating, widening the reach"),
    ]),
    ("m07-behind-onto", "Behind, onto and covering", [
        ("en", "за", 0),
        ("ru", "за-", 3, "an action after which the object ends up behind some boundary, real or imagined"),
        ("ru", "за-", 4, "covering, or being covered, with something"),
        ("en", "на", 0),
    ]),
    ("m08-adding", "Adding to", [
        ("ru", "до-", 1, "adding to what there was before"),
        ("en", "при", 2),
    ]),
    ("m09-ahead", "In advance", [
        ("ru", "за-", 1, "doing the action of the base word in advance, or to store"),
        ("en", "за", 2),
        ("ru", "пред-", 2, "an action carried out in advance"),
        ("en", "пред", 0),
    ]),
    ("m10-result", "Doing it fully, to the end", [
        ("ru", "вы-", 0, "fullness, exhaustion, the limit of an action"),
        ("ru", "о-", 6, "the limit, completeness, result of an action"),
        ("ru", "от-", 2, "thoroughness, completeness"),
        ("ru", "про-", 3, "completeness, exhaustion or thoroughness of an action"),
        ("ru", "с-", 7, "the limit, the result of the action itself"),
        ("ru", "у-", 5, "completing the action of the base verb, bringing it to a result or to exhaustive fullness"),
        ("ru", "по-", 2, "completing an action, covering its object fully or in part"),
        ("en", "под", 3),
        ("en", "на", 1),
        ("en", "за", 6),
        ("ru", "из-", 1, "fullness, abundance, exhaustion"),
        ("ru", "пре-", 1, "fullness or high intensity of an action"),
        ("ru", "в-", 1, "thoroughness, fullness of an action"),
    ]),
    ("m11-whole", "Over the whole thing", [
        ("ru", "о-", 3, "spreading the action over the whole object, its whole surface or volume"),
        ("ru", "у-", 1, "covering the object completely with something by the action of the base verb"),
        ("ru", "про-", 1, "an action spreading over the whole object"),
    ]),
    ("m12-loss", "Losing, using up, cutting off", [
        ("ru", "про-", 6, "loss, spending, losing"),
        ("en", "про", 6),
        ("ru", "у-", 10, "destroying or using up the object by the action of the base verb"),
        ("ru", "из-", 2, "destroying, reducing to nothing by use"),
        ("en", "из", 2),
        ("ru", "с-", 2, "removing, getting rid of"),
        ("en", "пере", 7),
    ]),
    ("m13-states", "Holding on, settling in, coming round", [
        ("ru", "у-", 4, "keeping in the state the base verb names"),
        ("en", "за", 7),
        ("ru", "у-", 9, "settling or placing something thoroughly, comfortably or for long"),
        ("ru", "о-", 5, "returning to the original state"),
        ("en", "о", 6),
        ("ru", "в-", 2, "giving or acquiring a status or state"),
        ("ru", "о-", 0, "turning into something, giving it particular properties"),
    ]),
    ("m14-perfective", "Just making the verb perfective", [
        ("en", "по", 0),
        ("en", "за", 3),
        ("t1", "с-", "сбыться"),
        ("ru", "воз-", 3, "the carrying out of the action itself"),
    ]),
    ("m15-times", "Twice, three times", [
        ("ru", "у-", 8, "making the object as many times bigger as the base numeral says"),
        ("ru", "в-", 5, "quantity"),
        ("en", "в", 4),
    ]),
    ("m16-nouns-adjectives", "Before, above, with, without, half, very", [
        ("ru", "пред-", 1, "position in front of, ahead of something"),
        ("t1", "пред-", "председатель"),
        ("ru", "над-", 3, "location above, on top of something"),
        ("ru", "со-", 1, "shared participation in something, or shared belonging"),
        ("ru", "без-", 0, "absence of the quality, feeling, object or action the root names"),
        ("ru", "бес-", 0, "absence of the quality, feeling, object or action the root names"),
        ("ru", "полу-", 0, "half of something, half-sized"),
        ("ru", "полу-", 1, "a feature not quite complete (“not quite”, “almost”)"),
        ("ru", "пре-", 0, "a high or the highest degree of a quality"),
        ("en", "пре", 1),
        ("ru", "сверх-", 2, "a feature going beyond what the base word names"),
        ("ru", "о-", 7, "something left over"),
        ("ru", "про-", 7, "being between things"),
        ("en", "про", 7),
    ]),
    ("m17-adverbs", "Adverbs of place, time and manner", [
        ("ru", "в-", 3, "the manner of an action, given by the base word"),
        ("en", "в", 3),
        ("en", "на", 3),
        ("en", "на", 4),
        ("ru", "с-", 8, "place or manner of an action"),
        ("en", "с", 3),
        ("ru", "из-", 6, "direction of an action"),
        ("en", "из", 6),
        ("ru", "от-", 5, "direction, distance"),
        ("ru", "до-", 5, "fullness, being brought to the utmost degree"),
    ]),
]

# The two «aspect» meanings that already have their own modules, built from the words' own definitions (t01, t02);
# these documented meanings are quoted there and their words added.
BEGIN_REFS = [("ru", "за-", 0, "starting to do the action"), ("en", "за", 1), ("ru", "по-", 4, "the beginning of a movement")]
WHILE_REFS = [("en", "по", 1), ("ru", "по-", 3, "doing the action for some time"), ("en", "про", 5),
              ("ru", "про-", 5, "an action lasting for a certain stretch of time")]

SUFFIX_MEANINGS = [
    ("x01-doer", "Someone who does or is something", [
        ("rule", "-тель"),
        ("ru", "-тель", 0, "someone who carries out the action of the base"),
        ("ru", "-ник", 0, "someone connected with the activity, profession, tool or material of the base"),
        ("en", "-ец", 0),
        ("ru", "-ец", 2, "someone engaged in the activity of the base"),
        ("ru", "-ец", 3, "someone who carries out the action of the base"),
        ("ru", "-ец", 6, "someone who has the property of the base"),
        ("ru", "-ец", 0, "someone belonging to the organisation or community of the base"),
        ("en", "-ок", 3),
        ("rule", "-щик"),
        ("rule", "-ист"),
    ]),
    ("x02-women", "Women", [
        ("ru", "-иц", 0, "a woman, formed from the word for the man"),
        ("ru", "-ин", 0, "a woman holding the title of the base"),
        ("ru", "-ух", 0, "a woman marked by the feature or action of the base"),
    ]),
    ("x03-places-things", "Places, things and results", [
        ("ru", "-ник", 1, "the place where the base's object lives, its territory"),
        ("ru", "-ищ", 1, "a place marked by the action of the base verb"),
        ("en", "-ок", 2),
        ("ru", "-ец", 4, "the result of the activity of the base"),
        ("en", "-ка", 2),
        ("en", "-ина", 3),
        ("ru", "-ин", 1, "the meat of these animals"),
    ]),
    ("x04-little", "Small and dear", [
        ("en", "-ок", 0),
        ("en", "-ка", 0),
        ("ru", "-к", 1, "smallness"),
        ("ru", "-иц", 1, "smallness and endearment"),
        ("ru", "-ушк", 1, "smallness, endearment"),
        ("ru", "-еньк", 0, "a noun with a diminutive meaning"),
        ("ru", "-еньк", 1, "an adjective with a diminutive meaning"),
        ("ru", "-еньк", 2, "an adverb with a diminutive meaning"),
    ]),
    ("x05-quality", "Qualities: nouns from adjectives", [
        ("rule", "-ость"),
        ("ru", "-ость", 0, "a property"),
        ("en", "-ость", 0),
        ("en", "-ота", 0),
        ("ru", "-от", 0, "an abstract feature"),
        ("ru", "-ств", 0, "a property"),
        ("ru", "-ин", 3, "abstractness"),
    ]),
    ("x06-groups", "Groups of people", [
        ("ru", "-ств", 1, "a community of people marked by the base word"),
        ("ru", "-от", 2, "a set of people marked by the base adjective"),
    ]),
    ("x07-action", "Actions and their results: nouns from verbs", [
        ("rule", "-ение"),
        ("rule", "-ание"),
        ("rule", "-ие"),
        ("en", "-ок", 7),
        ("ru", "-от", 1, "an action or the inclination to it; a physical state"),
    ]),
    ("x08-relating", "Adjectives: «of, to do with»", [
        ("rule", "-ный"),
        ("rule", "-ной"),
        ("ru", "-н", 0, "a general characteristic (having a feature)"),
        ("en", "-ский", 0),
        ("ru", "-ск", 0, "relation, typical belonging to what the base names"),
        ("ru", "-ск", 1, "features of people or things in relation to what the base names"),
        ("en", "-ской", 0),
        ("ru", "-ян", 2, "made of a material, or relating to something"),
        ("ru", "-онн", 0, "a feature or belonging named by the base"),
        ("ru", "-альн", 0, "having a property, or connected with an object"),
    ]),
    ("x09-having", "Adjectives: «having, inclined to»", [
        ("rule", "-ивый"),
        ("ru", "-ив", 0, "a constant property, an inclination to something"),
        ("ru", "-лив", 0, "an inclination to the action of the base"),
        ("en", "-тельный", 2),
        ("ru", "-тельн", 0, "characterised by a relation to the action of the base"),
        ("ru", "-оват", 0, "a quality present only slightly"),
    ]),
    ("x10-verbs", "Verbs from nouns and adjectives", [
        ("rule", "-овать"),
        ("rule", "-евать"),
        ("en", "-ить", 1),
        ("rule", "-еть"),
    ]),
    ("x11-adverbs", "Adverbs in -о", [
        ("rule", "-о"),
    ]),
]

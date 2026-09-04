
# constraint:
#     +1  notation  : the sentence uses complex phonetic notation / diacritics
#     +1  cross-type: the sentence drifts into the OPPOSITE feedback style.
#                     - articulatory feedback must NOT use English-word analogies
#                       -> +1 if it names "English" or a real English example word.
#                     - l1-informed feedback must NOT give articulatory mechanics
#                       -> +1 only if the sentence is PRIMARILY articulatory/
# hallucination:
#     +1  if the sentence contains hallucination artifacts

import re
import unicodedata


#Notations and Diactrict
IPA_CHARS = set("ɾɽɹɻʁʀχħʕʔɢɣɤɯɨʉɪʊɛɜɞɔɒɑʌæɐəɵøœɶɸβθðʃʒʂʐɕʑçʝɲŋɴɱɟʄɠɓɗʈɖɦɬɮɫʎʟɥʍɰⱱʦʣȵ")
SLASH_NOTATION = re.compile(r"/[^/\s]{1,4}/")


def hasIPA(s):
    return any(ch in IPA_CHARS for ch in s)

def hasDiacritic(s):
    return any(unicodedata.combining(ch) for ch in s)

def flagNotation(s):
    return hasIPA(s) or hasDiacritic(s) or bool(SLASH_NOTATION.search(s))


#English analogies
ENG_STRICT = re.compile(r"\bEnglish\b|\bin the word\b", re.IGNORECASE)  


def hasEnglishAnalogy(s):
    return bool(ENG_STRICT.search(s))


ANALOGY_TYPES = re.compile(
    r"\bEnglish\b"
    r"|\b(as|just|like) in\b"
    r"|\bin (the word )?[\"'“‘�][A-Za-z]"
    r"|\b(beginning|start|starts? with|first sound|ending|middle|end) of\b"
    r"|\blike the [\"'“‘�]?[A-Za-z]"
    r"|\b(word|words) [\"'“‘�][A-Za-z]"
    r"|\bsay(ing)? [\"'“‘�][A-Za-z]"
    r"|\bsound (in|like)\b"
    r"|\bthink of\b"
    r"|\bsimilar to\b"
    r"|\bpronoun\w*\b"
    r"|[\"'“‘]\w{1,3}[\"'”’] (in|at|of)\b",
    re.IGNORECASE,
)

ARTICULATORY_TYPES = re.compile(
    r"ridge (just )?behind|roof of your mouth|vocal cords|air ?flow|"
    r"soft palate|hard palate|alveolar|tip of your tongue|back of your (tongue|mouth)|"
    r"blow air|push air|release (the )?air|middle of your tongue|raise (the )?(back|middle|tip)",
    re.IGNORECASE,
)


def flagCrossType(s, condition):
    if condition == "articulatory":
        return hasEnglishAnalogy(s)
    else:
        return bool(ARTICULATORY_TYPES.search(s)) and not bool(ANALOGY_TYPES.search(s))


#Hallucination
EMPTY_QUOTES = re.compile(r"''|\"\"|“”|‘’")


def flagHallucination(s):
    if EMPTY_QUOTES.search(s):
        return True
    if "�" in s:
        return True
    for ch in s:
        cat = unicodedata.category(ch)
        if cat in ("So", "Co"):
            return True
        if cat == "Cc" and ch not in "\r\n\t":
            return True
    return False


#Functions
def GradeSentence(sentence, condition):
    if condition not in ("articulatory", "l1-informed"):
        raise ValueError(f"condition must be 'articulatory' or 'l1-informed', got {condition!r}")

    constraint = (1 if flagNotation(sentence) else 0) + (1 if flagCrossType(sentence, condition) else 0)
    hallucination = 1 if flagHallucination(sentence) else 0
    
    return constraint, hallucination



def GradeEntry(outputs, condition):
    c = h = 0
    for o in outputs:
        dc, dh = GradeSentence(o, condition)
        c += dc
        h += dh
    return c, h


if __name__ == "__main__":
    import json
    from pathlib import Path

    results_dir = Path(__file__).resolve().parent / "LLM-Results"
    files = sorted(results_dir.glob("results_*.json"))
    if not files:
        raise SystemExit(f"No results_*.json files found in {results_dir}")

    for path in files:
        
        with path.open(encoding="utf-8") as f:
            entries = json.load(f)

        for entry in entries:
            condition = entry["condition"]
            c, h = GradeEntry(entry["outputs"], condition)
            entry["constraint_grade"] = c
            entry["hallucination_grade"] = h

        with path.open("w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
            f.write("\n")

        total_c = sum(e["constraint_grade"] for e in entries)
        total_h = sum(e["hallucination_grade"] for e in entries)
        print(
            f"{path.name}: {len(entries)} entries graded "
            f"(constraint sum={total_c}, hallucination sum={total_h})"
        )

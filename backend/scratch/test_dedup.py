import re
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def deduplicate_consecutive_phrases(text: str) -> str:
    if not text:
        return ""
    # 1. Deduplicate consecutive identical sentences
    sentences = re.split(r"(?<=[.!?।])\s+", text.strip())
    cleaned_sentences = []
    prev_norm = None
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        norm = re.sub(r"[.!?।\s]+", "", s_clean.lower())
        if norm and norm == prev_norm:
            continue
        cleaned_sentences.append(s_clean)
        prev_norm = norm
    
    res = " ".join(cleaned_sentences).strip()

    # 2. Also check if a phrase of 3+ words is repeating consecutively within a sentence
    # e.g., "நண்டர்களது இனப்பகுதி 2வது என்பதின் நண்டர்களது இனப்பகுதி 2வது என்பதின்"
    words = res.split()
    if len(words) >= 6:
        for phrase_len in range(3, 10):
            i = 0
            new_words = []
            while i < len(words):
                phrase = words[i:i+phrase_len]
                next_phrase = words[i+phrase_len:i+2*phrase_len]
                if len(phrase) == phrase_len and phrase == next_phrase:
                    # Skip duplicate phrase
                    new_words.extend(phrase)
                    i += 2 * phrase_len
                    # Skip any further consecutive duplicates
                    while i + phrase_len <= len(words) and words[i:i+phrase_len] == phrase:
                        i += phrase_len
                else:
                    new_words.append(words[i])
                    i += 1
            words = new_words
        res = " ".join(words)

    return res

test_tamil = (
    "விளையாடல் ஆரம்பிக்கிறது. "
    "இதனை மதினையாக எழுதியது என்பது நூல் இருந்துவாதம். "
    "இதனை மதினையாக எழுதியது என்பது நூல் இருந்துவாதம். "
    "இதனை மதினையாக எழுதியது என்பது நூல் இருந்துவாதம். "
    "இதனை மதினையாக எழுதியது என்பது நூல் இருந்துவாதம். "
    "நன்றி."
)

print("Original length:", len(test_tamil.split()))
deduped = deduplicate_consecutive_phrases(test_tamil)
print("Deduped:\n", deduped)
print("Deduped length:", len(deduped.split()))

# APS Layer — Plan to "Validated & Done"

**Goal:** a component that, given (a) a learner's audio and (b) the target word they were
asked to say, reliably reports whether each of 5 target features was produced correctly.
This is the last technical milestone; after it, the research is literature review +
participant experiments. Optimize for **"good enough, measured, defensible,"** not maximal
sophistication.

## The reframe that makes this tractable

The APS does **known-target detection**, not open transcription. You always know the prompt
word, so you know the canonical IPA and *where* each target feature should occur. You are
asking 5 yes/no questions, not "transcribe everything":

| # | Feature | The question | Confusable with |
|---|---------|--------------|-----------------|
| 1 | singleton / geminate | is the stop/affricate long? | plain consonant |
| 2 | short / long vowel | is the vowel long? | short vowel |
| 3 | vowel devoicing | is the vowel devoiced/dropped? | fully voiced vowel |
| 4 | Japanese ɸ ("fu") | is /ɸ/ produced? | English f, h |
| 5 | Japanese ɾ ("r") | is /ɾ/ produced? | English ɹ, l, d |

**Consequence:** overall PER is the WRONG success metric. A model can have great PER and
miss devoicing, or mediocre PER and nail gemination. Success = per-feature detection
accuracy on realistic audio.

---

## Phase 0 — Decide the detection strategy (do this first, on paper)

Two ways the APS can turn model output into a yes/no per feature. Pick per feature; you can
mix.

- **A. Symbol-presence check.** Run recognizer → get phoneme string → check whether the
  target symbol/marker is present near the expected slot (e.g. is there a `ː`/`cl`/geminate
  marker on the consonant? is `ɸ` present where the word has fu?). Simple, interpretable,
  no training. Works when the model *emits* the distinction.
- **B. Alignment + duration/acoustic check.** Force-align audio to the target phonemes, then
  measure the physical cue directly: geminate = closure duration ratio; long vowel = vowel
  duration ratio; devoicing = voicing/energy in the vowel region. Model-independent for the
  duration features; more robust than trusting the model's symbol.

**Recommendation:** duration-based features (geminate #1, long vowel #2) are *fundamentally
duration contrasts* — strategy B (measure duration) is more reliable and honest than hoping
a CTC model emits `ː`. Devoicing #3 is also acoustic (voicing/energy) → B. The two
*segmental* features (ɸ #4, ɾ #5) are about identity → strategy A (symbol presence) fits.
This split also reads well in a thesis: "duration features measured acoustically, segmental
features via phoneme recognition."

---

## Phase 1 — Build the feature test set  (your idea #1)

This is the linchpin and also a thesis deliverable. Small, targeted, minimal pairs.

1. **Minimal pairs per feature**, each with a "correct" and an "error" realization:
   - geminate: 来た kita / 切った kitta; 罰 batsu / ばっか bakka; buka / bukka (you have these)
   - long vowel: おばさん obasan / おばあさん obaasan; ここ koko / こうこう koukou
   - devoicing: です desu (dev.) vs a voiced-vowel foil; した shita; 好き suki
   - fu: ふ fu (ɸ) vs learner "hu"/"foo"; 富士 fuji
   - r: ら ra (ɾ) vs English "rah" (ɹ); られる rareru
2. **Audio sources, in priority order:**
   - **Native correct**: Forvo (you have some), plus JVS clips you already trust.
   - **Learner-error realizations**: this is the hard part. Options: (a) record a few
     English L1 speakers deliberately producing the L2 errors (even you + labmates — n is
     small, this is a *validation* set not a study), (b) synthesize error cases (e.g. TTS
     with wrong length), (c) mine any existing L2-Japanese corpus.
   - You need BOTH correct and error audio, or you can only measure false-negatives.
3. **Label schema (CSV), one row per clip:**
   `file, target_word, target_ipa, feature, feature_slot_index, gold_label(correct/error)`
   Keep it ~15–30 clips per feature to start. Small is fine — it's a validation set.

**Deliverable:** `feature_test_set/` + `labels.csv`. This alone de-risks everything after.

---

## Phase 2 — Feature-only evaluation harness  (your idea #2)

One function per feature: `detect_<feature>(audio, target_ipa, slot) -> bool + score`.
Then score each candidate model/strategy against `labels.csv`:

- Metrics **per feature**: accuracy, precision/recall, and confusion (miss vs false alarm).
- Report a small table: rows = features, columns = candidate systems.
- This replaces PER entirely as your success criterion.

Candidate systems to put in the table (cheap to include, you already have most loaded):
your fine-tuned XLSR, **prj-beatrice Hubert-v5** (already strong on Forvo: emits `cl` for
gemination, correct `ɾ`), Allosaurus, MMS, and a pure-duration baseline (montreal/torch
forced alignment). Let the table tell you which wins each feature.

---

## Phase 3 — Decide the architecture from the table  (your ideas #3/#4)

Now "one model per feature" vs "one model" becomes an *evidence-based* choice, not a guess:

- If one system wins ≥4/5 features → use it; special-case the one loser. **Likely outcome.**
- If duration features are best via alignment and segmental via a recognizer → hybrid:
  1 recognizer + 1 aligner, not 5 models. This is clean and defensible.
- "One model per feature" only if the table genuinely shows no single system is adequate —
  avoid it unless forced; it multiplies maintenance for marginal gain.

**Strong prior given your data:** Hubert-v5 (Japanese-native) + a forced aligner for
duration will likely beat your fine-tuned XLSR on Forvo audio, because the domain gap
(JVS/TIMIT studio speech → noisy learner audio) is your real problem, not model capacity.
Your fine-tune may still win on the ɸ/ɾ identity features. The table decides.

---

## Phase 4 — Only if needed: close the domain gap

If no system clears your bar on realistic audio, THEN train — but targeted:
- Data augmentation (add noise, reverb, mic/codec variation, ±speed) so the model sees
  Forvo-like conditions. Cheapest high-impact fix; your JVS fine-tune never saw noise.
- Do NOT chase lower PER. Retrain only to improve the *feature detections that failed*.

---

## Definition of done (write this into the thesis)

> The APS layer detects each of the 5 target features at ≥ X% accuracy on a held-out
> feature test set of native-correct and L1-English-error realizations, using
> [chosen architecture]. Duration features are measured by forced-alignment duration
> ratios; segmental features by phoneme recognition symbol presence.

Pick X (e.g. 85–90%) up front. Once hit, the APS is DONE — stop, move to the experiments.

## Ordered checklist
- [ ] Phase 0: write down the per-feature detection strategy (A/B) — 1 sitting
- [ ] Phase 1: assemble feature test set + labels.csv — the real work
- [ ] Phase 2: build `detect_*` functions + scoring table
- [ ] Phase 3: read the table, pick architecture
- [ ] Phase 4: augment/retrain ONLY the features that missed
- [ ] Lock "done" criterion, write the methods paragraph, move on

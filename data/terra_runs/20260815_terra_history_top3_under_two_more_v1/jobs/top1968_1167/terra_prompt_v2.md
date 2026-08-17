# Terra classifier tie-breaker v2

Apply `METHODOLOGY.md` and the existing production classifier contract exactly.
This is a tie-breaker for Goodreads excerpts whose speaker context or quotation
marks have been stripped; it is a nudge, not a replacement rule.

- Call a quote `dialogue` only with affirmative evidence of character speech:
  quotation-mark majority, a speaker attribution or exchange, a clear vocative or
  conversational turn, or unmistakable spoken-address framing.
- First-person reflection is not dialogue merely because it could be spoken. When
  it is anchored to a narrator's memory, perception, state, or story-specific
  experience, prefer `event` and classify its grammatical tense.
- If a passage mixes recollection with a generalizing sentence, retain `event`
  when its controlling frame is story-specific narration. Do not discard its
  event evidence merely because a subordinate sentence is aphoristic.
- When speech versus narration is genuinely irresolvable, use `unclear` with a
  short note rather than defaulting to `dialogue`.

These rules do not weaken the quotation-mark-majority precedence rule. They only
apply when that test supplies no answer.

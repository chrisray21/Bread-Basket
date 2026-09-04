# Bread Basket

Four pass-and-play games for four people sitting at a restaurant table waiting
for food. One phone, passed around. Two teams of two.

Open `index.html` in any browser. That is the whole thing — one self-contained
file, no build step, no server, no dependencies. Once the page has loaded it
needs no connection, so it works in the car with no signal.

## The games

| Game | Type | Time | Ages |
|---|---|---|---|
| **Table Agents** | Word / clue-giving | 10–15 min | 8+ |
| **Cows & Bulls** | Deduction | 5–10 min | 9+ |
| **Bomb Range** | Nerve | 3–5 min | 6+ |
| **Race to 31** | Strategy | 2 min | 6+ |

Every game carries a "How to play" panel written for a 10-year-old reader:
short sentences, plain words, and a worked example. The rules are also reachable
mid-game from the **Rules** button in the top bar.

## Design notes worth keeping

**Table Agents — hold to see the key.** The clue-giver presses and holds the key
button; the board flips to the colour key only while their thumb is down and
snaps back the instant they release. That gesture *is* the security model. The
key button is then removed entirely once the phone is passed, so guessers cannot
peek even by accident.

**Table Agents — guess budget.** The clue-giver sets the clue number on screen
before passing. The guessers get exactly N+1 taps, shown as dots that fill in as
they're spent, and the turn ends by itself when they run out. A wrong colour
ends it immediately.

**Rules that teach rather than instruct.** Race to 31 deliberately withholds its
solution and tells players a pattern exists. Bomb Range likewise says nothing
about optimal play. Spoiling either would remove the reason to play twice.

**Bomb Range — the explosion.** Landing on the secret number fires a canvas
particle burst from the middle of the range box: white-hot core, expanding
shockwave, ~135 embers with motion-blurred tails under gravity and drag, smoke
puffs, and a dark scorch veil over the whole page so the fire reads on both the
light and dark themes. The screen shakes for half a second. The win panel is
deliberately held back until a second into the blast — the explosion is the
result, and announcing the loser over the top of it would waste it. The origin
is clamped into the middle band of the viewport, because the range box sits high
on a phone and a blast centred on it loses its top half off-screen. Under
`prefers-reduced-motion` the whole thing collapses to one still frame of scorch
and sparks that fades after 400ms.

**Two-tap New game.** One stray thumb should not wipe a live board.

## Testing

`test.py` drives the real page in headless Chromium and runs 50 checks across
all four games.

```
pip install playwright
playwright install chromium
python test.py
```

Two checks are worth knowing about. A solver plays Cows & Bulls to completion
using only the on-screen bull/cow feedback — if the scoring were wrong, the
candidate set would empty out and the test would fail. A binary search plays
Bomb Range the same way, which proves the range narrowing is correct. The suite
also confirms the assassin ends the game, the tap budget is enforced exactly,
`+3` is blocked at a total of 29, both light and dark themes resolve, and
nothing scrolls sideways down to a 320px-wide screen.

Screenshots are written beside the test as `shot-*.png`.

## Structure

Everything lives in `index.html`:

- **CSS custom properties** at the top define the palette once. Light theme on
  bare `:root`, dark redefined under both `prefers-color-scheme` and
  `[data-theme="dark"]`, so the page is correct whether the viewer has chosen a
  theme or left it on system.
- `--c` is the **accent slot**. The router sets it to the current game's colour;
  inside a game each view overrides it with the colour of the team whose turn it
  is. Every button, banner and border reads from it, so the whole screen shifts
  colour when the turn passes.
- **One `RULES` object** holds the rules HTML, rendered into both the home cards
  and the in-game modal, so there is only one copy to edit.
- Each game is a `start*` / `render` pair over a single state object, with the
  view swapped by `open()` / `home()`.

## Possible next steps

- Word decks for Table Agents: an easier one for younger kids, a harder one for
  adults, chosen at deal time.
- A clue log for Table Agents, listing past clues and their numbers.
- A three-player mode (one clue-giver, everyone guesses, beat your own record)
  for nights when someone is missing.
- An optional round timer.
- A web app manifest so "Add to Home Screen" gives it a real icon and opens it
  without browser chrome.

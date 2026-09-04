"""Browser test suite for Bread Basket.

Drives the real page in headless Chromium and checks all four games end to end.
    pip install playwright && playwright install chromium
    python test.py          # exits 0 when every check passes

Screenshots land beside this file as shot-*.png.
"""
import itertools, pathlib, sys
from playwright.sync_api import sync_playwright

URL = pathlib.Path("index.html").resolve().as_uri()
errs, fails = [], []

def check(cond, msg):
    if not cond:
        fails.append(msg)
        print("  FAIL:", msg)
    else:
        print("  ok:", msg)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.on("console", lambda m: errs.append(m.text) if (m.type == "error" and "fonts.googleapis" not in m.text and "ERR_TUNNEL" not in m.text) else None)
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.goto(URL)
    pg.wait_for_timeout(600)

    print("\n== HOME ==")
    check(pg.locator("#games .game").count() == 4, "4 game cards")
    check(pg.locator("#games .play").count() == 4, "4 play buttons")
    pg.screenshot(path="shot-home.png", full_page=True)

    # ---------------- TABLE AGENTS ----------------
    print("\n== TABLE AGENTS ==")
    pg.locator("#games .game").nth(0).locator(".play").click()
    pg.wait_for_timeout(250)
    check(pg.locator("#a-board .cell").count() == 25, "25 cards dealt")
    check(pg.locator("#a-board .cell[data-face]").count() == 0, "key hidden before hold")

    kb = pg.locator("#a-key")
    box = kb.bounding_box()
    pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    pg.mouse.down()
    pg.wait_for_timeout(120)
    faces = pg.locator("#a-board .cell").evaluate_all("els => els.map(e => e.dataset.face)")
    check(len([f for f in faces if f]) == 25, "hold reveals all 25 faces")
    check(faces.count("void") == 1, "exactly one assassin")
    check(sorted([faces.count("red"), faces.count("teal")]) == [8, 9], "9/8 team split")
    check(faces.count("tan") == 7, "7 bystanders")
    pg.screenshot(path="shot-agents-key.png")
    pg.mouse.up()
    pg.wait_for_timeout(120)
    check(pg.locator("#a-board .cell[data-face]").count() == 0, "key hides on release")

    # first team = the one with 9
    first = "red" if faces.count("red") == 9 else "teal"
    banner = pg.locator("#a-banner").inner_text().lower()
    check(first in banner, "banner names the starting team (%s)" % first)

    # board must not be tappable during the clue phase
    check(pg.locator("#a-board .cell").nth(0).is_disabled(), "board locked during clue phase")

    # set clue number to 3, pass, verify 4 taps
    pg.locator("#a-plus").click()
    check(pg.locator("#a-num").inner_text() == "3", "stepper reaches 3")
    pg.locator("#a-pass").click()
    pg.wait_for_timeout(150)
    check(pg.locator("#a-key").count() == 1 and pg.locator("#a-clue").is_hidden(), "key button gone after pass")
    check("4 TAPS LEFT" in pg.locator("#a-tapstext").inner_text().upper(), "N+1 = 4 taps granted")
    check(pg.locator("#a-tapdots .tapdot").count() == 4, "4 tap dots")

    # tap 4 correct cards -> turn must auto-end
    mine = [i for i, f in enumerate(faces) if f == first]
    for n, i in enumerate(mine[:4]):
        pg.locator("#a-board .cell").nth(i).click()
        pg.wait_for_timeout(60)
        if n < 3:
            want = "1 TAP LEFT" if (3 - n) == 1 else "%d TAPS LEFT" % (3 - n)
            check(want in pg.locator("#a-tapstext").inner_text().upper(),
                  "tap %d leaves %d" % (n + 1, 3 - n))
    pg.wait_for_timeout(120)
    check(pg.locator("#a-clue").is_visible(), "budget exhausted -> turn auto-ends")
    check(first not in pg.locator("#a-banner").inner_text().lower(), "turn passed to the other team")
    pg.screenshot(path="shot-agents.png")

    # wrong-colour tap ends turn immediately
    second = "teal" if first == "red" else "red"
    pg.locator("#a-pass").click()
    theirs_wrong = [i for i, f in enumerate(faces) if f == "tan"][0]
    pg.locator("#a-board .cell").nth(theirs_wrong).click()
    pg.wait_for_timeout(150)
    check(pg.locator("#a-clue").is_visible(), "bystander tap ends the turn at once")

    # assassin ends the game
    pg.locator("#a-pass").click()
    assassin = faces.index("void")
    pg.locator("#a-board .cell").nth(assassin).click()
    pg.wait_for_timeout(250)
    check(pg.locator(".modal .panel.win").count() == 1, "assassin triggers game over")
    check("WINS" in pg.locator(".modal h3").inner_text().upper(), "winner announced")
    pg.screenshot(path="shot-agents-win.png")
    pg.locator(".modal .btn").nth(1).click()   # back to basket
    pg.wait_for_timeout(200)
    check(pg.locator("#view-home").is_visible(), "back to basket works")

    # ---------------- COWS & BULLS ----------------
    print("\n== COWS & BULLS ==")
    pg.locator("#games .game").nth(1).locator(".play").click()
    pg.wait_for_timeout(250)
    check(pg.locator("#c-entry .slot").count() == 4, "4 entry slots")
    check(pg.locator("#c-pad .key").count() == 12, "12 keypad keys")
    check(pg.locator('#c-pad .key.go').is_disabled(), "Guess disabled while empty")

    def key(ch):
        pg.locator("#c-pad .key", has_text=ch).first.click()

    # repeat-digit guard
    pg.locator("#c-pad .key").nth(0).click()   # 1
    check(pg.locator("#c-pad .key").nth(0).is_disabled(), "used digit disabled (no repeats)")
    pg.locator('#c-pad .key.wide:not(.go)').click()  # delete
    check(not pg.locator("#c-pad .key").nth(0).is_disabled(), "delete frees the digit")

    cands = ["".join(c) for c in itertools.permutations("0123456789", 4)]
    def score(g, s):
        bl = sum(1 for i in range(4) if g[i] == s[i])
        cw = sum(1 for i in range(4) if g[i] != s[i] and g[i] in s)
        return bl, cw

    guesses = 0
    while cands and guesses < 12:
        g = cands[0]
        for ch in g:
            pg.locator("#c-pad .key").nth("1234567890".index(ch) if ch != "0" else 10).click()
        pg.locator("#c-pad .key.go").click()
        pg.wait_for_timeout(80)
        guesses += 1
        if pg.locator(".modal .panel.win").count():
            break
        top = pg.locator("#c-log .row").first
        tags = top.locator(".tag").all_inner_texts()
        bl = int(tags[0].split()[0]); cw = int(tags[1].split()[0])
        cands = [c for c in cands if score(g, c) == (bl, cw)]
        if guesses == 1:
            pg.screenshot(path="shot-cows.png")
    check(pg.locator(".modal .panel.win").count() == 1, "solver cracked the code in %d guesses" % guesses)
    check(guesses <= 8, "solved within 8 guesses (feedback is consistent)")
    pg.locator(".modal .btn").nth(1).click()
    pg.wait_for_timeout(200)

    # ---------------- BOMB RANGE ----------------
    print("\n== BOMB RANGE ==")
    pg.locator("#games .game").nth(2).locator(".play").click()
    pg.wait_for_timeout(250)
    check(pg.locator("#b-lo").inner_text() == "1" and pg.locator("#b-hi").inner_text() == "1000", "range starts 1-1000")
    check(pg.locator("#b-pad .key.go").is_disabled(), "Guess disabled while empty")

    def bkey(ch):
        idx = "1234567890".index(ch)
        pg.locator("#b-pad .key").nth(idx if ch != "0" else 10).click()

    turns = 0
    blew_up = False
    while not blew_up and turns < 40:
        lo = int(pg.locator("#b-lo").inner_text()); hi = int(pg.locator("#b-hi").inner_text())
        mid = (lo + hi) // 2
        for ch in str(mid):
            bkey(ch)
        check_ok = not pg.locator("#b-pad .key.go").is_disabled()
        if not check_ok:
            fails.append("mid guess %d rejected for range %d-%d" % (mid, lo, hi)); break
        pg.locator("#b-pad .key.go").click()
        pg.wait_for_timeout(70)
        turns += 1
        if turns == 3:
            pg.screenshot(path="shot-bomb.png")
        if pg.locator("#b-boom").count():
            blew_up = True
            # mid-blast: canvas is up, the app is shaking, the modal has not arrived yet
            check(pg.locator("#b-boom").count() == 1, "explosion canvas appears on the bomb")
            check(pg.evaluate("document.getElementById('app').classList.contains('shake')"),
                  "screen shake fires with the blast")
            check(pg.locator(".modal .panel.win").count() == 0, "win panel waits for the explosion")
            pg.wait_for_timeout(180)
            pg.screenshot(path="shot-boom.png")
            pg.wait_for_selector(".modal .panel.win", timeout=5000)
            pg.wait_for_timeout(1200)
            check(pg.locator("#b-boom").count() == 0, "explosion canvas cleans itself up")
            check(not pg.evaluate("document.getElementById('app').classList.contains('shake')"),
                  "shake class removed after the blast")
    check(pg.locator(".modal .panel.win").count() == 1, "bomb found after %d guesses" % turns)
    check(blew_up, "explosion played before the result")
    check(turns <= 11, "binary search converges in <=11 (range logic correct)")
    txt = pg.locator(".modal .why").inner_text()
    check("set off the bomb" in txt, "loss message: %r" % txt)
    pg.locator(".modal .btn").nth(1).click()
    pg.wait_for_timeout(200)

    # ---------------- RACE TO 31 ----------------
    print("\n== RACE TO 31 ==")
    pg.locator("#games .game").nth(3).locator(".play").click()
    pg.wait_for_timeout(250)
    check(pg.locator("#r-ladder .rung").count() == 31, "31 rungs")
    check(pg.locator("#r-total").inner_text() == "0", "total starts at 0")
    for i in range(31):
        if pg.locator(".modal .panel.win").count():
            break
        pg.locator('#view-race .add[data-n="1"]').click()
        pg.wait_for_timeout(30)
        if i == 8:
            pg.screenshot(path="shot-race.png")
    check(pg.locator(".modal .panel.win").count() == 1, "reaching 31 ends the game")
    check(pg.locator("#r-total").inner_text() == "31", "total lands on 31")
    check(pg.locator("#r-ladder .rung.red").count() + pg.locator("#r-ladder .rung.teal").count() == 31,
          "all 31 rungs claimed")
    pg.locator(".modal .btn").nth(1).click()
    pg.wait_for_timeout(150)

    # overflow guard: 29 + 3 must be blocked
    pg.locator("#games .game").nth(3).locator(".play").click()
    pg.wait_for_timeout(200)
    for _ in range(29):
        pg.locator('#view-race .add[data-n="1"]').click()
        pg.wait_for_timeout(15)
    check(pg.locator('#view-race .add[data-n="3"]').is_disabled(), "+3 blocked at total 29")
    check(not pg.locator('#view-race .add[data-n="2"]').is_disabled(), "+2 still allowed at 29")

    # ---------------- DARK THEME ----------------
    print("\n== DARK THEME ==")
    pg.emulate_media(color_scheme="dark")
    pg.locator("#back").click()
    pg.wait_for_timeout(300)
    pg.screenshot(path="shot-home-dark.png", full_page=True)
    bg = pg.evaluate("getComputedStyle(document.body).backgroundColor")
    check(bg == "rgb(20, 24, 26)", "dark ground applied: " + bg)

    b.close()

print("\n" + "=" * 46)
print("console errors:", errs if errs else "none")
print("failures:", len(fails))
for f in fails:
    print("  -", f)
sys.exit(1 if (fails or errs) else 0)

# ♟️ Chess For Dad

A calm, dead-simple chess board for two people to play together — for anyone who
finds chess.com busy and confusing. 🫶

One big high-contrast board, tap a piece to see its moves as fat dots, an
impossible-to-miss **Take back** button, and plain-language "*Name* to move." ✨
No clock, no accounts, no menus, no notation — and illegal moves simply can't be
made. ♜

![Chess For Dad board](assets/screenshot.jpg)

## 🧠 One rules brain, no bugs

The move legality and game status come from **OmegaZero**, my C++ chess engine —
its move generator, extracted and stripped down to just the rules. Same logic,
one source of truth, verified with `perft`:

```
make                     # build the chess-for-dad rules brain
./chess-for-dad perft 4  # move-generation self-check
./chess-for-dad moves    # legal moves + game status for a position
```

## ▶️ Play

**Two devices, live** — one command:

```
./start.sh        # builds if needed, then prints a link for each device
```

Open the printed link on both devices (same Wi-Fi) and moves sync instantly. 📱↔️📱

**One device** (pass-and-play) works with no server at all — just open `index.html`
or the [live board](https://noah8368.github.io/chess-for-dad/).

Tap the gear ⚙️ to set names, which side faces you, and **You play: White / Black /
Both** — so each person only moves their own pieces (or add `?side=w` / `?side=b`
to the URL).

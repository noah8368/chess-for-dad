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

Open `index.html`, or serve the folder:

```
python3 -m http.server 8000   # then visit http://localhost:8000
```

Tap the gear ⚙️ to set both players' names and which side faces you.

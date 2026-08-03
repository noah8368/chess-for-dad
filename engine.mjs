// Minimal, correct chess ruleset for the "play with Dad" board.
// PREVIEW-ONLY stand-in for OmegaZero's Board/GetGameStatus: the shipped
// remote version routes all legality + status through the OZ binary instead.
// Validated with perft (see perft.mjs) the same way OZ is validated.
//
// Square index = rank*8 + file, a1 = 0, h8 = 63. White pawns move +8.
// Pieces: uppercase = white (PNBRQK), lowercase = black, null = empty.

export const WHITE = 'w';
export const BLACK = 'b';

const isWhite = (p) => p !== null && p === p.toUpperCase();
const colorOf = (p) => (p === null ? null : isWhite(p) ? WHITE : BLACK);
const fileOf = (s) => s & 7;
const rankOf = (s) => s >> 3;
const onBoard = (f, r) => f >= 0 && f < 8 && r >= 0 && r < 8;

export function initialState() {
  const board = new Array(64).fill(null);
  const back = ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'];
  for (let f = 0; f < 8; f++) {
    board[f] = back[f];              // white back rank (rank 1)
    board[8 + f] = 'P';             // white pawns (rank 2)
    board[48 + f] = 'p';           // black pawns (rank 7)
    board[56 + f] = back[f].toLowerCase(); // black back rank (rank 8)
  }
  return {
    board,
    turn: WHITE,
    castling: { K: true, Q: true, k: true, q: true },
    ep: -1,          // en-passant target square, or -1
    halfmove: 0,     // plies since last pawn move / capture (50-move rule)
    fullmove: 1,
  };
}

const KNIGHT_DELTAS = [
  [1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2],
];
const KING_DELTAS = [
  [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1],
];
const BISHOP_DIRS = [[1, 1], [1, -1], [-1, 1], [-1, -1]];
const ROOK_DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1]];

export function kingSquare(board, color) {
  const k = color === WHITE ? 'K' : 'k';
  for (let s = 0; s < 64; s++) {
    if (board[s] === k) return s;
  }
  return -1;
}

// Is `sq` attacked by any piece of `by`?
export function isSquareAttacked(board, sq, by) {
  const f = fileOf(sq);
  const r = rankOf(sq);

  // Pawn attackers: a pawn attacks diagonally forward, so it sits one rank
  // *behind* the target from its own perspective.
  const pawnRank = by === WHITE ? r - 1 : r + 1;
  const pawnChar = by === WHITE ? 'P' : 'p';
  for (const df of [-1, 1]) {
    if (onBoard(f + df, pawnRank)) {
      if (board[pawnRank * 8 + (f + df)] === pawnChar) return true;
    }
  }

  // Knight attackers.
  const knightChar = by === WHITE ? 'N' : 'n';
  for (const [df, dr] of KNIGHT_DELTAS) {
    if (onBoard(f + df, r + dr)) {
      if (board[(r + dr) * 8 + (f + df)] === knightChar) return true;
    }
  }

  // King attackers.
  const kingChar = by === WHITE ? 'K' : 'k';
  for (const [df, dr] of KING_DELTAS) {
    if (onBoard(f + df, r + dr)) {
      if (board[(r + dr) * 8 + (f + df)] === kingChar) return true;
    }
  }

  // Sliding attackers (bishop/queen on diagonals, rook/queen on lines).
  const bishopChar = by === WHITE ? 'B' : 'b';
  const rookChar = by === WHITE ? 'R' : 'r';
  const queenChar = by === WHITE ? 'Q' : 'q';
  for (const [dirs, sliders] of [
    [BISHOP_DIRS, [bishopChar, queenChar]],
    [ROOK_DIRS, [rookChar, queenChar]],
  ]) {
    for (const [df, dr] of dirs) {
      let nf = f + df;
      let nr = r + dr;
      while (onBoard(nf, nr)) {
        const p = board[nr * 8 + nf];
        if (p !== null) {
          if (sliders.includes(p)) return true;
          break;
        }
        nf += df;
        nr += dr;
      }
    }
  }
  return false;
}

export function inCheck(state, color) {
  return isSquareAttacked(state.board, kingSquare(state.board, color),
                          color === WHITE ? BLACK : WHITE);
}

// Pseudo-legal moves (may leave own king in check; filtered by legalMoves).
function pseudoMoves(state) {
  const { board, turn, ep, castling } = state;
  const moves = [];
  const enemy = turn === WHITE ? BLACK : WHITE;
  const forward = turn === WHITE ? 1 : -1;
  const startRank = turn === WHITE ? 1 : 6;
  const promoRank = turn === WHITE ? 7 : 0;

  const add = (from, to, extra = {}) => moves.push({ from, to, ...extra });
  const addPawn = (from, to, extra = {}) => {
    if (rankOf(to) === promoRank) {
      for (const promo of ['Q', 'R', 'B', 'N']) {
        add(from, to, { ...extra, promotion: turn === WHITE ? promo : promo.toLowerCase() });
      }
    } else {
      add(from, to, extra);
    }
  };

  for (let s = 0; s < 64; s++) {
    const p = board[s];
    if (p === null || colorOf(p) !== turn) continue;
    const f = fileOf(s);
    const r = rankOf(s);
    const upper = p.toUpperCase();

    if (upper === 'P') {
      const oneR = r + forward;
      const one = oneR * 8 + f;
      if (onBoard(f, oneR) && board[one] === null) {
        addPawn(s, one);
        const twoR = r + 2 * forward;
        if (r === startRank && board[twoR * 8 + f] === null) {
          add(s, twoR * 8 + f, { double: true });
        }
      }
      for (const df of [-1, 1]) {
        const cf = f + df;
        const cr = r + forward;
        if (!onBoard(cf, cr)) continue;
        const target = cr * 8 + cf;
        if (board[target] !== null && colorOf(board[target]) === enemy) {
          addPawn(s, target);
        } else if (target === ep) {
          add(s, target, { ep: true });
        }
      }
    } else if (upper === 'N') {
      for (const [df, dr] of KNIGHT_DELTAS) {
        if (!onBoard(f + df, r + dr)) continue;
        const t = (r + dr) * 8 + (f + df);
        if (board[t] === null || colorOf(board[t]) === enemy) add(s, t);
      }
    } else if (upper === 'K') {
      for (const [df, dr] of KING_DELTAS) {
        if (!onBoard(f + df, r + dr)) continue;
        const t = (r + dr) * 8 + (f + df);
        if (board[t] === null || colorOf(board[t]) === enemy) add(s, t);
      }
      // Castling: rights intact, squares empty, king not in/through/into check.
      const rights = turn === WHITE ? ['K', 'Q'] : ['k', 'q'];
      const home = turn === WHITE ? 4 : 60;
      if (s === home && !isSquareAttacked(board, home, enemy)) {
        if (castling[rights[0]] &&
            board[home + 1] === null && board[home + 2] === null &&
            !isSquareAttacked(board, home + 1, enemy) &&
            !isSquareAttacked(board, home + 2, enemy)) {
          add(s, home + 2, { castle: 'k' });
        }
        if (castling[rights[1]] &&
            board[home - 1] === null && board[home - 2] === null &&
            board[home - 3] === null &&
            !isSquareAttacked(board, home - 1, enemy) &&
            !isSquareAttacked(board, home - 2, enemy)) {
          add(s, home - 2, { castle: 'q' });
        }
      }
    } else {
      const dirs = upper === 'B' ? BISHOP_DIRS
                 : upper === 'R' ? ROOK_DIRS
                 : [...BISHOP_DIRS, ...ROOK_DIRS]; // queen
      for (const [df, dr] of dirs) {
        let nf = f + df;
        let nr = r + dr;
        while (onBoard(nf, nr)) {
          const t = nr * 8 + nf;
          if (board[t] === null) {
            add(s, t);
          } else {
            if (colorOf(board[t]) === enemy) add(s, t);
            break;
          }
          nf += df;
          nr += dr;
        }
      }
    }
  }
  return moves;
}

// Apply a move, returning a new state (immutable).
export function makeMove(state, move) {
  const board = state.board.slice();
  const castling = { ...state.castling };
  const piece = board[move.from];
  const upper = piece.toUpperCase();
  const captured = board[move.to];
  const isPawn = upper === 'P';
  const isCapture = captured !== null || move.ep;

  board[move.to] = move.promotion ? move.promotion : piece;
  board[move.from] = null;

  if (move.ep) {
    // Captured pawn sits behind the target square.
    const capSq = move.to + (state.turn === WHITE ? -8 : 8);
    board[capSq] = null;
  }
  if (move.castle) {
    const home = state.turn === WHITE ? 4 : 60;
    if (move.castle === 'k') {
      board[home + 1] = board[home + 3];
      board[home + 3] = null;
    } else {
      board[home - 1] = board[home - 4];
      board[home - 4] = null;
    }
  }

  // Update castling rights when a king/rook moves or a rook is captured.
  if (upper === 'K') {
    if (state.turn === WHITE) { castling.K = false; castling.Q = false; }
    else { castling.k = false; castling.q = false; }
  }
  const clearRookRight = (sq) => {
    if (sq === 0) castling.Q = false;
    else if (sq === 7) castling.K = false;
    else if (sq === 56) castling.q = false;
    else if (sq === 63) castling.k = false;
  };
  clearRookRight(move.from);
  clearRookRight(move.to);

  const ep = move.double ? (move.from + move.to) / 2 : -1;

  return {
    board,
    turn: state.turn === WHITE ? BLACK : WHITE,
    castling,
    ep,
    halfmove: isPawn || isCapture ? 0 : state.halfmove + 1,
    fullmove: state.turn === BLACK ? state.fullmove + 1 : state.fullmove,
  };
}

// Fully legal moves: pseudo-legal moves that don't leave our king in check.
export function legalMoves(state) {
  const mover = state.turn;
  return pseudoMoves(state).filter((m) => {
    const next = makeMove(state, m);
    return !isSquareAttacked(next.board, kingSquare(next.board, mover),
                             mover === WHITE ? BLACK : WHITE);
  });
}

// A compact key for threefold-repetition detection.
export function positionKey(state) {
  return state.board.join('') + state.turn +
    (state.castling.K ? 'K' : '') + (state.castling.Q ? 'Q' : '') +
    (state.castling.k ? 'k' : '') + (state.castling.q ? 'q' : '') +
    ':' + state.ep;
}

export function insufficientMaterial(board) {
  const pieces = board.filter((p) => p !== null).map((p) => p.toUpperCase());
  const nonKing = pieces.filter((p) => p !== 'K');
  if (nonKing.length === 0) return true;                 // K vs K
  if (nonKing.length === 1 && (nonKing[0] === 'B' || nonKing[0] === 'N')) {
    return true;                                         // K+minor vs K
  }
  return false;
}

// Overall game status from the mover's perspective.
export function gameStatus(state, history) {
  const moves = legalMoves(state);
  const check = inCheck(state, state.turn);
  if (moves.length === 0) {
    return check ? 'checkmate' : 'stalemate';
  }
  if (state.halfmove >= 100) return 'draw-50';
  if (insufficientMaterial(state.board)) return 'draw-material';
  if (history) {
    const key = positionKey(state);
    let count = 0;
    for (const k of history) if (k === key) count++;
    if (count >= 3) return 'draw-repetition';
  }
  return check ? 'check' : 'ongoing';
}

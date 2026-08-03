import { initialState, legalMoves, makeMove } from './engine.mjs';

function perft(state, depth) {
  if (depth === 0) return 1;
  let nodes = 0;
  for (const m of legalMoves(state)) {
    nodes += perft(makeMove(state, m), depth - 1);
  }
  return nodes;
}

// Known perft values from the starting position.
const expected = { 1: 20, 2: 400, 3: 8902, 4: 197281 };
let ok = true;
for (const d of [1, 2, 3, 4]) {
  const n = perft(initialState(), d);
  const pass = n === expected[d];
  ok = ok && pass;
  console.log(`perft(${d}) = ${n}  expected ${expected[d]}  ${pass ? 'OK' : 'FAIL'}`);
}

// Kiwipete position (rich tactical position) — a stronger correctness check.
// r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -
function fromFen(fen) {
  const [placement, turn, castle, ep] = fen.split(' ');
  const board = new Array(64).fill(null);
  const ranks = placement.split('/');
  for (let r = 0; r < 8; r++) {
    let f = 0;
    for (const ch of ranks[7 - r]) {
      if (/\d/.test(ch)) f += Number(ch);
      else board[r * 8 + f++] = ch;
    }
  }
  const files = 'abcdefgh';
  return {
    board,
    turn,
    castling: {
      K: castle.includes('K'), Q: castle.includes('Q'),
      k: castle.includes('k'), q: castle.includes('q'),
    },
    ep: ep === '-' ? -1 : (Number(ep[1]) - 1) * 8 + files.indexOf(ep[0]),
    halfmove: 0,
    fullmove: 1,
  };
}

const kiwi = fromFen(
  'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1');
const kiwiExpected = { 1: 48, 2: 2039, 3: 97862 };
for (const d of [1, 2, 3]) {
  const n = perft(kiwi, d);
  const pass = n === kiwiExpected[d];
  ok = ok && pass;
  console.log(`kiwipete perft(${d}) = ${n}  expected ${kiwiExpected[d]}  ${pass ? 'OK' : 'FAIL'}`);
}

console.log(ok ? '\nALL PERFT TESTS PASSED' : '\nPERFT TESTS FAILED');
process.exit(ok ? 0 : 1);

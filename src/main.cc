/* Noah Himed
 *
 * chess-for-dad: the rules brain for Chess For Dad.
 *
 * A tiny command-line front end over the extracted OmegaZero move generator.
 * It is the single source of truth for legality and game status; the web app's
 * server calls it instead of trusting a second, separate chess implementation.
 *
 *   chess-for-dad perft <depth> [fen]   # move-generation self-check (divide)
 *   chess-for-dad moves [fen]           # legal moves (UCI) + game status
 *
 * Licensed under MIT License. Terms and conditions enclosed in "LICENSE.txt".
 */

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#include "bad_move.h"
#include "board.h"
#include "engine.h"
#include "move.h"

namespace omegazero {

using std::cout;
using std::endl;
using std::string;
using std::vector;

constexpr char kStartFen[] =
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

auto SqToStr(S8 sq) -> string {
  string s;
  s += static_cast<char>('a' + GetFileFromSq(sq));
  s += static_cast<char>('1' + GetRankFromSq(sq));
  return s;
}

// Long-algebraic (UCI) move string. Castling is emitted as the king's
// from/to squares, the UCI convention.
auto MoveToUci(const Move& m, S8 mover) -> string {
  if (m.castling_type == kKingSide) {
    return mover == kWhite ? "e1g1" : "e8g8";
  }
  if (m.castling_type == kQueenSide) {
    return mover == kWhite ? "e1c1" : "e8c8";
  }
  string s = SqToStr(m.start_sq) + SqToStr(m.target_sq);
  if (m.promoted_to_piece != kNA) {
    const char kPromoChars[] = {'?', 'n', 'b', 'r', 'q'};
    s += kPromoChars[m.promoted_to_piece];
  }
  return s;
}

auto StatusStr(S8 status) -> string {
  switch (status) {
    case kPlayerCheckmated:
      return "checkmate";
    case kPlayerInCheck:
      return "check";
    case kDraw:
      return "draw";
    default:
      return "ongoing";
  }
}

// Count leaf nodes per root move (perft "divide"), then the total. Mirrors the
// canonical perft output so counts can be diffed against known references.
auto RunPerft(const string& fen, int depth) -> void {
  Board board(fen);
  Engine engine(&board, 'w');
  U64 total = engine.Perft(depth);

  S8 mover = board.GetPlayerToMove();
  vector<Move> moves = engine.GenerateMoves();
  for (Move& m : moves) {
    try {
      board.MakeMove(m);
    } catch (BadMove&) {
      continue;
    }
    U64 sub = (depth > 1) ? engine.Perft(depth - 1) : 1;
    board.UnmakeMove(m);
    cout << MoveToUci(m, mover) << ": " << sub << endl;
  }
  cout << "\nTotal: " << total << endl;
}

// Print every legal move (UCI), then a "status:" line for the side to move.
auto RunMoves(const string& fen) -> void {
  Board board(fen);
  Engine engine(&board, 'w');
  S8 mover = board.GetPlayerToMove();
  vector<Move> pseudo = engine.GenerateMoves();
  for (Move& m : pseudo) {
    try {
      board.MakeMove(m);
    } catch (BadMove&) {
      continue;
    }
    board.UnmakeMove(m);
    cout << MoveToUci(m, mover) << endl;
  }
  cout << "status: " << StatusStr(engine.GetGameStatus()) << endl;
}

}  // namespace omegazero

auto main(int argc, char* argv[]) -> int {
  using omegazero::kStartFen;
  if (argc < 2) {
    std::cerr << "Usage:\n"
              << "  chess-for-dad perft <depth> [fen]\n"
              << "  chess-for-dad moves [fen]" << std::endl;
    return 1;
  }
  const std::string cmd = argv[1];
  if (cmd == "perft") {
    if (argc < 3) {
      std::cerr << "perft needs a depth" << std::endl;
      return 1;
    }
    int depth = std::atoi(argv[2]);
    std::string fen = (argc >= 4) ? argv[3] : kStartFen;
    omegazero::RunPerft(fen, depth);
    return 0;
  }
  if (cmd == "moves") {
    std::string fen = (argc >= 3) ? argv[2] : kStartFen;
    omegazero::RunMoves(fen);
    return 0;
  }
  std::cerr << "unknown command: " << cmd << std::endl;
  return 1;
}

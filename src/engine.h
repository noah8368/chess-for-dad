/* Noah Himed
 *
 * Define the Engine type: a legal-move generator and game-status oracle.
 *
 * This is the OmegaZero move generator and rules logic, extracted to serve as
 * the single source of truth for Chess For Dad. The search and evaluation
 * machinery of the full engine has been stripped out — all that remains is the
 * "rules brain": pseudo-legal move generation, make/unmake-based legality, and
 * check / checkmate / stalemate / draw detection.
 *
 * Licensed under MIT License. Terms and conditions enclosed in "LICENSE.txt".
 */

#ifndef CHESSFORDAD_SRC_ENGINE_H_
#define CHESSFORDAD_SRC_ENGINE_H_

#include <cstdint>
#include <vector>

#include "board.h"
#include "move.h"

namespace omegazero {

using std::vector;

enum GameStatus : S8 {
  kPlayerToMove,
  kPlayerInCheck,
  kDraw,
  kPlayerCheckmated,
};

// Fifty-move rule: 100 halfmoves without a capture or pawn move is a draw.
constexpr int kHalfmoveClockLimit = 100;

class Engine {
 public:
  Engine(Board* board, S8 player_side);

  // Check for checks, checkmates, and draws (fifty-move + threefold repetition).
  auto GetGameStatus() -> S8;
  auto GetUserSide() const -> S8;

  // Count leaves at `depth` plies below the current board state.
  auto Perft(int depth) -> U64;

  // All pseudo-legal moves at the current board state.
  auto GenerateMoves(bool captures_only = false) const -> vector<Move>;

  // Record the current position for repetition detection.
  auto AddPosToHistory() -> void;
  auto ClearHistory() -> void;
  auto RepDetected() const -> bool;

 private:
  auto AddCastlingMoves(vector<Move>& move_list) const -> void;
  auto AddEpMoves(vector<Move>& move_list, S8 enemy_player,
                  S8 moving_player) const -> void;
  auto AddMovesForPiece(vector<Move>& move_list, Bitboard attack_map,
                        S8 enemy_player, S8 moving_player, S8 moving_piece,
                        S8 start_sq) const -> void;

  Board* board_;
  S8 user_side_;
  vector<U64> pos_history_;
};

// --- Inline member functions ---

inline auto Engine::GetUserSide() const -> S8 { return user_side_; }

inline auto Engine::AddPosToHistory() -> void {
  pos_history_.push_back(board_->GetBoardHash());
}

inline auto Engine::ClearHistory() -> void { pos_history_.clear(); }

inline auto Engine::RepDetected() const -> bool {
  if (pos_history_.size() < 5) return false;
  U64 current = pos_history_.back();
  // Scan back over same-side-to-move positions.
  for (int pos_idx = static_cast<int>(pos_history_.size()) - 5; pos_idx >= 0;
       pos_idx -= 2) {
    if (pos_history_[pos_idx] == current) {
      return true;
    }
  }
  return false;
}

}  // namespace omegazero

#endif  // CHESSFORDAD_SRC_ENGINE_H_

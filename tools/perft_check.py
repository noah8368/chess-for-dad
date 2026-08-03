"""Faithful Python port of engine.mjs, used only to perft-validate the algorithm
that ships (in JS) in the artifact. Kept structurally identical to the JS."""
import copy

WHITE, BLACK = 'w', 'b'


def is_white(p): return p is not None and p == p.upper()
def color_of(p): return None if p is None else (WHITE if is_white(p) else BLACK)
def file_of(s): return s & 7
def rank_of(s): return s >> 3
def on_board(f, r): return 0 <= f < 8 and 0 <= r < 8


def initial_state():
    board = [None] * 64
    back = ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
    for f in range(8):
        board[f] = back[f]
        board[8 + f] = 'P'
        board[48 + f] = 'p'
        board[56 + f] = back[f].lower()
    return {'board': board, 'turn': WHITE,
            'castling': {'K': True, 'Q': True, 'k': True, 'q': True},
            'ep': -1, 'halfmove': 0, 'fullmove': 1}


KNIGHT_DELTAS = [[1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2]]
KING_DELTAS = [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]]
BISHOP_DIRS = [[1, 1], [1, -1], [-1, 1], [-1, -1]]
ROOK_DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1]]


def king_square(board, color):
    k = 'K' if color == WHITE else 'k'
    for s in range(64):
        if board[s] == k:
            return s
    return -1


def is_square_attacked(board, sq, by):
    f, r = file_of(sq), rank_of(sq)
    pawn_rank = r - 1 if by == WHITE else r + 1
    pawn_char = 'P' if by == WHITE else 'p'
    for df in (-1, 1):
        if on_board(f + df, pawn_rank) and board[pawn_rank * 8 + (f + df)] == pawn_char:
            return True
    knight_char = 'N' if by == WHITE else 'n'
    for df, dr in KNIGHT_DELTAS:
        if on_board(f + df, r + dr) and board[(r + dr) * 8 + (f + df)] == knight_char:
            return True
    king_char = 'K' if by == WHITE else 'k'
    for df, dr in KING_DELTAS:
        if on_board(f + df, r + dr) and board[(r + dr) * 8 + (f + df)] == king_char:
            return True
    bishop_char = 'B' if by == WHITE else 'b'
    rook_char = 'R' if by == WHITE else 'r'
    queen_char = 'Q' if by == WHITE else 'q'
    for dirs, sliders in ((BISHOP_DIRS, (bishop_char, queen_char)),
                          (ROOK_DIRS, (rook_char, queen_char))):
        for df, dr in dirs:
            nf, nr = f + df, r + dr
            while on_board(nf, nr):
                p = board[nr * 8 + nf]
                if p is not None:
                    if p in sliders:
                        return True
                    break
                nf += df
                nr += dr
    return False


def pseudo_moves(state):
    board, turn, ep, castling = state['board'], state['turn'], state['ep'], state['castling']
    moves = []
    enemy = BLACK if turn == WHITE else WHITE
    forward = 1 if turn == WHITE else -1
    start_rank = 1 if turn == WHITE else 6
    promo_rank = 7 if turn == WHITE else 0

    def add(frm, to, extra=None):
        m = {'from': frm, 'to': to}
        if extra:
            m.update(extra)
        moves.append(m)

    def add_pawn(frm, to, extra=None):
        if rank_of(to) == promo_rank:
            for promo in ('Q', 'R', 'B', 'N'):
                e = dict(extra or {})
                e['promotion'] = promo if turn == WHITE else promo.lower()
                add(frm, to, e)
        else:
            add(frm, to, extra)

    for s in range(64):
        p = board[s]
        if p is None or color_of(p) != turn:
            continue
        f, r = file_of(s), rank_of(s)
        upper = p.upper()
        if upper == 'P':
            one_r = r + forward
            one = one_r * 8 + f
            if on_board(f, one_r) and board[one] is None:
                add_pawn(s, one)
                two_r = r + 2 * forward
                if r == start_rank and board[two_r * 8 + f] is None:
                    add(s, two_r * 8 + f, {'double': True})
            for df in (-1, 1):
                cf, cr = f + df, r + forward
                if not on_board(cf, cr):
                    continue
                target = cr * 8 + cf
                if board[target] is not None and color_of(board[target]) == enemy:
                    add_pawn(s, target)
                elif target == ep:
                    add(s, target, {'ep': True})
        elif upper == 'N':
            for df, dr in KNIGHT_DELTAS:
                if not on_board(f + df, r + dr):
                    continue
                t = (r + dr) * 8 + (f + df)
                if board[t] is None or color_of(board[t]) == enemy:
                    add(s, t)
        elif upper == 'K':
            for df, dr in KING_DELTAS:
                if not on_board(f + df, r + dr):
                    continue
                t = (r + dr) * 8 + (f + df)
                if board[t] is None or color_of(board[t]) == enemy:
                    add(s, t)
            rights = ['K', 'Q'] if turn == WHITE else ['k', 'q']
            home = 4 if turn == WHITE else 60
            if s == home and not is_square_attacked(board, home, enemy):
                if (castling[rights[0]] and board[home + 1] is None and board[home + 2] is None
                        and not is_square_attacked(board, home + 1, enemy)
                        and not is_square_attacked(board, home + 2, enemy)):
                    add(s, home + 2, {'castle': 'k'})
                if (castling[rights[1]] and board[home - 1] is None and board[home - 2] is None
                        and board[home - 3] is None
                        and not is_square_attacked(board, home - 1, enemy)
                        and not is_square_attacked(board, home - 2, enemy)):
                    add(s, home - 2, {'castle': 'q'})
        else:
            dirs = BISHOP_DIRS if upper == 'B' else ROOK_DIRS if upper == 'R' else BISHOP_DIRS + ROOK_DIRS
            for df, dr in dirs:
                nf, nr = f + df, r + dr
                while on_board(nf, nr):
                    t = nr * 8 + nf
                    if board[t] is None:
                        add(s, t)
                    else:
                        if color_of(board[t]) == enemy:
                            add(s, t)
                        break
                    nf += df
                    nr += dr
    return moves


def make_move(state, move):
    board = state['board'][:]
    castling = dict(state['castling'])
    piece = board[move['from']]
    upper = piece.upper()
    captured = board[move['to']]
    is_pawn = upper == 'P'
    is_capture = captured is not None or move.get('ep')
    board[move['to']] = move.get('promotion') or piece
    board[move['from']] = None
    if move.get('ep'):
        cap_sq = move['to'] + (-8 if state['turn'] == WHITE else 8)
        board[cap_sq] = None
    if move.get('castle'):
        home = 4 if state['turn'] == WHITE else 60
        if move['castle'] == 'k':
            board[home + 1] = board[home + 3]
            board[home + 3] = None
        else:
            board[home - 1] = board[home - 4]
            board[home - 4] = None
    if upper == 'K':
        if state['turn'] == WHITE:
            castling['K'] = castling['Q'] = False
        else:
            castling['k'] = castling['q'] = False

    def clear_rook_right(sq):
        if sq == 0:
            castling['Q'] = False
        elif sq == 7:
            castling['K'] = False
        elif sq == 56:
            castling['q'] = False
        elif sq == 63:
            castling['k'] = False
    clear_rook_right(move['from'])
    clear_rook_right(move['to'])
    ep = (move['from'] + move['to']) // 2 if move.get('double') else -1
    return {'board': board, 'turn': BLACK if state['turn'] == WHITE else WHITE,
            'castling': castling, 'ep': ep,
            'halfmove': 0 if (is_pawn or is_capture) else state['halfmove'] + 1,
            'fullmove': state['fullmove'] + 1 if state['turn'] == BLACK else state['fullmove']}


def legal_moves(state):
    mover = state['turn']
    out = []
    for m in pseudo_moves(state):
        nxt = make_move(state, m)
        if not is_square_attacked(nxt['board'], king_square(nxt['board'], mover),
                                  BLACK if mover == WHITE else WHITE):
            out.append(m)
    return out


def perft(state, depth):
    if depth == 0:
        return 1
    return sum(perft(make_move(state, m), depth - 1) for m in legal_moves(state))


def from_fen(fen):
    placement, turn, castle, ep = fen.split(' ')[:4]
    board = [None] * 64
    ranks = placement.split('/')
    for r in range(8):
        f = 0
        for ch in ranks[7 - r]:
            if ch.isdigit():
                f += int(ch)
            else:
                board[r * 8 + f] = ch
                f += 1
    files = 'abcdefgh'
    return {'board': board, 'turn': turn,
            'castling': {'K': 'K' in castle, 'Q': 'Q' in castle,
                         'k': 'k' in castle, 'q': 'q' in castle},
            'ep': -1 if ep == '-' else (int(ep[1]) - 1) * 8 + files.index(ep[0]),
            'halfmove': 0, 'fullmove': 1}


ok = True
for d, exp in {1: 20, 2: 400, 3: 8902, 4: 197281}.items():
    n = perft(initial_state(), d)
    ok &= n == exp
    print(f"startpos perft({d}) = {n}  expected {exp}  {'OK' if n == exp else 'FAIL'}")

kiwi = from_fen('r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1')
for d, exp in {1: 48, 2: 2039, 3: 97862}.items():
    n = perft(kiwi, d)
    ok &= n == exp
    print(f"kiwipete perft({d}) = {n}  expected {exp}  {'OK' if n == exp else 'FAIL'}")

print('\nALL PERFT TESTS PASSED' if ok else '\nPERFT TESTS FAILED')

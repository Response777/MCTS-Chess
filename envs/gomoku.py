import numpy as np
import numba as nb
import gym


@nb.jit(nb.boolean(nb.i4[:, :], nb.i4, nb.i4))
def valid(board, x, y):
    board_size = board.shape[0]
    def _in_range(v):
        return (0 <= v) and (v < board_size)
    return _in_range(x) and _in_range(y)


@nb.jit(nb.boolean(nb.i4[:, :], nb.i4, nb.i4))
def available(board, x, y):
    return valid(board, x, y) and board[x][y] == -1


# Or: @nb.jit(nb.boolean(nb.i4[:, :], nb.types.UniTuple(nb.i4, 2), nb.i4))
# Or: @nb.jit(nb.boolean(nb.i4[:, :], nb.typeof((1, 1)), nb.i4))
@nb.jit('boolean(i4[:, :], UniTuple(i4, 2), i4)')
def check_win(board, pos, num_win):
    def _check_lines(pos, delta, player):
        x, y = pos
        dx, dy = delta

        count = 0
        while valid(board, x, y):
            if board[x][y] == player:
                x += dx
                y += dy
                count += 1
            else:
                break
        return count - 1

    dirs = ( (1, 0), (0, 1), (1, 1), (1, -1) )

    player = board[pos]
    for (dx, dy) in dirs:
        sum_1 = _check_lines( pos, ( dx,  dy), player )
        sum_2 = _check_lines( pos, (-dx, -dy), player )
        if (sum_1 + sum_2) >= (num_win - 1):
            return True
    return False


class GomokuState(object):
    def __init__(self, env, board, last_move, turn):
        self.env = env
        self.board = board
        self._last_move = last_move
        self._turn = turn
        self._valid_actions = None

        self._done = None
        self._result = None

    def __hash__(self):
        return hash(self.board.tobytes())

    def __eq__(self, other):
        # Note: it seems that np.array_equal could be slower?
        return (self.board == other.board).all()

    @property
    def valid_actions(self):
        if self._valid_actions is None:
            self._valid_actions = np.where(self.board.flatten() == -1)[0]
        return self._valid_actions

    @property
    def done(self):
        if self._done is None:
            if self._last_move is None: # First Move
                self._done = False
                self._result = 0
            else:
                board_size = self.env._board_size
                full = self._turn >= board_size**2
                x = self._last_move // board_size
                y = self._last_move % board_size
                win = check_win(self.board, (x, y), self.env._num_win)
                self._done = full or win
                self._result = int(win)
        return self._done

    @property
    def result(self):
        if self._result is None:
            self.done
        return self._result

    @property
    def cur_player(self):
        return self._turn % self.env.num_player

    def act(self, action):
        board = self.board.copy()
        x, y = action // self.env._board_size, action % self.env._board_size
        if not available(board, x, y):
            print("Illegal Move for player {}".format(self.cur_player))
            raise ValueError

        board[x, y] = self.cur_player
        return GomokuState(self.env, board, action, self._turn + 1)

    def reset(self):
        board = self.board.copy()
        board.fill(-1)
        return GomokuState(self.env, board, None, 0)


class GomokuEnv(gym.Env):
    def __init__(self, board_size, num_win, num_player=2):
        self._board_size = board_size
        self._num_win = num_win
        self._num_player = num_player

        board = -np.ones( (board_size, board_size), dtype='i4')
        self.state = GomokuState(self, board, None, 0)

    @property
    def num_player(self):
        return self._num_player

    def reset(self):
        self.state = self.state.reset()
        return self.state

    def step(self, action):
        self.state = self.state.act(action)
        return self.state, self.state.result, self.state.done, {}

    def render(self, mode='human'):
        raise NotImplementedError

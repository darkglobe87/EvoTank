from evotank_sim.extinction import ExtinctionController, SimState


def test_running_to_last_chance_to_game_over():
    ctrl = ExtinctionController()
    assert ctrl.evaluate(5) == SimState.RUNNING
    assert ctrl.evaluate(1) == SimState.LAST_CHANCE
    assert ctrl.evaluate(0) == SimState.GAME_OVER


def test_game_over_is_terminal():
    ctrl = ExtinctionController()
    ctrl.evaluate(0)
    assert ctrl.evaluate(10) == SimState.GAME_OVER      # no resurrection


def test_revive_returns_to_running():
    ctrl = ExtinctionController()
    ctrl.evaluate(1)
    assert ctrl.state == SimState.LAST_CHANCE
    assert ctrl.apply_revive() is True
    assert ctrl.state == SimState.RUNNING
    assert ctrl.apply_revive() is False                 # offer consumed

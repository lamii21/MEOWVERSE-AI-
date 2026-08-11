from app.services.progression import (
    MAX_LEVEL,
    LevelProgress,
    level_for_xp,
    title_for_level,
    xp_required_for_level,
)


class TestLevelFormula:
    def test_zero_xp_is_level_one(self):
        assert level_for_xp(0) == 1

    def test_level_boundaries_are_exact(self):
        # LEVEL_XP_STEP=100: level N requires 100*(N-1)^2.
        assert level_for_xp(99) == 1
        assert level_for_xp(100) == 2
        assert level_for_xp(399) == 2
        assert level_for_xp(400) == 3

    def test_level_never_exceeds_max_level(self):
        assert level_for_xp(10_000_000) == MAX_LEVEL

    def test_xp_required_for_level_one_is_zero(self):
        assert xp_required_for_level(1) == 0

    def test_xp_required_is_monotonically_increasing(self):
        thresholds = [xp_required_for_level(n) for n in range(1, MAX_LEVEL + 1)]
        assert thresholds == sorted(thresholds)
        assert len(set(thresholds)) == len(thresholds)

    def test_title_for_level_never_empty(self):
        for level in range(1, MAX_LEVEL + 1):
            assert title_for_level(level)


class TestLevelProgress:
    def test_mid_level_progress_ratio(self):
        progress = LevelProgress(150)
        assert progress.level == 2
        assert progress.xp_for_current_level == 100
        assert progress.xp_for_next_level == 400
        assert progress.xp_into_level == 50
        assert progress.xp_needed_for_level == 300
        assert progress.progress_ratio == 50 / 300

    def test_max_level_has_no_next_level_and_full_ratio(self):
        progress = LevelProgress(xp_required_for_level(MAX_LEVEL) + 5000)
        assert progress.level == MAX_LEVEL
        assert progress.xp_for_next_level is None
        assert progress.progress_ratio == 1.0

import derived_market_join as j

def test_exact_goal_markets_remain_unmatchable():
    assert 'exact_total_goals' not in j.MATCHABLE
    assert 'home_exact_goals' not in j.MATCHABLE
    assert 'away_exact_goals' not in j.MATCHABLE

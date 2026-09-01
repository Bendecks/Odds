import math
from derived_btts_model import model_probs


def exact_goal_probability(lam, goals):
    return math.exp(-lam) * (lam ** goals) / math.factorial(goals)


def goal_market_probabilities(home_lambda, away_lambda):
    total = home_lambda + away_lambda
    even = (1.0 + math.exp(-2.0 * total)) / 2.0
    return {
        'odd_even': {'odd': 1.0 - even, 'even': even},
        'clean_sheet_home': {'yes': math.exp(-away_lambda), 'no': 1.0 - math.exp(-away_lambda)},
        'clean_sheet_away': {'yes': math.exp(-home_lambda), 'no': 1.0 - math.exp(-home_lambda)},
        'exact_total_goals': {str(k): exact_goal_probability(total, k) for k in range(7)},
        'home_exact_goals': {str(k): exact_goal_probability(home_lambda, k) for k in range(5)},
        'away_exact_goals': {str(k): exact_goal_probability(away_lambda, k) for k in range(5)},
    }

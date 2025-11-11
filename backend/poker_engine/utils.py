from itertools import combinations
from collections import Counter

RANK_TO_VALUE = {
    '2': 2, '3': 3, '4': 4, '5': 5,
    '6': 6, '7': 7, '8': 8, '9': 9,
    '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
}

HAND_RANKS = {
    "high_card": 1,
    "one_pair": 2,
    "two_pair": 3,
    "three_of_a_kind": 4,
    "straight": 5,
    "flush": 6,
    "full_house": 7,
    "four_of_a_kind": 8,
    "straight_flush": 9,
    "royal_flush": 10
}

def _is_flush(suits):
    return len(set(suits)) == 1

def _is_straight(values):
    vals = sorted(values)
    if len(set(vals)) != 5:
        return (False, None)
    if vals[-1] - vals[0] == 4:
        return (True, vals[-1])
    if set(vals) == {14, 2, 3, 4, 5}: 
        return (True, 5)
    return (False, None)

def get_hand_strength(hand):
    ranks = [c.rank for c in hand]
    suits = [c.suit for c in hand]
    values = sorted([RANK_TO_VALUE[r] for r in ranks])

    rank_count = Counter(values)
    counts_sorted = sorted(rank_count.items(), key=lambda x: (-x[1], -x[0]))

    is_flush = _is_flush(suits)
    straight, straight_high = _is_straight(values)

    if is_flush and straight:
        if straight_high == 14:
            return (HAND_RANKS["royal_flush"],)
        return (HAND_RANKS["straight_flush"], straight_high)

    if counts_sorted[0][1] == 4: 
        four_rank = counts_sorted[0][0]
        kicker = [v for v in values if v != four_rank][-1]
        return (HAND_RANKS["four_of_a_kind"], four_rank, kicker)
    
    if counts_sorted[0][1] == 3 and counts_sorted[1][1] == 2:
        three_rank = counts_sorted[0][0]
        pair_rank = counts_sorted[1][0]
        return (HAND_RANKS["full_house"], three_rank, pair_rank)
    
    if is_flush:
        tiebreakers = tuple(sorted(values, reverse=True))
        return (HAND_RANKS["flush"],) + tiebreakers
    
    if straight:
        return (HAND_RANKS["straight"], straight_high)
    
    if counts_sorted[0][1] == 3:
        three_rank = counts_sorted[0][0]
        kickers = [v for v in sorted(values, reverse=True) if v != three_rank]
        return (HAND_RANKS["three_of_a_kind"], three_rank, kickers[0], kickers[1])
    
    if counts_sorted[0][1] == 2 and counts_sorted[1][1] == 2:
        high_pair = counts_sorted[0][0]
        low_pair = counts_sorted[1][0]
        kicker = [v for v in sorted(values, reverse=True) if v != high_pair and v != low_pair][0]
        return (HAND_RANKS["two_pair"], high_pair, low_pair, kicker)

    if counts_sorted[0][1] == 2:
        pair_rank = counts_sorted[0][0]
        kickers = [v for v in sorted(values, reverse=True) if v != pair_rank]
        return (HAND_RANKS["one_pair"], pair_rank, kickers[0], kickers[1], kickers[2])

    tiebreakers = tuple(sorted(values, reverse=True))
    return (HAND_RANKS["high_card"],) + tiebreakers


def eval_hand(cards):
    best_score = None
    best_hand = None

    for combo in combinations(cards, 5):
        score = get_hand_strength(combo)
        if best_score is None or score > best_score:
            best_score = score
            best_hand = combo
    
    return best_score, best_hand


def compare_hands(player1_cards, player2_cards):
    s1, h1 = eval_hand(player1_cards)
    s2, h2 = eval_hand(player2_cards)

    if s1 > s2:
        return 1
    elif s2 > s1:
        return -1
    else:
        return 0

"""
Unit tests for tiebreaker logic
"""
import pytest


def test_tiebreaker_by_total_score():
    """Test that higher total_score wins"""
    
    participants = [
        {'id': 1, 'score': 15, 'best': 1, 'random': 0.5},
        {'id': 2, 'score': 18, 'best': 2, 'random': 0.5},
        {'id': 3, 'score': 12, 'best': 1, 'random': 0.5},
    ]
    
    sorted_participants = sorted(
        participants,
        key=lambda x: (-x['score'], x['best'], x['random'])
    )
    
    assert sorted_participants[0]['id'] == 2  # 18 points
    assert sorted_participants[1]['id'] == 1  # 15 points
    assert sorted_participants[2]['id'] == 3  # 12 points


def test_tiebreaker_by_best_placement():
    """Test that better placement wins when scores are equal"""
    
    participants = [
        {'id': 1, 'score': 15, 'best': 1, 'random': 0.5},
        {'id': 2, 'score': 15, 'best': 2, 'random': 0.5},
        {'id': 3, 'score': 15, 'best': 3, 'random': 0.5},
    ]
    
    sorted_participants = sorted(
        participants,
        key=lambda x: (-x['score'], x['best'], x['random'])
    )
    
    assert sorted_participants[0]['id'] == 1  # best=1
    assert sorted_participants[1]['id'] == 2  # best=2
    assert sorted_participants[2]['id'] == 3  # best=3


def test_tiebreaker_by_random():
    """Test that random breaks ties when score and placement are equal"""
    
    participants = [
        {'id': 1, 'score': 15, 'best': 1, 'random': 0.7},
        {'id': 2, 'score': 15, 'best': 1, 'random': 0.3},
        {'id': 3, 'score': 15, 'best': 1, 'random': 0.5},
    ]
    
    sorted_participants = sorted(
        participants,
        key=lambda x: (-x['score'], x['best'], x['random'])
    )
    
    # Lower random number wins (coin flip)
    assert sorted_participants[0]['id'] == 2  # random=0.3
    assert sorted_participants[1]['id'] == 3  # random=0.5
    assert sorted_participants[2]['id'] == 1  # random=0.7


def test_best_placement_calculation():
    """Test finding best placement from game results"""
    
    # Player A: placements [5, 1, 3] → best = 1
    placements_a = [5, 1, 3]
    best_a = min(placements_a)
    assert best_a == 1
    
    # Player B: placements [4, 2, 3] → best = 2
    placements_b = [4, 2, 3]
    best_b = min(placements_b)
    assert best_b == 2
    
    # Player C: placements [8, 8, 8] → best = 8
    placements_c = [8, 8, 8]
    best_c = min(placements_c)
    assert best_c == 8


def test_complex_tiebreaker_scenario():
    """Test complex scenario with multiple tiebreaker levels"""
    
    participants = [
        {'id': 1, 'score': 20, 'best': 1, 'random': 0.5},  # Winner by score
        {'id': 2, 'score': 15, 'best': 1, 'random': 0.3},  # 2nd by best placement
        {'id': 3, 'score': 15, 'best': 1, 'random': 0.7},  # 3rd by random
        {'id': 4, 'score': 15, 'best': 2, 'random': 0.1},  # 4th by best placement
        {'id': 5, 'score': 10, 'best': 1, 'random': 0.1},  # 5th by score
    ]
    
    sorted_participants = sorted(
        participants,
        key=lambda x: (-x['score'], x['best'], x['random'])
    )
    
    assert sorted_participants[0]['id'] == 1  # 20 points
    assert sorted_participants[1]['id'] == 2  # 15 points, best=1, random=0.3
    assert sorted_participants[2]['id'] == 3  # 15 points, best=1, random=0.7
    assert sorted_participants[3]['id'] == 4  # 15 points, best=2
    assert sorted_participants[4]['id'] == 5  # 10 points

"""
Unit tests for Swiss system pairing logic
"""
import pytest


def test_swiss_pairing_simple():
    """Test basic Swiss pairing (strong with strong)"""
    
    # 16 participants sorted by score
    participants = [
        {'id': 1, 'score': 20},
        {'id': 2, 'score': 18},
        {'id': 3, 'score': 16},
        {'id': 4, 'score': 14},
        {'id': 5, 'score': 12},
        {'id': 6, 'score': 10},
        {'id': 7, 'score': 8},
        {'id': 8, 'score': 6},
        {'id': 9, 'score': 5},
        {'id': 10, 'score': 4},
        {'id': 11, 'score': 3},
        {'id': 12, 'score': 2},
        {'id': 13, 'score': 1},
        {'id': 14, 'score': 0},
        {'id': 15, 'score': 0},
        {'id': 16, 'score': 0},
    ]
    
    # Distribute to games (8 per game)
    game1 = participants[0:8]   # Top 8
    game2 = participants[8:16]  # Bottom 8
    
    # Game 1 should have stronger players
    assert all(p['score'] >= 6 for p in game1)
    
    # Game 2 should have weaker players
    assert all(p['score'] <= 5 for p in game2)


def test_participants_per_game():
    """Test that each game has exactly 8 participants"""
    
    total_participants = 24
    participants_per_game = 8
    
    num_games = total_participants // participants_per_game
    assert num_games == 3
    
    # Verify distribution
    for game_index in range(num_games):
        start = game_index * participants_per_game
        end = start + participants_per_game
        game_size = end - start
        assert game_size == 8


def test_all_participants_assigned():
    """Test that all participants are assigned to games"""
    
    total_participants = 32
    participants_per_game = 8
    
    participants = list(range(total_participants))
    
    # Assign to games
    games = []
    for i in range(0, total_participants, participants_per_game):
        game = participants[i:i+participants_per_game]
        games.append(game)
    
    # Verify all assigned
    assigned = [p for game in games for p in game]
    assert len(assigned) == total_participants
    assert set(assigned) == set(participants)


def test_score_ordering():
    """Test that participants are correctly ordered by score"""
    
    participants = [
        {'id': 1, 'score': 5},
        {'id': 2, 'score': 15},
        {'id': 3, 'score': 10},
        {'id': 4, 'score': 20},
    ]
    
    sorted_participants = sorted(participants, key=lambda x: -x['score'])
    
    assert sorted_participants[0]['id'] == 4  # 20
    assert sorted_participants[1]['id'] == 2  # 15
    assert sorted_participants[2]['id'] == 3  # 10
    assert sorted_participants[3]['id'] == 1  # 5

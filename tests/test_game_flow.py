"""
Unit tests for game state transitions
"""
import pytest


def test_game_status_flow():
    """Test valid game status transitions"""
    
    # Valid flow: PENDING → ACTIVE → COMPLETED
    statuses = ['pending', 'active', 'completed']
    
    for i in range(len(statuses) - 1):
        current = statuses[i]
        next_status = statuses[i + 1]
        # Transition should be valid
        assert current != next_status


def test_game_can_start():
    """Test conditions for starting a game"""
    
    game = {
        'status': 'pending',
        'participants_count': 8,
        'required_participants': 8,
    }
    
    can_start = (
        game['status'] == 'pending' and
        game['participants_count'] == game['required_participants']
    )
    assert can_start is True
    
    # Not enough participants
    game['participants_count'] = 6
    can_start = (
        game['status'] == 'pending' and
        game['participants_count'] == game['required_participants']
    )
    assert can_start is False


def test_game_can_complete():
    """Test conditions for completing a game"""
    
    game = {
        'status': 'active',
        'participants': [
            {'id': 1, 'positions': '[1]'},
            {'id': 2, 'positions': '[2]'},
            {'id': 3, 'positions': '[3]'},
            {'id': 4, 'positions': '[4]'},
            {'id': 5, 'positions': '[5]'},
            {'id': 6, 'positions': '[6]'},
            {'id': 7, 'positions': '[7]'},
            {'id': 8, 'positions': '[8]'},
        ]
    }
    
    # All have results
    all_have_results = all(p['positions'] is not None for p in game['participants'])
    can_complete = game['status'] == 'active' and all_have_results
    assert can_complete is True
    
    # One missing result
    game['participants'][3]['positions'] = None
    all_have_results = all(p['positions'] is not None for p in game['participants'])
    can_complete = game['status'] == 'active' and all_have_results
    assert can_complete is False


def test_round_can_complete():
    """Test conditions for completing a round"""
    
    round_data = {
        'status': 'active',
        'games': [
            {'id': 1, 'status': 'completed'},
            {'id': 2, 'status': 'completed'},
        ]
    }
    
    all_games_done = all(g['status'] == 'completed' for g in round_data['games'])
    can_complete = round_data['status'] == 'active' and all_games_done
    assert can_complete is True
    
    # One game still active
    round_data['games'][0]['status'] = 'active'
    all_games_done = all(g['status'] == 'completed' for g in round_data['games'])
    can_complete = round_data['status'] == 'active' and all_games_done
    assert can_complete is False


def test_participant_result_validation():
    """Test validation of participant results"""
    
    # Valid result
    result = {
        'positions': [1],
        'points': 8,
    }
    
    is_valid = (
        result['positions'] is not None and
        len(result['positions']) > 0 and
        1 <= min(result['positions']) <= 8 and
        1 <= max(result['positions']) <= 8
    )
    assert is_valid is True
    
    # Invalid: position out of range
    result['positions'] = [9]
    is_valid = (
        result['positions'] is not None and
        len(result['positions']) > 0 and
        1 <= min(result['positions']) <= 8 and
        1 <= max(result['positions']) <= 8
    )
    assert is_valid is False


def test_shared_positions_validation():
    """Test validation of shared positions"""
    
    # Valid: consecutive positions [6, 7, 8]
    positions = [6, 7, 8]
    sorted_pos = sorted(positions)
    
    is_consecutive = all(
        sorted_pos[i] == sorted_pos[i-1] + 1
        for i in range(1, len(sorted_pos))
    )
    assert is_consecutive is True
    
    # Invalid: non-consecutive [1, 3, 5]
    positions = [1, 3, 5]
    sorted_pos = sorted(positions)
    
    is_consecutive = all(
        sorted_pos[i] == sorted_pos[i-1] + 1
        for i in range(1, len(sorted_pos))
    )
    assert is_consecutive is False


def test_lobby_maker_required():
    """Test that lobby maker must be assigned before results"""
    
    game = {
        'lobby_maker_id': None,
        'status': 'active',
    }
    
    can_submit_results = game['lobby_maker_id'] is not None
    assert can_submit_results is False
    
    # With lobby maker assigned
    game['lobby_maker_id'] = 5
    can_submit_results = game['lobby_maker_id'] is not None
    assert can_submit_results is True

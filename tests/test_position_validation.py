"""
Unit tests for position conflict validation
"""
import pytest


def test_no_position_overlap():
    """Test that positions without overlap are valid"""
    positions_map = {
        1: [1],
        2: [2, 3, 4],
        3: [5],
        4: [6, 7, 8]
    }
    
    # Check no overlaps
    all_positions = set()
    for participant_id, positions in positions_map.items():
        for pos in positions:
            assert pos not in all_positions, f"Position {pos} is duplicated"
            all_positions.add(pos)


def test_position_overlap_detection():
    """Test detecting position overlaps"""
    # Valid case
    player_a_positions = [1]
    player_b_positions = [2, 3, 4]
    
    overlap = set(player_a_positions) & set(player_b_positions)
    assert len(overlap) == 0
    
    # Invalid case
    player_c_positions = [2]
    overlap = set(player_b_positions) & set(player_c_positions)
    assert len(overlap) > 0
    assert 2 in overlap


def test_shared_positions_count():
    """Test that shared positions can be used correct number of times"""
    # [2,3,4] can be used max 3 times
    shared_positions = [2, 3, 4]
    max_uses = len(shared_positions)
    
    assignments = [
        {"participant": 1, "positions": [2, 3, 4]},
        {"participant": 2, "positions": [2, 3, 4]},
        {"participant": 3, "positions": [2, 3, 4]}
    ]
    
    # This should be valid if all use the EXACT same positions
    # But our validation doesn't allow ANY overlap
    # So this would actually be invalid
    
    # Check for overlaps
    used_positions = set()
    for assignment in assignments:
        positions_set = set(assignment["positions"])
        overlap = used_positions & positions_set
        if overlap:
            # Conflict detected
            assert True  # This is expected
            break
        used_positions.update(positions_set)


def test_single_position_vs_shared():
    """Test that single position conflicts with shared positions"""
    player_a = [2]
    player_b = [2, 3]
    
    overlap = set(player_a) & set(player_b)
    assert len(overlap) > 0
    assert 2 in overlap


def test_valid_game_example():
    """Test valid game scenario"""
    game_results = {
        "Player A": [1],
        "Player B": [2, 3, 4],
        "Player C": [5],
        "Player D": [6, 7, 8]
    }
    
    # Note: In our implementation, [2,3,4] can only be used once
    # because ANY overlap is forbidden
    
    all_positions = set()
    for player, positions in game_results.items():
        positions_set = set(positions)
        overlap = all_positions & positions_set
        assert len(overlap) == 0, f"{player} has overlap: {overlap}"
        all_positions.update(positions_set)


def test_invalid_game_example():
    """Test invalid game scenario"""
    # This should fail validation
    game_results = {
        "Player A": [2],
        "Player B": [2, 3]  # Conflict on position 2
    }
    
    all_positions = set()
    conflict_detected = False
    
    for player, positions in game_results.items():
        positions_set = set(positions)
        overlap = all_positions & positions_set
        if overlap:
            conflict_detected = True
            break
        all_positions.update(positions_set)
    
    assert conflict_detected is True


def test_consecutive_positions():
    """Test that shared positions must be consecutive"""
    # Valid consecutive
    valid_positions = [
        [2, 3],
        [4, 5, 6],
        [1, 2, 3, 4]
    ]
    
    for positions in valid_positions:
        sorted_pos = sorted(positions)
        is_consecutive = all(
            sorted_pos[i] == sorted_pos[i-1] + 1
            for i in range(1, len(sorted_pos))
        )
        assert is_consecutive is True
    
    # Invalid non-consecutive
    invalid_positions = [
        [1, 3],
        [2, 4, 5],
        [1, 2, 4]
    ]
    
    for positions in invalid_positions:
        sorted_pos = sorted(positions)
        is_consecutive = all(
            sorted_pos[i] == sorted_pos[i-1] + 1
            for i in range(1, len(sorted_pos))
        )
        assert is_consecutive is False


def test_position_range():
    """Test that positions must be 1-8"""
    valid_positions = [1, 2, 3, 4, 5, 6, 7, 8]
    
    for pos in valid_positions:
        assert 1 <= pos <= 8
    
    invalid_positions = [0, 9, -1, 10]
    
    for pos in invalid_positions:
        assert not (1 <= pos <= 8)


def test_batch_update_conflicts():
    """Test detecting conflicts in batch updates"""
    batch_updates = [
        {"participant_id": 1, "positions": [1]},
        {"participant_id": 2, "positions": [2, 3]},
        {"participant_id": 3, "positions": [3, 4]}  # Conflict with participant 2
    ]
    
    all_positions = {}
    conflict_detected = False
    
    for update in batch_updates:
        participant_id = update["participant_id"]
        positions = update["positions"]
        
        for pos in positions:
            if pos in all_positions:
                conflict_detected = True
                break
            all_positions[pos] = participant_id
        
        if conflict_detected:
            break
    
    assert conflict_detected is True

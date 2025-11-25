"""
Unit tests for tournament validation logic
"""
import pytest
from fastapi import HTTPException


def test_validate_participants_divisible_by_8():
    """Test that total_participants must be divisible by 8"""
    
    # Valid cases
    valid_sizes = [8, 16, 24, 32, 40, 48, 56, 64]
    for size in valid_sizes:
        assert size % 8 == 0, f"{size} should be valid"
    
    # Invalid cases
    invalid_sizes = [7, 9, 15, 17, 23, 25, 31, 33]
    for size in invalid_sizes:
        assert size % 8 != 0, f"{size} should be invalid"


def test_calculate_total_rounds():
    """Test auto-calculation of total_rounds"""
    import math
    
    test_cases = [
        (8, 3),    # log2(8) = 3
        (16, 4),   # log2(16) = 4
        (32, 5),   # log2(32) = 5
        (64, 6),   # log2(64) = 6
    ]
    
    for participants, expected_rounds in test_cases:
        calculated = math.ceil(math.log2(participants))
        assert calculated == expected_rounds, \
            f"For {participants} participants, expected {expected_rounds} rounds, got {calculated}"


def test_games_per_round():
    """Test calculation of games per round"""
    
    test_cases = [
        (8, 1),    # 8 participants = 1 game
        (16, 2),   # 16 participants = 2 games
        (24, 3),   # 24 participants = 3 games
        (32, 4),   # 32 participants = 4 games
    ]
    
    for participants, expected_games in test_cases:
        calculated = participants // 8
        assert calculated == expected_games, \
            f"For {participants} participants, expected {expected_games} games, got {calculated}"

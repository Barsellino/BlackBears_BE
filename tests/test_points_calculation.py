"""
Unit tests for points calculation
"""
import pytest
import json


def test_position_to_points_mapping():
    """Test that positions correctly map to points"""
    
    position_points = {
        1: 8,
        2: 7,
        3: 6,
        4: 5,
        5: 4,
        6: 3,
        7: 2,
        8: 1,
    }
    
    for position, expected_points in position_points.items():
        calculated_points = 9 - position
        assert calculated_points == expected_points, \
            f"Position {position} should give {expected_points} points"


def test_shared_positions_points():
    """Test points calculation for shared positions"""
    
    # Positions [6, 7, 8] shared → average = (3+2+1)/3 = 2.0
    positions = [6, 7, 8]
    points = [9 - p for p in positions]  # [3, 2, 1]
    average = sum(points) / len(points)
    assert average == 2.0
    
    # Positions [1, 2] shared → average = (8+7)/2 = 7.5
    positions = [1, 2]
    points = [9 - p for p in positions]  # [8, 7]
    average = sum(points) / len(points)
    assert average == 7.5


def test_json_positions_parsing():
    """Test parsing positions from JSON"""
    
    # Single position
    json_str = "[1]"
    positions = json.loads(json_str)
    assert positions == [1]
    
    # Multiple positions (shared)
    json_str = "[6, 7, 8]"
    positions = json.loads(json_str)
    assert positions == [6, 7, 8]
    
    # Calculate points
    points = [9 - p for p in positions]
    average = sum(points) / len(points)
    assert average == 2.0


def test_total_score_accumulation():
    """Test accumulation of total score across games"""
    
    game_results = [
        {'positions': [1], 'points': 8.0},
        {'positions': [3], 'points': 6.0},
        {'positions': [2], 'points': 7.0},
    ]
    
    total_score = sum(r['points'] for r in game_results)
    assert total_score == 21.0


def test_best_placement_from_results():
    """Test finding best placement across all games"""
    
    game_results = [
        {'positions': [5]},
        {'positions': [1]},
        {'positions': [3]},
    ]
    
    all_positions = [r['positions'][0] for r in game_results]
    best_placement = min(all_positions)
    assert best_placement == 1

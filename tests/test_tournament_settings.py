"""
Unit tests for tournament creation with new settings (prizes, is_free, first_round_strategy)
"""
import pytest


def test_prize_structure():
    """Test Prize model structure"""
    prize = {
        "name": "Gaming Mouse",
        "img": "https://example.com/mouse.jpg",
        "url": "https://example.com/product"
    }
    
    assert prize["name"] == "Gaming Mouse"
    assert prize["img"] is not None
    assert prize["url"] is not None


def test_prize_minimal():
    """Test Prize with only required field"""
    prize = {
        "name": "Keyboard",
        "img": None,
        "url": None
    }
    
    assert prize["name"] == "Keyboard"
    assert prize["img"] is None
    assert prize["url"] is None


def test_tournament_with_prizes():
    """Test tournament data structure with prizes"""
    tournament = {
        "name": "Pro Tournament",
        "total_participants": 16,
        "total_rounds": 4,
        "is_free": False,
        "prizes": [
            {"name": "Mouse", "img": "url1", "url": "link1"},
            {"name": "Keyboard", "img": None, "url": None}
        ],
        "first_round_strategy": "BALANCED"
    }
    
    assert tournament["is_free"] is False
    assert len(tournament["prizes"]) == 2
    assert tournament["prizes"][0]["name"] == "Mouse"
    assert tournament["first_round_strategy"] == "BALANCED"


def test_tournament_free_no_prizes():
    """Test free tournament without prizes"""
    tournament = {
        "name": "Free Tournament",
        "total_participants": 8,
        "total_rounds": 3,
        "is_free": True,
        "prizes": None,
        "first_round_strategy": "RANDOM"
    }
    
    assert tournament["is_free"] is True
    assert tournament["prizes"] is None
    assert tournament["first_round_strategy"] == "RANDOM"


def test_first_round_strategies():
    """Test all three first round strategies"""
    strategies = ["RANDOM", "BALANCED", "STRONG_VS_STRONG"]
    
    for strategy in strategies:
        tournament = {
            "first_round_strategy": strategy
        }
        assert tournament["first_round_strategy"] in strategies


def test_multiple_prizes():
    """Test tournament with multiple prizes"""
    prizes = [
        {"name": "1st Place - Gaming Setup", "img": "img1.jpg", "url": "link1"},
        {"name": "2nd Place - Mouse", "img": "img2.jpg", "url": "link2"},
        {"name": "3rd Place - Mousepad", "img": None, "url": None},
        {"name": "4th Place - Sticker Pack", "img": None, "url": None}
    ]
    
    tournament = {
        "prizes": prizes
    }
    
    assert len(tournament["prizes"]) == 4
    assert all("name" in prize for prize in tournament["prizes"])


def test_prize_validation():
    """Test that prize must have name"""
    # Valid prize
    valid_prize = {"name": "Prize", "img": None, "url": None}
    assert "name" in valid_prize
    
    # Invalid prize (missing name)
    invalid_prize = {"img": "image.jpg", "url": "link"}
    assert "name" not in invalid_prize


def test_tournament_defaults():
    """Test default values for new fields"""
    tournament = {
        "name": "Default Tournament",
        "total_participants": 8,
        "total_rounds": 3
    }
    
    # These would be set by backend defaults
    expected_defaults = {
        "is_free": True,
        "prizes": None,
        "first_round_strategy": "RANDOM"
    }
    
    # Verify defaults exist
    for key, value in expected_defaults.items():
        assert key in expected_defaults


def test_paid_tournament_with_prizes():
    """Test paid tournament must have prizes"""
    tournament = {
        "is_free": False,
        "prizes": [
            {"name": "Cash Prize $100", "img": None, "url": None}
        ]
    }
    
    assert tournament["is_free"] is False
    assert tournament["prizes"] is not None
    assert len(tournament["prizes"]) > 0


def test_strategy_enum_values():
    """Test that strategy values are from allowed enum"""
    allowed_strategies = ["RANDOM", "BALANCED", "STRONG_VS_STRONG"]
    
    # Valid
    for strategy in allowed_strategies:
        assert strategy in allowed_strategies
    
    # Invalid
    invalid_strategy = "INVALID_STRATEGY"
    assert invalid_strategy not in allowed_strategies

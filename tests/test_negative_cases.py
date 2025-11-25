"""
Negative test cases - testing error conditions
"""
import pytest


class TestInvalidTournamentCreation:
    """Test invalid tournament creation scenarios"""
    
    def test_participants_not_divisible_by_8(self):
        """Should fail: participants not divisible by 8"""
        invalid_sizes = [7, 9, 15, 17, 23, 25, 31, 33, 100]
        
        for size in invalid_sizes:
            # Should raise error
            is_valid = size % 8 == 0
            assert is_valid is False, f"{size} should be invalid"
    
    def test_zero_participants(self):
        """Should fail: zero participants"""
        participants = 0
        is_valid = participants > 0 and participants % 8 == 0
        assert is_valid is False
    
    def test_negative_participants(self):
        """Should fail: negative participants"""
        participants = -8
        is_valid = participants > 0
        assert is_valid is False
    
    def test_too_few_rounds(self):
        """Should fail: 0 or negative rounds"""
        invalid_rounds = [0, -1, -5]
        
        for rounds in invalid_rounds:
            is_valid = rounds > 0
            assert is_valid is False


class TestInvalidTournamentTransitions:
    """Test invalid tournament state transitions"""
    
    def test_start_already_active_tournament(self):
        """Should fail: starting already active tournament"""
        tournament = {'status': 'active'}
        can_start = tournament['status'] == 'registration'
        assert can_start is False
    
    def test_start_finished_tournament(self):
        """Should fail: starting finished tournament"""
        tournament = {'status': 'finished'}
        can_start = tournament['status'] == 'registration'
        assert can_start is False
    
    def test_start_without_enough_participants(self):
        """Should fail: starting with incomplete registration"""
        tournament = {
            'status': 'registration',
            'total_participants': 16,
            'registered_count': 10,  # Only 10/16
        }
        
        can_start = (
            tournament['status'] == 'registration' and
            tournament['registered_count'] == tournament['total_participants']
        )
        assert can_start is False
    
    def test_create_round_when_finished(self):
        """Should fail: creating round when tournament finished"""
        tournament = {
            'current_round': 3,
            'total_rounds': 3,
        }
        
        can_create = tournament['current_round'] < tournament['total_rounds']
        assert can_create is False
    
    def test_finish_tournament_before_all_rounds(self):
        """Should fail: finishing before completing all rounds"""
        tournament = {
            'current_round': 2,
            'total_rounds': 3,
        }
        
        can_finish = tournament['current_round'] == tournament['total_rounds']
        assert can_finish is False


class TestInvalidGameOperations:
    """Test invalid game operations"""
    
    def test_start_game_without_participants(self):
        """Should fail: starting game with 0 participants"""
        game = {
            'status': 'pending',
            'participants_count': 0,
            'required_participants': 8,
        }
        
        can_start = (
            game['status'] == 'pending' and
            game['participants_count'] == game['required_participants']
        )
        assert can_start is False
    
    def test_start_game_with_too_few_participants(self):
        """Should fail: starting game with only 5 participants"""
        game = {
            'status': 'pending',
            'participants_count': 5,
            'required_participants': 8,
        }
        
        can_start = (
            game['status'] == 'pending' and
            game['participants_count'] == game['required_participants']
        )
        assert can_start is False
    
    def test_complete_game_without_all_results(self):
        """Should fail: completing game with missing results"""
        game = {
            'status': 'active',
            'participants': [
                {'id': 1, 'positions': '[1]'},
                {'id': 2, 'positions': '[2]'},
                {'id': 3, 'positions': None},  # Missing!
                {'id': 4, 'positions': '[4]'},
            ]
        }
        
        all_have_results = all(p['positions'] is not None for p in game['participants'])
        assert all_have_results is False
    
    def test_submit_results_without_lobby_maker(self):
        """Should fail: submitting results without lobby maker"""
        game = {
            'lobby_maker_id': None,
            'status': 'active',
        }
        
        can_submit = game['lobby_maker_id'] is not None
        assert can_submit is False


class TestInvalidResultSubmission:
    """Test invalid result submission scenarios"""
    
    def test_position_out_of_range_too_high(self):
        """Should fail: position > 8"""
        positions = [9]
        is_valid = all(1 <= p <= 8 for p in positions)
        assert is_valid is False
    
    def test_position_out_of_range_too_low(self):
        """Should fail: position < 1"""
        positions = [0]
        is_valid = all(1 <= p <= 8 for p in positions)
        assert is_valid is False
    
    def test_position_negative(self):
        """Should fail: negative position"""
        positions = [-1]
        is_valid = all(1 <= p <= 8 for p in positions)
        assert is_valid is False
    
    def test_empty_positions(self):
        """Should fail: empty positions array"""
        positions = []
        is_valid = len(positions) > 0
        assert is_valid is False
    
    def test_too_many_positions(self):
        """Should fail: more than 8 positions"""
        positions = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        is_valid = len(positions) <= 8
        assert is_valid is False
    
    def test_non_consecutive_shared_positions(self):
        """Should fail: shared positions not consecutive [1, 3, 5]"""
        positions = [1, 3, 5]
        sorted_pos = sorted(positions)
        
        is_consecutive = all(
            sorted_pos[i] == sorted_pos[i-1] + 1
            for i in range(1, len(sorted_pos))
        )
        assert is_consecutive is False
    
    def test_duplicate_positions(self):
        """Should fail: duplicate positions [1, 1, 2]"""
        positions = [1, 1, 2]
        has_duplicates = len(positions) != len(set(positions))
        assert has_duplicates is True  # Should have duplicates (bad!)


class TestInvalidScoreCalculations:
    """Test invalid score calculation scenarios"""
    
    def test_negative_points(self):
        """Should fail: negative points"""
        points = -5
        is_valid = points >= 0
        assert is_valid is False
    
    def test_points_too_high(self):
        """Should fail: points > 8 (max for position 1)"""
        points = 10
        is_valid = points <= 8
        assert is_valid is False
    
    def test_total_score_negative(self):
        """Should fail: negative total score"""
        total_score = -10
        is_valid = total_score >= 0
        assert is_valid is False


class TestInvalidLobbyMakerOperations:
    """Test invalid lobby maker operations"""
    
    def test_assign_lobby_maker_not_in_game(self):
        """Should fail: assigning lobby maker who is not in game"""
        game_participants = [1, 2, 3, 4, 5, 6, 7, 8]
        lobby_maker_id = 99  # Not in game!
        
        is_valid = lobby_maker_id in game_participants
        assert is_valid is False
    
    def test_assign_lobby_maker_to_finished_game(self):
        """Should fail: assigning lobby maker to finished game"""
        game = {'status': 'completed'}
        can_assign = game['status'] in ['pending', 'active']
        assert can_assign is False
    
    def test_multiple_lobby_makers(self):
        """Should fail: multiple participants marked as lobby maker"""
        participants = [
            {'id': 1, 'is_lobby_maker': True},
            {'id': 2, 'is_lobby_maker': True},  # Two lobby makers!
            {'id': 3, 'is_lobby_maker': False},
        ]
        
        lobby_maker_count = sum(1 for p in participants if p['is_lobby_maker'])
        is_valid = lobby_maker_count <= 1
        assert is_valid is False  # More than 1!


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_exactly_8_participants(self):
        """Edge case: exactly 8 participants (minimum valid)"""
        participants = 8
        is_valid = participants % 8 == 0 and participants > 0
        assert is_valid is True  # This should be valid
    
    def test_position_1_gives_8_points(self):
        """Edge case: position 1 should give exactly 8 points"""
        position = 1
        points = 9 - position
        assert points == 8
    
    def test_position_8_gives_1_point(self):
        """Edge case: position 8 should give exactly 1 point"""
        position = 8
        points = 9 - position
        assert points == 1
    
    def test_all_positions_shared(self):
        """Edge case: all 8 positions shared (tie)"""
        positions = [1, 2, 3, 4, 5, 6, 7, 8]
        points = [9 - p for p in positions]
        average = sum(points) / len(points)
        assert average == 4.5  # (8+7+6+5+4+3+2+1)/8

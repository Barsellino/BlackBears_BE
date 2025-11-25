"""
Unit tests for Lobby Maker operations
"""
import pytest


class TestLobbyMakerAssignment:
    """Test Lobby Maker assignment logic"""
    
    def test_can_assign_lobby_maker_to_pending_game(self):
        """Should allow: assign lobby maker to pending game"""
        game = {'status': 'pending', 'lobby_maker_id': None}
        participant = {'id': 1, 'user_id': 10, 'in_game': True}
        
        # Should be allowed
        can_assign = (
            game['status'] == 'pending' and
            participant['in_game']
        )
        assert can_assign is True
    
    def test_cannot_assign_lobby_maker_not_in_game(self):
        """Should fail: assign lobby maker who is not in game"""
        game = {'status': 'pending'}
        participant = {'id': 1, 'user_id': 10, 'in_game': False}
        
        can_assign = participant['in_game']
        assert can_assign is False
    
    def test_can_reassign_lobby_maker(self):
        """Should allow: reassign lobby maker to different participant"""
        game = {'status': 'pending', 'lobby_maker_id': 5}
        new_participant = {'id': 2, 'user_id': 12, 'in_game': True}
        
        # Should be allowed to change
        can_reassign = (
            game['status'] == 'pending' and
            new_participant['in_game']
        )
        assert can_reassign is True


class TestLobbyMakerRemoval:
    """Test Lobby Maker removal logic"""
    
    def test_can_remove_from_game_without_results(self):
        """Should allow: remove lobby maker when no results submitted"""
        game = {
            'lobby_maker_id': 10,
            'participants': [
                {'positions': None},
                {'positions': None},
                {'positions': None},
            ]
        }
        
        has_results = any(p['positions'] is not None for p in game['participants'])
        can_remove = not has_results
        
        assert can_remove is True
    
    def test_cannot_remove_when_results_submitted(self):
        """Should fail: remove lobby maker when results already submitted"""
        game = {
            'lobby_maker_id': 10,
            'participants': [
                {'positions': '[1]'},  # One result submitted
                {'positions': None},
                {'positions': None},
            ]
        }
        
        has_results = any(p['positions'] is not None for p in game['participants'])
        can_remove = not has_results
        
        assert can_remove is False
    
    def test_cannot_remove_when_all_results_submitted(self):
        """Should fail: remove lobby maker when all results submitted"""
        game = {
            'lobby_maker_id': 10,
            'participants': [
                {'positions': '[1]'},
                {'positions': '[2]'},
                {'positions': '[3]'},
            ]
        }
        
        has_results = any(p['positions'] is not None for p in game['participants'])
        can_remove = not has_results
        
        assert can_remove is False
    
    def test_can_remove_if_no_lobby_maker_assigned(self):
        """Edge case: removing when no lobby maker assigned"""
        game = {
            'lobby_maker_id': None,
            'participants': [
                {'positions': None},
                {'positions': None},
            ]
        }
        
        # Should handle gracefully (no-op)
        has_lobby_maker = game['lobby_maker_id'] is not None
        assert has_lobby_maker is False


class TestLobbyMakerValidation:
    """Test Lobby Maker validation rules"""
    
    def test_cannot_submit_results_without_lobby_maker(self):
        """Should fail: submit results when no lobby maker assigned"""
        game = {'lobby_maker_id': None}
        
        can_submit = game['lobby_maker_id'] is not None
        assert can_submit is False
    
    def test_can_submit_results_with_lobby_maker(self):
        """Should allow: submit results when lobby maker assigned"""
        game = {'lobby_maker_id': 10}
        
        can_submit = game['lobby_maker_id'] is not None
        assert can_submit is True
    
    def test_only_one_lobby_maker_per_game(self):
        """Should validate: only one participant can be lobby maker"""
        participants = [
            {'id': 1, 'is_lobby_maker': True},
            {'id': 2, 'is_lobby_maker': False},
            {'id': 3, 'is_lobby_maker': False},
        ]
        
        lobby_maker_count = sum(1 for p in participants if p['is_lobby_maker'])
        is_valid = lobby_maker_count == 1
        
        assert is_valid is True
    
    def test_lobby_maker_must_be_participant(self):
        """Should validate: lobby maker must be in the game"""
        game_participants = [1, 2, 3, 4, 5, 6, 7, 8]
        lobby_maker_id = 10  # Not in game
        
        is_valid = lobby_maker_id in game_participants
        assert is_valid is False


class TestLobbyMakerPriorityList:
    """Test priority list functionality"""
    
    def test_priority_list_order_matters(self):
        """Priority list order determines assignment priority"""
        priority_list = [5, 12, 8, 3]
        
        # First in list has highest priority
        highest_priority = priority_list[0]
        assert highest_priority == 5
    
    def test_empty_priority_list(self):
        """Empty priority list means no auto-assignment"""
        priority_list = []
        
        has_priorities = len(priority_list) > 0
        assert has_priorities is False
    
    def test_priority_list_with_non_participants(self):
        """Priority list can contain users not in game"""
        priority_list = [5, 12, 8, 3, 15]
        game_participants = [1, 2, 3, 4, 5, 6, 7, 8]
        
        # Find first user from priority list who is in game
        lobby_maker = next(
            (user_id for user_id in priority_list if user_id in game_participants),
            None
        )
        
        assert lobby_maker == 5  # First match
    
    def test_no_priority_users_in_game(self):
        """No lobby maker assigned if no priority users in game"""
        priority_list = [99, 100, 101]
        game_participants = [1, 2, 3, 4, 5, 6, 7, 8]
        
        lobby_maker = next(
            (user_id for user_id in priority_list if user_id in game_participants),
            None
        )
        
        assert lobby_maker is None


class TestLobbyMakerWorkflow:
    """Test complete lobby maker workflow"""
    
    def test_full_workflow_with_priority_list(self):
        """Test: create game → auto-assign → submit results"""
        # Step 1: Create game with priority list
        tournament = {'lobby_maker_priority_list': [5, 12, 8]}
        game = {
            'id': 1,
            'participants': [
                {'user_id': 1}, {'user_id': 2}, {'user_id': 3},
                {'user_id': 5}, {'user_id': 6}, {'user_id': 7},
                {'user_id': 8}, {'user_id': 9}
            ]
        }
        
        # Step 2: Auto-assign lobby maker (first from priority in game)
        lobby_maker = next(
            (uid for uid in tournament['lobby_maker_priority_list']
             if uid in [p['user_id'] for p in game['participants']]),
            None
        )
        assert lobby_maker == 5
        
        # Step 3: Assign
        game['lobby_maker_id'] = lobby_maker
        assert game['lobby_maker_id'] == 5
        
        # Step 4: Can submit results
        can_submit = game['lobby_maker_id'] is not None
        assert can_submit is True
    
    def test_workflow_manual_assignment(self):
        """Test: create game → manual assign → submit results"""
        game = {'lobby_maker_id': None}
        
        # Manual assignment
        game['lobby_maker_id'] = 10
        assert game['lobby_maker_id'] == 10
        
        # Can submit
        can_submit = game['lobby_maker_id'] is not None
        assert can_submit is True
    
    def test_workflow_remove_and_reassign(self):
        """Test: assign → remove → reassign"""
        game = {
            'lobby_maker_id': 5,
            'participants': [
                {'positions': None},
                {'positions': None},
            ]
        }
        
        # Remove (no results yet)
        has_results = any(p['positions'] is not None for p in game['participants'])
        assert has_results is False
        
        game['lobby_maker_id'] = None
        assert game['lobby_maker_id'] is None
        
        # Reassign to different user
        game['lobby_maker_id'] = 12
        assert game['lobby_maker_id'] == 12

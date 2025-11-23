from pydantic import BaseModel, Field, validator
from typing import List

class GameResultInputV2(BaseModel):
    participant_id: int
    positions: List[int] = Field(..., min_items=1, max_items=8, description="Shared positions (e.g. [6,7,8] for tie)")
    
    @validator('positions')
    def validate_positions(cls, v):
        # Check all positions are between 1-8
        for pos in v:
            if not (1 <= pos <= 8):
                raise ValueError("All positions must be between 1 and 8")
        
        # Check positions are consecutive if more than one
        if len(v) > 1:
            sorted_pos = sorted(v)
            for i in range(1, len(sorted_pos)):
                if sorted_pos[i] != sorted_pos[i-1] + 1:
                    raise ValueError("Shared positions must be consecutive")
        
        return sorted(v)

class GameResultsSubmissionV2(BaseModel):
    results: List[GameResultInputV2] = Field(..., min_items=1, max_items=8)
    
    @validator('results')
    def validate_results(cls, v):
        # Check unique participants
        participant_ids = [r.participant_id for r in v]
        if len(participant_ids) != len(set(participant_ids)):
            raise ValueError("All participants must be unique")
        
        # Check all positions 1-8 are covered exactly once
        all_positions = []
        for result in v:
            all_positions.extend(result.positions)
        
        if sorted(all_positions) != list(range(1, 9)):
            raise ValueError("All positions 1-8 must be assigned exactly once")
        
        return v

def calculate_points_from_positions(positions: List[int]) -> float:
    """Calculate points based on shared positions using your table"""
    
    # Points mapping based on your table
    points_map = {
        (1,): 8.2,
        (2,): 7.1,
        (2, 3): 6.6,
        (2, 3, 4): 6.1,
        (3,): 6.0,
        (3, 4): 5.6,
        (3, 4, 5): 5.1,
        (4,): 5.0,
        (4, 5): 4.6,
        (4, 5, 6): 4.1,
        (4, 5, 6, 7): 3.6,
        (5,): 4.0,
        (5, 6): 3.6,
        (5, 6, 7): 3.1,
        (5, 6, 7, 8): 2.6,
        (6,): 3.0,
        (6, 7): 2.6,
        (6, 7, 8): 2.1,
        (7,): 2.0,
        (7, 8): 1.6,
        (8,): 1.0
    }
    
    positions_tuple = tuple(sorted(positions))
    return points_map.get(positions_tuple, 0.0)
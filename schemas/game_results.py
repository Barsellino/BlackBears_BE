from pydantic import BaseModel, Field, validator
from typing import List
from core.validators import validate_position_and_points


class GameResultInput(BaseModel):
    participant_id: int
    points: int = Field(..., ge=1, le=8, description="Points earned (1-8)")


class GameResultsSubmission(BaseModel):
    results: List[GameResultInput] = Field(..., min_items=1, max_items=8)
    
    @validator('results')
    def validate_unique_participants(cls, v):
        participant_ids = [r.participant_id for r in v]
        if len(participant_ids) != len(set(participant_ids)):
            raise ValueError("All participants must be unique")
        return v


class GameResultResponse(BaseModel):
    game_id: int
    updated_participants: int
    message: str
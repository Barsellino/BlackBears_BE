from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from core.validators import validate_participants_count, validate_rounds_count, validate_position_and_points


class TournamentStatus(str, Enum):
    REGISTRATION = "registration"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class RoundStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


class GameStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


# Tournament schemas
class TournamentBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="Tournament name")
    description: Optional[str] = Field(None, max_length=500, description="Tournament description")
    tournament_type: str = Field(default="SWISS", description="Tournament type")
    total_participants: int = Field(..., ge=8, le=128, description="Total participants (must be divisible by 8)")
    total_rounds: int = Field(..., ge=1, le=10, description="Number of rounds (required)")
    registration_deadline: Optional[datetime] = None
    total_rounds: int = Field(..., ge=1, le=10, description="Number of rounds (required)")
    registration_deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None
    lobby_maker_priority_list: Optional[List[int]] = None

    @validator('registration_deadline', pre=True)
    def parse_registration_deadline(cls, v):
        if v == "" or v is None:
            return None
        return v
    
    @validator('total_rounds')
    def validate_rounds(cls, v, values):
        if 'total_participants' in values:
            validate_rounds_count(v, values['total_participants'])
        return v
    
    @validator('start_date')
    def validate_start_date(cls, v, values):
        if v and 'registration_deadline' in values and values['registration_deadline']:
            if v <= values['registration_deadline']:
                raise ValueError('Start date must be after registration deadline')
        return v


class TournamentCreate(TournamentBase):
    @validator('total_participants')
    def validate_participants(cls, v):
        validate_participants_count(v)
        return v


class TournamentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    registration_deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    status: Optional[TournamentStatus] = None
    lobby_maker_priority_list: Optional[List[int]] = None


class LobbyMakerPriorityUpdate(BaseModel):
    priority_list: List[int]


class Tournament(TournamentBase):
    id: int
    creator_id: int
    current_round: int
    status: TournamentStatus
    current_round: int
    status: TournamentStatus
    lobby_maker_priority_list: Optional[List[int]] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Participant schemas
class TournamentParticipantBase(BaseModel):
    pass


class TournamentParticipantCreate(TournamentParticipantBase):
    tournament_id: int


class TournamentParticipant(TournamentParticipantBase):
    id: int
    tournament_id: int
    user_id: int
    total_score: float
    final_position: Optional[int] = None
    joined_at: datetime
    
    # User info
    battletag: Optional[str] = None
    name: Optional[str] = None

    class Config:
        from_attributes = True


# Round schemas
class TournamentRoundBase(BaseModel):
    round_number: int


class TournamentRoundCreate(TournamentRoundBase):
    tournament_id: int


class TournamentRound(TournamentRoundBase):
    id: int
    tournament_id: int
    status: RoundStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Game schemas
class TournamentGameBase(BaseModel):
    game_number: int


class TournamentGameCreate(TournamentGameBase):
    tournament_id: int
    round_id: int


class TournamentGame(TournamentGameBase):
    id: int
    tournament_id: int
    round_id: int
    status: GameStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    
    # Round info
    round_number: Optional[int] = None
    lobby_maker_id: Optional[int] = None
    
    # Computed fields
    can_edit: Optional[bool] = None
    is_my_game: Optional[bool] = None

    class Config:
        from_attributes = True


# Game participant schemas
class GameParticipantBase(BaseModel):
    points: Optional[int] = Field(None, ge=1, le=8, description="Points earned (1-8)")


class GameParticipantCreate(GameParticipantBase):
    game_id: int
    participant_id: int


class GameParticipantUpdate(BaseModel):
    points: Optional[int] = Field(None, ge=1, le=8, description="Points earned (1-8)")


class GameParticipant(GameParticipantBase):
    id: int
    game_id: int
    participant_id: int
    
    # User info
    user_id: Optional[int] = None
    battletag: Optional[str] = None
    name: Optional[str] = None
    
    # Additional fields for positions
    positions: Optional[str] = None
    calculated_points: Optional[float] = None
    is_lobby_maker: bool = False

    class Config:
        from_attributes = True


# Extended schemas with relationships
class TournamentWithParticipants(Tournament):
    participants: List[TournamentParticipant] = []


class TournamentGameWithParticipants(TournamentGame):
    participants: List[GameParticipant] = []


class TournamentRoundWithGames(TournamentRound):
    games: List[TournamentGameWithParticipants] = []
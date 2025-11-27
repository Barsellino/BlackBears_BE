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


class FirstRoundStrategy(str, Enum):
    RANDOM = "RANDOM"
    BALANCED = "BALANCED"
    STRONG_VS_STRONG = "STRONG_VS_STRONG"


class Prize(BaseModel):
    name: str
    img: Optional[str] = None
    url: Optional[str] = None


# Tournament schemas
class TournamentBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="Tournament name")
    description: Optional[str] = Field(None, max_length=500, description="Tournament description")
    tournament_type: str = Field(default="SWISS", description="Tournament type")
    total_participants: int = Field(..., ge=8, le=128, description="Total participants (must be divisible by 8)")
    total_rounds: int = Field(..., ge=1, le=10, description="Number of rounds (required)")
    registration_deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None
    lobby_maker_priority_list: Optional[List[int]] = None
    
    # New fields
    is_free: bool = True
    prizes: Optional[List[Prize]] = None
    first_round_strategy: FirstRoundStrategy = FirstRoundStrategy.RANDOM
    
    # Finals settings
    with_finals: bool = False
    finals_games_count: Optional[int] = Field(None, ge=1, le=10, description="Number of games in finals")
    finals_participants_count: Optional[int] = Field(None, ge=8, le=16, description="Number of participants in finals (8 or 16)")

    @validator('registration_deadline', pre=True)
    def parse_registration_deadline(cls, v):
        if v == "" or v is None:
            return None
    
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
        
    @validator('finals_games_count')
    def validate_finals_games(cls, v, values):
        if values.get('with_finals') and v is None:
            raise ValueError('finals_games_count is required when with_finals is True')
        return v

    @validator('finals_participants_count')
    def validate_finals_participants(cls, v, values):
        if values.get('with_finals'):
            if v is None:
                raise ValueError('finals_participants_count is required when with_finals is True')
            if v not in [8, 16]:
                raise ValueError('finals_participants_count must be 8 or 16')
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
    status: Optional[TournamentStatus] = None
    lobby_maker_priority_list: Optional[List[int]] = None
    is_free: Optional[bool] = None
    prizes: Optional[List[Prize]] = None
    first_round_strategy: Optional[FirstRoundStrategy] = None
    total_participants: Optional[int] = Field(None, ge=8, le=128, description="Total participants (must be divisible by 8)")
    total_rounds: Optional[int] = Field(None, ge=1, le=10, description="Number of rounds")
    
    # Finals settings
    with_finals: Optional[bool] = None
    finals_games_count: Optional[int] = Field(None, ge=1, le=10)
    finals_participants_count: Optional[int] = Field(None, ge=8, le=16)
    
    @validator('total_participants')
    def validate_participants(cls, v):
        if v is not None:
            validate_participants_count(v)
        return v
    
    @validator('total_rounds')
    def validate_rounds(cls, v, values):
        if v is not None and 'total_participants' in values and values['total_participants'] is not None:
            validate_rounds_count(v, values['total_participants'])
        return v


class LobbyMakerPriorityUpdate(BaseModel):
    priority_list: List[int]


class TournamentWinner(BaseModel):
    user_id: int
    battletag: str
    final_position: int
    total_score: float


class Tournament(BaseModel):
    """Response schema for Tournament - no validation on total_rounds"""
    id: int
    name: str
    description: Optional[str] = None
    tournament_type: str = "SWISS"
    total_participants: int
    total_rounds: int  # Can be increased when finals start
    creator_id: int
    current_round: int
    status: TournamentStatus
    registration_deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None
    lobby_maker_priority_list: Optional[List[int]] = None
    is_free: bool = True
    prizes: Optional[List[Prize]] = None
    first_round_strategy: FirstRoundStrategy = FirstRoundStrategy.RANDOM
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Finals settings
    with_finals: bool = False
    finals_games_count: Optional[int] = None
    finals_participants_count: Optional[int] = None
    regular_rounds: Optional[int] = None  # Original rounds count (before finals)
    finals_started: bool = False  # Whether finals have started
    
    # Computed fields
    occupied_slots: Optional[int] = 0
    creator_battletag: Optional[str] = None
    winners: Optional[List[TournamentWinner]] = None
    
    # Finals participants (top-N sorted by finals_score)
    finals: Optional[List["TournamentParticipant"]] = None
    
    # Tournament format info
    format: Optional[dict] = None
    
    # User's participation status
    my_status: Optional[str] = None  # "registered" | "playing" | "finished" | null
    my_result: Optional[int] = None  # Position (finals position if was in finals, otherwise regular position)
    was_in_finals: Optional[bool] = None  # True if user participated in finals

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
    finals_score: float = 0.0  # Score from finals only
    final_position: Optional[int] = None
    joined_at: datetime
    
    # User info
    battletag: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    telegram: Optional[str] = None
    battlegrounds_rating: Optional[int] = None

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
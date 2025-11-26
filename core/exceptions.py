from fastapi import HTTPException, status


class TournamentException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class TournamentNotFound(TournamentException):
    def __init__(self):
        super().__init__("Tournament not found", status.HTTP_404_NOT_FOUND)


class TournamentFull(TournamentException):
    def __init__(self):
        super().__init__("Tournament is full")


class TournamentClosed(TournamentException):
    def __init__(self, detail: str = "Tournament registration is closed"):
        super().__init__(detail)


class AlreadyJoined(TournamentException):
    def __init__(self):
        super().__init__("Already joined this tournament")


class NotParticipating(TournamentException):
    def __init__(self):
        super().__init__("Not participating in this tournament")


class UnauthorizedAction(TournamentException):
    def __init__(self, action: str = "perform this action"):
        super().__init__(f"Only tournament creator can {action}", status.HTTP_403_FORBIDDEN)


class GameFull(TournamentException):
    def __init__(self):
        super().__init__("Game is full (maximum 8 players)")


class InvalidGameMove(TournamentException):
    def __init__(self, reason: str = "Invalid move"):
        super().__init__(f"Cannot move participant: {reason}")


class UserNotFound(TournamentException):
    def __init__(self):
        super().__init__("User not found", status.HTTP_404_NOT_FOUND)


class InvalidTournamentState(TournamentException):
    def __init__(self, action: str):
        super().__init__(f"Cannot {action} in current tournament state")
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Tuple
from datetime import datetime
from enum import Enum


class BlockColor(str, Enum):
    PURPLE = "purple"
    GREEN = "green" 
    BLUE = "blue"
    YELLOW = "yellow"
    RED = "red"
    PINK = "pink"
    BOMB = "bomb"


class GameStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class Position(BaseModel):
    """Represents a position on the board (x, y)"""
    x: int
    y: int
    
    def to_list(self) -> List[int]:
        return [self.x, self.y]


class BlockMove(BaseModel):
    """Represents a block falling or moving"""
    from_pos: Position = Field(alias="from")
    to_pos: Position = Field(alias="to")
    
    model_config = ConfigDict(populate_by_name=True)


class NewBlock(BaseModel):
    """Represents a new block that appears"""
    pos: Position
    value: BlockColor


class Player(BaseModel):
    """Player in a game session"""
    uniq_id: str
    name: str
    score: int = 0
    moves_left: int = 2
    bombs: int = 0  # Number of bombs available


class GameBoard:
    """Game board logic - 7x8 hexagonal grid (7 columns, 8 rows)"""
    def __init__(self, board: Optional[List[List[int]]] = None):
        if board is None:
            # Initialize with random colors (0-5 representing different colors)
            import random
            self.board = [[random.randint(0, 5) for _ in range(7)] for _ in range(8)]
        else:
            self.board = [row[:] for row in board]  # Deep copy
    
    def get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Get hexagonal neighbors for position (x,y)
        Note: 0,0 is bottom-left, hexagonal grid means 0,1 touches 1,0"""
        neighbors = []
        
        # Standard adjacent positions
        directions = [
            (0, 1),   # up
            (0, -1),  # down
            (1, 0),   # right
            (-1, 0),  # left
        ]
        
        # Hexagonal connections - odd rows have different diagonal neighbors
        if y % 2 == 0:  # even row
            directions.extend([
                (-1, 1),  # up-left
                (-1, -1), # down-left
            ])
        else:  # odd row
            directions.extend([
                (1, 1),   # up-right  
                (1, -1),  # down-right
            ])
        
        for dx, dy in directions:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < 7 and 0 <= new_y < 8:  # Updated for 7x8 board
                neighbors.append((new_x, new_y))
        
        return neighbors
    
    def find_matches(self) -> List[List[Tuple[int, int]]]:
        """Find all groups of 3+ connected blocks of same color"""
        visited = set()
        matches = []
        
        for y in range(8):  # Updated for 8 rows
            for x in range(7):  # Updated for 7 columns
                if (x, y) not in visited:
                    color = self.board[y][x]
                    if color == -1:  # Empty space
                        continue
                        
                    group = self._flood_fill(x, y, color, visited)
                    if len(group) >= 3:
                        matches.append(group)
        
        return matches
    
    def _flood_fill(self, x: int, y: int, color: int, visited: set) -> List[Tuple[int, int]]:
        """Flood fill to find connected blocks of same color"""
        if (x, y) in visited or self.board[y][x] != color:
            return []
        
        visited.add((x, y))
        group = [(x, y)]
        
        for nx, ny in self.get_neighbors(x, y):
            if (nx, ny) not in visited and self.board[ny][nx] == color:
                group.extend(self._flood_fill(nx, ny, color, visited))
        
        return group
    
    def explode_blocks(self, positions: List[Tuple[int, int]]) -> None:
        """Remove blocks at given positions"""
        for x, y in positions:
            self.board[y][x] = -1  # Mark as empty
    
    def apply_gravity(self) -> List[BlockMove]:
        """Apply gravity and return list of moves made"""
        moves = []
        
        for x in range(7):  # Updated for 7 columns
            # Get all non-empty blocks in this column
            column_blocks = []
            for y in range(8):  # Updated for 8 rows
                if self.board[y][x] != -1:
                    column_blocks.append((y, self.board[y][x]))
            
            # Clear the column
            for y in range(8):  # Updated for 8 rows
                self.board[y][x] = -1
            
            # Place blocks at bottom
            for i, (old_y, color) in enumerate(column_blocks):
                new_y = i
                self.board[new_y][x] = color
                
                if old_y != new_y:
                    moves.append(BlockMove(
                        from_pos=Position(x=x, y=old_y),
                        to_pos=Position(x=x, y=new_y)
                    ))
        
        return moves
    
    def fill_empty_spaces(self) -> List[NewBlock]:
        """Fill empty spaces with new random blocks"""
        import random
        new_blocks = []
        
        for x in range(7):  # Updated for 7 columns
            for y in range(7, -1, -1):  # Top to bottom, updated for 8 rows
                if self.board[y][x] == -1:
                    color = random.randint(0, 5)
                    self.board[y][x] = color
                    new_blocks.append(NewBlock(
                        pos=Position(x=x, y=y),
                        value=list(BlockColor)[color]
                    ))
        
        return new_blocks


class GameState(BaseModel):
    """Complete game state"""
    id: Optional[str] = Field(None, alias="_id")
    player1: Player
    player2: Player
    current_player: str  # uniq_id of current player
    board: List[List[int]]  # 7x8 board with color indices
    round: int = 1
    status: GameStatus = GameStatus.WAITING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class MoveRequest(BaseModel):
    """Request to make a move"""
    x: int
    y: int
    game_id: str
    uniqId: str


class MoveResponse(BaseModel):
    """Response after making a move"""
    score_gained: int
    total_score: int
    round: int
    moves_left: int
    board: List[List[int]]
    exploded: List[List[int]]
    fallen: List[dict]
    new_blocks: List[dict]
    game_over: bool = False
    winner: Optional[str] = None


class GameSession(BaseModel):
    """Game session for database storage"""
    id: Optional[str] = Field(None, alias="_id") 
    player1_id: str
    player2_id: str
    player1_name: str
    player2_name: str
    current_player_id: str
    board: List[List[int]]  # 7x8 board
    player1_score: int = 0
    player2_score: int = 0
    player1_moves_left: int = 2
    player2_moves_left: int = 2
    player1_bombs: int = 0
    player2_bombs: int = 0
    round: int = 1
    status: GameStatus = GameStatus.IN_PROGRESS
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

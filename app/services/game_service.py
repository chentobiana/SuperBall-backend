from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from app.models.game import (
    GameSession, GameBoard, MoveResponse, GameStatus
)
from app.database.game_repository import GameRepository
import logging

logger = logging.getLogger(__name__)


class GameService:
    """Service for handling all server-side game rules and persistence.

    Responsibilities:
    - Create and persist `GameSession` objects
    - Validate turns, moves left, and board boundaries
    - Execute explosions, gravity, refills, cascades, and bomb usage
    - Update scores, turns, bombs, and rounds
    - Produce `MoveResponse` payloads matching the Unity contract
    """

    def __init__(self):
        self.game_repo = GameRepository()

    async def create_game_session(self, player1_id: str, player1_name: str,
                                  player2_id: str, player2_name: str) -> GameSession:
        """Create a new game session between two players.

        Player 1 always starts with the turn per game rules.
        Board is initialized as a 7x8 numeric matrix (colors 0..5).
        """

        # Generate initial random board (flip to match frontend Y=0 at bottom)
        temp_board = GameBoard().board
        board = [temp_board[7-i] for i in range(8)]  # Flip vertically

        game_session = GameSession(
            player1_id=player1_id,
            player2_id=player2_id,
            player1_name=player1_name,
            player2_name=player2_name,
            current_player_id=player1_id,  # Player 1 starts
            board=board,
            status=GameStatus.IN_PROGRESS
        )

        # Initialize first turn deadline (default 30s if not configured)
        try:
            from app.config import settings
            turn_seconds = int(getattr(settings, "TURN_SECONDS", 30))
        except Exception:
            turn_seconds = 30
        game_session.current_turn_deadline = datetime.utcnow() + timedelta(seconds=turn_seconds)

        return await self.game_repo.create_game(game_session)

    async def make_move(self, game_id: str, uniqId: str, x: int, y: int) -> MoveResponse:
        """Process a player's move and return the full `MoveResponse`.

        If the clicked group is < 3, return the current board with score_gained=0.
        """

        # Get game session
        game = await self.game_repo.find_by_id(game_id)
        if not game:
            raise ValueError("Game not found")

        # Validate it's the player's turn
        if game.current_player_id != uniqId:
            raise ValueError("Not your turn")

        # Validate player has moves left
        moves_left_before = (
            game.player1_moves_left if game.player1_id == uniqId else game.player2_moves_left
        )
        if moves_left_before <= 0:
            raise ValueError("No moves left")

        # Do NOT consume a move yet; only after a valid explosion
        if game.player1_id == uniqId:
            current_score = game.player1_score
        else:
            current_score = game.player2_score

        # Validate position
        if not (0 <= x < 7 and 0 <= y < 8):
            raise ValueError("Invalid position")

        # Check if position has a block (board now uses frontend coordinates)
        if game.board[y][x] == "Empty":
            raise ValueError("No block at this position")

        # Process the move (flip board back to internal format for processing)
        internal_board = [game.board[7-i] for i in range(8)]
        game_board = GameBoard(internal_board)
        
        # Simulate clicking on the block - for now just explode connected blocks of same color
        # Convert coordinates back to internal format for processing
        internal_y = 7 - y
        clicked_color = game_board.board[internal_y][x]
        exploded_positions = self._get_connected_blocks(game_board, x, internal_y, clicked_color)
        
        if len(exploded_positions) < 3:
            # No valid match: do not consume move and do not switch turn
            logger.warning(f"Player {uniqId} clicked ({x},{y}) with color '{clicked_color}' but only found {len(exploded_positions)} connected blocks")
            
            # Ensure there is at least one possible move; regenerate silently if needed
            board_regenerated = False
            # Convert to internal format for processing
            internal_board_after = [game.board[7-i] for i in range(8)]
            game_board_after = GameBoard(internal_board_after)
            if not game_board_after.has_possible_moves():
                logger.info(f"No possible moves found, regenerating board for game {game_id}")
                game_board_after.regenerate_board()
                # Flip the regenerated board to match frontend coordinates
                game.board = [game_board_after.board[7-i] for i in range(8)]
                board_regenerated = True
            else:
                logger.info(f"Board still has possible moves, keeping current board for game {game_id}")

            # Persist state (board may have changed)
            await self.game_repo.update_game(game_id, {
                "board": game.board,
                "player1_score": game.player1_score,
                "player2_score": game.player2_score,
                "player1_moves_left": game.player1_moves_left,
                "player2_moves_left": game.player2_moves_left,
                "player1_bombs": game.player1_bombs,
                "player2_bombs": game.player2_bombs,
                "current_player_id": game.current_player_id,
                "round": game.round,
            })

            return MoveResponse(
                score_gained=0,
                total_score=current_score,
                round=game.round,
                moves_left=moves_left_before,
                board=game.board,
                exploded=[],
                fallen=[],
                new_blocks=[],
                board_regenerated=board_regenerated,
            )
        
        # Calculate score
        score_gained = self._calculate_score(len(exploded_positions))
        
        # Check for bomb bonus (5+ blocks)
        bomb_bonus = len(exploded_positions) >= 5
        
        # Apply explosions
        game_board.explode_blocks(exploded_positions)
        
        # Apply gravity
        fallen_moves = game_board.apply_gravity()
        
        # Fill empty spaces
        new_blocks = game_board.fill_empty_spaces()
        
        # Check for cascading matches
        cascaded_explosions = []
        cascaded_fallen = []
        cascaded_new_blocks = []
        total_score_gained = score_gained
        
        while True:
            matches = game_board.find_matches()
            if not matches:
                break
            
            # Explode all matches
            all_match_positions = []
            for match in matches:
                all_match_positions.extend(match)
            
            cascaded_explosions.extend([[pos[0], pos[1]] for pos in all_match_positions])
            game_board.explode_blocks(all_match_positions)
            
            # Add cascade score
            total_score_gained += self._calculate_score(len(all_match_positions))
            
            # Apply gravity again
            cascade_fallen = game_board.apply_gravity()
            cascaded_fallen.extend(cascade_fallen)
            
            # Fill empty spaces again
            cascade_new = game_board.fill_empty_spaces()
            cascaded_new_blocks.extend(cascade_new)
        
        # Consume move now that a valid explosion occurred
        if game.player1_id == uniqId:
            game.player1_moves_left -= 1
            moves_left_after = game.player1_moves_left
        else:
            game.player2_moves_left -= 1
            moves_left_after = game.player2_moves_left

        # Update game state (scores/bombs)
        if game.player1_id == uniqId:
            game.player1_score += total_score_gained
            if bomb_bonus:
                game.player1_bombs += 1
            current_score = game.player1_score
        else:
            game.player2_score += total_score_gained
            if bomb_bonus:
                game.player2_bombs += 1
            current_score = game.player2_score
        
        # Check if turn should switch (2 moves per player)
        if moves_left_after == 0:
            # Switch to other player
            if game.current_player_id == game.player1_id:
                game.current_player_id = game.player2_id
                game.player2_moves_left = 2
            else:
                game.current_player_id = game.player1_id
                game.player1_moves_left = 2
                game.round += 1  # New round when it comes back to player 1
        
        # Reset/extend turn deadline for the (possibly new) current player
        try:
            from app.config import settings
            turn_seconds = int(getattr(settings, "TURN_SECONDS", 30))
        except Exception:
            turn_seconds = 30
        game.current_turn_deadline = datetime.utcnow() + timedelta(seconds=turn_seconds)
        
        # Ensure next board has possible moves; regenerate if needed
        board_regenerated = False
        if not game_board.has_possible_moves():
            game_board.regenerate_board()
            board_regenerated = True

        # Update board (flip to match frontend coordinates)
        game.board = [game_board.board[7-i] for i in range(8)]
        
        # Save game state
        await self.game_repo.update_game(game_id, {
            "board": game.board,
            "player1_score": game.player1_score,
            "player2_score": game.player2_score,
            "player1_moves_left": game.player1_moves_left,
            "player2_moves_left": game.player2_moves_left,
            "player1_bombs": game.player1_bombs,
            "player2_bombs": game.player2_bombs,
            "current_player_id": game.current_player_id,
            "round": game.round,
            "current_turn_deadline": game.current_turn_deadline,
        })
        
        # Prepare response in the exact schema expected by the client
        all_exploded = [[pos[0], pos[1]] for pos in exploded_positions] + cascaded_explosions
        all_fallen = [{"from": move.from_pos.to_list(), "to": move.to_pos.to_list()} 
                     for move in fallen_moves + cascaded_fallen]
        all_new_blocks = [{"pos": block.pos.to_list(), "value": block.value} 
                         for block in new_blocks + cascaded_new_blocks]
        
        return MoveResponse(
            score_gained=total_score_gained,
            total_score=current_score,
            round=game.round,
            moves_left=moves_left_after,
            board=game.board,
            exploded=all_exploded,
            fallen=all_fallen,
            new_blocks=all_new_blocks,
            board_regenerated=board_regenerated,
        )
    
    def _get_connected_blocks(self, game_board: GameBoard, x: int, y: int, color: str) -> List[Tuple[int, int]]:
        """Get all connected blocks of the same color using flood fill"""
        visited = set()
        return game_board._flood_fill(x, y, color, visited)
    
    def _calculate_score(self, blocks_count: int) -> int:
        """Calculate score based on number of blocks exploded"""
        base_score = 10
        if blocks_count == 3:
            return base_score * 3
        elif blocks_count == 4:
            return base_score * 6
        elif blocks_count == 5:
            return base_score * 10
        else:
            # 6+ blocks - exponential bonus
            return base_score * (blocks_count * 2)
    
    async def use_bomb(self, game_id: str, uniqId: str, x: int, y: int) -> MoveResponse:
        """Use a bomb at the specified position"""
        
        # Get game session
        game = await self.game_repo.find_by_id(game_id)
        if not game:
            raise ValueError("Game not found")
        
        # Validate it's the player's turn
        if game.current_player_id != uniqId:
            raise ValueError("Not your turn")
        
        # Check if player has bombs
        bombs_available = (game.player1_bombs if game.player1_id == uniqId 
                          else game.player2_bombs)
        if bombs_available <= 0:
            raise ValueError("No bombs available")
        
        # Validate position
        if not (0 <= x < 7 and 0 <= y < 8):
            raise ValueError("Invalid position")
        
        # Get all neighbors + center position (convert to internal format for processing)
        internal_board = [game.board[7-i] for i in range(8)]
        game_board = GameBoard(internal_board)
        internal_y = 7 - y
        bomb_positions = [(x, internal_y)]
        bomb_positions.extend(game_board.get_neighbors(x, internal_y))
        
        # Remove positions that are already empty (unified sentinel)
        bomb_positions = [
            (bx, by)
            for bx, by in bomb_positions
            if game_board.board[by][bx] != "Empty"
        ]
        
        # Calculate score
        score_gained = self._calculate_score(len(bomb_positions)) * 2  # Bomb bonus
        
        # Apply explosions then run the common settle loop (gravity + refills + cascades)
        game_board.explode_blocks(bomb_positions)
        (
            fallen_moves,
            new_blocks,
            cascaded_explosions,
            cascaded_fallen,
            cascaded_new_blocks,
            cascade_score
        ) = self._settle_board(game_board)
        total_score_gained = score_gained + cascade_score
        
        # Update game state
        if game.player1_id == uniqId:
            game.player1_score += total_score_gained
            game.player1_bombs -= 1
            game.player1_moves_left -= 1
            current_score = game.player1_score
            moves_left = game.player1_moves_left
        else:
            game.player2_score += total_score_gained
            game.player2_bombs -= 1
            game.player2_moves_left -= 1
            current_score = game.player2_score
            moves_left = game.player2_moves_left
        
        # Check if turn should switch
        if moves_left == 0:
            if game.current_player_id == game.player1_id:
                game.current_player_id = game.player2_id
                game.player2_moves_left = 2
            else:
                game.current_player_id = game.player1_id
                game.player1_moves_left = 2
                game.round += 1
        
        # Update board (flip to match frontend coordinates)
        game.board = [game_board.board[7-i] for i in range(8)]
        
        # Save game state
        await self.game_repo.update_game(game_id, {
            "board": game.board,
            "player1_score": game.player1_score,
            "player2_score": game.player2_score,
            "player1_moves_left": game.player1_moves_left,
            "player2_moves_left": game.player2_moves_left,
            "player1_bombs": game.player1_bombs,
            "player2_bombs": game.player2_bombs,
            "current_player_id": game.current_player_id,
            "round": game.round
        })
        
        # Prepare response
        all_exploded = [[pos[0], pos[1]] for pos in bomb_positions] + cascaded_explosions
        all_fallen = [{"from": move.from_pos.to_list(), "to": move.to_pos.to_list()} 
                     for move in fallen_moves + cascaded_fallen]
        all_new_blocks = [
            {"pos": block.pos.to_list(), "value": block.value}
            for block in new_blocks + cascaded_new_blocks
        ]
        
        return MoveResponse(
            score_gained=total_score_gained,
            total_score=current_score,
            round=game.round,
            moves_left=moves_left,
            board=game.board,
            exploded=all_exploded,
            fallen=all_fallen,
            new_blocks=all_new_blocks
        )

    def _settle_board(self, game_board: GameBoard):
        """Run gravity + refill + cascading matches until stable.

        Returns: (fallen_moves, new_blocks, cascaded_explosions, cascaded_fallen, cascaded_new_blocks, cascade_score)
        """
        # First gravity + refill after the initial explosion
        fallen_moves = game_board.apply_gravity()
        new_blocks = game_board.fill_empty_spaces()

        cascaded_explosions = []
        cascaded_fallen = []
        cascaded_new_blocks = []
        cascade_score = 0

        while True:
            matches = game_board.find_matches()
            if not matches:
                break
            all_match_positions = []
            for match in matches:
                all_match_positions.extend(match)
            cascaded_explosions.extend([[pos[0], pos[1]] for pos in all_match_positions])
            game_board.explode_blocks(all_match_positions)
            cascade_score += self._calculate_score(len(all_match_positions))
            cascade_fallen = game_board.apply_gravity()
            cascaded_fallen.extend(cascade_fallen)
            cascade_new = game_board.fill_empty_spaces()
            cascaded_new_blocks.extend(cascade_new)

        return (
            fallen_moves,
            new_blocks,
            cascaded_explosions,
            cascaded_fallen,
            cascaded_new_blocks,
            cascade_score,
        )

    
    async def get_game_state(self, game_id: str) -> Optional[GameSession]:
        """Get current game state"""
        return await self.game_repo.find_by_id(game_id)
    
    async def get_player_games(self, uniqId: str) -> List[GameSession]:
        """Get all games for a player"""
        return await self.game_repo.find_by_player(uniqId, GameStatus.IN_PROGRESS)

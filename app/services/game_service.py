from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from app.models.game import (
    GameSession, GameBoard, MoveResponse, GameStatus
)
from app.database.game_repository import GameRepository
from app.services.reward_service import RewardService
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
        self.reward_service = RewardService()

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

        # Check if game is finished
        if game.status == GameStatus.FINISHED:
            raise ValueError("Game is finished")

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

        # Convert frontend Y coordinate (Y=0 at bottom) to server Y coordinate (Y=0 at top)
        server_y = y
        logger.info(f"Frontend sent ({x},{y}) -> converting to server ({x},{server_y})")

        # Check if position has a block
        if game.board[server_y][x] == "Empty":
            raise ValueError("No block at this position")

        # Process the move (flip board back to internal format for processing)
        internal_board = [game.board[7-i] for i in range(8)]
        game_board = GameBoard(internal_board)
        
        # Save original board for comparison
        original_board = [row[:] for row in game.board]
        
        # Simulate clicking on the block - handle bombs specially
        # Convert coordinates back to internal format for processing
        internal_y = y  # server_y is already converted from frontend
        clicked_color = game_board.board[internal_y][x]
        logger.info(
            "Processing click at server (%d,%d) -> internal (%d,%d) with color '%s'",
            x,
            server_y,
            x,
            internal_y,
            clicked_color,
        )
        
        # Check if clicked block is a bomb
        if clicked_color == "Bomb":
            # Bomb behavior: explode center + all neighbors
            bomb_positions = [(x, internal_y)]
            bomb_positions.extend(game_board.get_neighbors(x, internal_y))
            
            # Remove positions that are already empty
            bomb_positions = [
                (bx, by)
                for bx, by in bomb_positions
                if game_board.board[by][bx] != "Empty"
            ]
            
            exploded_positions = bomb_positions
            logger.info(
                "Bomb clicked: exploding center + %d neighbors: %s",
                len(bomb_positions) - 1,
                exploded_positions,
            )
        else:
            # Regular block behavior: explode connected blocks of same color
            exploded_positions = self._get_connected_blocks(
                game_board, x, internal_y, clicked_color
            )
            logger.info(
                "Found %d connected blocks: %s",
                len(exploded_positions),
                exploded_positions,
            )
        
        if len(exploded_positions) < 3:
            # No valid match: do not consume move and do not switch turn
            logger.warning(
                "Player %s clicked (%d,%d) with color '%s' but only found %d connected blocks",
                uniqId,
                x,
                y,
                clicked_color,
                len(exploded_positions),
            )
            
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

            # Check if game is over
            game_over = game.status == GameStatus.FINISHED
            winner = None
            if game_over:
                if game.player1_score > game.player2_score:
                    winner = game.player1_name
                elif game.player2_score > game.player1_score:
                    winner = game.player2_name
                else:
                    winner = "Tie"
            
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
                game_over=game_over,
                winner=winner,
                clicked_x=x,
                clicked_y=y,
            )
        
        # Calculate score - special handling for bombs
        if clicked_color == "Bomb":
            # Bomb scoring: score_gained = _calculate_score(len(bomb_positions)) * 2
            score_gained = self._calculate_score(len(exploded_positions)) * 2
            bomb_bonus = False  # Bombs don't give bomb bonuses
        else:
            # Regular scoring
            score_gained = self._calculate_score(len(exploded_positions))
            # Check for bomb bonus (5+ blocks)
            bomb_bonus = len(exploded_positions) >= 5
        
        # Apply explosions
        game_board.explode_blocks(exploded_positions)
        
        # Apply gravity
        fallen_moves = game_board.apply_gravity()
        
        # Fill empty spaces
        new_blocks = game_board.fill_empty_spaces()
        
        # Per new rules: do NOT auto-cascade. Only the clicked group explodes this turn.
        total_score_gained = score_gained
        
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
                
                # Check if game should end after 5 rounds
                if game.round > 5:
                    game.status = GameStatus.FINISHED
                    # Determine winner based on score
                    if game.player1_score > game.player2_score:
                        winner = game.player1_name
                    elif game.player2_score > game.player1_score:
                        winner = game.player2_name
                    else:
                        winner = "Tie"
                    
                    # Process rewards for finished game
                    await self.finish_game(game.id)
        
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
        # No coordinate conversion needed - board already uses frontend coordinates
        all_exploded = [[pos[0], pos[1]] for pos in exploded_positions]
        all_fallen = [{
            "from": move.from_pos.to_list(),
            "to": move.to_pos.to_list(),
        } for move in fallen_moves]
        all_new_blocks = [{
            "pos": block.pos.to_list(),
            "value": block.value,
        } for block in new_blocks]
        
        exploded_coords = set((pos[0], pos[1]) for pos in all_exploded)
        fallen_from_coords = set((move["from"][0], move["from"][1]) for move in all_fallen)
        overlap = exploded_coords.intersection(fallen_from_coords)
        if overlap:
            logger.error(
                "IMPOSSIBLE: Block(s) %s appear in both exploded and fallen! This should never happen!",
                overlap,
            )
        
        if game.board == original_board:
            logger.error(
                "CRITICAL: Board didn't change after successful move with %d explosions!",
                len(exploded_positions),
            )
            logger.error("Original board: %s", original_board)
            logger.error("Final board: %s", game.board)
        
        # Check if game is over
        game_over = game.status == GameStatus.FINISHED
        winner = None
        if game_over:
            if game.player1_score > game.player2_score:
                winner = game.player1_name
            elif game.player2_score > game.player1_score:
                winner = game.player2_name
            else:
                winner = "Tie"
        
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
            game_over=game_over,
            winner=winner,
            clicked_x=x,
            clicked_y=y,
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
    
    async def finish_game(self, game_id: str) -> bool:
        """
        Finish a game and process rewards for both players
        Returns True if successful, False otherwise
        """
        try:
            # Get game session
            game = await self.game_repo.find_by_id(game_id)
            if not game:
                logger.error(f"Game {game_id} not found")
                return False
            
            # Mark game as finished
            await self.game_repo.update_game(game_id, {
                "status": GameStatus.FINISHED,
                "updated_at": datetime.utcnow()
            })
            
            # Process rewards for both players
            player1_result, player2_result = await self.reward_service.process_game_result(
                game_id=game_id,
                player1_id=game.player1_id,
                player2_id=game.player2_id
            )
            
            if player1_result and player2_result:
                logger.info(f"Successfully processed rewards for finished game {game_id}")
                
                # Send game over notification via WebSocket
                from app.routes.game import manager
                await manager.send_personal_message({
                    "type": "game_over",
                    "game_id": game_id,
                    "player1_result": {
                        "player_id": game.player1_id,
                        "player_name": game.player1_name,
                        "score": game.player1_score,
                        "trophies_gained": player1_result.trophies_gained,
                        "money_gained": player1_result.money_gained,
                        "stars_earned": player1_result.stars_earned,
                        "outcome": player1_result.outcome.value
                    },
                    "player2_result": {
                        "player_id": game.player2_id,
                        "player_name": game.player2_name,
                        "score": game.player2_score,
                        "trophies_gained": player2_result.trophies_gained,
                        "money_gained": player2_result.money_gained,
                        "stars_earned": player2_result.stars_earned,
                        "outcome": player2_result.outcome.value
                    }
                }, game_id)
                
                return True
            else:
                logger.error(f"Failed to process rewards for game {game_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error finishing game {game_id}: {e}")
            return False

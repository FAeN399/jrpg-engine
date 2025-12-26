import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from engine.resources.database import Database

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("DataVerification")
    
    try:
        # Initialize Database
        db = Database(Path("game/data"))
        
        # Load all data
        logger.info("Loading database...")
        db.load_all()
        
        # Verify Items
        assert db.get_item("weapon_iron_sword") is not None, "Missing Iron Sword"
        assert db.get_item("weapon_steel_sword") is not None, "Missing Steel Sword"
        assert db.items["weapon_iron_sword"]["price"] == 100
        
        # Verify Enemies
        assert db.get_enemy("enemy_slime") is not None
        assert db.get_enemy("enemy_wolf") is not None
        assert db.enemies["enemy_wolf"]["hp"] == 80
        
        # Verify Skills
        assert db.get_skill("skill_bash") is not None
        assert db.skills["skill_fireball"]["type"] == "magic"
        
        # Verify Quests
        assert "quest_main_01" in db.quests
        
        # Verify Dialog
        assert "dialog_intro" in db.dialogs
        
        logger.info("VERIFICATION SUCCESSFUL: All data loaded and validated.")
        
    except Exception as e:
        logger.error(f"VERIFICATION FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

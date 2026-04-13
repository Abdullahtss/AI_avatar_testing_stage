from config import EXERCISE_CATALOG
from trainer import Trainer


class ExerciseConfig:
    """Dynamic exercise configuration"""
    def __init__(self, name, exercise_type, primary_angle, min_rom=30):
        self.name = name
        self.type = exercise_type  # 'single', 'boxing', 'yaml'
        self.primary_angle = primary_angle
        self.min_rom = min_rom


def display_available_exercises():
    """Show exercises from catalog"""
    print("\n" + "="*60)
    print("AVAILABLE EXERCISES")
    print("="*60)
    
    exercises = list(EXERCISE_CATALOG.keys())
    for idx, name in enumerate(exercises, 1):
        cfg = EXERCISE_CATALOG[name]
        print(f"{idx}. {name.upper():20} (Type: {cfg.type})")
    
    print("="*60 + "\n")
    return exercises


def get_exercise_selection():
    """Get existing exercise from user"""
    exercises = display_available_exercises()
    
    while True:
        user_input = input("Enter exercise name or number (or 'new' for new exercise): ").strip().lower()
        
        if user_input == 'new':
            return None  # Signal to create new exercise
        
        if user_input == 'list':
            display_available_exercises()
            continue
        
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(exercises):
                return exercises[idx]
            else:
                print(f"Invalid number. Enter 1-{len(exercises)}\n")
                continue
        
        if user_input in exercises:
            return user_input
        
        print(f"Unknown exercise: {user_input}\n")


def create_new_exercise():
    """Create new exercise at runtime"""
    print("\n" + "="*60)
    print("CREATE NEW EXERCISE")
    print("="*60)
    
    exercise_name = input("Exercise name: ").strip().lower()
    
    if exercise_name in EXERCISE_CATALOG:
        print(f"Exercise '{exercise_name}' already exists!\n")
        return None
    
    print("\nExercise types:")
    print("1. single  - Single stage (squat, pushup)")
    print("2. boxing  - Multi-stage punching")
    print("3. yoga    - Multi-stage holding poses")
    
    while True:
        exercise_type = input("\nSelect type (1-3 or name): ").strip().lower()
        
        if exercise_type in ['1', 'single']:
            exercise_type = 'single'
            break
        elif exercise_type in ['2', 'boxing']:
            exercise_type = 'multi'
            break
        elif exercise_type in ['3', 'yoga']:
            exercise_type = 'multi'
            break
        else:
            print("Invalid type. Enter: single, boxing, or yoga")
    
    # Get primary joint
    print("\nCommon joints:")
    print("- right_elbow, left_elbow")
    print("- right_knee, left_knee")
    print("- right_shoulder, left_shoulder")
    
    primary_angle = input("Primary joint to track: ").strip().lower()
    
    # Get ROM (only for single-stage)
    min_rom = 30  # Default
    if exercise_type == 'single':
        while True:
            try:
                min_rom_input = input("Minimum ROM (range of motion) in degrees (default: 30): ").strip()
                if not min_rom_input:
                    min_rom = 30
                    break
                min_rom = int(min_rom_input)
                if min_rom > 0:
                    break
                else:
                    print("Must be positive number")
            except ValueError:
                print("Invalid number")
    
    # Create config
    cfg = ExerciseConfig(
        name=exercise_name,
        exercise_type=exercise_type,
        primary_angle=primary_angle,
        min_rom=min_rom
    )
    
    # Save to catalog
    EXERCISE_CATALOG[exercise_name] = cfg
    
    print(f"\n✓ Exercise '{exercise_name}' created!")
    print(f"  Type: {exercise_type}")
    print(f"  Primary joint: {primary_angle}")
    if exercise_type == 'single':
        print(f"  Min ROM: {min_rom}°")
    
    return exercise_name


def get_training_parameters():
    """Get number of reps to train"""
    print("\n" + "="*60)
    print("TRAINING PARAMETERS")
    print("="*60)
    
    while True:
        try:
            num_reps = input("Number of reps to train (default: 10): ").strip()
            
            if not num_reps:
                return 10
            
            num_reps = int(num_reps)
            if num_reps > 0:
                print(f"✓ Will train {num_reps} reps\n")
                return num_reps
            else:
                print("Must be positive number\n")
        except ValueError:
            print("Invalid number\n")


def main():
    """Main training entry point"""
    print("\n" + "="*60)
    print("EXERCISE TRAINER - RUNTIME CONFIGURATION")
    print("="*60)
    
    # Step 1: Get exercise
    exercise = get_exercise_selection()
    
    if exercise is None:
        # User wants to create new exercise
        exercise = create_new_exercise()
        if exercise is None:
            print("Failed to create exercise")
            return
    
    # Step 2: Validate exercise exists
    if exercise not in EXERCISE_CATALOG:
        print(f"Error: Exercise '{exercise}' not found")
        return
    
    cfg = EXERCISE_CATALOG[exercise]
    
    # Step 3: Get training parameters
    num_reps = get_training_parameters()
    
    # Step 4: Start training
    print("="*60)
    print(f"Exercise: {exercise.upper()}")
    print(f"Type: {cfg.type}")
    print(f"Reps: {num_reps}")
    print("="*60 + "\n")
    
    try:
        trainer = Trainer(cfg, num_reps=num_reps)
        trainer.run()
    except KeyboardInterrupt:
        print("\n\nTraining interrupted")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
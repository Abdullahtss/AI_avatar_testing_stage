"""
Modified run_coach.py - Interactive exercise selection for coaching
Allows users to select exercises at runtime and start coaching session
"""

from config import EXERCISE_CATALOG
from coach import LiveCoach


def display_available_exercises():
    """Display all available exercises from EXERCISE_CATALOG"""
    print("\n" + "="*70)
    print("AVAILABLE EXERCISES FOR COACHING")
    print("="*70)
    
    exercises = list(EXERCISE_CATALOG.keys())
    
    if not exercises:
        print("No exercises in catalog yet.")
        print("Train exercises first using: python run_trainer.py")
        print("="*70 + "\n")
        return exercises
    
    for idx, name in enumerate(exercises, 1):
        cfg = EXERCISE_CATALOG[name]
        exercise_type = cfg.type if hasattr(cfg, 'type') else 'unknown'
        print(f"{idx:2}. {name.upper():25} (Type: {exercise_type})")
    
    print("="*70 + "\n")
    return exercises


def get_exercise_selection():
    """Get exercise from user"""
    exercises = display_available_exercises()
    
    if not exercises:
        print("✗ No exercises available to coach")
        return None
    
    print("OPTIONS:")
    print("  - Enter exercise number: 1, 2, 3, etc.")
    print("  - Enter exercise name: boxing, squat, pullups, etc.")
    print("  - Type 'list' to see all exercises again")
    print()
    
    while True:
        try:
            user_input = input("Select exercise: ").strip().lower()
            
            # Show list again
            if user_input == 'list':
                display_available_exercises()
                continue
            
            # User entered a number
            if user_input.isdigit():
                idx = int(user_input) - 1
                if 0 <= idx < len(exercises):
                    selected = exercises[idx]
                    print(f"\n✓ Selected: {selected.upper()}\n")
                    return selected
                else:
                    print(f"✗ Invalid number. Enter 1-{len(exercises)}\n")
                    continue
            
            # User entered exercise name
            if user_input in exercises:
                print(f"\n✓ Selected: {user_input.upper()}\n")
                return user_input
            
            # Invalid input
            print(f"✗ Unknown exercise: '{user_input}'")
            print(f"   Available: {', '.join(exercises)}\n")
            
        except KeyboardInterrupt:
            print("\n\n✗ Cancelled by user")
            exit(1)
        except Exception as e:
            print(f"✗ Error: {e}\n")


def display_exercise_info(exercise_name):
    """Display information about selected exercise"""
    cfg = EXERCISE_CATALOG[exercise_name]
    
    print("="*70)
    print("EXERCISE INFORMATION")
    print("="*70)
    print(f"Name:              {exercise_name.upper()}")
    print(f"Type:              {cfg.type}")
    print(f"Primary Joint:     {cfg.primary_angle}")
    
    if hasattr(cfg, 'min_rom'):
        print(f"Min ROM:           {cfg.min_rom}°")
    
    print("="*70 + "\n")


def main():
    """Main coaching entry point"""
    print("\n" + "="*70)
    print("AI EXERCISE COACH - RUNTIME CONFIGURATION")
    print("="*70)
    print("Select an exercise to start coaching")
    print("="*70 + "\n")
    
    # Step 1: Get exercise selection
    exercise = get_exercise_selection()
    
    if exercise is None:
        print("✗ No exercise selected")
        return
    
    # Step 2: Validate exercise exists
    if exercise not in EXERCISE_CATALOG:
        print(f"✗ Error: Exercise '{exercise}' not found")
        return
    
    cfg = EXERCISE_CATALOG[exercise]
    
    # Step 3: Display exercise information
    display_exercise_info(exercise)
    
    # Step 4: Show readiness message
    print("="*70)
    print("COACHING SESSION")
    print("="*70)
    print(f"Starting coach for: {exercise.upper()}")
    print("\nMake sure:")
    print("  1. Video sender is running")
    print("  2. Audio is enabled for feedback")
    print("  3. You're in good position on camera")
    print("\nPress 'q' during coaching to quit")
    print("="*70 + "\n")
    
    try:
        # Initialize and run coach
        coach = LiveCoach(cfg)
        coach.run()
        
        print("\n" + "="*70)
        print("✓ COACHING SESSION COMPLETE")
        print("="*70)
        print(f"Exercise: {exercise.upper()}")
        print("Thanks for training with AI Coach!")
        print("="*70 + "\n")
    
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print(f"\nMake sure you trained '{exercise}' first:")
        print(f"  python run_trainer.py")
        print(f"  Select exercise: {exercise}")
    
    except KeyboardInterrupt:
        print("\n\n✗ Coaching interrupted by user")
        exit(0)
    
    except Exception as e:
        print(f"\n✗ Error during coaching: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
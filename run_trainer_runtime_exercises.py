# =============================================================================
# Copyright (c) 2024 Abdullah (GitHub: Abdullahtss)
# All Rights Reserved.
#
# PROPRIETARY AND CONFIDENTIAL
# This file is part of the AI Avatar Exercise Correction System.
#
# UNAUTHORIZED COPYING, MODIFICATION, DISTRIBUTION, OR USE OF THIS FILE,
# VIA ANY MEDIUM, IS STRICTLY PROHIBITED WITHOUT PRIOR WRITTEN PERMISSION
# FROM THE AUTHOR. Submitting this code as your own work constitutes
# plagiarism and may result in academic and/or legal consequences.
#
# For permissions: https://github.com/Abdullahtss
# =============================================================================
"""
Modified run_trainer.py - Add exercises at runtime
Supports single-stage (pushup, pullup) and multi-stage (yoga, stretching)
"""

from config import EXERCISE_CATALOG
from trainer import Trainer


class ExerciseConfig:
    """Dynamic exercise configuration"""
    def __init__(self, name, exercise_type, primary_angle, min_rom=30):
        """
        Create exercise configuration
        
        Args:
            name (str): Exercise name (e.g., 'pullup')
            exercise_type (str): 'single', 'boxing', or 'yoga'
            primary_angle (str): Joint to track
            min_rom (int): Minimum range of motion (for single-stage only)
        """
        self.name = name
        self.type = exercise_type
        self.primary_angle = primary_angle
        self.min_rom = min_rom


def display_available_exercises():
    """Show all available exercises from catalog"""
    print("\n" + "="*70)
    print("AVAILABLE EXERCISES")
    print("="*70)
    
    exercises = list(EXERCISE_CATALOG.keys())
    for idx, name in enumerate(exercises, 1):
        cfg = EXERCISE_CATALOG[name]
        exercise_type = cfg.type if hasattr(cfg, 'type') else 'standard'
        print(f"{idx}. {name.upper():20} (Type: {exercise_type})")
    
    print("="*70)
    print(f"\nTotal exercises available: {len(exercises)}")
    print("Or type 'new' to add a new exercise\n")
    
    return exercises


def get_exercise_selection():
    """Get existing exercise from user"""
    exercises = display_available_exercises()
    
    while True:
        user_input = input("Enter exercise name, number, or 'new' to create: ").strip().lower()
        
        # User wants to create new exercise
        if user_input == 'new':
            return None
        
        # Show list again
        if user_input == 'list':
            display_available_exercises()
            continue
        
        # User entered a number
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(exercises):
                print(f"\n✓ Selected: {exercises[idx].upper()}\n")
                return exercises[idx]
            else:
                print(f"✗ Invalid number. Enter 1-{len(exercises)}\n")
                continue
        
        # User entered exercise name
        if user_input in exercises:
            print(f"\n✓ Selected: {user_input.upper()}\n")
            return user_input
        
        # Invalid input
        print(f"✗ Unknown exercise: '{user_input}'")
        print(f"   Type 'list' to see all exercises\n")


def show_available_joints():
    """Display commonly used joints"""
    print("\n" + "="*70)
    print("AVAILABLE JOINTS TO TRACK")
    print("="*70)
    print("Common joints:")
    print("  - right_elbow       (arms bent/extended)")
    print("  - left_elbow")
    print("  - right_shoulder    (arms raise/lower)")
    print("  - left_shoulder")
    print("  - right_knee        (legs bend/extend)")
    print("  - left_knee")
    print("="*70 + "\n")


def get_exercise_type():
    """Get exercise type from user"""
    print("\n" + "="*70)
    print("SELECT EXERCISE TYPE")
    print("="*70)
    print("\n1. SINGLE-STAGE (Push/Pull movements)")
    print("   Examples: pushup, pullup, squat, curl, dip")
    print("   Movement: up ↔ down (2 stages)")
    print("\n2. MULTI-STAGE - BOXING (Punching movements)")
    print("   Examples: jab, cross, hooks")
    print("   Movement: guard → punch → recover")
    print("\n3. MULTI-STAGE - YOGA (Holding poses)")
    print("   Examples: stretching, plank hold, downward dog")
    print("   Movement: entering → hold → exiting")
    print("\n" + "="*70 + "\n")
    
    while True:
        choice = input("Select type (1-3 or name): ").strip().lower()
        
        if choice in ['1', 'single']:
            return 'single'
        elif choice in ['2', 'boxing']:
            return 'boxing'
        elif choice in ['3', 'yoga']:
            return 'yoga'
        else:
            print("✗ Invalid choice. Enter: 1, 2, 3, 'single', 'boxing', or 'yoga'\n")


def get_primary_joint():
    """Get primary joint to track from user"""
    show_available_joints()
    
    common_joints = [
        "right_elbow", "left_elbow",
        "right_shoulder", "left_shoulder",
        "right_knee", "left_knee"
    ]
    
    while True:
        joint = input("Enter primary joint to track: ").strip().lower()
        
        if joint in common_joints:
            print(f"✓ Primary joint: {joint}\n")
            return joint
        elif joint == 'list':
            show_available_joints()
            continue
        else:
            print(f"⚠ '{joint}' not in common list, but will accept it")
            print(f"   (Make sure it's a valid joint name)\n")
            confirm = input("Continue with this joint? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                return joint
            continue


def get_min_rom():
    """Get minimum ROM for single-stage exercises"""
    print("\n" + "="*70)
    print("MINIMUM RANGE OF MOTION (ROM)")
    print("="*70)
    print("This is the minimum angle movement required for a valid rep\n")
    print("Examples:")
    print("  - Pushup: 60-90° (arm bend)")
    print("  - Pullup: 100-150° (arm bend)")
    print("  - Squat: 60-90° (knee bend)")
    print("  - Curl: 80-120° (elbow bend)")
    print("\nDefault: 30° (most flexible)\n")
    
    while True:
        try:
            rom_input = input("Minimum ROM in degrees (default: 30): ").strip()
            
            if not rom_input:
                print("✓ Using default: 30°\n")
                return 30
            
            min_rom = int(rom_input)
            if min_rom > 0 and min_rom < 180:
                print(f"✓ Minimum ROM: {min_rom}°\n")
                return min_rom
            else:
                print("✗ ROM must be between 1-179°\n")
        except ValueError:
            print("✗ Invalid number. Please enter a valid integer\n")


def get_stage_sequence(exercise_type):
    """Get expected stage sequence for multi-stage exercises"""
    print("\n" + "="*70)
    print("EXPECTED REP SEQUENCE")
    print("="*70)
    
    if exercise_type == "boxing":
        print("\nFor boxing, a typical rep sequence is:")
        print("  guard → punch → recover → (back to guard)")
        print("\nDefault: ['guard', 'punch', 'recover']")
        
        sequence_input = input("Enter stages (comma-separated, or press Enter for default): ").strip()
        
        if not sequence_input:
            return ["guard", "punch", "recover"]
        
        stages = [s.strip().lower() for s in sequence_input.split(",")]
        print(f"✓ Stage sequence: {stages}\n")
        return stages
    
    elif exercise_type == "yoga":
        print("\nFor yoga/stretching, a typical rep sequence is:")
        print("  entering → hold → exiting → (return to start)")
        print("\nDefault: ['entering', 'hold', 'exiting']")
        
        sequence_input = input("Enter stages (comma-separated, or press Enter for default): ").strip()
        
        if not sequence_input:
            return ["entering", "hold", "exiting"]
        
        stages = [s.strip().lower() for s in sequence_input.split(",")]
        print(f"✓ Stage sequence: {stages}\n")
        return stages
    
    return []


def create_new_exercise():
    """Create new exercise at runtime"""
    print("\n" + "="*70)
    print("CREATE NEW EXERCISE")
    print("="*70)
    
    # Step 1: Get exercise name
    while True:
        exercise_name = input("\nExercise name (e.g., 'pullup', 'stretching'): ").strip().lower()
        
        if not exercise_name:
            print("✗ Exercise name cannot be empty\n")
            continue
        
        if exercise_name in EXERCISE_CATALOG:
            print(f"✗ Exercise '{exercise_name}' already exists!\n")
            continue
        
        if len(exercise_name) > 30:
            print("✗ Exercise name too long (max 30 characters)\n")
            continue
        
        print(f"✓ Exercise name: {exercise_name}\n")
        break
    
    # Step 2: Get exercise type
    exercise_type = get_exercise_type()
    
    # Step 3: Get primary joint
    primary_angle = get_primary_joint()
    
    # Step 4: Get ROM (only for single-stage)
    min_rom = 30
    if exercise_type == 'single':
        min_rom = get_min_rom()
    
    # Step 5: Get stage sequence (only for multi-stage)
    stage_sequence = None
    if exercise_type in ['boxing', 'yaml']:
        stage_sequence = get_stage_sequence(exercise_type)
    
    # Create config
    cfg = ExerciseConfig(
        name=exercise_name,
        exercise_type=exercise_type,
        primary_angle=primary_angle,
        min_rom=min_rom
    )
    
    # Add to catalog
    EXERCISE_CATALOG[exercise_name] = cfg
    
    # Print summary
    print("\n" + "="*70)
    print("✓ EXERCISE CREATED SUCCESSFULLY")
    print("="*70)
    print(f"Name:              {exercise_name.upper()}")
    print(f"Type:              {exercise_type}")
    print(f"Primary Joint:     {primary_angle}")
    if exercise_type == 'single':
        print(f"Minimum ROM:       {min_rom}°")
    if stage_sequence:
        print(f"Stage Sequence:    {' → '.join(stage_sequence)}")
    print("="*70 + "\n")
    
    return exercise_name, cfg, stage_sequence


def get_training_parameters():
    """Get number of reps to train"""
    print("\n" + "="*70)
    print("TRAINING PARAMETERS")
    print("="*70)
    
    while True:
        try:
            num_reps_input = input("\nNumber of reps to train (default: 10): ").strip()
            
            if not num_reps_input:
                print("✓ Will train 10 reps\n")
                return 10
            
            num_reps = int(num_reps_input)
            if num_reps > 0 and num_reps < 1000:
                print(f"✓ Will train {num_reps} reps\n")
                return num_reps
            else:
                print("✗ Number of reps must be between 1-999\n")
        except ValueError:
            print("✗ Invalid number. Please enter a valid integer\n")


def main():
    """Main training entry point"""
    print("\n" + "="*70)
    print("EXERCISE TRAINER - RUNTIME CONFIGURATION")
    print("="*70)
    
    # Step 1: Get exercise
    exercise = get_exercise_selection()
    
    # If user wants new exercise, create it
    if exercise is None:
        exercise, cfg, stage_sequence = create_new_exercise()
        
        # Update trainer to use custom stage sequence if provided
        if stage_sequence:
            # This will be handled in trainer.py if we pass it
            pass
    
    # Step 2: Validate exercise exists
    if exercise not in EXERCISE_CATALOG:
        print(f"✗ Error: Exercise '{exercise}' not found")
        return
    
    cfg = EXERCISE_CATALOG[exercise]
    
    # Step 3: Get training parameters
    num_reps = get_training_parameters()
    
    # Step 4: Summary and start
    print("="*70)
    print("TRAINING SUMMARY")
    print("="*70)
    print(f"Exercise:          {exercise.upper()}")
    print(f"Type:              {cfg.type}")
    print(f"Primary Joint:     {cfg.primary_angle}")
    print(f"Target Reps:       {num_reps}")
    
    if hasattr(cfg, 'min_rom'):
        print(f"Minimum ROM:       {cfg.min_rom}°")
    
    print("="*70)
    print("\nStarting training session...")
    print("[Make sure video sender is ready]\n")
    
    try:
        trainer = Trainer(cfg, num_reps=num_reps)
        trainer.run()
        
        print("\n" + "="*70)
        print("✓ TRAINING COMPLETE")
        print("="*70)
        print(f"Exercise: {exercise}")
        print(f"Model saved to: baselines/{exercise}_model.json")
        print(f"Motion saved to: baselines/{exercise}_motion.json")
        print("="*70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n✗ Training interrupted by user")
    except Exception as e:
        print(f"\n✗ Error during training: {e}")


if __name__ == "__main__":
    main()
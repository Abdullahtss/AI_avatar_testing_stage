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
import argparse
import json
from config import EXERCISE_CATALOG, Model
from trainer import Trainer
from coach import LiveCoach

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["train","coach"])
    parser.add_argument("--exercise", choices=list(EXERCISE_CATALOG.keys()))
    parser.add_argument("--out")
    parser.add_argument("--model")
    args = parser.parse_args()

    mode = args.mode if  args.mode else 'train'
    exercise = args.exercise if args.exercise else'bicep_curl'
    if mode == "train":
        cfg = EXERCISE_CATALOG[exercise]
        Trainer(cfg).run(args.out)
    else:
        with open(args.model,"r") as f:
            model = Model.from_json(f.read())
        cfg = EXERCISE_CATALOG[model.exercise]
        LiveCoach(model,cfg).run()

if __name__ == "__main__":
    main()

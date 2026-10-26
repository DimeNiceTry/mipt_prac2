import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="ghcr.io/dimenicetry/mipt_prac2")
    parser.add_argument("--tag", default="lab2")
    args = parser.parse_args()
    image = f"{args.image}:{args.tag}"
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["docker", "build", "--pull", "--tag", image, "."], cwd=root, check=True)
    subprocess.run(["docker", "push", image], cwd=root, check=True)


if __name__ == "__main__":
    main()

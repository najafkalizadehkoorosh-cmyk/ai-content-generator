from pathlib import Path
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "data" / "models"
MODEL_PATH = MODEL_DIR / "best.pt"
REPO_ID = "Hexmon/vyra-yolo-ppe-detection"


def main() -> int:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 10_000_000:
        print(f"Model already installed: {MODEL_PATH}")
        return 0
    print("Downloading PPE weights once. This step needs internet.")
    try:
        downloaded = hf_hub_download(
            repo_id=REPO_ID, filename="best.pt", local_dir=str(MODEL_DIR)
        )
        source = Path(downloaded)
        if not MODEL_PATH.exists():
            import shutil
            shutil.copy2(source, MODEL_PATH)
        print(f"Model ready: {MODEL_PATH}")
        print("You can now disconnect the internet and run the app locally.")
        return 0
    except Exception as exc:
        print(f"Download failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

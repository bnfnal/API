from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
from PIL import Image
import shutil
import cv2
import uuid

app = FastAPI()

UPLOAD_DIR = Path("files")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/upload/")
def upload_file(file: UploadFile = File(...)):
    if not is_image(file.filename) and not is_video(file.filename):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением или видео")

    for existing_file in UPLOAD_DIR.glob(f"*_{file.filename}"):
        existing_id = existing_file.stem.split("_")[0]
        return {"id": existing_id, "filename": file.filename, "message": "Файл уже существует"}

    unique_id = str(uuid.uuid4())
    file_name = f"{unique_id}_{file.filename}"
    file_path = UPLOAD_DIR / file_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"id": unique_id, "filename": file.filename, "message": "Файл успешно загружен"}


@app.get("/download/{file_id}")
def download_file(file_id: str, width: int = Query(None), height: int = Query(None)):
    matching_files = list(UPLOAD_DIR.glob(f"{file_id}_*"))
    if not matching_files:
        raise HTTPException(status_code=404, detail="Файл не найден")
    file_path = matching_files[0]

    if width and height:
        if is_image(file_path):
            return create_image_preview(file_path, width, height)
        elif is_video(file_path):
            return create_video_preview(file_path, width, height)

    return FileResponse(file_path, filename=file_path.name)


def is_image(file_name: str) -> bool:
    file_path = Path(file_name)
    return file_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}


def is_video(file_name: str) -> bool:
    file_path = Path(file_name)
    return file_path.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"}


def create_image_preview(file_path: Path, width: int, height: int) -> FileResponse:
    preview_path = file_path.with_name(f"preview_{file_path.stem}.jpg")
    img = cv2.imread(str(file_path))
    if img is None:
        raise HTTPException(status_code=500, detail="Не удалось загрузить изображение для превью")
    img_resized = cv2.resize(img, (width, height))
    cv2.imwrite(str(preview_path), img_resized)
    return FileResponse(preview_path)


def create_video_preview(file_path: Path, width: int, height: int) -> FileResponse:
    preview_path = file_path.with_name(f"preview_{file_path.stem}.jpg")
    cap = cv2.VideoCapture(str(file_path))
    success, frame = cap.read()
    if not success:
        cap.release()
        raise HTTPException(status_code=500, detail="Не удалось создать превью видео")

    frame = cv2.resize(frame, (width, height))
    cv2.imwrite(str(preview_path), frame)
    cap.release()
    return FileResponse(preview_path)
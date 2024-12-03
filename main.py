from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from sqlmodel import Session
from models import MediaFile
from database import get_session
from pathlib import Path
import shutil
import uuid
from datetime import datetime, timedelta
import magic
import cv2
import asyncio

UPLOAD_DIR = Path("files")
UPLOAD_DIR.mkdir(exist_ok=True)

PREVIEW_DIR = Path("previews")
PREVIEW_DIR.mkdir(exist_ok=True)
PREVIEW_LIFETIME = timedelta(hours=1)

app = FastAPI()

async def clean_previews():
    while True:
        now = datetime.now()
        for file in PREVIEW_DIR.iterdir():
            if file.is_file():
                file_mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if now - file_mtime > PREVIEW_LIFETIME:
                    file.unlink()
        await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(clean_previews())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

app = FastAPI(lifespan=lifespan)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_session)):
    extension = Path(file.filename).suffix.lower()
    file_id = str(uuid.uuid4())
    file_name = f"{file_id}{extension}"
    file_path = UPLOAD_DIR / file_name

    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(await file.read(2048))
    await file.seek(0)

    if mime_type.startswith("image/"):
        file_type = "IMG"
    elif mime_type.startswith("video/"):
        file_type = "VID"
    else:
        raise HTTPException(status_code=400, detail="Файл должен быть изображением или видео")


    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = file_path.stat().st_size

    new_file = MediaFile(
        file_id=file_id,
        path=str(file_path),
        type=file_type,
        size=file_size,
        created_at=datetime.now()
    )
    try:
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
    except Exception:
        file_path.unlink()
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка сохранения файла в базу данных")

    return {"id": file_id, "message": "Файл успешно загружен"}


@app.get("/download/{file_id}")
def download_file(file_id: str, width: int = Query(None), height: int = Query(None), db: Session = Depends(get_session)):
    db_file = db.query(MediaFile).filter(MediaFile.file_id == file_id).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="Файл не найден")

    file_path = Path(db_file.path)

    if width and height:
        preview_name = f"preview_{file_id}_{width}_{height}.jpg"
        preview_path = PREVIEW_DIR / preview_name

        if preview_path.exists():
            return FileResponse(preview_path)

        if db_file.type == "IMG":
            return create_image_preview(file_path, preview_path, width, height)
        elif db_file.type == "VID":
            return create_video_preview(file_path, preview_path, width, height)

    return FileResponse(file_path, filename=file_path.name)


def create_image_preview(file_path: Path, preview_path: Path, width: int, height: int) -> FileResponse:
    img = cv2.imread(str(file_path))
    if img is None:
        raise HTTPException(status_code=500, detail="Не удалось загрузить изображение для превью")
    img_resized = cv2.resize(img, (width, height))
    cv2.imwrite(str(preview_path), img_resized)
    return FileResponse(preview_path)


def create_video_preview(file_path: Path, preview_path: Path, width: int, height: int) -> FileResponse:
    cap = cv2.VideoCapture(str(file_path))
    success, frame = cap.read()
    if not success:
        cap.release()
        raise HTTPException(status_code=500, detail="Не удалось создать превью видео")

    frame = cv2.resize(frame, (width, height))
    cv2.imwrite(str(preview_path), frame)
    cap.release()
    return FileResponse(preview_path)

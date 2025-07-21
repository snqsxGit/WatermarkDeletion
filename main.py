import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from moviepy import VideoFileClip

PROGRESS_BAR = None

def select_watermark_area(frame):
    roi = cv2.selectROI("Выделение водяного знака", frame, showCrosshair=True)
    cv2.destroyWindow("Выделение водяного знака")
    return roi

def remove_watermark_with_audio(input_path, output_path):
    global PROGRESS_BAR
    temp_video = "temp_video_no_audio.mp4"

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        messagebox.showerror("Ошибка", "Не удалось открыть видео.")
        return

    fps        = cap.get(cv2.CAP_PROP_FPS)
    total      = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    skip       = int(fps * 3)
    to_proc    = max(0, total - skip)

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    ret, first = cap.read()
    if not ret:
        messagebox.showerror("Ошибка", "Не удалось прочитать первый кадр.")
        cap.release()
        return

    x, y, w, h = select_watermark_area(first)

    PROGRESS_BAR['maximum'] = to_proc
    PROGRESS_BAR['value'] = 0
    PROGRESS_BAR.update()

    out = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    for i in range(to_proc):
        ret, frame = cap.read()
        if not ret:
            break
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        mask[y:y+h, x:x+w] = 255
        cleaned = cv2.inpaint(frame, mask, 3, cv2.INPAINT_TELEA)
        out.write(cleaned)

        if (i+1) % 10 == 0 or i+1 == to_proc:
            PROGRESS_BAR['value'] = i+1
            PROGRESS_BAR.update()
    cap.release()
    out.release()
    print(f"[1] Видео без звука готов: {temp_video}")

    try:
        print("[2] Загружаем temp-видео и оригинал...")
        video_clip    = VideoFileClip(temp_video)
        original_clip = VideoFileClip(input_path)

        if original_clip.audio is None:
            raise AttributeError("Аудио-дорожка отсутствует")

        end_t = max(0, original_clip.duration - 3)
        print(f"[2] Обрезаем аудио до {end_t} сек")
        audio_cut = original_clip.subclipped(0, end_t).audio

        print("[2] Присоединяем аудио и записываем финал...")
        final_clip = video_clip.with_audio(audio_cut)
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        final_clip.close()
        audio_cut.close()
        video_clip.close()
        original_clip.close()

        os.remove(temp_video)
        print(f"[3] Готово! Итоговый файл: {output_path}")
        messagebox.showinfo("Готово", f"Видео сохранено со звуком:\n{output_path}")

    except Exception as e:
        import traceback; traceback.print_exc()
        if os.path.exists(temp_video):
            os.rename(temp_video, output_path)
            messagebox.showwarning(
                "Сохранено без звука",
                f"Аудио не приклеилось ({e}).\nСохранил видео без звука:\n{output_path}"
            )

    finally:
        PROGRESS_BAR['value'] = 0
        PROGRESS_BAR.update()


def choose_video():
    inp = filedialog.askopenfilename(
        title="Выберите видео",
        filetypes=[("Видео","*.mp4 *.avi *.mov *.mkv")]
    )
    if not inp: return
    outp = filedialog.asksaveasfilename(
        title="Сохранить как",
        defaultextension=".mp4",
        filetypes=[("MP4","*.mp4")]
    )
    if not outp: return
    remove_watermark_with_audio(inp, outp)


def main():
    global PROGRESS_BAR
    root = tk.Tk()
    root.title("Удаление водяного знака")
    root.geometry("420x260")
    root.resizable(False, False)

    tk.Label(root,
        text="Удаление статической метки\n(последние 3 сек не сохраняются)",
        font=("Arial",12), justify="center"
    ).pack(pady=15)

    tk.Button(root, text="Выбрать видео", font=("Arial",12),
              command=choose_video).pack(pady=10)

    PROGRESS_BAR = ttk.Progressbar(root, orient="horizontal",
                                   length=350, mode="determinate")
    PROGRESS_BAR.pack(pady=20)

    root.mainloop()


if __name__ == "__main__":
    main()

import os
import yt_dlp

from rich.console import Console
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    SpinnerColumn,
)

console = Console()

DOWNLOAD_DIR = "downloads"


def format_size(size):
    if not size:
        return "نامشخص"

    size_mb = size / (1024 * 1024)

    if size_mb >= 1024:
        return f"{size_mb / 1024:.2f} GB"

    return f"{size_mb:.1f} MB"


def get_video_info(url):
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False)


def show_video_formats(info):
    formats = info.get("formats", [])

    video_formats = [
        f for f in formats
        if f.get("vcodec") != "none"
        and f.get("height")
    ]

    resolutions = sorted(
        set(f["height"] for f in video_formats)
    )

    console.print("\n[bold cyan]========== کیفیت‌های ویدیو ==========[/bold cyan]")

    for height in resolutions:
        matching = [
            f for f in video_formats
            if f["height"] == height
        ]

        best = max(
            matching,
            key=lambda f: f.get("fps") or 0
        )

        console.print(
            f"[green]{height}p[/green] | "
            f"FPS: {best.get('fps', 'N/A')} | "
            f"فرمت: {best.get('ext', 'N/A')} | "
            f"تعداد فرمت‌ها: {len(matching)}"
        )

    console.print("\n[bold cyan]========== فرمت‌های ویدیویی ==========[/bold cyan]")

    for f in video_formats:
        console.print(
            f"ID: {f['format_id']} | "
            f"{f.get('height')}p | "
            f"{f.get('ext')} | "
            f"{f.get('fps', '?')} FPS | "
            f"{format_size(f.get('filesize') or f.get('filesize_approx'))} | "
            f"صدا: {'دارد' if f.get('acodec') != 'none' else 'ندارد'}"
        )

    return resolutions


def show_audio_formats(info):
    formats = info.get("formats", [])

    audio_formats = [
        f for f in formats
        if f.get("acodec") != "none"
        and f.get("vcodec") == "none"
    ]

    console.print("\n[bold cyan]========== فرمت‌های صوتی ==========[/bold cyan]")

    for f in audio_formats:
        console.print(
            f"ID: {f['format_id']} | "
            f"فرمت: {f.get('ext')} | "
            f"Bitrate: {f.get('abr', 'N/A')} kbps | "
            f"حجم: {format_size(f.get('filesize') or f.get('filesize_approx'))}"
        )


def create_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("[progress.percentage]{task.percentage:>5.1f}%"),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


def create_progress_hook(progress):
    tasks = {}

    def hook(data):
        status = data["status"]

        if status == "downloading":
            downloaded = data.get("downloaded_bytes", 0)
            total = (
                data.get("total_bytes")
                or data.get("total_bytes_estimate")
            )

            # شناسه فایل دانلودی
            filename = data.get("filename", "download")

            if filename not in tasks:
                task_id = progress.add_task(
                    os.path.basename(filename),
                    total=total or None
                )
                tasks[filename] = task_id

            task_id = tasks[filename]

            progress.update(
                task_id,
                completed=downloaded,
                total=total if total else None
            )

        elif status == "finished":
            filename = data.get("filename", "download")
            if filename in tasks:
                task_id = tasks[filename]
                progress.update(
                    task_id,
                    completed=progress.tasks[task_id].total or 0
                )
                progress.update(
                    task_id,
                    description=f"[green]Downloaded: {os.path.basename(filename)}"
                )

    return hook


def download_video(url, height):
    progress = create_progress()

    options = {
        "format": (
            f"bestvideo[height<={height}]"
            "+bestaudio/"
            f"best[height<={height}]"
        ),
        "outtmpl": os.path.join(
            DOWNLOAD_DIR,
            "%(title)s.%(ext)s"
        ),
        "progress_hooks": [create_progress_hook(progress)],
        "noplaylist": True,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    with progress:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])


def download_audio(url, audio_type):
    progress = create_progress()

    options = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(
            DOWNLOAD_DIR,
            "%(title)s.%(ext)s"
        ),
        "progress_hooks": [create_progress_hook(progress)],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    if audio_type == "mp3":
        options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    with progress:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])


def main():

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    console.print(
        "\n[bold magenta]========== YouTube Downloader ==========[/bold magenta]\n"
    )

    url = input("لینک ویدیو را وارد کن: ").strip()

    if not url:
        console.print("[red]لینک وارد نشده است.[/red]")
        return

    try:
        console.print("\n[yellow]در حال دریافت اطلاعات ویدیو...[/yellow]")

        info = get_video_info(url)

        console.print(f"\n[bold]عنوان:[/bold] {info.get('title')}")
        console.print(
            f"[bold]مدت زمان:[/bold] {info.get('duration')} ثانیه"
        )

        resolutions = show_video_formats(info)
        show_audio_formats(info)

        console.print("\n[bold cyan]========== انتخاب حالت دانلود ==========[/bold cyan]")
        console.print("1. دانلود ویدیو")
        console.print("2. دانلود فقط صدا")

        choice = input("\nانتخاب تو: ").strip()

        if choice == "1":

            if not resolutions:
                console.print("[red]کیفیت ویدیویی پیدا نشد.[/red]")
                return

            console.print(f"\nکیفیت‌های موجود: {resolutions}")

            height_input = input(
                "کیفیت موردنظرت (مثلاً 1080): "
            ).strip()

            if not height_input.isdigit():
                console.print("[red]کیفیت نامعتبر است.[/red]")
                return

            height = int(height_input)

            if height not in resolutions:
                console.print("[red]این کیفیت موجود نیست.[/red]")
                return

            console.print(
                f"\n[bold green]شروع دانلود با حداکثر کیفیت {height}p[/bold green]\n"
            )

            download_video(url, height)

        elif choice == "2":

            console.print("\n1. فرمت اصلی صدا")
            console.print("2. تبدیل به MP3")

            audio_choice = input("انتخاب تو: ").strip()

            if audio_choice == "1":
                download_audio(url, "original")

            elif audio_choice == "2":
                download_audio(url, "mp3")

            else:
                console.print("[red]انتخاب نامعتبر است.[/red]")
                return

        else:
            console.print("[red]انتخاب نامعتبر است.[/red]")
            return
        console.print("\n[bold green]✓ عملیات با موفقیت انجام شد![/bold green]")
        console.print(
            f"مسیر ذخیره‌سازی: {os.path.abspath(DOWNLOAD_DIR)}"
        )

    except Exception as error:
        console.print(f"\n[bold red]خطا:[/bold red] {error}")


if __name__ == "__main__":
    main()
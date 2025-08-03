"""
ファイル監視システム
ホットリロード機能のためのファイル変更検知
"""

import os
import time
from pathlib import Path
from typing import List, Set, Callable, Optional, Any, TYPE_CHECKING
from threading import Thread

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver as ObserverType

# Define Observer as a variable that can hold the class or be None.
Observer = None

try:
    # Import the class under an alias to avoid name conflict
    from watchdog.observers import Observer as WatchdogObserver
    from watchdog.events import FileSystemEventHandler, FileSystemEvent

    # Assign the imported class to our variable
    Observer = WatchdogObserver
    HAS_WATCHDOG = True

except ImportError:
    HAS_WATCHDOG = False

    # ダミークラスを定義
    class FileSystemEventHandler(object):  # type: ignore
        pass

    class FileSystemEvent(object):  # type: ignore
        def __init__(self, src_path: str) -> None:
            self.src_path = src_path
            self.is_directory: Optional[bool] = None

    # 'Observer' is already None if the import fails, so no assignment is needed here.


class ReloadHandler(FileSystemEventHandler):
    """ファイル変更を監視するハンドラー"""

    def __init__(
        self,
        restart_callback: Callable[[], None],
        watch_extensions: Optional[Set[str]] = None,
        ignore_patterns: Optional[Set[str]] = None,
        debounce_delay: float = 1.0,
    ) -> None:
        self.restart_callback = restart_callback
        self.watch_extensions = watch_extensions or {".py"}
        self.ignore_patterns = ignore_patterns or {
            "__pycache__",
            ".git",
            ".mypy_cache",
            ".pytest_cache",
        }
        self.debounce_delay = debounce_delay
        self.last_reload = 0.0

    def should_reload(self, file_path: str) -> bool:
        """ファイルがリロード対象かどうかを判定"""
        path = Path(file_path)

        # 拡張子チェック
        if path.suffix not in self.watch_extensions:
            return False

        # 無視パターンチェック
        for ignore_pattern in self.ignore_patterns:
            if ignore_pattern in str(path):
                return False

        return True

    def _dispatch_reload(self, path: Any) -> None:
        """Helper to decode path and trigger reload."""
        path_str = os.fsdecode(path)

        if not self.should_reload(path_str):
            return

        # デバウンス処理
        now = time.time()
        if now - self.last_reload < self.debounce_delay:
            return

        print(f"🔄 ファイル変更を検知: {path_str}")
        print("🔄 サーバーを再起動中...")

        self.last_reload = now
        self.restart_callback()

    def on_modified(self, event: FileSystemEvent) -> None:
        """ファイル変更時の処理"""
        if not event.is_directory:
            self._dispatch_reload(event.src_path)

    def on_created(self, event: FileSystemEvent) -> None:
        """ファイル作成時の処理"""
        if not event.is_directory:
            self._dispatch_reload(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        """ファイル移動時の処理"""
        if not event.is_directory and hasattr(event, "dest_path"):
            self._dispatch_reload(event.dest_path)


class FileWatcher:
    """ファイル監視システム"""

    def __init__(
        self,
        restart_callback: Callable[[], None],
        watch_dirs: Optional[List[str]] = None,
        watch_extensions: Optional[Set[str]] = None,
        ignore_patterns: Optional[Set[str]] = None,
        debounce_delay: float = 1.0,
    ) -> None:
        self.restart_callback = restart_callback
        self.watch_dirs = watch_dirs or ["."]
        self.watch_extensions = watch_extensions or {".py"}
        self.ignore_patterns = ignore_patterns or {
            "__pycache__",
            ".git",
            ".mypy_cache",
            ".pytest_cache",
        }
        self.debounce_delay = debounce_delay

        self.observer: Optional["ObserverType"] = None
        self.is_watching = False

    def start(self) -> bool:
        """ファイル監視を開始"""
        if not HAS_WATCHDOG or Observer is None:
            print("⚠️ watchdog ライブラリがインストールされていません")
            print("   ホットリロード機能を使用するには以下を実行してください:")
            print("   pip install 'lambapi[dev]' または pip install watchdog")
            return False

        if self.is_watching:
            return True

        try:
            self.observer = Observer()
            handler = ReloadHandler(
                restart_callback=self.restart_callback,
                watch_extensions=self.watch_extensions,
                ignore_patterns=self.ignore_patterns,
                debounce_delay=self.debounce_delay,
            )

            for watch_dir in self.watch_dirs:
                if os.path.exists(watch_dir):
                    self.observer.schedule(handler, watch_dir, recursive=True)
                    print(f"📁 監視開始: {os.path.abspath(watch_dir)}")

            self.observer.start()
            self.is_watching = True
            print(f"👀 ホットリロード機能が有効です (拡張子: {', '.join(self.watch_extensions)})")
            return True

        except Exception as e:
            print(f"❌ ファイル監視の開始に失敗しました: {e}")
            return False

    def stop(self) -> None:
        """ファイル監視を停止"""
        if self.is_watching:
            if self.observer is None:
                raise RuntimeError("Observer must be initialized if watching is active")
            self.observer.stop()
            self.observer.join()
            self.is_watching = False
            print("⏹️ ファイル監視を停止しました")

    def __enter__(self) -> "FileWatcher":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()


def get_watch_paths(app_path: str) -> List[str]:
    """アプリケーションファイルから監視対象パスを自動判定"""
    watch_paths = []

    # アプリケーションファイルのディレクトリ
    app_dir = os.path.dirname(os.path.abspath(app_path))
    if app_dir:
        watch_paths.append(app_dir)

    # カレントディレクトリ
    current_dir = os.getcwd()
    if current_dir not in watch_paths:
        watch_paths.append(current_dir)

    return watch_paths


class PollingWatcher:
    """watchdog が利用できない場合のフォールバック監視システム"""

    def __init__(
        self,
        restart_callback: Callable[[], None],
        watch_dirs: Optional[List[str]] = None,
        watch_extensions: Optional[Set[str]] = None,
        ignore_patterns: Optional[Set[str]] = None,
        poll_interval: float = 2.0,
    ) -> None:
        self.restart_callback = restart_callback
        self.watch_dirs = watch_dirs or ["."]
        self.watch_extensions = watch_extensions or {".py"}
        self.ignore_patterns = ignore_patterns or {
            "__pycache__",
            ".git",
            ".mypy_cache",
            ".pytest_cache",
        }
        self.poll_interval = poll_interval

        self.file_mtimes: dict[str, float] = {}
        self.is_watching = False
        self.watch_thread: Optional[Thread] = None

    def _scan_files(self) -> None:
        """ファイルをスキャンして変更を検知"""
        while self.is_watching:
            try:
                for watch_dir in self.watch_dirs:
                    if not os.path.exists(watch_dir):
                        continue

                    for root, dirs, files in os.walk(watch_dir):
                        # 無視ディレクトリをスキップ
                        dirs[:] = [
                            d
                            for d in dirs
                            if not any(pattern in d for pattern in self.ignore_patterns)
                        ]

                        for file in files:
                            file_path = os.path.join(root, file)
                            path = Path(file_path)

                            # 拡張子と無視パターンをチェック
                            if path.suffix not in self.watch_extensions:
                                continue
                            if any(pattern in str(path) for pattern in self.ignore_patterns):
                                continue

                            try:
                                current_mtime = os.path.getmtime(file_path)

                                if file_path in self.file_mtimes:
                                    if current_mtime > self.file_mtimes[file_path]:
                                        print(f"🔄 ファイル変更を検知: {file_path}")
                                        print("🔄 サーバーを再起動中...")
                                        self.file_mtimes[file_path] = current_mtime
                                        self.restart_callback()
                                        time.sleep(1.0)  # デバウンス
                                else:
                                    self.file_mtimes[file_path] = current_mtime
                            except OSError:
                                # ファイルアクセスエラーは無視
                                pass

                time.sleep(self.poll_interval)
            except Exception as e:
                print(f"⚠️ ファイル監視エラー: {e}")
                time.sleep(self.poll_interval)

    def start(self) -> bool:
        """ポーリング監視を開始"""
        if self.is_watching:
            return True

        self.is_watching = True
        self.watch_thread = Thread(target=self._scan_files, daemon=True)
        self.watch_thread.start()

        print(f"📁 ポーリング監視開始: {', '.join(self.watch_dirs)}")
        print(f"👀 ホットリロード機能が有効です (拡張子: {', '.join(self.watch_extensions)})")
        print("   ⚠️ より効率的な監視のため watchdog のインストールを推奨します")
        return True

    def stop(self) -> None:
        """ポーリング監視を停止"""
        if self.is_watching:
            self.is_watching = False
            if self.watch_thread:
                self.watch_thread.join(timeout=1.0)
            print("⏹️ ファイル監視を停止しました")

    def __enter__(self) -> "PollingWatcher":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

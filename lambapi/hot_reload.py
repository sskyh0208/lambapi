"""
ホットリロード機能
ファイル変更を検知してサーバーを自動再起動
"""

import os
import sys
import signal
import threading
import subprocess  # nosec B404
import time
import socket
from typing import List, Set, Optional, Union, Any
from .file_watcher import FileWatcher, PollingWatcher, get_watch_paths, HAS_WATCHDOG


class HotReloadServer:
    """ホットリロード機能付きサーバー"""

    def __init__(
        self,
        app_path: str,
        host: str = "localhost",
        port: int = 8000,
        debug: bool = False,
        reload: bool = True,
        watch_dirs: Optional[List[str]] = None,
        watch_extensions: Optional[Set[str]] = None,
        ignore_patterns: Optional[Set[str]] = None,
        reload_delay: float = 1.0,
        verbose: bool = False,
    ) -> None:
        self.app_path = app_path
        self.host = host
        self.port = port
        self.debug = debug
        self.reload = reload
        self.watch_dirs = watch_dirs or get_watch_paths(app_path)
        self.watch_extensions = watch_extensions or {".py"}
        self.ignore_patterns = ignore_patterns or {
            "__pycache__",
            ".git",
            ".mypy_cache",
            ".pytest_cache",
        }
        self.reload_delay = reload_delay
        self.verbose = verbose

        self.server_process: Optional[subprocess.Popen] = None
        self.watcher: Optional[Union[FileWatcher, PollingWatcher]] = None
        self.is_running = False
        self.restart_requested = False
        self.restart_lock = threading.Lock()
        self.restart_count = 0
        self.max_restart_attempts = 5

    def _get_server_command(self) -> List[str]:
        """サーバー起動コマンドを生成"""
        # モジュール重複インポート警告を回避するため、専用ランチャーを使用
        launcher_path = os.path.join(os.path.dirname(__file__), "server_launcher.py")
        cmd = [
            sys.executable,
            launcher_path,
            self.app_path,
            "--host",
            self.host,
            "--port",
            str(self.port),
        ]

        if self.debug:
            cmd.append("--debug")

        return cmd

    def _start_server_process(self) -> bool:
        """サーバープロセスを開始"""
        try:
            cmd = self._get_server_command()
            if self.verbose:
                print(f"🔧 サーバー起動コマンド: {' '.join(cmd)}")

            self.server_process = subprocess.Popen(  # nosec B603
                cmd,
                stdout=None,  # サーバーのログを直接表示
                stderr=None,  # サーバーのログを直接表示
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            if self.verbose:
                print(f"🚀 サーバープロセス開始 (PID: {self.server_process.pid})")

            return True
        except Exception as e:
            print(f"❌ サーバー起動エラー: {e}")
            return False

    def _stop_server_process(self) -> None:
        """サーバープロセスを停止"""
        if self.server_process is None:
            return

        try:
            if self.verbose:
                print(f"⏹️ サーバープロセス停止中 (PID: {self.server_process.pid})")

            # Graceful shutdown
            self.server_process.terminate()

            try:
                self.server_process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                if self.verbose:
                    print("⚠️ Graceful shutdown がタイムアウト、強制終了します")
                self.server_process.kill()
                self.server_process.wait()

            if self.verbose:
                print("✅ サーバープロセス停止完了")

        except Exception as e:
            if self.verbose:
                print(f"⚠️ サーバープロセス停止エラー: {e}")
        finally:
            self.server_process = None
            # ポート解放を待機
            self._wait_for_port_release()

    def _wait_for_port_release(self) -> None:
        """ポートが解放されるまで待機（ローカル開発用に継続的に待機）"""
        attempt = 0
        wait_time = 0.1  # 初期待機時間を短く
        max_wait_time = 2.0  # 最大待機時間
        backoff_factor = 1.2  # 指数バックオフ係数

        while True:
            try:
                # ポートが使用可能かテスト
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind((self.host, self.port))
                sock.close()
                if self.verbose and attempt > 0:
                    print(f"✅ ポート {self.port} が解放されました (試行回数: {attempt + 1})")
                return
            except OSError:
                attempt += 1
                if self.verbose and attempt == 1:
                    print(f"⏳ ポート {self.port} の解放を待機中...")
                elif self.verbose and attempt % 10 == 0:  # 10 回ごとに進捗表示
                    print(f"⏳ ポート解放待機中... (試行回数: {attempt})")

                time.sleep(wait_time)
                # 指数バックオフで待機時間を徐々に延長（上限あり）
                wait_time = min(wait_time * backoff_factor, max_wait_time)

    def _restart_server(self) -> None:
        """サーバーを再起動"""
        with self.restart_lock:
            if self.restart_requested:
                return  # 既に再起動リクエスト中

            self.restart_requested = True
            self.restart_count += 1

            try:
                if self.verbose:
                    print("🔄 サーバー再起動開始...")

                self._stop_server_process()

                if self._start_server_process():
                    if self.verbose:
                        print("✅ サーバー再起動完了")
                else:
                    print("❌ サーバー再起動に失敗しました")

            finally:
                self.restart_requested = False

    def _setup_signal_handlers(self) -> None:
        """シグナルハンドラーの設定"""

        def signal_handler(signum: int, frame: Any) -> None:
            print("\n👋 ホットリロードサーバーを終了中...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def start(self) -> bool:
        """ホットリロードサーバーを開始"""
        if self.is_running:
            return True

        # シグナルハンドラーの設定
        self._setup_signal_handlers()

        # 初回サーバー起動
        if not self._start_server_process():
            return False

        self.is_running = True

        # ホットリロード機能の開始（reload=True の場合のみ）
        if self.reload:
            try:
                # watchdog が利用可能な場合はそれを使用、そうでなければポーリング
                if HAS_WATCHDOG:
                    self.watcher = FileWatcher(
                        restart_callback=self._restart_server,
                        watch_dirs=self.watch_dirs,
                        watch_extensions=self.watch_extensions,
                        ignore_patterns=self.ignore_patterns,
                        debounce_delay=self.reload_delay,
                    )
                else:
                    self.watcher = PollingWatcher(
                        restart_callback=self._restart_server,
                        watch_dirs=self.watch_dirs,
                        watch_extensions=self.watch_extensions,
                        ignore_patterns=self.ignore_patterns,
                        poll_interval=max(2.0, self.reload_delay),
                    )

                if self.watcher and hasattr(self.watcher, "start") and not self.watcher.start():
                    print("⚠️ ファイル監視の開始に失敗しました。ホットリロード機能は無効です。")

            except Exception as e:
                print(f"⚠️ ホットリロード機能の初期化に失敗しました: {e}")
                print("   ホットリロード機能なしでサーバーを継続します。")
        else:
            print("ℹ️ ホットリロード機能は無効です")

        return True

    def stop(self) -> None:
        """ホットリロードサーバーを停止"""
        if not self.is_running:
            return

        self.is_running = False

        # ファイル監視を停止
        if self.watcher:
            self.watcher.stop()
            self.watcher = None

        # サーバープロセスを停止
        self._stop_server_process()

    def run(self) -> None:
        """ホットリロードサーバーを実行（ブロッキング）"""
        if not self.start():
            print("❌ サーバーの起動に失敗しました")
            return

        try:
            # メインループ（サーバープロセスが停止してもファイル監視は継続）
            while self.is_running:
                try:
                    # サーバープロセスが存在する場合のみ状態を監視
                    if self.server_process:
                        return_code = self.server_process.poll()
                    else:
                        return_code = None
                    if return_code is not None:
                        if self.verbose:
                            print(f"⚠️ サーバープロセスが終了しました (終了コード: {return_code})")

                        # 異常終了の場合の処理
                        if return_code != 0 and self.is_running:
                            if self.verbose:
                                print(
                                    "⚠️ サーバーが異常終了しました（構文エラーなどの可能性があります）"
                                )
                                print(
                                    "📁 ファイル監視は継続中です。ファイルを修正すると自動で再起動を試行します。"
                                )

                            # サーバープロセスをクリアして監視を継続
                            self.server_process = None
                            # 再起動カウントをリセット（ファイル変更による再起動は別カウント）
                            self.restart_count = 0

                    # CPU 使用率を抑制
                    threading.Event().wait(0.5)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    if self.verbose:
                        print(f"⚠️ メインループエラー: {e}")
                    break

        finally:
            self.stop()

    def __enter__(self) -> "HotReloadServer":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()


def serve_with_reload(
    app_path: str,
    host: str = "localhost",
    port: int = 8000,
    debug: bool = False,
    reload: bool = True,
    watch_dirs: Optional[List[str]] = None,
    watch_extensions: Optional[Set[str]] = None,
    ignore_patterns: Optional[Set[str]] = None,
    reload_delay: float = 1.0,
    verbose: bool = False,
) -> None:
    """ホットリロード機能付きでサーバーを起動"""

    # 実行環境チェック
    if reload and "LAMBDA_TASK_ROOT" in os.environ:
        print("⚠️ Lambda 環境ではホットリロード機能を無効化します")
        reload = False

    server = HotReloadServer(
        app_path=app_path,
        host=host,
        port=port,
        debug=debug,
        reload=reload,
        watch_dirs=watch_dirs,
        watch_extensions=watch_extensions,
        ignore_patterns=ignore_patterns,
        reload_delay=reload_delay,
        verbose=verbose,
    )

    try:
        server.run()
    except KeyboardInterrupt:
        print("\n👋 サーバーを停止しました")
    except Exception as e:
        print(f"❌ サーバーエラー: {e}")
        sys.exit(1)

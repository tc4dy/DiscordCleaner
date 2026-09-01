import asyncio
import aiohttp
import json
import sys
import time
import os
import argparse
import signal
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

RESET = "\033[0m"
BRIGHT = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"

class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    SUCCESS = 2
    WARNING = 3
    ERROR = 4
    RATE = 5
    PROGRESS = 6

@dataclass
class Config:
    token: str = ""
    author_id: str = ""
    channel_id: str = ""
    guild_id: Optional[str] = None
    after_message_id: Optional[str] = None
    before_message_id: Optional[str] = None
    content_filter: Optional[str] = None
    has_link: bool = False
    has_file: bool = False
    include_nsfw: bool = False
    batch_size: int = 3
    delete_delay: int = 1000
    search_delay: int = 2000
    max_retries: int = 10
    max_consecutive_failures: int = 20
    rate_limit_cooldown: int = 60
    verbose: bool = False
    dry_run: bool = False

@dataclass
class Stats:
    deleted: int = 0
    failed: int = 0
    skipped: int = 0
    total_checked: int = 0
    rate_limits: int = 0
    api_calls: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    last_success: float = field(default_factory=time.time)
    consecutive_failures: int = 0
    deleted_ids: Set[str] = field(default_factory=set)

class Logger:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.log_level = LogLevel.INFO

    def _format_time(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _log(self, level: LogLevel, msg: str, color: str = WHITE, prefix: str = ""):
        if level.value < self.log_level.value:
            return
        timestamp = self._format_time()
        colored_prefix = f"{CYAN}[{timestamp}]{RESET}"
        colored_msg = f"{color}{prefix} {msg}{RESET}"
        print(f"{colored_prefix} {colored_msg}")

    def debug(self, msg: str):
        if self.verbose:
            self._log(LogLevel.DEBUG, msg, CYAN, "[DBG]")

    def info(self, msg: str):
        self._log(LogLevel.INFO, msg, BLUE, "[INF]")

    def success(self, msg: str):
        self._log(LogLevel.SUCCESS, msg, GREEN, "[OK]")

    def warning(self, msg: str):
        self._log(LogLevel.WARNING, msg, YELLOW, "[!]")

    def error(self, msg: str):
        self._log(LogLevel.ERROR, msg, RED, "[ERR]")

    def rate(self, msg: str):
        self._log(LogLevel.RATE, msg, MAGENTA, "[RATE]")

    def progress(self, msg: str):
        self._log(LogLevel.PROGRESS, msg, CYAN, "[PRG]")

    def batch(self, msg: str):
        self._log(LogLevel.INFO, msg, YELLOW, "[BATCH]")

    def delete(self, msg: str):
        self._log(LogLevel.SUCCESS, msg, GREEN, "[DEL]")

    def skip(self, msg: str):
        self._log(LogLevel.INFO, msg, DIM, "[SKIP]")

    def prompt(self, msg: str):
        print(f"{MAGENTA}[?] {msg}{RESET}")

class DiscordCleaner:
    def __init__(self, config: Config):
        self.config = config
        self.stats = Stats()
        self.logger = Logger(config.verbose)
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = True
        self.paused = False
        self.base_url = "https://discord.com/api/v9"
        self.headers = {
            "Authorization": config.token,
            "Content-Type": "application/json"
        }
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.logger.warning("Interrupt received, stopping gracefully...")
        self.running = False

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=300, connect=30)
        self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_time_str(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def _get_stats(self) -> Dict[str, Any]:
        elapsed = time.time() - self.stats.start_time
        speed = self.stats.deleted / elapsed if self.stats.deleted > 0 else 0
        return {
            "elapsed": elapsed,
            "speed": speed,
            "deleted": self.stats.deleted,
            "failed": self.stats.failed,
            "skipped": self.stats.skipped,
            "total": self.stats.total_checked,
            "rate_limits": self.stats.rate_limits,
            "errors": self.stats.errors,
            "api_calls": self.stats.api_calls
        }

    def _print_stats(self):
        stats = self._get_stats()
        time_str = self._get_time_str(stats["elapsed"])
        self.logger.progress(
            f"[+] {stats['deleted']} deleted | [-] {stats['failed']} failed | "
            f"[*] {stats['skipped']} skipped | [R] {stats['rate_limits']} rate limits | "
            f"[S] {stats['speed']:.2f} msg/s | [T] {time_str}"
        )

    async def _safe_request(self, method: str, endpoint: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        url = f"{self.base_url}{endpoint}"
        retry_count = 0

        while retry_count < self.config.max_retries and self.running:
            try:
                self.stats.api_calls += 1
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 429:
                        data = await response.json()
                        wait_time = data.get("retry_after", 10) * 1000
                        wait_time = max(wait_time, 10000)
                        wait_time += 5000 if method == "DELETE" else 10000
                        self.stats.rate_limits += 1
                        self.logger.rate(f"Rate limited! Waiting {wait_time/1000:.1f}s (Total: {self.stats.rate_limits})")

                        if self.stats.rate_limits > 5:
                            self.config.delete_delay = min(self.config.delete_delay + 1000, 10000)
                            self.config.search_delay = min(self.config.search_delay + 1000, 10000)
                            self.logger.rate(f"Adjusted delays: {self.config.delete_delay}ms delete, {self.config.search_delay}ms search")

                        await asyncio.sleep(wait_time / 1000)
                        if self.stats.rate_limits > 10:
                            self.logger.warning("Too many rate limits, pausing for 60 seconds...")
                            await asyncio.sleep(60)
                            self.stats.rate_limits = 0
                        continue

                    if response.status in (401, 403):
                        self.logger.error(f"Authentication error ({response.status})")
                        self.running = False
                        return None

                    if response.status == 404:
                        return response

                    if not response.ok and retry_count < self.config.max_retries:
                        self.logger.warning(f"Request failed ({response.status}), retrying {retry_count + 1}/{self.config.max_retries}")
                        await asyncio.sleep(2 * (retry_count + 1))
                        retry_count += 1
                        continue

                    if not response.ok:
                        self.logger.error(f"Request failed permanently: {response.status} {response.reason}")
                        self.stats.errors += 1
                        return response

                    self.stats.consecutive_failures = 0
                    self.stats.last_success = time.time()
                    return response

            except asyncio.TimeoutError:
                self.stats.errors += 1
                self.stats.consecutive_failures += 1
                self.logger.error(f"Timeout error (attempt {retry_count + 1})")
                if self.stats.consecutive_failures > self.config.max_consecutive_failures:
                    self.logger.error("Too many consecutive failures, pausing for 30 seconds...")
                    await asyncio.sleep(30)
                    self.stats.consecutive_failures = 0

            except aiohttp.ClientError as e:
                self.stats.errors += 1
                self.stats.consecutive_failures += 1
                self.logger.error(f"Client error: {str(e)}")

            except Exception as e:
                self.stats.errors += 1
                self.logger.error(f"Unexpected error: {str(e)}")

            if retry_count < self.config.max_retries:
                await asyncio.sleep(5 * (retry_count + 1))
                retry_count += 1

        return None

    async def _get_messages(self, before_id: Optional[str] = None) -> Optional[List[Dict]]:
        endpoint = f"/channels/{self.config.channel_id}/messages?limit=100"
        if before_id:
            endpoint += f"&before={before_id}"

        response = await self._safe_request("GET", endpoint)
        if not response or not response.ok:
            return None

        try:
            return await response.json()
        except:
            return None

    async def _delete_message(self, message_id: str) -> bool:
        if self.config.dry_run:
            self.logger.info(f"[DRY RUN] Would delete message {message_id}")
            return True

        endpoint = f"/channels/{self.config.channel_id}/messages/{message_id}"
        response = await self._safe_request("DELETE", endpoint)

        if response is None:
            return False

        if response.status == 404:
            return True

        return response.ok

    def _should_delete_message(self, message: Dict) -> bool:
        if message["author"]["id"] != self.config.author_id:
            return False

        if self.config.content_filter:
            content = message.get("content", "")
            if self.config.content_filter not in content:
                return False

        if self.config.has_link and not any(
            word.startswith(("http://", "https://"))
            for word in message.get("content", "").split()
        ):
            return False

        if self.config.has_file and not message.get("attachments"):
            return False

        return True

    async def run(self):
        self.logger.info("[+] Starting Discord Cleaner | by @tc4dy")
        self.logger.info(f"[T] Target user: {self.config.author_id}")
        self.logger.info(f"[C] Target channel: {self.config.channel_id}")
        if self.config.dry_run:
            self.logger.warning("[!] DRY RUN MODE - No messages will be deleted")
        self.logger.info("[S] Press Ctrl+C to stop gracefully")

        before_id = self.config.before_message_id

        while self.running:
            try:
                if self.paused:
                    await asyncio.sleep(1)
                    continue

                messages = await self._get_messages(before_id)

                if messages is None:
                    if not self.running:
                        break
                    self.logger.error("Failed to fetch messages, waiting 10 seconds...")
                    await asyncio.sleep(10)
                    continue

                if not messages:
                    self.logger.success("[+] All messages scanned!")
                    break

                filtered_messages = [
                    msg for msg in messages
                    if self._should_delete_message(msg)
                    and msg["id"] not in self.stats.deleted_ids
                ]

                self.stats.total_checked += len(messages)
                self.logger.info(
                    f"[C] Checked {len(messages)} messages, found {len(filtered_messages)} to delete "
                    f"(Total checked: {self.stats.total_checked})"
                )

                if not filtered_messages:
                    if messages:
                        before_id = messages[-1]["id"]
                    await asyncio.sleep(1)
                    continue

                for i in range(0, len(filtered_messages), self.config.batch_size):
                    if not self.running:
                        break

                    batch = filtered_messages[i:i + self.config.batch_size]
                    batch_num = i // self.config.batch_size + 1
                    total_batches = (len(filtered_messages) + self.config.batch_size - 1) // self.config.batch_size
                    self.logger.batch(
                        f"[B] Processing {len(batch)} messages "
                        f"(Batch {batch_num}/{total_batches})"
                    )

                    deleted_in_batch = 0
                    failed_in_batch = 0

                    for message in batch:
                        if not self.running:
                            break

                        if self.paused:
                            await asyncio.sleep(1)
                            continue

                        if message["id"] in self.stats.deleted_ids:
                            self.logger.skip(f"[*] Message already deleted: {message['id']}")
                            self.stats.skipped += 1
                            continue

                        success = await self._delete_message(message["id"])

                        if success:
                            self.stats.deleted += 1
                            deleted_in_batch += 1
                            self.stats.deleted_ids.add(message["id"])
                            content = message.get("content", "")[:30]
                            if content:
                                content += "..." if len(message.get("content", "")) > 30 else ""
                            else:
                                content = "[empty/attachment]"
                            self.logger.delete(
                                f"[+] [{self.stats.deleted}] Deleted: {content}"
                            )
                            self.stats.last_success = time.time()
                        else:
                            self.stats.failed += 1
                            failed_in_batch += 1
                            self.logger.error(f"[-] Failed to delete: {message['id']}")

                        await asyncio.sleep(self.config.delete_delay / 1000)

                    if deleted_in_batch > 5:
                        self.logger.warning("[!] Deleting too fast, slowing down...")
                        await asyncio.sleep(5)

                    if failed_in_batch > self.config.batch_size:
                        self.logger.error("[!] Too many failures in batch, pausing...")
                        await asyncio.sleep(10)

                    if self.stats.errors > 50:
                        self.logger.error(f"[!] Too many errors ({self.stats.errors}), pausing for 30 seconds...")
                        await asyncio.sleep(30)
                        self.stats.errors = 0

                    if self.stats.deleted % 10 == 0 and self.stats.deleted > 0:
                        self._print_stats()

                if messages:
                    before_id = messages[-1]["id"]
                    self.logger.info(f"[W] Loading next batch in {self.config.search_delay/1000} seconds...")
                    await asyncio.sleep(self.config.search_delay / 1000)

                if time.time() - self.stats.last_success > 60:
                    self.logger.warning("[!] No successful deletions in 60 seconds, checking connection...")
                    self.stats.consecutive_failures += 1
                    if self.stats.consecutive_failures > self.config.max_consecutive_failures:
                        self.logger.error("[!] Too many consecutive failures, pausing...")
                        await asyncio.sleep(30)
                        self.stats.consecutive_failures = 0

            except Exception as e:
                self.stats.errors += 1
                self.logger.error(f"[!] Critical error: {str(e)}")
                self.logger.warning("[!] Restarting loop in 10 seconds...")
                await asyncio.sleep(10)
                if self.stats.errors > 100:
                    self.logger.error("[!] Too many errors, forcing pause for 60 seconds...")
                    await asyncio.sleep(60)
                    self.stats.errors = 0

        elapsed = time.time() - self.stats.start_time
        time_str = self._get_time_str(elapsed)

        self.logger.success("[+] " + "=" * 50)
        self.logger.success("[+] PROCESS COMPLETED")
        self.logger.success("[+] " + "=" * 50)
        self.logger.success(f"[+] Deleted: {self.stats.deleted} messages")
        self.logger.error(f"[-] Failed: {self.stats.failed} messages")
        self.logger.info(f"[*] Skipped: {self.stats.skipped} messages")
        self.logger.info(f"[C] Total checked: {self.stats.total_checked} messages")
        self.logger.info(f"[R] Rate limits: {self.stats.rate_limits} times")
        self.logger.info(f"[E] Total errors: {self.stats.errors}")
        self.logger.info(f"[A] API calls: {self.stats.api_calls}")
        self.logger.info(f"[T] Time elapsed: {time_str}")
        if self.stats.deleted > 0:
            speed = self.stats.deleted / elapsed
            self.logger.success(f"[S] Average speed: {speed:.2f} messages/second")
        self.logger.success("[+] " + "=" * 50)

class InputValidator:
    @staticmethod
    def validate_token(token: str) -> bool:
        return len(token) >= 10 and "." in token

    @staticmethod
    def validate_id(id_str: str) -> bool:
        return len(id_str) >= 10 and id_str.isdigit()

    @staticmethod
    def validate_channel_id(channel_id: str) -> bool:
        return len(channel_id) >= 10 and channel_id.isdigit()

class InteractivePrompt:
    def __init__(self):
        self.logger = Logger()

    async def get_input(self, prompt: str, validator=None, error_msg: str = "Invalid input") -> str:
        while True:
            value = input(f"{MAGENTA}[?] {prompt}{RESET} ").strip()
            if not value:
                self.logger.error("Input cannot be empty")
                continue
            if validator and not validator(value):
                self.logger.error(error_msg)
                continue
            return value

    async def get_bool(self, prompt: str, default: bool = False) -> bool:
        default_str = "Y/n" if default else "y/N"
        value = await self.get_input(f"{prompt} [{default_str}]")
        if not value:
            return default
        return value.lower() in ("y", "yes", "true", "t", "1")

async def main():
    parser = argparse.ArgumentParser(
        description="Discord Cleaner | by @tc4dy"
    )
    parser.add_argument("--token", help="Discord authentication token")
    parser.add_argument("--author-id", help="User ID to delete messages from")
    parser.add_argument("--channel-id", help="Channel ID to clean")
    parser.add_argument("--guild-id", help="Guild ID (for server channels)")
    parser.add_argument("--content", help="Filter messages containing this text")
    parser.add_argument("--has-link", action="store_true", help="Only delete messages with links")
    parser.add_argument("--has-file", action="store_true", help="Only delete messages with files")
    parser.add_argument("--include-nsfw", action="store_true", help="Include NSFW channels")
    parser.add_argument("--batch-size", type=int, default=3, help="Messages per batch (default: 3)")
    parser.add_argument("--delete-delay", type=int, default=1000, help="Delay between deletions in ms (default: 1000)")
    parser.add_argument("--search-delay", type=int, default=2000, help="Delay between searches in ms (default: 2000)")
    parser.add_argument("--max-retries", type=int, default=10, help="Maximum retry attempts (default: 10)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be deleted without actually deleting")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--config", help="Load configuration from JSON file")

    args = parser.parse_args()

    config = Config()
    prompt = InteractivePrompt()

    if args.config and os.path.exists(args.config):
        with open(args.config, "r") as f:
            data = json.load(f)
            config = Config(**data)
        print(f"{GREEN}[+] Loaded configuration from {args.config}{RESET}")

    if args.interactive or not args.token:
        print(f"{CYAN}[+] " + "=" * 50 + RESET)
        print(f"{MAGENTA}[+] Discord Cleaner | by @tc4dy{RESET}")
        print(f"{CYAN}[+] " + "=" * 50 + RESET)
        print(f"{YELLOW}[!] This action cannot be undone!{RESET}")
        print()

        config.token = await prompt.get_input(
            "Enter your Discord token",
            InputValidator.validate_token,
            "Invalid token (must be at least 10 characters and contain '.')"
        )

        config.author_id = await prompt.get_input(
            "Enter the user ID to delete messages from",
            InputValidator.validate_id,
            "Invalid user ID (must be at least 10 digits)"
        )

        config.channel_id = await prompt.get_input(
            "Enter the channel ID",
            InputValidator.validate_channel_id,
            "Invalid channel ID (must be at least 10 digits)"
        )

        config.content_filter = await prompt.get_input(
            "Filter messages containing this text (leave empty for all)",
            lambda x: True
        ) or None

        config.has_link = await prompt.get_bool("Only delete messages with links")
        config.has_file = await prompt.get_bool("Only delete messages with files")
        config.dry_run = await prompt.get_bool("Dry run mode (preview only)", False)

    else:
        if args.token:
            config.token = args.token
        if args.author_id:
            config.author_id = args.author_id
        if args.channel_id:
            config.channel_id = args.channel_id
        if args.guild_id:
            config.guild_id = args.guild_id
        if args.content:
            config.content_filter = args.content
        config.has_link = args.has_link
        config.has_file = args.has_file
        config.include_nsfw = args.include_nsfw
        config.batch_size = args.batch_size
        config.delete_delay = args.delete_delay
        config.search_delay = args.search_delay
        config.max_retries = args.max_retries
        config.verbose = args.verbose
        config.dry_run = args.dry_run

    if not config.token:
        print(f"{RED}[-] Error: Token is required{RESET}")
        sys.exit(1)

    if not config.author_id:
        print(f"{RED}[-] Error: Author ID is required{RESET}")
        sys.exit(1)

    if not config.channel_id:
        print(f"{RED}[-] Error: Channel ID is required{RESET}")
        sys.exit(1)

    async with DiscordCleaner(config) as cleaner:
        await cleaner.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[!] Interrupted by user{RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"{RED}[-] Fatal error: {str(e)}{RESET}")
        sys.exit(1)

"""Native desktop notifications for Windows and cross-platform systems."""

import logging
import platform
import subprocess
import threading

logger = logging.getLogger(__name__)


def send_notification(title: str, message: str) -> None:
    """Send a non-blocking desktop toast notification."""
    threading.Thread(
        target=_dispatch_notification,
        args=(title, message),
        daemon=True,
        name="NotificationThread",
    ).start()


def _dispatch_notification(title: str, message: str) -> None:
    """Internal notification dispatcher."""
    system = platform.system()
    if system == "Windows":
        _send_windows_toast(title, message)
    elif system == "Darwin":
        _send_macos_notification(title, message)
    elif system == "Linux":
        _send_linux_notification(title, message)
    else:
        logger.info("[Notification] %s: %s", title, message)


def _send_windows_toast(title: str, message: str) -> None:
    """Send Windows Toast notification via PowerShell."""
    safe_title = title.replace('"', '`"')
    safe_msg = message.replace('"', '`"')
    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $textNodes = $template.GetElementsByTagName("text")
    $textNodes.Item(0).AppendChild($template.CreateTextNode("{safe_title}")) > $null
    $textNodes.Item(1).AppendChild($template.CreateTextNode("{safe_msg}")) > $null
    $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("VoxLocal")
    $notifier.Show($toast)
    """
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            timeout=5,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        logger.debug("Failed sending Windows toast: %s", exc)


def _send_macos_notification(title: str, message: str) -> None:
    """Send macOS notification via osascript."""
    cmd = f'display notification "{message}" with title "{title}"'
    try:
        subprocess.run(["osascript", "-e", cmd], capture_output=True, timeout=3, check=False)
    except Exception as exc:
        logger.debug("Failed sending macOS notification: %s", exc)


def _send_linux_notification(title: str, message: str) -> None:
    """Send Linux notification via notify-send."""
    try:
        subprocess.run(["notify-send", title, message], capture_output=True, timeout=3, check=False)
    except Exception as exc:
        logger.debug("Failed sending Linux notification: %s", exc)

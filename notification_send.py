"""Deliver one bounded stdin notification over D-Bus, without private argv."""
import html
import json
import signal
import sys

MAX_INPUT_BYTES = 16384


def read_payload(stream):
    raw = stream.readline(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Notification exceeds input limit")
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {"message", "image"}:
        raise ValueError("Invalid notification")
    for key, limit in (("message", 2048), ("image", 4096)):
        if not isinstance(value[key], str) or len(value[key]) > limit or "\0" in value[key]:
            raise ValueError("Invalid notification field")
    return value


def send(payload):
    from gi.repository import Gio, GLib

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    # Notification bodies support markup; user-supplied names remain literal.
    arguments = GLib.Variant("(susssasa{sv}i)", (
        "Plancks", 0, payload["image"], "Plancks",
        html.escape(payload["message"], quote=False), [],
        {"urgency": GLib.Variant("y", 1),
         "suppress-sound": GLib.Variant("b", True)}, 8000))
    bus.call_sync("org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                  "org.freedesktop.Notifications", "Notify", arguments,
                  GLib.VariantType.new("(u)"), Gio.DBusCallFlags.NONE, 5000, None)


def main():
    # Bound waiting for stdin as well as the D-Bus request. Never log payloads.
    signal.alarm(10)
    try:
        send(read_payload(sys.stdin.buffer))
    except Exception:
        print("Could not deliver desktop notification.", file=sys.stderr)
        return 1
    finally:
        signal.alarm(0)
    return 0


if __name__ == "__main__":
    sys.exit(main())

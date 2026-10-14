import io
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from notification_send import MAX_INPUT_BYTES, read_payload


class NotificationTests(unittest.TestCase):
    def test_payload_bounds_and_types(self):
        value = {"message": "Private activity", "image": "/tmp/icon.png"}
        self.assertEqual(read_payload(io.BytesIO(json.dumps(value).encode())), value)
        for bad in (b"x" * (MAX_INPUT_BYTES + 1), b"{}", b"[]",
                    json.dumps(dict(value, message="x" * 2049)).encode(),
                    json.dumps(dict(value, image=123)).encode(),
                    json.dumps(dict(value, message="bad\0name")).encode()):
            with self.subTest(payload=bad[:30]), self.assertRaises(ValueError):
                read_payload(io.BytesIO(bad))

    def test_unavailable_service_returns_generic_error(self):
        result = subprocess.run(
            ["dbus-run-session", "--", sys.executable, str(ROOT / "notification_send.py")],
            input=json.dumps({"message": "Private activity", "image": "/private/icon.png"}) + "\n",
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "Could not deliver desktop notification.\n")

    def test_controller_keeps_payload_out_of_arguments(self):
        source = (ROOT / "EpochController.qml").read_text()
        delivery = source.split("property Process notification: Process {", 1)[1].split("\n  }", 1)[0]
        command = next(line for line in delivery.splitlines() if "command:" in line)
        self.assertIn('notification_send.py', command)
        self.assertNotIn("notificationMessage", command)
        self.assertNotIn("notificationImage", command)
        self.assertNotIn("notify-send", source)
        self.assertIn("stdinEnabled: true", delivery)

    @unittest.skipUnless(importlib.util.find_spec("gi"), "GObject integration runs in the Arch CI job")
    def test_private_stdin_delivery_on_isolated_bus(self):
        result = subprocess.run(
            ["dbus-run-session", "--", sys.executable, str(Path(__file__).resolve()), "--probe"],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def probe():
    from gi.repository import Gio, GLib
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    bus.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
                  "RequestName", GLib.Variant("(su)", ("org.freedesktop.Notifications", 0)),
                  GLib.VariantType.new("(u)"), Gio.DBusCallFlags.NONE, 1000, None)
    xml = """<node><interface name="org.freedesktop.Notifications">
      <method name="Notify">
        <arg type="s" direction="in"/><arg type="u" direction="in"/>
        <arg type="s" direction="in"/><arg type="s" direction="in"/>
        <arg type="s" direction="in"/><arg type="as" direction="in"/>
        <arg type="a{sv}" direction="in"/><arg type="i" direction="in"/>
        <arg type="u" direction="out"/>
      </method></interface></node>"""
    received, errors = [], []
    loop = GLib.MainLoop()
    message = "Private client <img src='https://example.invalid/secret'> & planning"
    icon = "/private/test-user/notification.png"

    def notify(connection, sender, path, interface, method, parameters, invocation):
        try:
            values = parameters.unpack()
            assert values[:4] == ("Plancks", 0, icon, "Plancks"), values[:4]
            assert values[4] == "Private client &lt;img src='https://example.invalid/secret'&gt; &amp; planning"
            assert values[5] == []
            assert values[6] == {"urgency": 1, "suppress-sound": True}
            assert values[7] == 8000
            arguments = Path(f"/proc/{client.pid}/cmdline").read_bytes()
            assert message.encode() not in arguments and icon.encode() not in arguments
            assert b"notification_send.py" in arguments
            received.append(True)
            invocation.return_value(GLib.Variant("(u)", (1,)))
        except Exception as exc:
            errors.append(repr(exc))
            invocation.return_dbus_error("org.example.TestFailure", "Notification mismatch")

    registration = bus.register_object("/org/freedesktop/Notifications",
                                       Gio.DBusNodeInfo.new_for_xml(xml).interfaces[0], notify, None, None)
    client = subprocess.Popen([sys.executable, str(ROOT / "notification_send.py")],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    client.stdin.write(json.dumps({"message": message, "image": icon}).encode() + b"\n")
    client.stdin.close()

    def poll():
        if client.poll() is None:
            return True
        loop.quit()
        return False

    def timeout():
        errors.append("Notification delivery timed out")
        client.kill()
        loop.quit()
        return False

    GLib.timeout_add(20, poll)
    deadline = GLib.timeout_add_seconds(8, timeout)
    loop.run()
    GLib.source_remove(deadline)
    client.wait(timeout=2)
    bus.unregister_object(registration)
    assert client.returncode == 0, client.stderr.read().decode()
    assert received and not errors, errors


if __name__ == "__main__":
    if "--probe" in sys.argv:
        probe()
    else:
        unittest.main()

# CtsVerifier Test Automation Development & TestBuilder Workbench

This directory contains development tools for interactively recording, exploring, and building CtsVerifier test automation scripts.

---

## 🛠️ `test_builder.py`

An interactive test building tool that lets an engineer or agent execute a test manually step-by-step while automatically:
1. Capturing UI XML dumps (`window_dump.xml`) and Screenshots (`.png`) at every state transition.
2. Building an interactive menu of clickable elements with text, resource IDs, and content descriptions.
3. Recording every action (`tap`, `swipe`, `keyevent`, `reboot`, `sleep`) into a clean, auto-generated Python test script (`pass_<test_name>_test.py`).
4. Providing a `ping <message>` command to pause and request human guidance whenever an unexpected dialog or unblocking step is encountered!

---

## 🚀 Usage

Run the TestBuilder tool for any CtsVerifier test:

```bash
python3 third_party/adt-infra/goldfish_test/xts/verifier/automation_dev/test_builder.py --test "Screen Lock Test"
```

### Interactive Commands:
- `<number>`: Tap interactive element by menu index number.
- `tap <text/id>`: Tap element matching text or resource ID.
- `swipe_up`: Execute swipe up gesture (unlock / scroll).
- `key <code/name>`: Send key event (`82`, `KEYCODE_WAKEUP`, etc.).
- `reboot`: Trigger `reboot_and_wait()`.
- `sleep <seconds>`: Insert explicit delay.
- `ping <message>`: Pause and ping user for guidance.
- `pass`: Tap Pass button and emit generated `pass_<test_name>_test.py` script.

---

## 📂 Session Output Directory
Session recordings (XML dumps and screenshots for every step) are saved in:
`third_party/adt-infra/goldfish_test/xts/verifier/automation_dev/sessions/<test_slug>/`

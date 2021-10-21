package com.google.emu

import android.view.KeyEvent
import com.google.protobuf.MessageOrBuilder
import com.google.protobuf.util.JsonFormat

class JsonLogger {
    companion object {
        val jsonPrinter = JsonFormat.printer().preservingProtoFieldNames()

        fun toJson(typ: String, msg: MessageOrBuilder): String {
            return """{ "type" : "${typ}", "object" : ${jsonPrinter.print(msg)} }""".replace(
                '\n',
                ' '
            )
        }

        fun translateKeyEvent(keyEvent: KeyEvent): String {
            return when (keyEvent.keyCode) {
                KeyEvent.KEYCODE_SHIFT_LEFT, KeyEvent.KEYCODE_SHIFT_RIGHT -> "Shift"
                KeyEvent.KEYCODE_DEL -> "Backspace"
                KeyEvent.KEYCODE_ENTER -> "Enter"
                else -> keyEvent.unicodeChar.toChar().toLowerCase().toString()
            }
        }
    }
}
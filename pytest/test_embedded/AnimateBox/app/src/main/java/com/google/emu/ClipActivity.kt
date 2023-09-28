package com.google.emu

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.os.Bundle
import android.util.Log
import android.view.OrientationEventListener
import android.widget.TextView


class ClipActivity : Activity() {
    val TAG = "aemu"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.clip_activity);
        // Check if the Intent contains extras
        if (intent != null && intent.extras != null) {
            val value = intent.getStringExtra("clip")

            // Check if the value is not null
            if (value != null) {
                val clipboard: ClipboardManager =
                    getSystemService(CLIPBOARD_SERVICE) as ClipboardManager

                Log.i(TAG, "Setting clipboard to: $value")
                val clip: ClipData = ClipData.newPlainText("label", value)
                clipboard.setPrimaryClip(clip)

                val textView = findViewById<TextView>(R.id.clipView)
                textView.text = value
            }
        }
    }
}

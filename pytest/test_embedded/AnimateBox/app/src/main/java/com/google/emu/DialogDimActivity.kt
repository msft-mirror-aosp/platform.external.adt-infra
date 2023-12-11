// Copyright 2023 The Android Open Source Project
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package com.google.emu

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogWindowProvider

class DialogDimActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            // A surface container using the 'background' color from the theme
            Surface(
                modifier = Modifier.fillMaxSize(),
                color = Color(0, 0, 255, 255)
            ) {
                Text(
                    text = "Background should not be #0000ff when background dimming is" +
                            " enabled while showing the dialog.",
                    color = Color.Red,
                )

                var hideDialog = false
                if (intent != null && intent.extras != null) {
                    val value = intent.getStringExtra("hideDialog")

                    // hide dialog if hideDialog intent extra has content.
                    if (value != null) {
                        hideDialog = true
                    }
                }
                if (!hideDialog) {
                    DialogNoContent()
                }
            }
        }
    }
}

@Preview
@Composable
fun DialogNoContent() {
    Dialog(onDismissRequest = {}) {
        // This modifies the alpha value of the dimming background from the dialog.
        // To validate that the dimming works, we need to set it to a value d that is
        // 0 < d < 1.0. From testing, setting it to 1.0 does not trigger
        // HWC2_COMPOSITION_SOLID_COLOR.
        (LocalView.current.parent as DialogWindowProvider)?.window?.setDimAmount(0.8f)
    }
}
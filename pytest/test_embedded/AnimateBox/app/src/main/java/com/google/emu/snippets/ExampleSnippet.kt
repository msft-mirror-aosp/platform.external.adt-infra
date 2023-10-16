package com.google.emu.snippets

import com.google.android.mobly.snippet.Snippet
import com.google.android.mobly.snippet.rpc.Rpc

/*
 * Copyright (C) 2016 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
class ExampleSnippet : Snippet {
  @Rpc(description = "Returns the given integer with the prefix \"foo\"")
  fun getFoo(input: Int): String {
    return "foo $input"
  }

  override fun shutdown() {}
}
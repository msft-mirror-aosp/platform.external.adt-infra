/*
 * Copyright (c) 2016 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.devtools.systemimage.uitest.utils;

import androidx.test.espresso.IdlingResource;
import androidx.test.uiautomator.UiObject;

public class IdlingResourceUtil implements IdlingResource {
    private ResourceCallback resourceCallback;
    private final UiObject idleTarget;

    public IdlingResourceUtil(UiObject idleTarget) {
        this.idleTarget = idleTarget;
    }

    @Override
    public String getName() {
        return IdlingResourceUtil.class.getName();
    }

    @Override
    public boolean isIdleNow() {
        boolean isIdle = idleTarget.exists();

        if (isIdle && resourceCallback != null) {
            resourceCallback.onTransitionToIdle();
        }

        return isIdle;
    }

    @Override
    public void registerIdleTransitionCallback(ResourceCallback resourceCallback) {
        this.resourceCallback = resourceCallback;
    }
}

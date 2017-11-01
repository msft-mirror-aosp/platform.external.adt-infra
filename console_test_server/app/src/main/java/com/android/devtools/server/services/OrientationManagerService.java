/*
 * Copyright (c) 2017 The Android Open Source Project
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

package com.android.devtools.server.services;

import com.android.devtools.server.model.RestServiceModel;
import com.android.devtools.server.model.Result;
import com.android.devtools.server.model.OrientationManagerModel;
import com.android.devtools.server.utils.Constants;
import com.google.gson.Gson;

import java.io.IOException;

import android.content.Context;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;
import android.view.WindowManager;

/**
 * Service for getting device screen orientation information.
 */

public class OrientationManagerService implements Service {
  private static final String TAG = OrientationManagerService.class.getSimpleName();
  private final Context mContext;
  private final UiDevice mDevice;

  public OrientationManagerService(Context context, UiDevice uiDevice) {
    mContext = context;
    mDevice = uiDevice;
  }

  @Override
  public String execute(String json) throws IOException {
    boolean isSuccess = false;
    Result result = new Result();

    // In order to get screen orientation and rotation, an application with UI
    // needs to be launched.
    try {
      this.launchAppWithUI();
    } catch (UiObjectNotFoundException e) {
      mDevice.pressHome();
      Log.e(TAG, "Failed to launch app with UI.");
      result.setIsFail(true);
      result.setDescription("Failed to launch app with UI.");
      return new Gson().toJson(result);
    }

    OrientationManagerModel orientationModel = new Gson()
        .fromJson(json, OrientationManagerModel.class);
    if (orientationModel == null) {
      Log.e(TAG, "OrientationModel is null. Invalid POST Request body: " + json);
      result.setIsFail(true);
      result.setDescription("Invalid POST Request body");
      return new Gson().toJson(result);
    }

    // Screen rotation has four values:
    // in android.view.Surface:
    //   ROTATION_0: 0
    //   ROTATION_180: 2
    //   ROTATION_270: 3
    //   ROTATION_90: 1
    final int screenRotation = ((WindowManager) mContext
        .getSystemService(Context.WINDOW_SERVICE)).getDefaultDisplay().getRotation();

    // Screen orientation has two common values:
    // in android.content.res.Configuration:
    //   ORIENTATION_PORTRAIT: 1
    //   ORIENTATION_LANDSCAPE: 2
    final int screenOrientation = mContext.getResources().getConfiguration().orientation;

    result.setScreenRotation(Integer.toString(screenRotation));
    result.setScreenOrientation(Integer.toString(screenOrientation));
    isSuccess = true;
    result.setIsFail(!isSuccess);
    mDevice.pressHome();
    return new Gson().toJson(result);
  }

  private void launchAppWithUI() throws UiObjectNotFoundException {
    // For API 18, 19, 21, there is a tip on the screen. ('OK')
    // For API 22, 23, 24, there is a tip on the screen. ('Got it')
    // It needs to be removed by clicking on it.
    try {
      mDevice.findObject(new UiSelector().text(Constants.TIP_BUTTON_OK))
          .clickAndWaitForNewWindow();
      Log.d(TAG, "Welcome screen tip, " + Constants.TIP_BUTTON_OK + " clicked.");
    } catch (UiObjectNotFoundException e) {
      Log.e(TAG, e.getMessage());
    }

    try {
      mDevice.findObject(new UiSelector().text(Constants.TIP_BUTTON_GOT_IT))
          .clickAndWaitForNewWindow();
      Log.d(TAG, "Welcome screen tip, " + Constants.TIP_BUTTON_GOT_IT + " clicked.");
    } catch (UiObjectNotFoundException e) {
      Log.e(TAG, e.getMessage());
    }

    // Launch pre-installed application: Calculator.
    final String appName = "Calculator";

    mDevice.findObject(new UiSelector().descriptionContains(Constants.APPS))
        .clickAndWaitForNewWindow();

    // For API 18, 19, 21, after opening Apps, there is another tip on the
    // the screen. It needs to be removed by clicking on it. ('OK')
    try {
      mDevice.findObject(new UiSelector().text(Constants.TIP_BUTTON_OK))
          .clickAndWaitForNewWindow();
      Log.i(TAG, "Apps tip, " + Constants.TIP_BUTTON_OK + " clicked.");
    } catch (UiObjectNotFoundException e) {
      Log.e(TAG, e.getMessage());
    }

    UiScrollable appList = new UiScrollable(new UiSelector()
        .resourceIdMatches(Constants.LAUNCHER_LIST_CONTAINER_RES));

    UiObject app;
    try {
      appList.setAsVerticalList();
      app = appList.getChildByText(
          new UiSelector().className(Constants.TEXT_VIEW_CLASS_NAME),
          appName);
    } catch (UiObjectNotFoundException e) {
      appList.setAsHorizontalList();
      app = appList.getChildByText(
          new UiSelector().className(Constants.TEXT_VIEW_CLASS_NAME),
          appName);
    }
    app.clickAndWaitForNewWindow();
  }

  @Override
  public String toString() {
    return new Gson().toJson(new RestServiceModel(
        POST,
        "/OrientationManagerService",
        new OrientationManagerModel("String").toString()));
  }
}

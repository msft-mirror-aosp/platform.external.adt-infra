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

import com.android.devtools.server.model.GeoManagerModel;
import com.android.devtools.server.model.RestServiceModel;
import com.android.devtools.server.model.Result;
import com.android.devtools.server.utils.Constants;
import com.google.gson.Gson;

import java.io.IOException;

import android.content.Context;
import android.location.Location;
import android.location.LocationManager;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;


/**
 * Service for getting geo information.
 */

public class GeoManagerService implements Service {
  private static final String ACCEPT_AND_CONTINUE =
          "(?i:.*ACCEPT & CONTINUE.*)";
  private static final String GOOGLE_MAPS = "Maps";
  private static final String GPS_PROVIDER = "gps";
  private static final String IMAGE_VIEW_CLASS_NAME =
          "android.widget.ImageView";
  // This resouce id is only for API 25 & 24 & 23.
  private static final String LOCATION_BUTTON_R_ID =
          "com.google.android.apps.maps:id/mylocation_button | com.google.android.apps.gmm:id/mylocation_button";
  private static final String TAG = GeoManagerService.class.getSimpleName();

  private final Context mContext;
  private final UiDevice mDevice;

  public GeoManagerService(Context context, UiDevice uiDevice) {
    mContext = context;
    mDevice = uiDevice;
  }

  @Override
  public String execute(String json) throws IOException {
    boolean isSuccess = false;
    Result result = new Result();

    Log.d(TAG, "json = [" + json + "]");
    Log.d(TAG, "{} json payload is to get geo information.");

    if (json.equals("{}")) { // '{}' is the payload to get last know geo info.
      GeoManagerModel geoModel = new Gson().fromJson(json,
              GeoManagerModel.class);
      if (geoModel == null) {
        Log.e(TAG, "geoModel is null. Invalid POST Request body: " + json);
        result.setIsFail(true);
        result.setDescription("Invalid POST Request body");
        return new Gson().toJson(result);
      }

      LocationManager locationManager = (LocationManager)
              mContext.getSystemService(Context.LOCATION_SERVICE);
      Log.d(TAG, "locationManager = " + locationManager.toString());
      Location location = locationManager.getLastKnownLocation(GPS_PROVIDER);
      Log.d(TAG, "location = " + location.toString());

      result.setLongitude(Integer.toString((int) location.getLongitude()));
      result.setLatitude(Integer.toString((int) location.getLatitude()));
      result.setAltitude(Integer.toString((int) location.getAltitude()));
      Log.d(TAG, "set all 3 tudes.");

      isSuccess = true;
      result.setIsFail(!isSuccess);
      mDevice.pressHome();
      Log.d(TAG, "return");
      return new Gson().toJson(result);
    } else {
      Log.e(TAG, "Initially, dismiss tips on welcome and Apps screens.");
      try {
        this.dismissTips(mDevice);
      } catch (UiObjectNotFoundException e) {
        mDevice.pressHome();
        String errMsg = "Failed to dismiss tips.";
        Log.e(TAG, errMsg);
        result.setIsFail(true);
        result.setDescription(errMsg);
        return new Gson().toJson(result);
      }

      Log.d(TAG, "Go to Apps window, launch " + GOOGLE_MAPS +
              " app, accpet the terms and conditions, " +
              "enable Location service, then Tap on My Location.");
      try {
        this.launchGoogleMapsApp(mDevice);
      } catch (UiObjectNotFoundException e) {
        mDevice.pressHome();
        String errMsg = "Failed to launch " + GOOGLE_MAPS;
        Log.e(TAG, errMsg);
        result.setIsFail(true);
        result.setDescription(errMsg);
        return new Gson().toJson(result);
      }

      result.setIsFail(false);
      result.setDescription("Initially set a location.");
      return new Gson().toJson(result);
    }
  }

  private static void dismissTips(UiDevice uiDevice)
          throws UiObjectNotFoundException {
    Log.d(TAG, "For API 18, 19, 21, there is a tip on the screen. (\"OK\")\n" +
            "For API 22, 23, 24, there is a tip on the screen. (\"GOT IT\")\n" +
            "It needs to be removed by clicking on it.");
    try {
      uiDevice.findObject(new UiSelector().text(Constants.TIP_BUTTON_OK)).
              clickAndWaitForNewWindow();
      Log.d(TAG, "Welcome screen tip, " + Constants.TIP_BUTTON_OK + " clicked.");
    } catch (UiObjectNotFoundException e) {
      Log.e(TAG, e.getMessage());
    }

    try {
      uiDevice.findObject(new UiSelector().text(Constants.TIP_BUTTON_GOT_IT)).
              clickAndWaitForNewWindow();
      Log.d(TAG, "Welcome screen tip, " + Constants.TIP_BUTTON_GOT_IT +
              " clicked.");
    } catch (UiObjectNotFoundException e) {
      Log.e(TAG, e.getMessage());
    }

    Log.d(TAG, "Open and go to Apps window.");
    uiDevice.findObject(new UiSelector().descriptionContains(Constants.APPS)).
            clickAndWaitForNewWindow();

    Log.d(TAG, "For API 18, 19, 21, after opening Apps, there is another \n" +
            "tip on the the screen. It needs to be removed by clicking on " +
            "it. (\"OK\")");
    try {
      uiDevice.findObject(new UiSelector().text(Constants.TIP_BUTTON_OK)).
              clickAndWaitForNewWindow();
      Log.d(TAG, "Apps screen tip, " + Constants.TIP_BUTTON_OK + " clicked.");
    } catch (UiObjectNotFoundException e) {
      Log.e(TAG, e.getMessage());
    }

    Log.d(TAG,
          "After dismissing tips on welcome and Apps screen, go back to home.");
    uiDevice.pressHome();
  }

  public static void launchGoogleMapsApp(UiDevice uiDevice)
          throws UiObjectNotFoundException {

    Log.d(TAG, "1) Go to " + Constants.APPS + " screen.");
    uiDevice.findObject(new UiSelector().descriptionContains(Constants.APPS)).
            clickAndWaitForNewWindow();

    UiScrollable appList = new UiScrollable(new UiSelector().resourceIdMatches(
            Constants.LAUNCHER_LIST_CONTAINER_RES));

    Log.d(TAG, "2) Launch " + GOOGLE_MAPS + " application.");
    UiObject app;
    try {
      appList.setAsVerticalList();
      app = appList.getChildByText(
              new UiSelector().className(Constants.TEXT_VIEW_CLASS_NAME),
              GOOGLE_MAPS);
    } catch (UiObjectNotFoundException e) {
      appList.setAsHorizontalList();
      app = appList.getChildByText(
              new UiSelector().className(Constants.TEXT_VIEW_CLASS_NAME),
              GOOGLE_MAPS);
    }
    app.clickAndWaitForNewWindow();

    Log.d(TAG, "2.1) It's the first time to launch " + GOOGLE_MAPS +
            ", we need to accept the terms and enable location service. " +
            "Then go back to home screen.");
    try {
      uiDevice.findObject(new UiSelector().textMatches(ACCEPT_AND_CONTINUE)).
              clickAndWaitForNewWindow();
      Log.d(TAG, GOOGLE_MAPS + ": " + ACCEPT_AND_CONTINUE + " clicked.");
    } catch (UiObjectNotFoundException e) {
      Log.e(TAG, e.getMessage());
    }

    // Enable location service.
    // The 'Location' icon neither has resource id nor text,
    // but it's parent's parent.
    // Hence, using it's parent's parent to get 'Location' item.
    Log.d(TAG, "2.2) Start to enable GPS.");
    UiSelector pppParent = new UiSelector().resourceId(LOCATION_BUTTON_R_ID);

    UiSelector ppParent = pppParent.index(0);
    Log.d(TAG, "Get ppParent.");

    UiSelector pParent = ppParent.index(0);

    UiObject myLocationButton = uiDevice.findObject(pParent.childSelector(
            new UiSelector().className(IMAGE_VIEW_CLASS_NAME)));
    if (myLocationButton.exists()) {
      Log.d(TAG, "Get myLocationButton.");
    } else {
      Log.e(TAG, "myLocationButton doesn't exit.");
    }

    myLocationButton.clickAndWaitForNewWindow();
    Log.d(TAG, "Enabled GPS.");

    try {
      uiDevice.findObject(new UiSelector().text(Constants.TIP_BUTTON_OK)).
              clickAndWaitForNewWindow();
      Log.d(TAG, "2.3) Improve location accuracy, " + Constants.TIP_BUTTON_OK + " clicked.");
    } catch (UiObjectNotFoundException e) {
      Log.e(TAG, e.getMessage());
    }

    // fix current location
    UiSelector ppFrameLoayout = new UiSelector().resourceId(
            LOCATION_BUTTON_R_ID);

    UiSelector pFrameLoayout = ppFrameLoayout.index(0);
    Log.d(TAG, "get pFrameLoayout.");

    UiObject currentLocationButton = uiDevice.findObject(
            pFrameLoayout.childSelector(
                    new UiSelector().className(IMAGE_VIEW_CLASS_NAME)));
    if (currentLocationButton.exists()) {
      Log.d(TAG, "get currentLocationButton.");
    } else {
      Log.e(TAG, "currentLocationButton doesn't exit.");
    }

    currentLocationButton.clickAndWaitForNewWindow();
    Log.d(TAG, GOOGLE_MAPS + " launched.");
  }

  @Override
  public String toString() {
    return new Gson().toJson(new RestServiceModel(
        POST,
        "/GeoManagerService",
        new GeoManagerModel("String").toString()));
  }
}


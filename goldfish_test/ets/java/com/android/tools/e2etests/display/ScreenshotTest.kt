package com.android.tools.e2etests.display

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.platform.io.PlatformTestStorage
import androidx.test.platform.io.PlatformTestStorageRegistry
import com.android.emulator.control.Image
import com.android.emulator.control.ImageFormat
import com.android.emulator.control.ParameterValue
import com.android.emulator.control.PhysicalModelValue
import com.android.tools.e2etests.animatebox.AnimateBox
import com.android.tools.e2etests.grpc.EmulatorController
import com.google.protobuf.ByteString
import com.google.testing.junit.testparameterinjector.TestParameter
import com.google.testing.junit.testparameterinjector.TestParameterInjector
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith

val TAG = "ScreenshotTest"

@RunWith(TestParameterInjector::class)
class ScreenshotTest {
  val inst = InstrumentationRegistry.getInstrumentation()
  val testStorage: PlatformTestStorage = PlatformTestStorageRegistry.getInstance()

  enum class TestCase(val format: ImageFormat.ImgFormat, val rotation: Float) {
    RGB888_0(ImageFormat.ImgFormat.RGB888, 0f),
    RGB888_90(ImageFormat.ImgFormat.RGB888, 90f),
    RGBA8888_0(ImageFormat.ImgFormat.RGBA8888, 0f),
    RGBA8888_90(ImageFormat.ImgFormat.RGBA8888, 90f),
  }

  @Test
  fun screenshotExactAmountOfPixels(@TestParameter testCase: TestCase) {
    EmulatorController.defaultDeadline()
      .setPhysicalModel(
        PhysicalModelValue.newBuilder()
          .setTarget(PhysicalModelValue.PhysicalType.ROTATION)
          .setValue(ParameterValue.newBuilder().addAllData(listOf(0f, 0f, testCase.rotation)))
          .build()
      )
    val imageFormat = ImageFormat.newBuilder().setFormat(testCase.format).build()
    val resp = EmulatorController.defaultDeadline().getScreenshot(imageFormat)

    saveScreenshot("screenshotExactAmountOfPixels_${testCase.toString()}.png", resp)

    Assert.assertEquals(
      resp.getImage().size(),
      imageFormatBPP(imageFormat) * resp.getFormat().getWidth() * resp.getFormat().getHeight(),
    )
  }

  enum class FormatsEqualCase(val width: Int, val height: Int) {
    CASE_0_0(0, 0),
    CASE_320_200(320, 200),
    CASE_1920_1080(1920, 1080),
  }

  @Test
  fun screenshotAllFormatsAreEqual() {
    val animateBox = AnimateBox(inst)
    animateBox.start()
    animateBox.pause()

    // The pause action can trigger the clock/status to be shown.
    Thread.sleep(500)

    // The above work can take some time, so only do it once. Ideally all these cases should be
    // run even if the first fails, but that seems to involve pulling in more third party
    // libraries.
    Log.i(TAG, "Running test")
    for (testCase in FormatsEqualCase.entries) {
      var lastPixels: IntArray? = null
      for (format in
        listOf(
          ImageFormat.ImgFormat.RGBA8888,
          ImageFormat.ImgFormat.RGB888,
          ImageFormat.ImgFormat.PNG,
        )) {
        val imageFormat =
          ImageFormat.newBuilder()
            .setFormat(format)
            .setWidth(testCase.width)
            .setHeight(testCase.height)
            .build()
        val resp = EmulatorController.defaultDeadline().getScreenshot(imageFormat)
        val bmp =
          saveScreenshot(
            "screenshotAllFormatsAreEqual_${testCase.toString()}_${format.toString()}.png",
            resp,
          )
        if (lastPixels == null) {
          lastPixels = IntArray(bmp.width * bmp.height)
          bmp.getPixels(lastPixels, 0, bmp.width, 0, 0, bmp.width, bmp.height)
          // Make sure the pixels are not all the same (i.e. the screen is not blank). The other
          // screenshots must match this one, so there's no need to do this check again.
          Assert.assertFalse(pixelsAreTheSame(lastPixels))
        } else {
          val currentPixels = IntArray(bmp.width * bmp.height)
          bmp.getPixels(currentPixels, 0, bmp.width, 0, 0, bmp.width, bmp.height)
          Assert.assertArrayEquals(
            "${testCase.toString()}_${format.toString()}",
            lastPixels,
            currentPixels,
          )
        }
      }
    }
  }

  fun saveScreenshot(name: String, image: Image): Bitmap {
    if (image.getFormat().getFormat() == ImageFormat.ImgFormat.PNG) {
      return savePngScreenshot(name, image)
    }
    val bitmap =
      Bitmap.createBitmap(
        toColorArray(image),
        image.getFormat().getWidth(),
        image.getFormat().getHeight(),
        Bitmap.Config.ARGB_8888,
      )
    testStorage.openOutputFile(name).use { bitmap.compress(Bitmap.CompressFormat.PNG, 90, it) }
    return bitmap
  }

  fun savePngScreenshot(name: String, image: Image): Bitmap {
    testStorage.openOutputFile(name).use { it.write(image.getImage().toByteArray()) }
    return BitmapFactory.decodeByteArray(image.getImage().toByteArray(), 0, image.getImage().size())
  }
}

fun pixelsAreTheSame(pixels: IntArray): Boolean {
  return pixels.isEmpty() || pixels.all { it == pixels[0] }
}

fun toColorArray(image: Image): IntArray {
  val imagePixels = image.getFormat().getWidth() * image.getFormat().getHeight()
  val ret = IntArray(imagePixels)
  val bpp = imageFormatBPP(image.getFormat())

  for (i in 0 until imagePixels) {
    ret.set(i, pixelToColor(image.getImage(), i, bpp))
  }
  return ret
}

fun imageFormatBPP(imageFormat: ImageFormat): Int {
  return when (imageFormat.getFormat()) {
    ImageFormat.ImgFormat.RGB888 -> 3
    ImageFormat.ImgFormat.RGBA8888 -> 4
    else -> 0
  }
}

fun pixelToColor(raw: ByteString, pixel: Int, bpp: Int): Int {
  var alpha = 255
  if (bpp == 4) {
    alpha = raw.byteAt(pixel * bpp + 3).toInt() and 0xFF
  }
  // NOTE: Byte values are signed in Java, so promoting to an int will cause negative values to be
  // out of range. Color.argb() does not handle this, so we need to do it.
  return Color.argb(
    alpha,
    raw.byteAt(pixel * bpp).toInt() and 0xFF,
    raw.byteAt(pixel * bpp + 1).toInt() and 0xFF,
    raw.byteAt(pixel * bpp + 2).toInt() and 0xFF,
  )
}

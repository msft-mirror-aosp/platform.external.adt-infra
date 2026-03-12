package com.android.tools.e2etests.display

import android.graphics.Bitmap
import android.graphics.Color
import androidx.test.platform.io.PlatformTestStorage
import androidx.test.platform.io.PlatformTestStorageRegistry
import com.android.emulator.control.Image
import com.android.emulator.control.ImageFormat
import com.android.emulator.control.ParameterValue
import com.android.emulator.control.PhysicalModelValue
import com.android.tools.e2etests.grpc.EmulatorController
import com.google.protobuf.ByteString
import com.google.testing.junit.testparameterinjector.TestParameter
import com.google.testing.junit.testparameterinjector.TestParameterInjector
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(TestParameterInjector::class)
class ScreenshotTest {

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

  fun saveScreenshot(name: String, image: Image) {
    val bitmap =
      Bitmap.createBitmap(
        toColorArray(image),
        image.getFormat().getWidth(),
        image.getFormat().getHeight(),
        Bitmap.Config.ARGB_8888,
      )
    testStorage.openOutputFile(name).use { bitmap.compress(Bitmap.CompressFormat.PNG, 90, it) }
  }
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
    alpha = raw.byteAt(pixel * bpp + 3).toInt()
  }
  return Color.argb(
    alpha,
    raw.byteAt(pixel * bpp).toInt(),
    raw.byteAt(pixel * bpp + 1).toInt(),
    raw.byteAt(pixel * bpp + 2).toInt(),
  )
}

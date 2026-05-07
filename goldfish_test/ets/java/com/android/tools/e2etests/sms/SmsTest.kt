package com.android.tools.e2etests.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.provider.Telephony
import androidx.test.platform.app.InstrumentationRegistry
import com.android.emulator.control.PhoneResponse
import com.android.emulator.control.SmsMessage
import com.android.tools.e2etests.grpc.EmulatorController
import org.junit.Assert
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

val TAG = "SmsTest"
val SENDER_NUMBER = "+1234567890"
val SMS_TEXT = "Hello from Emulator Controller!"

class SmsTest {
    /**
     * Verifies that sending an SMS via Emulator Controller results in the message
     * being received by Android.
     */
    @Test
    fun sendSmsTest() {
        val context = InstrumentationRegistry.getInstrumentation().getTargetContext()
        val latch = CountDownLatch(1)

        // Generate unique text to avoid catching leftover messages from previous runs
        val uniqueText = "$SMS_TEXT ${java.util.UUID.randomUUID()}"
        var receivedText = ""
        var receivedSender = ""

        val receiver =
            object : BroadcastReceiver() {
                override fun onReceive(
                    context: Context,
                    intent: Intent,
                ) {
                    if (intent.action == Telephony.Sms.Intents.SMS_RECEIVED_ACTION) {
                        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
                        var currentText = ""
                        var currentSender = ""
                        for (msg in messages) {
                            currentText += msg.messageBody
                            currentSender = msg.originatingAddress ?: ""
                        }

                        // Only accept the message if it matches our expected sender and unique text
                        if (currentSender == SENDER_NUMBER && currentText == uniqueText) {
                            receivedText = currentText
                            receivedSender = currentSender
                            latch.countDown()
                        }
                    }
                }
            }

        val filter = IntentFilter(Telephony.Sms.Intents.SMS_RECEIVED_ACTION)
        context.registerReceiver(receiver, filter)

        try {
            val resp = sendSms(SENDER_NUMBER, uniqueText)
            Assert.assertEquals(resp, PhoneResponse.Response.OK)

            val success = latch.await(10, TimeUnit.SECONDS)
            Assert.assertTrue("Timed out waiting for SMS", success)
            Assert.assertEquals(uniqueText, receivedText)
            Assert.assertEquals(SENDER_NUMBER, receivedSender)
        } finally {
            context.unregisterReceiver(receiver)
        }
    }

    fun sendSms(
        sender: String,
        text: String,
    ): PhoneResponse.Response {
        val resp =
            EmulatorController
                .defaultDeadline()
                .sendSms(
                    SmsMessage
                        .newBuilder()
                        .setSrcAddress(sender)
                        .setText(text)
                        .build(),
                )

        return resp.getResponse()
    }
}

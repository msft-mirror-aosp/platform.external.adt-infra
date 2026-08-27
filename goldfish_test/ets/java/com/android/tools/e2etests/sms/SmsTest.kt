package com.android.tools.e2etests.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import android.provider.Telephony
import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import com.android.emulation.control.incubating.SmsMessage
import com.android.tools.e2etests.grpc.ModemService
import org.junit.Assert
import org.junit.Before
import org.junit.Ignore
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

val TAG = "SmsTest"
val SENDER_NUMBER = "+1234567890"
val SMS_TEXT = "Hello from Emulator Controller!"

@Ignore("The service is migrating to netsim")
class SmsTest {

    @Before
    fun verifySystemReadiness() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as android.telephony.TelephonyManager

        Log.i(TAG, "Waiting for virtual modem and SIM to initialize...")
        var isReady = false
        for (attempt in 1..60) {
            val state = tm.simState
            Log.d(TAG, "SIM State is currently: $state (Attempt $attempt/300)")
            if (state == android.telephony.TelephonyManager.SIM_STATE_READY) {
                isReady = true
                break
            }
            Thread.sleep(1000L)
        }

        if (!isReady) {
            Assert.fail("Virtual modem/SIM never reached READY state")
        }
    }

    /**
     * Verifies that sending an SMS via Modem Service results in the message
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

                        Log.i(TAG, "Received SMS from: $currentSender with text: $currentText")

                        if (currentText == uniqueText) {
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
            sendSms(SENDER_NUMBER, uniqueText)
            // If call succeeds, we wait for the broadcast

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
    ) {
        Log.i(TAG, "Attempting to send SMS via gRPC ModemService...")
        try {
            ModemService
                .stub!!
                .withDeadlineAfter(10, TimeUnit.SECONDS)
                .receiveSms(
                    SmsMessage
                        .newBuilder()
                        .setNumber(sender)
                        .setText(text)
                        .build(),
                )
            Log.i(TAG, "gRPC receiveSms call completed successfully (Status OK)")
        } catch (e: io.grpc.StatusRuntimeException) {
            Log.e(TAG, "gRPC receiveSms call failed! Status: ${e.status.code}, Description: ${e.status.description}")
            throw e
        } catch (e: Exception) {
            Log.e(TAG, "gRPC receiveSms call failed with unexpected exception: ${e.message}", e)
            throw e
        }
    }
}

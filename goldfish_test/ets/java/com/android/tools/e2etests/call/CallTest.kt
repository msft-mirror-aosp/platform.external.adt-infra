package com.android.tools.e2etests.call

import android.app.Activity
import android.content.Context
import android.os.Bundle
import android.os.ParcelFileDescriptor
import android.telecom.Call
import android.telecom.InCallService
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import androidx.test.platform.app.InstrumentationRegistry
import com.android.emulator.control.PhoneCall
import com.android.emulator.control.PhoneResponse
import com.android.tools.e2etests.grpc.EmulatorController
import org.junit.AfterClass
import org.junit.Assert
import org.junit.BeforeClass
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

val TAG = "CallTest"
val PHONE_NUMBER = "1234567890"

/**
 * A minimal implementation of [InCallService] that allows the test to capture
 * the active [Call] object. This is needed to verify detailed call states
 * like [Call.STATE_HOLDING] which are not exposed by [TelephonyManager].
 */
class TestInCallService : InCallService() {
    companion object {
        var currentCall: Call? = null
            private set

        fun clear() {
            currentCall = null
        }
    }

    override fun onCallAdded(call: Call) {
        super.onCallAdded(call)
        currentCall = call
    }

    override fun onCallRemoved(call: Call) {
        super.onCallRemoved(call)
        if (currentCall == call) {
            currentCall = null
        }
    }
}

class DummyActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        finish()
    }
}

class CallTest {
    /**
     * Setup and teardown methods to configure the test app as the default dialer.
     * This is required for the system to bind to our [TestInCallService].
     * We use [UiAutomation] to execute shell commands to grant/revoke the role.
     */
    companion object {
        @BeforeClass
        @JvmStatic
        fun setUpClass() {
            val uiAutomation = InstrumentationRegistry.getInstrumentation().getUiAutomation()
            val packageName = InstrumentationRegistry.getInstrumentation().getTargetContext().packageName
            val cmd = "cmd role add-role-holder android.app.role.DIALER $packageName"
            val pfd = uiAutomation.executeShellCommand(cmd)
            val fis = ParcelFileDescriptor.AutoCloseInputStream(pfd)
            fis.readBytes() // consume to ensure completion
        }

        @AfterClass
        @JvmStatic
        fun tearDownClass() {
            val uiAutomation = InstrumentationRegistry.getInstrumentation().getUiAutomation()
            val packageName = InstrumentationRegistry.getInstrumentation().getTargetContext().packageName
            val cmd = "cmd role remove-role-holder android.app.role.DIALER $packageName"
            val pfd = uiAutomation.executeShellCommand(cmd)
            val fis = ParcelFileDescriptor.AutoCloseInputStream(pfd)
            fis.readBytes() // consume
        }
    }

    /**
     * Performs an action and verifies that the call state changes to the expected state.
     * It registers a [TelephonyCallback], runs the action, waits for the callback to report
     * the expected state, and then unregisters the callback.
     */
    fun doAndVerifyCallState(
        expectedState: Int,
        timeoutSeconds: Long = 5,
        action: () -> Unit,
    ) {
        val context = InstrumentationRegistry.getInstrumentation().getTargetContext()
        val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager

        val latch = CountDownLatch(1)
        var receivedState = -1

        val callback =
            object : TelephonyCallback(), TelephonyCallback.CallStateListener {
                override fun onCallStateChanged(state: Int) {
                    receivedState = state
                    if (state == expectedState) {
                        latch.countDown()
                    }
                }
            }

        tm.registerTelephonyCallback(context.mainExecutor, callback)

        try {
            action()
            val success = latch.await(timeoutSeconds, TimeUnit.SECONDS)
            Assert.assertTrue("Timed out waiting for state $expectedState", success)
            Assert.assertEquals(expectedState, receivedState)
        } finally {
            tm.unregisterTelephonyCallback(callback)
        }
    }

    fun verifyCallState(
        expectedState: Int,
        timeoutSeconds: Long = 5,
    ) {
        doAndVerifyCallState(expectedState, timeoutSeconds) {}
    }

    /**
     * Helper to setup an inbound call and verify it is ringing.
     */
    fun setupInboundCall() {
        val resp = sendPhoneCall(PhoneCall.Operation.InitCall, PHONE_NUMBER)
        Assert.assertEquals(resp, PhoneResponse.Response.OK)
        verifyCallState(TelephonyManager.CALL_STATE_RINGING)
    }

    /**
     * Helper to setup an active call (inbound + accept) and verify it is offhook.
     */
    fun setupActiveCall() {
        setupInboundCall()
        val resp = sendPhoneCall(PhoneCall.Operation.AcceptCall, PHONE_NUMBER)
        Assert.assertEquals(resp, PhoneResponse.Response.OK)
        verifyCallState(TelephonyManager.CALL_STATE_OFFHOOK)
    }

    /**
     * Helper to setup a held call and verify it is holding.
     * Returns the captured Call object.
     */
    fun setupHeldCall(): Call {
        setupActiveCall()
        val resp = sendPhoneCall(PhoneCall.Operation.PlaceCallOnHold, PHONE_NUMBER)
        Assert.assertEquals(resp, PhoneResponse.Response.OK)

        val call = TestInCallService.currentCall
        Assert.assertNotNull("No current call found in InCallService", call)

        var attempts = 0
        while (call?.details?.state != Call.STATE_HOLDING && attempts < 10) {
            Thread.sleep(500)
            attempts++
        }

        Assert.assertEquals(Call.STATE_HOLDING, call?.details?.state)
        return call!!
    }

    /**
     * Verifies that initiating a call results in the phone ringing.
     */
    @Test
    fun inboundCall() {
        doAndVerifyCallState(TelephonyManager.CALL_STATE_RINGING) {
            val resp = sendPhoneCall(PhoneCall.Operation.InitCall, PHONE_NUMBER)
            Assert.assertEquals(resp, PhoneResponse.Response.OK)
        }
    }

    /**
     * Verifies that accepting a call changes the state to OFFHOOK (active).
     * Requires an incoming call to be present.
     */
    @Test
    fun acceptCall() {
        setupInboundCall()

        doAndVerifyCallState(TelephonyManager.CALL_STATE_OFFHOOK) {
            val resp = sendPhoneCall(PhoneCall.Operation.AcceptCall, PHONE_NUMBER)
            Assert.assertEquals(resp, PhoneResponse.Response.OK)
        }
    }

    /**
     * Verifies that rejecting a call returns the state to IDLE.
     * Requires an incoming call to be present.
     */
    @Test
    fun rejectCallExplicit() {
        setupInboundCall()

        doAndVerifyCallState(TelephonyManager.CALL_STATE_IDLE) {
            val resp = sendPhoneCall(PhoneCall.Operation.RejectCallExplicit, PHONE_NUMBER)
            Assert.assertEquals(resp, PhoneResponse.Response.OK)
        }
    }

    /**
     * Verifies that rejecting a call with busy signal returns the state to IDLE.
     * Requires an incoming call to be present.
     */
    @Test
    fun rejectCallBusy() {
        setupInboundCall()

        doAndVerifyCallState(TelephonyManager.CALL_STATE_IDLE) {
            val resp = sendPhoneCall(PhoneCall.Operation.RejectCallBusy, PHONE_NUMBER)
            Assert.assertEquals(resp, PhoneResponse.Response.OK)
        }
    }

    /**
     * Verifies that disconnecting an active call returns the state to IDLE.
     * Requires an active call to be present.
     */
    @Test
    fun disconnectCall() {
        setupActiveCall()

        doAndVerifyCallState(TelephonyManager.CALL_STATE_IDLE) {
            val resp = sendPhoneCall(PhoneCall.Operation.DisconnectCall, PHONE_NUMBER)
            Assert.assertEquals(resp, PhoneResponse.Response.OK)
        }
    }

    /**
     * Verifies that placing a call on hold results in Call.STATE_HOLDING.
     * Requires an active call to be present.
     */
    @Test
    fun placeCallOnHold() {
        setupActiveCall()

        val resp = sendPhoneCall(PhoneCall.Operation.PlaceCallOnHold, PHONE_NUMBER)
        Assert.assertEquals(resp, PhoneResponse.Response.OK)

        // Verify hold state via InCallService
        val call = TestInCallService.currentCall
        Assert.assertNotNull("No current call found in InCallService", call)

        // Wait a bit for state to propagate
        var attempts = 0
        while (call?.details?.state != Call.STATE_HOLDING && attempts < 10) {
            Thread.sleep(500)
            attempts++
        }

        Assert.assertEquals(Call.STATE_HOLDING, call?.details?.state)
    }

    /**
     * Verifies that taking a call off hold returns it to active state (STATE_ACTIVE).
     * Requires a held call to be present.
     */
    @Test
    fun takeCallOffHold() {
        val call = setupHeldCall()

        val resp = sendPhoneCall(PhoneCall.Operation.TakeCallOffHold, PHONE_NUMBER)
        Assert.assertEquals(resp, PhoneResponse.Response.OK)

        // Wait for active state
        var attempts = 0
        while (call.details.state != Call.STATE_ACTIVE && attempts < 10) {
            Thread.sleep(500)
            attempts++
        }
        Assert.assertEquals(Call.STATE_ACTIVE, call.details.state)
    }

    /**
     * Verifies that initiating a call with a bad number returns BadNumber response.
     */
    @Test
    fun inboundCallBadNumber() {
        val resp = sendPhoneCall(PhoneCall.Operation.InitCall, "aaa")
        Assert.assertEquals(resp, PhoneResponse.Response.BadNumber)
    }

    fun sendPhoneCall(
        op: PhoneCall.Operation,
        number: String,
    ): PhoneResponse.Response {
        val resp =
            EmulatorController
                .defaultDeadline()
                .sendPhone(
                    PhoneCall
                        .newBuilder()
                        .setOperation(op)
                        .setNumber(number)
                        .build(),
                )

        return resp.getResponse()
    }
}

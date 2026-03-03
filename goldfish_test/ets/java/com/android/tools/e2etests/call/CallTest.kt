package com.android.tools.e2etests.call

import com.android.emulator.control.PhoneCall
import com.android.emulator.control.PhoneResponse
import com.android.tools.e2etests.grpc.EmulatorController
import java.util.concurrent.TimeUnit
import org.junit.Assert
import org.junit.Test

val TAG = "CallTest"
val PHONE_NUMBER = "1234567890"

class CallTest {

  @Test
  fun inboundCall() {
    val resp = sendPhoneCall(PhoneCall.Operation.InitCall, PHONE_NUMBER)
    Assert.assertEquals(resp, PhoneResponse.Response.OK)
  }

  @Test
  fun acceptCall() {
    val resp = sendPhoneCall(PhoneCall.Operation.AcceptCall, PHONE_NUMBER)
    Assert.assertEquals(resp, PhoneResponse.Response.OK)
  }

  @Test
  fun rejectCallExplicit() {
    val resp = sendPhoneCall(PhoneCall.Operation.RejectCallExplicit, PHONE_NUMBER)
    Assert.assertEquals(resp, PhoneResponse.Response.OK)
  }

  @Test
  fun rejectCallBusy() {
    val resp = sendPhoneCall(PhoneCall.Operation.RejectCallBusy, PHONE_NUMBER)
    Assert.assertEquals(resp, PhoneResponse.Response.OK)
  }

  @Test
  fun disconnectCall() {
    val resp = sendPhoneCall(PhoneCall.Operation.DisconnectCall, PHONE_NUMBER)
    Assert.assertEquals(resp, PhoneResponse.Response.OK)
  }

  @Test
  fun placeCallOnHold() {
    val resp = sendPhoneCall(PhoneCall.Operation.PlaceCallOnHold, PHONE_NUMBER)
    Assert.assertEquals(resp, PhoneResponse.Response.OK)
  }

  @Test
  fun takeCallOffHold() {
    val resp = sendPhoneCall(PhoneCall.Operation.TakeCallOffHold, PHONE_NUMBER)
    Assert.assertEquals(resp, PhoneResponse.Response.OK)
  }

  @Test
  fun inboundCallBadNumber() {
    val resp = sendPhoneCall(PhoneCall.Operation.InitCall, "aaa")
    Assert.assertEquals(resp, PhoneResponse.Response.BadNumber)
  }

  fun sendPhoneCall(op: PhoneCall.Operation, number: String): PhoneResponse.Response {
    val resp =
      EmulatorController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
        .sendPhone(PhoneCall.newBuilder().setOperation(op).setNumber(number).build())

    return resp.getResponse()
  }
}

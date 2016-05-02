package com.android.devtools.systemimage.uitest.utils;

import com.google.common.base.Stopwatch;

import android.os.SystemClock;

import java.util.concurrent.TimeUnit;

/**
 * Generic wait class which allows tests to await expected conditions becoming true.
 * <p>
 * Expected use:
 *    new wait(timeout, polltime).until(expectedCondition);
 */
public class Wait {
  private static final long DEFAULT_WAIT_TIME = TimeUnit.MILLISECONDS.convert(3L, TimeUnit.SECONDS);
  private static final long DEFAULT_POLL_TIME =
      TimeUnit.MILLISECONDS.convert(100L, TimeUnit.MILLISECONDS);

  private long timeout;
  private long polltime;

  public interface ExpectedCondition {
    /**
     * Interface method to check if the condition meets.
     * @return true if waited on condition holds,
     * or false will cause wait to block and invoke again after the poll time.
     * @throws Exception
     */
    boolean isTrue() throws Exception;
  }

  public Wait() {
    this(DEFAULT_WAIT_TIME, DEFAULT_POLL_TIME);
  }

  public Wait(long timeout) {
    this(timeout, DEFAULT_POLL_TIME);
  }

  public Wait(long timeout, long polltime) {
    this.timeout = timeout;
    this.polltime = polltime;
  }

  /**
   * Polls the given expected condition at the given poll ratail either
   * the given ExpectedCondition's isTrue method returns true or timeout is
   * reached.
   * @param expectedCondition the expected condition to meet
   * @return {@code true} if the given ExpectedCondition's isTrue method returns
   * true before timeout is reached, or {@code false} otherwise.
   * @throws Exception
   */
  public boolean until(ExpectedCondition expectedCondition) throws Exception {
    Stopwatch stopwatch = Stopwatch.createStarted();
    while (stopwatch.elapsed(TimeUnit.MILLISECONDS) < timeout) {
      if (expectedCondition.isTrue()) {
        return true;
      }
      SystemClock.sleep(polltime);
    }
    return false;
  }
}

// Copyright 2025 The Android Open Source Project
//
// This software is licensed under the terms of the GNU General Public
// License version 2, as published by the Free Software Foundation, and
// may be copied, distributed, and modified under those terms.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.

#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>

@interface PowerMonitor : NSObject

- (void)startMonitoring;
- (void)stopMonitoring;
- (void)checkPowerState;

@property (nonatomic, strong) NSTimer *timer;
@property (nonatomic, strong) NSSpeechSynthesizer *speechSynthesizer; // TTS engine

@end

@implementation PowerMonitor

- (void)startMonitoring {
    self.timer = [NSTimer scheduledTimerWithTimeInterval:1.0 // Check every second
                          target:self
                          selector:@selector(checkPowerState)
                          userInfo:nil
                          repeats:YES];
    self.speechSynthesizer = [[NSSpeechSynthesizer alloc] init];
    NSLog(@"Power monitoring started.");
}

- (void)stopMonitoring {
    [self.timer invalidate];
    self.timer = nil;
    self.speechSynthesizer = nil;

    NSLog(@"Power monitoring stopped.");
}

- (void)checkPowerState {
    NSTask *task = [[NSTask alloc] init];
    [task setLaunchPath:@"/usr/bin/pmset"];
    [task setArguments:@[@"-g", @"batt"]]; // Get battery status

    NSPipe *pipe = [NSPipe pipe];
    [task setStandardOutput:pipe];

    [task launch];

    NSData *data = [[pipe fileHandleForReading] readDataToEndOfFile];
    NSString *output = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];

    [task waitUntilExit];

    if (output) {
        if ([output containsString:@"AC Power"]) {
            NSLog(@"Power cable connected. AC Power.");
        } else if ([output containsString:@"Battery Power"]) {
            NSLog(@"Power cable disconnected. Battery Power.");
            // TODO: Send bug after 5 minutes of being unplugged?
            [self.speechSynthesizer startSpeakingString:@"You unplugged me! How dare you!"];
            [NSThread sleepForTimeInterval:3.0];
        } else {
            NSLog(@"pmset output: %@", output); //For debugging if you get unexpected results
        }
    } else {
        NSLog(@"Error getting power state.");
    }
}

@end

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        PowerMonitor *monitor = [[PowerMonitor alloc] init];
        [monitor startMonitoring];

        [[NSRunLoop currentRunLoop] run];

        [monitor stopMonitoring];
    }
    return 0;
}

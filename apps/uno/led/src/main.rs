#![no_std]
#![no_main]

use panic_halt as _;

#[arduino_hal::entry]
fn main() -> ! {
    let dp = arduino_hal::Peripherals::take().unwrap();
    let pins = arduino_hal::pins!(dp);

    // assign red, green, and blue pins to digital PWM
    let red = pins.d6.into_output();
    let green = pins.d5.into_output();
    let blue = pins.d3.into_output();

    loop {
        red.set_duty(200);
        green.set_duty(200);
        blue.set_duty(50);
    }
}

#![no_std]
#![no_main]

use panic_halt as _;

#[avr_device::entry]
fn main() -> ! {
    // initialize
    let dp = avr_device::atmega328p::Peripherals::take().unwrap();

    // set pin as output
    // PB5 is set to the LED output on the board
    dp.PORTB.ddrb().write(|w| w.pb5().set_bit());
    // start the clock with 1024 prescale
    dp.TC0.tccr0b().write(|w| w.cs0().prescale_1024());

    let mut overflows: u8 = 0;
    loop {
        // wait for next overflow
        // does nothing during wait though, so not optimal
        while dp.TC0.tifr0().read().tov0().bit_is_clear() {}
        // resets the overflow when 255 is reached
        // and increments counter
        dp.TC0.tifr0().write(|w| w.tov0().set_bit());
        overflows += 1;

        // equates to 500ms
        if overflows >= 120 {
            overflows = 0;
            // Toggle PB5
            dp.PORTB.pinb().write(|w| w.pb5().set_bit());
        }            
    }
}

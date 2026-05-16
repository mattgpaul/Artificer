#![no_std]
#![no_main]

#[avr_device::entry]
fn main() -> ! {
    // initialize
    let dp = avr_device::atmega328p::Peripherals.take().unwrap();

    // set pin as output
    // PB5 is set to the LED output on the board
    dp.PORTB.ddrb.write(|w| w.pb5().set_bit());
    
    
    loop {
        //toggle high

        //toggle low
        
    }
}

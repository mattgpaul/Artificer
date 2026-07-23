use embedded_hal::digital::InputPin;
use crate::button::{Button, ButtonError};

/// How the pin level maps to "pressed".
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[cfg_attr(feature = "defmt", derive(defmt::Format))]
pub enum Polarity {
    /// Pressed == pin HIGH (e.g. switch wired to VCC).
    ActiveHigh,
    /// Pressed == pin LOW (e.g. switch to ground with a pull-up — the usual
    /// keyboard wiring).
    ActiveLow,
}

/// A single key on a keyboard: an input pin, its wiring polarity, and the
/// character it represents. Implements [`Button`], so it gets the debounce /
/// tap / hold state machine for free.
pub struct Key<P: InputPin> {
    pin: P,
    polarity: Polarity,
    code: char,
}

impl<P: InputPin> Key<P> {
    pub fn new(pin: P, polarity: Polarity, code: char) -> Self {
        Self { pin, polarity, code }
    }

    /// The character this key represents.
    pub fn code(&self) -> char {
        todo!("return self.code")
    }
}

impl<P: InputPin> Button for Key<P> {
    fn is_pressed(&mut self) -> Result<bool, ButtonError> {
        // Read `self.pin`, interpret the level against `self.polarity`, and map
        // any pin read error to `ButtonError::ActuationError`.
        todo!("read the pin and interpret it per self.polarity")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    extern crate std;

    #[derive(Debug, Clone, Copy)]
    struct FakePinError;

    impl embedded_hal::digital::Error for FakePinError {
        fn kind(&self) -> embedded_hal::digital::ErrorKind {
            embedded_hal::digital::ErrorKind::Other
        }
    }

    /// `level` is the value `is_high()` reports; `is_low()` is its negation, so
    /// the fake behaves correctly whether `is_pressed` is implemented via
    /// `is_high()` or `is_low()`, and for any number of reads.
    struct FakePin {
        level: Result<bool, FakePinError>,
    }

    impl embedded_hal::digital::ErrorType for FakePin {
        type Error = FakePinError;
    }

    impl InputPin for FakePin {
        fn is_high(&mut self) -> Result<bool, Self::Error> {
            self.level
        }

        fn is_low(&mut self) -> Result<bool, Self::Error> {
            self.level.map(|high| !high)
        }
    }

    fn key(level: Result<bool, FakePinError>, polarity: Polarity) -> Key<FakePin> {
        Key::new(FakePin { level }, polarity, 'A')
    }

    #[test]
    fn active_high_high_is_pressed() {
        let mut k = key(Ok(true), Polarity::ActiveHigh);
        assert_eq!(k.is_pressed().unwrap(), true);
    }

    #[test]
    fn active_high_low_is_not_pressed() {
        let mut k = key(Ok(false), Polarity::ActiveHigh);
        assert_eq!(k.is_pressed().unwrap(), false);
    }

    #[test]
    fn active_low_low_is_pressed() {
        let mut k = key(Ok(false), Polarity::ActiveLow);
        assert_eq!(k.is_pressed().unwrap(), true);
    }

    #[test]
    fn active_low_high_is_not_pressed() {
        let mut k = key(Ok(true), Polarity::ActiveLow);
        assert_eq!(k.is_pressed().unwrap(), false);
    }

    #[test]
    fn pin_error_maps_to_actuation_error() {
        let mut k = key(Err(FakePinError), Polarity::ActiveHigh);
        assert!(matches!(k.is_pressed(), Err(ButtonError::ActuationError)));
    }

    #[test]
    fn code_returns_configured_char() {
        let k = key(Ok(true), Polarity::ActiveHigh);
        assert_eq!(k.code(), 'A');
    }
}

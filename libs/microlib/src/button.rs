use embedded_hal_async::delay::DelayNs;

#[derive(Debug)]
#[cfg_attr(feature = "defmt", derive(defmt::Format))]
pub enum ButtonError {
    ActuationError,
    InvalidTimer,
}

pub enum ButtonState {
    Idle,
    Bounce,
    Tap,
    Hold,
}

pub trait Button {
    fn is_pressed(&mut self) -> Result<bool, ButtonError>;
    async fn get_button_state<D: DelayNs>(
        &mut self,
        delay: &mut D,
        debounce_limit_ms: u32,
        tap_limit_ms: u32,
    ) -> Result<ButtonState, ButtonError> {
        if debounce_limit_ms >= tap_limit_ms {
            return Err(ButtonError::InvalidTimer)
        }
        if !self.is_pressed()? {
            // button not pressed, return 
            return Ok(ButtonState::Idle)
        }
        delay.delay_ms(debounce_limit_ms).await;
        if !self.is_pressed()? {
            return Ok(ButtonState::Bounce)
        }
        delay.delay_ms(tap_limit_ms - debounce_limit_ms).await;
        if !self.is_pressed()? {
            return Ok(ButtonState::Tap)
        } 
        Ok(ButtonState::Hold)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    extern crate std;
    use std::rc::Rc;
    use std::cell::RefCell;
    use std::collections::VecDeque;
    use std::vec::Vec;
    use std::vec;
    use futures::executor::block_on;

    #[derive(Debug, Clone, PartialEq)]
    enum Event {
        Read(bool),
        Delay(u32),
    }

    struct FakeButton {
        events: Rc<RefCell<Vec<Event>>>,
        readings: VecDeque<Result<bool, ButtonError>>,
    }

    struct FakeDelay {
        events: Rc<RefCell<Vec<Event>>>,
    }

    impl Button for FakeButton {
        fn is_pressed(&mut self) -> Result<bool, ButtonError> {
            // Panics if the state machine reads the pin more times than scripted,
            // which catches accidental extra reads.
            let reading = self
                .readings
                .pop_front()
                .expect("is_pressed called more times than scripted");
            let value = reading?;
            self.events.borrow_mut().push(Event::Read(value));
            Ok(value)
        }
    }

    impl DelayNs for FakeDelay {
        async fn delay_ns(&mut self, ns: u32) {
            self.events.borrow_mut().push(Event::Delay(ns / 1000 / 1000));
        }
    }

    /// Drives `get_button_state` with a scripted sequence of pin readings and
    /// returns both the resulting state and the interleaved log of reads/delays.
    fn run(
        readings: Vec<Result<bool, ButtonError>>,
        debounce_limit_ms: u32,
        tap_limit_ms: u32,
    ) -> (Result<ButtonState, ButtonError>, Vec<Event>) {
        let shared = Rc::new(RefCell::new(Vec::new()));
        let mut button = FakeButton {
            events: Rc::clone(&shared),
            readings: readings.into(),
        };
        let mut delay = FakeDelay { events: Rc::clone(&shared) };
        let result = block_on(button.get_button_state(&mut delay, debounce_limit_ms, tap_limit_ms));
        let events = shared.borrow().clone();
        (result, events)
    }

    #[test]
    fn debounce_equal_to_tap_is_invalid() {
        let (result, events) = run(vec![Ok(true)], 50, 50);
        assert!(matches!(result, Err(ButtonError::InvalidTimer)));
        // Timer validation must happen before the pin is ever read.
        assert!(events.is_empty());
    }

    #[test]
    fn debounce_greater_than_tap_is_invalid() {
        let (result, events) = run(vec![Ok(true)], 100, 50);
        assert!(matches!(result, Err(ButtonError::InvalidTimer)));
        assert!(events.is_empty());
    }

    #[test]
    fn not_pressed_is_idle() {
        let (result, events) = run(vec![Ok(false)], 10, 100);
        assert!(matches!(result, Ok(ButtonState::Idle)));
        // Idle path reads once and never delays.
        assert_eq!(events, vec![Event::Read(false)]);
    }

    #[test]
    fn released_after_debounce_is_bounce() {
        let (result, events) = run(vec![Ok(true), Ok(false)], 10, 100);
        assert!(matches!(result, Ok(ButtonState::Bounce)));
        assert_eq!(
            events,
            vec![Event::Read(true), Event::Delay(10), Event::Read(false)]
        );
    }

    #[test]
    fn released_after_tap_window_is_tap() {
        let (result, events) = run(vec![Ok(true), Ok(true), Ok(false)], 10, 100);
        assert!(matches!(result, Ok(ButtonState::Tap)));
        // The second delay must be `tap - debounce` (90), not the full tap limit.
        assert_eq!(
            events,
            vec![
                Event::Read(true),
                Event::Delay(10),
                Event::Read(true),
                Event::Delay(90),
                Event::Read(false),
            ]
        );
    }

    #[test]
    fn still_pressed_is_hold() {
        let (result, events) = run(vec![Ok(true), Ok(true), Ok(true)], 10, 100);
        assert!(matches!(result, Ok(ButtonState::Hold)));
        assert_eq!(
            events,
            vec![
                Event::Read(true),
                Event::Delay(10),
                Event::Read(true),
                Event::Delay(90),
                Event::Read(true),
            ]
        );
    }

    #[test]
    fn zero_debounce_is_valid() {
        let (result, events) = run(vec![Ok(true), Ok(true), Ok(false)], 0, 100);
        assert!(matches!(result, Ok(ButtonState::Tap)));
        // A zero debounce still delays (by 0) and the tap window is the full limit.
        assert_eq!(
            events,
            vec![
                Event::Read(true),
                Event::Delay(0),
                Event::Read(true),
                Event::Delay(100),
                Event::Read(false),
            ]
        );
    }

    #[test]
    fn minimal_tap_window_is_valid() {
        // debounce one less than tap: the second delay should be exactly 1.
        let (result, events) = run(vec![Ok(true), Ok(true), Ok(true)], 99, 100);
        assert!(matches!(result, Ok(ButtonState::Hold)));
        assert_eq!(
            events,
            vec![
                Event::Read(true),
                Event::Delay(99),
                Event::Read(true),
                Event::Delay(1),
                Event::Read(true),
            ]
        );
    }

    #[test]
    fn error_on_first_read_propagates() {
        let (result, events) = run(vec![Err(ButtonError::ActuationError)], 10, 100);
        assert!(matches!(result, Err(ButtonError::ActuationError)));
        // Error surfaced before any delay.
        assert!(events.is_empty());
    }

    #[test]
    fn error_after_debounce_propagates() {
        let (result, events) =
            run(vec![Ok(true), Err(ButtonError::ActuationError)], 10, 100);
        assert!(matches!(result, Err(ButtonError::ActuationError)));
        assert_eq!(events, vec![Event::Read(true), Event::Delay(10)]);
    }

    #[test]
    fn error_after_tap_window_propagates() {
        let (result, events) = run(
            vec![Ok(true), Ok(true), Err(ButtonError::ActuationError)],
            10,
            100,
        );
        assert!(matches!(result, Err(ButtonError::ActuationError)));
        assert_eq!(
            events,
            vec![
                Event::Read(true),
                Event::Delay(10),
                Event::Read(true),
                Event::Delay(90),
            ]
        );
    }

    #[test]
    fn invalid_timer_checked_before_reading_pin() {
        // Even with a pressed button, an invalid timer short-circuits without a read.
        let (result, events) = run(vec![Ok(true)], 100, 100);
        assert!(matches!(result, Err(ButtonError::InvalidTimer)));
        assert!(events.is_empty());
    }
}

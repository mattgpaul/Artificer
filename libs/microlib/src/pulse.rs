use embedded_hal_async::delay::DelayNs;
use futures::executor::block_on;

#[derive(Debug)]
#[cfg_attr(feature = "defmt", derive(defmt::Format))]
pub enum PulseError {
    ActuationError,
    UnsupportedChar(char),
}

pub trait Pulse {
    fn on(&mut self) -> Result<(), PulseError>;
    fn off(&mut self) -> Result<(), PulseError>;
    async fn blink<D: DelayNs>(
        &mut self,
        delay: &mut D,
        period_ms: u32,
    ) -> Result<(), PulseError> {
        self.on()?;
        delay.delay_ms(period_ms).await;
        self.off()?;
        delay.delay_ms(period_ms).await;
        Ok(())
    } 

    async fn send_morse<D: DelayNs>(
        &mut self,
        delay: &mut D,
        msg: &str,
        baseline_dit_ms: u32,
    ) -> Result<(), PulseError> {
        //check if the message is valid first
        for c in msg.chars() {
            morse_from(c).ok_or(PulseError::UnsupportedChar(c))?;
        }

        let mut prev_was_letter: bool = false;
        for c in msg.chars() {
            let code = morse_from(c).unwrap();
            if code == "/" {
                // word gap, silent for 7 ticks
                delay.delay_ms(baseline_dit_ms * 7).await;
                prev_was_letter = false;
                continue
            }

            if prev_was_letter {
                // letter gap, silent for 3 ticks
                delay.delay_ms(baseline_dit_ms * 3).await;
            }

            prev_was_letter = true;
            let mut symbols = code.bytes().peekable();
            while let Some(sym) = symbols.next() {
                let on_units = if sym == b'-' { 3 } else { 1 };
                self.on()?;
                delay.delay_ms(baseline_dit_ms * on_units).await;
                self.off()?;
                if symbols.peek().is_some() {
                    delay.delay_ms(baseline_dit_ms).await;
                }
            }
        }
        Ok(())
    }

}

fn morse_from(c: char) -> Option<&'static str> {
    Some(match c.to_ascii_uppercase() {
        'A' => ".-",
        'B' => "-...",
        'C' => "-.-.",
        'D' => "-..",
        'E' => ".",
        'F' => "..-.",
        'G' => "--.",
        'H' => "....",
        'I' => "..",
        'J' => ".---",
        'K' => "-.-",
        'L' => ".-..",
        'M' => "--",
        'N' => "-.",
        'O' => "---",
        'P' => ".--.",
        'Q' => "--.-",
        'R' => ".-.",
        'S' => "...",
        'T' => "-",
        'U' => "..-",
        'V' => "...-",
        'W' => ".--",
        'X' => "-..-",
        'Y' => "-.--",
        'Z' => "--..",
        '1' => ".----",
        '2' => "..---",
        '3' => "...--",
        '4' => "....-",
        '5' => ".....",
        '6' => "-....",
        '7' => "--...",
        '8' => "---..",
        '9' => "----.",
        '0' => "-----",
        ' ' => "/",
        _ => return None,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Debug, PartialEq)]
    enum Event {
        On,
        Off,
        Delay(u32),
    }

    struct FakePulse {
        events: Vec<Event>,
    }

    struct FakeDelay {
        durations: Vec<u32>,
    }

    impl Pulse for FakePulse {
        fn on(&mut self) -> Result<(), PulseError>  {
            self.events.push(Event::On);
            Ok(())
        }

        fn off(&mut self) -> Result<(), PulseError>  {
            self.events.push(Event::Off);
            Ok(())
        }
    }

    impl DelayNs for FakeDelay {
        async fn delay_ns(&mut self, ns: u32) {
            self.durations.push(ns / 1000 / 1000);
        }
    }
    
    #[test]
    fn test_on_off_functions() {
        let mut fake = FakePulse { events: Vec::new() };
        fake.on().unwrap();
        fake.off().unwrap();
        assert_eq!(fake.events, vec![Event::On, Event::Off])
    }

    #[test]
    fn test_blink() {
        let mut fake = FakePulse { events: Vec::new() };
        let mut fake_delay = FakeDelay { durations: Vec::new() };
        block_on(fake.blink(&mut fake_delay, 300)).unwrap();

        assert_eq!(fake.events, vec![Event::On, Event::Off]);
        assert_eq!(fake_delay.durations, vec![300, 300]);
    }

    #[test]
    fn morse_from_maps_a_known_letter() {
        assert_eq!(morse_from('A'), Some(".-"));
    }

    #[test]
    fn morse_from_handles_unsupported_char() {
        assert_eq!(morse_from('@'), None);
    }

    #[test]
    fn morse_from_handles_lowercase() {
        assert_eq!(morse_from('a'), Some(".-"));
    }
    
}

use embedded_hal_async::delay::DelayNs;

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

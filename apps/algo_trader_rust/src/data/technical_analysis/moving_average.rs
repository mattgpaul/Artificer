pub enum MovingAverageError {
    WindowZero,
    WindowExceedsData { window: usize, len: usize},
}


pub fn simple_moving_average(
    data: &[f64],
    window: usize,
) -> Result<impl Iterator<Item = f64> + '_, MovingAverageError> {
     if window == 0 {
         return Err(MovingAverageError::WindowZero)
     }
     if window > data.len() {
         return Err(MovingAverageError::WindowExceedsData { window, len: data.len() });
     }
     Ok(data.windows(window)
         .map(|w| w.iter().sum::<f64>() / w.len() as f64))
} 

pub fn exponential_moving_average(
    data: &[f64],
    window: usize,
) -> Result<impl Iterator<Item = f64> + '_, MovingAverageError> {
     if window == 0 {
         return Err(MovingAverageError::WindowZero)
     }
     if window > data.len() {
         return Err(MovingAverageError::WindowExceedsData { window, len: data.len() });
     }

     let seed = data[..window].iter().sum::<f64>() / window as f64;
     let multiplier = 2.0 / (window + 1) as f64;

     Ok(std::iter::once(seed).chain(
             data[window..].iter().scan(seed, move |prev_ema, &value| {
                 let ema = value * multiplier + *prev_ema * (1.0 - multiplier);
                 *prev_ema = ema;
                 Some(ema)
             })
     ))
    
}

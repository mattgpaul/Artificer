pub enum MovingAverageError {
    WindowZero,
    WindowExceedsData { window: usize, len: usize },
}

pub fn simple_moving_average(data: &[f64], window: usize) -> Result<Vec<f64>, MovingAverageError> {
    if window == 0 {
        return Err(MovingAverageError::WindowZero);
    }
    if window > data.len() {
        return Err(MovingAverageError::WindowExceedsData { window, len: data.len() });
    }
    let result = data
        .windows(window)
        .map(|w| w.iter().sum::<f64>() / w.len() as f64)
        .collect();
    Ok(result)
}

pub fn exponential_moving_average(data: &[f64], window: usize) -> Result<Vec<f64>, MovingAverageError> {
    if window == 0 {
        return Err(MovingAverageError::WindowZero);
    }
    if window > data.len() {
        return Err(MovingAverageError::WindowExceedsData { window, len: data.len() });
    }

    let seed = data[..window].iter().sum::<f64>() / window as f64;
    let multiplier = 2.0 / (window + 1) as f64;

    let mut result = vec![seed];
    let mut prev_ema = seed;
    for &value in &data[window..] {
        let ema = value * multiplier + prev_ema * (1.0 - multiplier);
        result.push(ema);
        prev_ema = ema;
    }
    Ok(result)
}


use crate::data::technical_analysis::moving_average::simple_moving_average;

pub fn sma_crossover(data: &[f64], short_window: usize, long_window: usize) -> bool {
    let Ok(short_ma) = simple_moving_average(data, short_window) else { return false };
    let Ok(long_ma) = simple_moving_average(data, long_window) else { return false };

    if short_ma.len() < 2 || long_ma.len() < 2 {
        return false;
    }

    let short_prev = short_ma[short_ma.len() - 2];
    let short_last = short_ma[short_ma.len() - 1];
    let long_prev = long_ma[long_ma.len() - 2];
    let long_last = long_ma[long_ma.len() - 1];

    short_prev <= long_prev && short_last > long_last
}


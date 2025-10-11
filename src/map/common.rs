pub(super) fn round(value: f32, digits: usize) -> f32 {
    let factor = 10f32.powi(digits as i32);
    (value * factor).round() / factor
}

fn alpha() -> i32 {
    1
}

fn beta(x: i32) -> i32 {
    x + 1
}

fn gamma() -> i32 {
    beta(alpha())
}

#[derive(Debug, Clone, PartialEq)]
pub struct CpuCoreTelemetry {
    pub core_num: usize,
    pub usage: u64,
    user: u64,
    nice: u64,
    system: u64,
    idle: u64,
    iowait: u64,
    irq: u64,
    softirq: u64,
    steal: u64,
    guest: u64,
    guest_nice: u64,
}

impl CpuCoreTelemetry {
    pub fn new(core_num: usize) -> Self {
        CpuCoreTelemetry {
            core_num,
            usage: 0,
            user: 0,
            nice: 0,
            system: 0,
            idle: 0,
            iowait: 0,
            irq: 0,
            softirq: 0,
            steal: 0,
            guest: 0,
            guest_nice: 0,
        }
    }

    pub fn update_from_stat(&mut self, stat_contents: &str) {
        let prefix = format!("cpu{} ", self.core_num);
        let Some(line) = stat_contents.lines().find(|l| l.starts_with(&prefix)) else {
            return;
        };
        let mut parts = line.split_whitespace().skip(1);
        let mut next = || parts.next().and_then(|s| s.parse::<u64>().ok()).unwrap_or(0);

        let previous_total = self.get_total_time();
        let previous_idle = self.get_idle_time();

        self.user       = next();
        self.nice       = next();
        self.system     = next();
        self.idle       = next();
        self.iowait     = next();
        self.irq        = next();
        self.softirq    = next();
        self.steal      = next();
        self.guest      = next();
        self.guest_nice = next();

        let delta_total = self.get_total_time().saturating_sub(previous_total);
        let delta_idle  = self.get_idle_time().saturating_sub(previous_idle);
        self.usage = if delta_total > 0 {
            ((delta_total - delta_idle) * 100 + delta_total / 2) / delta_total
        } else {
            0
        };
    }

    fn get_total_time(&self) -> u64 {
        self.user + self.nice + self.system + self.idle + self.iowait
            + self.irq + self.softirq + self.steal + self.guest + self.guest_nice
    }

    fn get_idle_time(&self) -> u64 {
        self.idle + self.iowait
    }
}
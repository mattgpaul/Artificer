use std::fs;
use std::io::BufRead;
use std::io::BufReader;
use std::time::Instant;

#[derive(Debug, Clone)]
pub struct CpuInfo {
    pub cpu_usage: f64,
    pub cpu_count: usize,
    pub load_average: [f64; 3],
    pub timestamp: Instant,
}

impl CpuInfo {
    pub fn new() -> Self {
        CpuInfo {
            cpu_usage: 0.0,
            cpu_count: num_cpus::get(),
            load_average: [0.0, 0.0, 0.0],
            timestamp: Instant::now(),
        }
    }
}

pub struct CpuMonitor {
    last_idle: u64,
    last_total: u64,
}

impl CpuMonitor {
    pub fn new() -> Self {
        let mut monitor = CpuMonitor {
            last_idle: 0,
            last_total: 0,
        };
        // Initialize with current values
        let _ = monitor.update();
        monitor
    }

    pub fn update(&mut self) -> Result<CpuInfo, Box<dyn std::error::Error>> {
        let cpu_info = self.get_cpu_info()?;
        self.last_idle = cpu_info.1;
        self.last_total = cpu_info.2;
        Ok(cpu_info.0)
    }

    fn get_cpu_info(&self) -> Result<(CpuInfo, u64, u64), Box<dyn std::error::Error>> {
        let file = fs::File::open("/proc/stat")?;
        let reader = BufReader::new(file);
        
        let mut lines = reader.lines();
        let first_line = lines.next().unwrap().unwrap();
        
        let parts: Vec<&str> = first_line.split_whitespace().collect();
        if parts.len() < 5 {
            return Err("Invalid /proc/stat format".into());
        }
        
        let user = parts[1].parse::<u64>()?;
        let nice = parts[2].parse::<u64>()?;
        let system = parts[3].parse::<u64>()?;
        let idle = parts[4].parse::<u64>()?;
        let iowait = parts[5].parse::<u64>()?;
        let irq = parts[6].parse::<u64>()?;
        let softirq = parts[7].parse::<u64>()?;
        
        let total = user + nice + system + idle + iowait + irq + softirq;
        let idle = idle + iowait;
        
        let mut cpu_info = CpuInfo::new();
        cpu_info.timestamp = Instant::now();
        
        // Calculate CPU usage percentage
        if self.last_total > 0 {
            let total_diff = total - self.last_total;
            let idle_diff = idle - self.last_idle;
            cpu_info.cpu_usage = 100.0 * (total_diff as f64 - idle_diff as f64) / total_diff as f64;
        }
        
        // Get load average
        let loadavg = fs::read_to_string("/proc/loadavg")?;
        let load_parts: Vec<&str> = loadavg.split_whitespace().collect();
        if load_parts.len() >= 3 {
            cpu_info.load_average[0] = load_parts[0].parse::<f64>()?;
            cpu_info.load_average[1] = load_parts[1].parse::<f64>()?;
            cpu_info.load_average[2] = load_parts[2].parse::<f64>()?;
        }
        
        Ok((cpu_info, idle, total))
    }
}

impl Default for CpuMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cpu_info_creation() {
        let cpu_info = CpuInfo::new();
        assert_eq!(cpu_info.cpu_count, num_cpus::get());
        assert_eq!(cpu_info.cpu_usage, 0.0);
    }

    #[test]
    fn test_cpu_monitor_creation() {
        let monitor = CpuMonitor::new();
        assert_eq!(monitor.last_idle, 0);
        assert_eq!(monitor.last_total, 0);
    }
}
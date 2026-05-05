use crate::models;
use crate::traits::telemetry::Telemetry;
use models::cpu::Cpu;
use models::gpu::Gpu;
use models::memory::Memory;
use models::network::Network;
use models::storage::Storage;

pub struct Service {
    pub cpu: Cpu,
    pub gpu: Gpu,
    pub memory: Memory,
    pub network: Network,
    pub storage: Storage,
}

impl Service {
    pub fn new() -> Self {
        Service {
            cpu: Cpu::new().expect("Could not initialize CPU"),
            gpu: Gpu::new().expect("Failed to initialize GPU"),
            memory: Memory::new().expect("Failed to initialize Memory"),
            network: Network::new().expect("Failed to initialize Network"),
            storage: Storage::new().expect("Failed to initialize Storage"),
        }
    }
    // to be run every tick
    pub fn tick(&mut self) {
        self.cpu.refresh();
        self.gpu.refresh();
        self.memory.refresh();
        self.network.refresh();
        self.storage.refresh();
    }
}
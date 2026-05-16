use std::default::Default;

use crate::models;
use crate::traits::telemetry::Telemetry;
use models::cpu::Cpu;
use models::gpu::Gpu;
use models::memory::Memory;
use models::network::Network;
use models::storage::Storage;

pub struct Service {
    cpu: Cpu,
    gpu: Gpu,
    memory: Memory,
    network: Network,
    storage: Storage,
}

impl Service {
    // to be run every tick
    pub fn tick(&mut self) {
        self.cpu.refresh();
        self.gpu.refresh();
        self.memory.refresh();
        self.network.refresh();
        self.storage.refresh();
    }
    
    pub fn cpu(&self) -> &Cpu { &self.cpu }
    pub fn gpu(&self) -> &Gpu { &self.gpu }
    pub fn memory(&self) -> &Memory { &self.memory }
    pub fn network(&self) -> &Network { &self.network }
    pub fn storage(&self) -> &Storage { &self.storage }
}

impl Default for Service {
    fn default() -> Self {
        Service {
            cpu: Cpu::new().expect("Could not initialize CPU"),
            gpu: Gpu::new().expect("Failed to initialize GPU"),
            memory: Memory::new().expect("Failed to initialize Memory"),
            network: Network::new().expect("Failed to initialize Network"),
            storage: Storage::new().expect("Failed to initialize Storage"),
        }
    }
}

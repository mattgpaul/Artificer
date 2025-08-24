//ARM-Cortex-A72 System Registers
#pragma once
#include <cstdint>

namespace cortex_a72 {
    namespace system_registers {
        //Cpu info
        inline uint64_t read_midr_el1() {
            uint64_t result;
            asm volatile("mrs %0, midr_el1" : "=r" (result));
            return result;
        }
        
        //Number of cores
        inline uint64_t read_mpidr_el1() {
            uint64_t result;
            asm volatile("mrs %0, mpidr_el1" : "=r" (result));
            return result;
        }

        //Performance monitor
        inline uint64_t read_pmccntr_el0() {
            uint64_t result;
            asm volatile("mrs %0, pmccntr_el0" : "=r" (result));
            return result;
        }
    }
}
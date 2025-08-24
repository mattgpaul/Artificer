// ARM Cortex A72 header class
#pragma once
#include "cpu.hpp"
#include "registers/system_registers.hpp"

class ArmCortexA72 : public Cpu {
public:
    // From Component base class
    std::string getName() const override {
        return "ARM-Cortex_A72";
    }

    std::string getType() const override {
        return "component::processor::cpu";
    }

    int getMaxClockSpeed() const override {
        return 1800; //MHz
    }

    int getNumCores() const override {
        return 4;
    }

    float getTemp() override {
        return 50.0;
    }

    int getUsage() override {
        return -1;
    }

};
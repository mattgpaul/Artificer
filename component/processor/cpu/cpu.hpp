//Base class for a CPU
#pragma once
#include "processor.hpp"

class Cpu : public Processor {
public:
    virtual ~Cpu() = default;

    virtual int getNumCores() const = 0;
    virtual float getTemp() = 0;
    virtual int getUsage() = 0;

protected:
    Cpu() = default;
};
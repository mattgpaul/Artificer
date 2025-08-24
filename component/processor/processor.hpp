//Processor base class
#pragma once
#include "component.hpp"

class Processor : public Component {
public:
    virtual ~Processor() = default;

    virtual int getMaxClockSpeed() const = 0;

protected:
    Processor() = default;
};
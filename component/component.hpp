// Component base class
#pragma once
#include <string>

class Component {
public:
    //Virtual destructor
    virtual ~Component() = default;

    //Virtual functions to be implemented by child classes
    virtual std::string getName() const = 0;
    virtual std::string getType() const = 0;

protected:
    //Protected constructor
    Component() = default;
};
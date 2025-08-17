// telemetry_message.hpp - TelemetryMessage class declaration
#pragma once

#include <string>

namespace telemetry {

class TelemetryMessage {
public:
    TelemetryMessage();
    
    std::string to_string() const;
    
private:
    std::string message_id_;
    
    static std::string generate_message_id();
};

}

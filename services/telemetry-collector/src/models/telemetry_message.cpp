// telemetry_message.cpp - TelemetryMessage class implementation  
#include "telemetry_message.hpp"

#include <sstream>
#include <random>

namespace telemetry {

TelemetryMessage::TelemetryMessage() 
    : message_id_(generate_message_id())
{
}

std::string TelemetryMessage::to_string() const {
    std::ostringstream oss;
    oss << "TelemetryMessage{id=" << message_id_ << "}";
    return oss.str();
}

std::string TelemetryMessage::generate_message_id() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(1000, 9999);
    
    return "msg-" + std::to_string(dis(gen));
}

}

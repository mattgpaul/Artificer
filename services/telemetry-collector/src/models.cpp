/**
 * @file models.cpp
 * @brief Implementation of telemetry data models - Clean C++
 * 
 * LEARNING OBJECTIVES:
 * - Constructor initialization lists
 * - String formatting and manipulation
 * - Random number generation
 * - Time handling in C++
 */

#include "models.hpp"

#include <sstream>
#include <iomanip>
#include <random>
#include <stdexcept>

namespace telemetry {

// TelemetryMessage Implementation

TelemetryMessage::TelemetryMessage(int schema_version, std::string service_name, std::string hostname)
    : schema_version_(schema_version)
    , service_name_(std::move(service_name))  // Move constructor for efficiency
    , hostname_(std::move(hostname))
    , message_id_(generate_message_id())      // Generate unique ID
    , timestamp_(std::chrono::system_clock::now())  // Current time
{
    // Constructor body - use for validation if needed
    if (schema_version_ <= 0) {
        throw std::invalid_argument("Schema version must be positive");
    }
    if (service_name_.empty()) {
        throw std::invalid_argument("Service name cannot be empty");
    }
    if (hostname_.empty()) {
        throw std::invalid_argument("Hostname cannot be empty");
    }
}

std::string TelemetryMessage::to_string() const {
    // Format timestamp for display
    auto time_t = std::chrono::system_clock::to_time_t(timestamp_);
    std::ostringstream oss;
    oss << "TelemetryMessage{";
    oss << "schema_version=" << schema_version_;
    oss << ", service_name=" << service_name_;
    oss << ", hostname=" << hostname_;
    oss << ", message_id=" << message_id_;
    oss << ", timestamp=" << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S");
    oss << "}";
    return oss.str();
}

std::string TelemetryMessage::generate_message_id() {
    // Simple UUID-like ID: timestamp + random number
    // Industry standard would use proper UUID library, but this works for learning
    
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(0, 15);
    static const char hex_chars[] = "0123456789abcdef";
    
    auto now = std::chrono::system_clock::now();
    auto timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();
    
    std::ostringstream oss;
    oss << std::hex << timestamp << "-";
    
    // Add random hex suffix
    for (int i = 0; i < 8; ++i) {
        oss << hex_chars[dis(gen)];
    }
    
    return oss.str();
}

// CpuMetrics Implementation

CpuMetrics::CpuMetrics(double usage_percent, int core_count, double load_average_1m)
    : usage_percent_(usage_percent)
    , core_count_(core_count)
    , load_average_1m_(load_average_1m)
{
    // Input validation - industry standard practice
    if (usage_percent_ < 0.0 || usage_percent_ > 100.0) {
        throw std::invalid_argument("CPU usage percent must be between 0 and 100");
    }
    if (core_count_ <= 0) {
        throw std::invalid_argument("Core count must be positive");
    }
    if (load_average_1m_ < 0.0) {
        throw std::invalid_argument("Load average cannot be negative");
    }
}

std::string CpuMetrics::to_string() const {
    std::ostringstream oss;
    oss << "CpuMetrics{";
    oss << "usage_percent=" << std::fixed << std::setprecision(2) << usage_percent_;
    oss << ", core_count=" << core_count_;
    oss << ", load_average_1m=" << std::fixed << std::setprecision(2) << load_average_1m_;
    oss << "}";
    return oss.str();
}

} // namespace telemetry

/**
 * IMPLEMENTATION COMPLETE - WHAT YOU LEARNED:
 * 
 * 1. CONSTRUCTOR PATTERNS:
 *    - Initialization lists for efficiency
 *    - std::move() for string parameters
 *    - Input validation with exceptions
 * 
 * 2. STRING FORMATTING:
 *    - std::ostringstream for building strings
 *    - std::setprecision() for floating point display
 *    - Time formatting with std::put_time()
 * 
 * 3. RANDOM GENERATION:
 *    - std::random_device for seeding
 *    - std::mt19937 for generation
 *    - Creating simple UUID-like strings
 * 
 * 4. ERROR HANDLING:
 *    - std::invalid_argument for input validation
 *    - RAII ensures cleanup even with exceptions
 * 
 * NEXT STEPS:
 * 1. Build this: bazel build //services/telemetry-collector:telemetry_collector_lib
 * 2. Test in main.cpp by creating objects and printing them
 * 3. Add abstract base classes for collectors and publishers
 * 
 * INDUSTRY PATTERNS DEMONSTRATED:
 * - Clean constructors with validation
 * - Const correctness throughout
 * - Move semantics for efficiency
 * - Clear error messages
 * - Readable string representations
 */

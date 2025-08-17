/**
 * @file models.hpp
 * @brief Core telemetry data models - Industry standard C++ patterns
 * 
 * LEARNING OBJECTIVES:
 * - Modern C++ class design (RAII, SOLID principles)
 * - Const correctness and encapsulation
 * - Value semantics and move semantics
 * - Clean interfaces and dependency injection
 */

#pragma once

#include <string>
#include <chrono>
#include <memory>
#include <vector>

namespace telemetry {

/**
 * @class TelemetryMessage
 * @brief Main container for telemetry data following SOLID principles
 * 
 * INDUSTRY PATTERNS:
 * - Single Responsibility: Only handles message data
 * - Encapsulation: Private data with controlled access
 * - RAII: Automatic resource management
 * - Value semantics: Copyable and movable
 */
class TelemetryMessage {
public:
    // Constructor with all required data
    TelemetryMessage(int schema_version, std::string service_name, std::string hostname);
    
    // Rule of 5: Explicit defaults for modern C++
    ~TelemetryMessage() = default;
    TelemetryMessage(const TelemetryMessage&) = default;
    TelemetryMessage& operator=(const TelemetryMessage&) = default;
    TelemetryMessage(TelemetryMessage&&) = default;
    TelemetryMessage& operator=(TelemetryMessage&&) = default;
    
    // Public interface - const methods for immutable access
    int get_schema_version() const noexcept { return schema_version_; }
    const std::string& get_service_name() const noexcept { return service_name_; }
    const std::string& get_hostname() const noexcept { return hostname_; }
    const std::string& get_message_id() const noexcept { return message_id_; }
    const std::chrono::system_clock::time_point& get_timestamp() const noexcept { return timestamp_; }
    
    // String representation for debugging/logging
    std::string to_string() const;
    
private:
    // Core message data
    int schema_version_;
    std::string service_name_;
    std::string hostname_;
    std::string message_id_;    // Generated UUID
    std::chrono::system_clock::time_point timestamp_;
    
    // Helper to generate UUID-like message ID
    static std::string generate_message_id();
};

/**
 * @class CpuMetrics  
 * @brief CPU telemetry data with value semantics
 * 
 * INDUSTRY PATTERNS:
 * - Value object: Immutable after construction
 * - Clear data ownership
 * - Easy to test and reason about
 */
class CpuMetrics {
public:
    // Constructor with all CPU data
    CpuMetrics(double usage_percent, int core_count, double load_average_1m);
    
    // Default operations
    ~CpuMetrics() = default;
    CpuMetrics(const CpuMetrics&) = default;
    CpuMetrics& operator=(const CpuMetrics&) = default;
    CpuMetrics(CpuMetrics&&) = default;
    CpuMetrics& operator=(CpuMetrics&&) = default;
    
    // Accessors
    double get_usage_percent() const noexcept { return usage_percent_; }
    int get_core_count() const noexcept { return core_count_; }
    double get_load_average_1m() const noexcept { return load_average_1m_; }
    
    // String representation
    std::string to_string() const;
    
private:
    double usage_percent_;
    int core_count_;
    double load_average_1m_;
};

} // namespace telemetry

/**
 * YOUR IMPLEMENTATION TASKS:
 * 
 * 1. Implement TelemetryMessage constructor:
 *    - Store provided parameters
 *    - Generate message_id_ using generate_message_id()
 *    - Set timestamp_ to current time
 * 
 * 2. Implement generate_message_id():
 *    - Create simple UUID-like string (timestamp + random)
 *    - Return as string
 * 
 * 3. Implement to_string() methods:
 *    - Format object data as readable string
 *    - Useful for logging and debugging
 * 
 * 4. Implement CpuMetrics constructor:
 *    - Validate inputs (usage_percent 0-100, etc.)
 *    - Store values
 * 
 * FOCUS: Clean, simple C++ without external dependencies
 * ADD COMPLEXITY LATER: Serialization, networking, etc.
 */

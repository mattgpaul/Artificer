// cpu_metrics.hpp - CpuMetrics class declaration
#pragma once
#include <string>

namespace telemetry {

class CpuMetrics {
public:
    CpuMetrics(double usage_percent, double temperature_celsius);
    
    double get_usage_percent() const;
    double get_temperature() const;
    std::string to_string() const;
    
private:
    double usage_percent_;
    double temperature_celsius_;
};

}

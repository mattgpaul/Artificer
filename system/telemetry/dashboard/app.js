// Telemetry Dashboard - Main Application
const app = {
    PROM_API: '/prom/api/v1',
    UPDATE_INTERVAL: 5000, // 5 seconds
    // No personal defaults here: hostname/user should come from Prometheus labels/metrics.
    updateTimer: null,
    currentHostname: null,
    primaryNetworkDevice: null,
    primaryNetworkIp: null,

    async init() {
        this.currentHostname = await this.detectHostname();
        this.setupNavigation();
        this.updateTime();
        setInterval(() => this.updateTime(), 1000);
        await this.detectPrimaryNetworkDevice();
        this.startUpdates();
    },

    async detectHostname() {
        // Auto-select a hostname from the scraped node-exporter targets.
        // (Future: add dropdown when multiple hosts exist.)
        try {
            const resp = await fetch(
                `${this.PROM_API}/query?query=${encodeURIComponent('up{job=\"node-exporter\"}')}`
            );
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            const result = data?.data?.result;
            if (Array.isArray(result) && result.length > 0) {
                // Prefer an 'up' target if multiple exist (value == 1), else first.
                const upTarget = result.find(r => r?.value?.[1] === '1');
                return (upTarget?.metric?.hostname) || (result[0]?.metric?.hostname) || null;
            }
        } catch (e) {
            // fall through
        }
        return null;
    },

    setupNavigation() {
        // Card click handlers
        document.querySelectorAll('.card[data-section]').forEach(card => {
            card.addEventListener('click', () => {
                const section = card.getAttribute('data-section');
                this.navigateToDetail(section);
            });
        });

        // Hash-based routing
        window.addEventListener('hashchange', () => this.handleRoute());
        this.handleRoute();
    },

    handleRoute() {
        const hash = window.location.hash.slice(1);
        if (!hash || hash === 'overview') {
            this.navigateToOverview();
        } else {
            this.navigateToDetail(hash);
        }
    },

    navigateToOverview() {
        window.location.hash = '';
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });
        document.getElementById('overview').classList.add('active');
    },

    navigateToDetail(section) {
        window.location.hash = section;
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });
        const detailPage = document.getElementById(`detail-${section}`);
        if (detailPage) {
            detailPage.classList.add('active');
            this.updateDetailView(section);
        }
    },

    updateTime() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
        const dateStr = now.toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
        
        const timeEl = document.getElementById('current-time');
        const dateEl = document.getElementById('current-date');
        if (timeEl) timeEl.textContent = timeStr;
        if (dateEl) dateEl.textContent = dateStr;
    },

    async queryPrometheus(query) {
        try {
            const response = await fetch(`${this.PROM_API}/query?query=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            if (data.status !== 'success') {
                throw new Error(data.error || 'Query failed');
            }
            return data.data.result || [];
        } catch (error) {
            console.error('Prometheus query error:', error);
            return [];
        }
    },

    async queryRangePrometheus(query, start, end, step = '5s') {
        try {
            const url = `${this.PROM_API}/query_range?query=${encodeURIComponent(query)}&start=${start}&end=${end}&step=${step}`;
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            if (data.status !== 'success') {
                throw new Error(data.error || 'Query failed');
            }
            return data.data.result || [];
        } catch (error) {
            console.error('Prometheus query_range error:', error);
            return [];
        }
    },

    getValue(result, defaultValue = '--') {
        if (!result || result.length === 0) return defaultValue;
        const value = parseFloat(result[0].value[1]);
        return isNaN(value) ? defaultValue : value;
    },

    formatBytes(bytes) {
        if (bytes === '--' || bytes === null || bytes === undefined) return '--';
        const b = parseFloat(bytes);
        if (isNaN(b)) return '--';
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let i = 0;
        let size = b;
        while (size >= 1024 && i < units.length - 1) {
            size /= 1024;
            i++;
        }
        return `${size.toFixed(1)} ${units[i]}`;
    },

    formatDuration(seconds) {
        if (seconds === '--' || seconds === null || seconds === undefined) return '--';
        const s = parseFloat(seconds);
        if (isNaN(s)) return '--';
        const hours = Math.floor(s / 3600);
        const minutes = Math.floor((s % 3600) / 60);
        return `${hours}h ${minutes}m`;
    },

    async detectPrimaryNetworkDevice() {
        // Find the network device with the highest traffic (excluding lo)
        const query = `topk(1, sum by (device) (rate(node_network_receive_bytes_total{device!~"^(lo|docker.*|br-.*|veth.*)$",hostname="${this.currentHostname}"}[5m])) + sum by (device) (rate(node_network_transmit_bytes_total{device!~"^(lo|docker.*|br-.*|veth.*)$",hostname="${this.currentHostname}"}[5m])))`;
        const result = await this.queryPrometheus(query);
        if (result.length > 0) {
            this.primaryNetworkDevice = result[0].metric.device;
        } else {
            // Fallback: try to find any non-lo device
            const fallbackQuery = `node_network_receive_bytes_total{device!~"^(lo|docker.*|br-.*|veth.*)$",hostname="${this.currentHostname}"}`;
            const fallbackResult = await this.queryPrometheus(fallbackQuery);
            if (fallbackResult.length > 0) {
                this.primaryNetworkDevice = fallbackResult[0].metric.device;
            }
        }
    },

    async updateStatusCard() {
        // OS status (check if node is up)
        const upQuery = `up{job="node-exporter",hostname="${this.currentHostname}"}`;
        const upResult = await this.queryPrometheus(upQuery);
        const isUp = this.getValue(upResult, 0) === 1;
        document.getElementById('status-os').textContent = isUp ? 'GO' : 'WARNING';
        document.getElementById('status-os').className = `status-value ${isUp ? 'go' : 'warning'}`;

        // CPU temp status (> 90°C = warning)
        const cpuTempQuery = `max(node_hwmon_temp_celsius{chip=~"pci0000:00_.*",hostname="${this.currentHostname}"})`;
        const cpuTempResult = await this.queryPrometheus(cpuTempQuery);
        const cpuTemp = this.getValue(cpuTempResult);
        const cpuStatus = (cpuTemp !== '--' && cpuTemp > 90) ? 'warning' : 'go';
        document.getElementById('status-cpu').textContent = cpuStatus === 'warning' ? 'WARNING' : 'GO';
        document.getElementById('status-cpu').className = `status-value ${cpuStatus}`;

        // GPU temp status (> 100°C = warning)
        const gpuTempQuery = `max(node_textfile_gpu_temperature_celsius{hostname="${this.currentHostname}"})`;
        const gpuTempResult = await this.queryPrometheus(gpuTempQuery);
        const gpuTemp = this.getValue(gpuTempResult);
        let gpuStatus = 'go';
        if (gpuTemp !== '--') {
            gpuStatus = gpuTemp > 100 ? 'warning' : 'go';
            document.getElementById('status-gpu').textContent = gpuStatus === 'warning' ? 'WARNING' : 'GO';
        } else {
            document.getElementById('status-gpu').textContent = 'N/A';
        }
        document.getElementById('status-gpu').className = `status-value ${gpuStatus}`;

        // Memory status (> 90% = warning)
        const memQuery = `100 * (1 - (node_memory_MemAvailable_bytes{hostname="${this.currentHostname}"} / node_memory_MemTotal_bytes{hostname="${this.currentHostname}"}))`;
        const memResult = await this.queryPrometheus(memQuery);
        const memPercent = this.getValue(memResult);
        const memStatus = (memPercent !== '--' && memPercent > 90) ? 'warning' : 'go';
        document.getElementById('status-memory').textContent = memStatus === 'warning' ? 'WARNING' : 'GO';
        document.getElementById('status-memory').className = `status-value ${memStatus}`;
    },

    async updateSystemCard() {
        // OS (Ubuntu version) from node_os_info
        const osQuery = `node_os_info{hostname="${this.currentHostname}"}`;
        const osResult = await this.queryPrometheus(osQuery);
        if (osResult.length > 0) {
            const pretty = osResult[0].metric.pretty_name || '';
            // Match your desired style (e.g. "UBUNTU-24")
            const m = pretty.match(/Ubuntu\\s+([0-9]{2})\\./i);
            const osDisplay = m ? `UBUNTU-${m[1]}` : (pretty || '--');
            document.getElementById('system-os').textContent = osDisplay;
        } else {
            document.getElementById('system-os').textContent = '--';
        }

        // Kernel
        const kernelQuery = `node_uname_info{hostname="${this.currentHostname}"}`;
        const kernelResult = await this.queryPrometheus(kernelQuery);
        if (kernelResult.length > 0) {
            const kernel = kernelResult[0].metric.release;
            document.getElementById('system-kernel').textContent = kernel;
        }

        // Uptime
        const uptimeQuery = `time() - node_boot_time_seconds{hostname="${this.currentHostname}"}`;
        const uptimeResult = await this.queryPrometheus(uptimeQuery);
        const uptime = this.getValue(uptimeResult);
        document.getElementById('system-uptime').textContent = this.formatDuration(uptime);

        // User (prefer textfile metric label; fallback to configured user)
        const userQuery = `node_textfile_system_user{hostname="${this.currentHostname}"}`;
        const userResult = await this.queryPrometheus(userQuery);
        if (userResult.length > 0 && userResult[0].metric.user) {
            document.getElementById('system-user').textContent = userResult[0].metric.user;
        } else {
            document.getElementById('system-user').textContent = '--';
        }
    },

    async updateCpuCard() {
        // CPU name (from textfile metric label; node_exporter doesn't expose model name by default)
        const cpuModelQuery = `node_textfile_system_cpu_model{hostname="${this.currentHostname}"}`;
        const cpuModelResult = await this.queryPrometheus(cpuModelQuery);
        if (cpuModelResult.length > 0 && cpuModelResult[0].metric.model) {
            document.getElementById('cpu-name').textContent = cpuModelResult[0].metric.model;
        } else {
            document.getElementById('cpu-name').textContent = 'CPU';
        }

        // CPU temp
        const cpuTempQuery = `max(node_hwmon_temp_celsius{chip=~"pci0000:00_.*",hostname="${this.currentHostname}"})`;
        const cpuTempResult = await this.queryPrometheus(cpuTempQuery);
        const cpuTemp = this.getValue(cpuTempResult);
        document.getElementById('cpu-temp').textContent = cpuTemp !== '--' ? `${cpuTemp.toFixed(1)}°C` : '--';

        // Overall CPU usage
        const cpuUsageQuery = `100 - (avg by (hostname) (rate(node_cpu_seconds_total{mode="idle",hostname="${this.currentHostname}"}[1m])) * 100)`;
        const cpuUsageResult = await this.queryPrometheus(cpuUsageQuery);
        const cpuUsage = this.getValue(cpuUsageResult);
        document.getElementById('cpu-usage').textContent = cpuUsage !== '--' ? `${cpuUsage.toFixed(1)}%` : '--';
    },

    async updateGpuCard() {
        // GPU name: pick the "primary" GPU as the one with the largest VRAM total,
        // then read its exported model label.
        const primaryGpuQuery = `topk(1, node_textfile_gpu_memory_total_bytes{hostname="${this.currentHostname}"})`;
        const primaryGpuResult = await this.queryPrometheus(primaryGpuQuery);
        const primaryGpu = primaryGpuResult.length > 0 ? primaryGpuResult[0].metric.gpu : null;

        const gpuModelQuery = primaryGpu
            ? `node_textfile_gpu_model{hostname="${this.currentHostname}",gpu="${primaryGpu}"}`
            : `node_textfile_gpu_model{hostname="${this.currentHostname}"}`;
        const gpuModelResult = await this.queryPrometheus(gpuModelQuery);
        if (gpuModelResult.length > 0 && gpuModelResult[0].metric.model) {
            document.getElementById('gpu-name').textContent = gpuModelResult[0].metric.model;
        } else {
            const gpuQuery = `node_textfile_gpu_temperature_celsius{hostname="${this.currentHostname}"}`;
            const gpuResult = await this.queryPrometheus(gpuQuery);
            document.getElementById('gpu-name').textContent = gpuResult.length > 0 ? 'AMD GPU' : 'N/A';
        }

        // GPU temp
        const gpuTempQuery = `max(node_textfile_gpu_temperature_celsius{hostname="${this.currentHostname}"})`;
        const gpuTempResult = await this.queryPrometheus(gpuTempQuery);
        const gpuTemp = this.getValue(gpuTempResult);
        document.getElementById('gpu-temp').textContent = gpuTemp !== '--' ? `${gpuTemp.toFixed(1)}°C` : '--';

        // GPU usage
        const gpuUsageQuery = `max(node_textfile_gpu_utilization_percent{hostname="${this.currentHostname}"})`;
        const gpuUsageResult = await this.queryPrometheus(gpuUsageQuery);
        const gpuUsage = this.getValue(gpuUsageResult);
        document.getElementById('gpu-usage').textContent = gpuUsage !== '--' ? `${gpuUsage.toFixed(1)}%` : '--';

        // VRAM
        const vramUsedQuery = `max(node_textfile_gpu_memory_used_bytes{hostname="${this.currentHostname}"})`;
        const vramTotalQuery = `max(node_textfile_gpu_memory_total_bytes{hostname="${this.currentHostname}"})`;
        const vramUsedResult = await this.queryPrometheus(vramUsedQuery);
        const vramTotalResult = await this.queryPrometheus(vramTotalQuery);
        const vramUsed = this.getValue(vramUsedResult);
        const vramTotal = this.getValue(vramTotalResult);
        if (vramUsed !== '--' && vramTotal !== '--') {
            document.getElementById('gpu-vram').textContent = `${this.formatBytes(vramUsed)} / ${this.formatBytes(vramTotal)}`;
        } else {
            document.getElementById('gpu-vram').textContent = '--';
        }

        // Clock speed (current / max)
        const clockQuery = `max(node_textfile_gpu_clock_frequency_hz{hostname="${this.currentHostname}"})`;
        const clockMaxQuery = `max(node_textfile_gpu_clock_max_frequency_hz{hostname="${this.currentHostname}"})`;
        const [clockResult, clockMaxResult] = await Promise.all([
            this.queryPrometheus(clockQuery),
            this.queryPrometheus(clockMaxQuery),
        ]);
        const clockHz = this.getValue(clockResult);
        const clockMaxHz = this.getValue(clockMaxResult);
        if (clockHz !== '--') {
            const clockMhz = clockHz / 1_000_000;
            if (clockMaxHz !== '--' && clockMaxHz > 0) {
                const clockMaxMhz = clockMaxHz / 1_000_000;
                document.getElementById('gpu-clock').textContent = `${clockMhz.toFixed(0)} / ${clockMaxMhz.toFixed(0)} MHz`;
            } else {
                document.getElementById('gpu-clock').textContent = `${clockMhz.toFixed(0)} MHz`;
            }
        } else {
            document.getElementById('gpu-clock').textContent = '--';
        }

        // Fan speed (current / max)
        const fanQuery = `max(node_textfile_gpu_fan_rpm{hostname="${this.currentHostname}"})`;
        const fanMaxQuery = `max(node_textfile_gpu_fan_max_rpm{hostname="${this.currentHostname}"})`;
        const [fanResult, fanMaxResult] = await Promise.all([
            this.queryPrometheus(fanQuery),
            this.queryPrometheus(fanMaxQuery),
        ]);
        const fanRpm = this.getValue(fanResult);
        const fanMaxRpm = this.getValue(fanMaxResult);
        if (fanRpm !== '--') {
            if (fanMaxRpm !== '--' && fanMaxRpm > 0) {
                document.getElementById('gpu-fan').textContent = `${fanRpm.toFixed(0)} / ${fanMaxRpm.toFixed(0)} RPM`;
            } else {
                document.getElementById('gpu-fan').textContent = `${fanRpm.toFixed(0)} RPM`;
            }
        } else {
            // If we have no fan metric yet, show 0 instead of N/A (matches your expectation when stopped)
            document.getElementById('gpu-fan').textContent = `0 RPM`;
        }
    },

    async updateMemoryCard() {
        // RAM
        const ramTotalQuery = `node_memory_MemTotal_bytes{hostname="${this.currentHostname}"}`;
        const ramAvailableQuery = `node_memory_MemAvailable_bytes{hostname="${this.currentHostname}"}`;
        const ramTotalResult = await this.queryPrometheus(ramTotalQuery);
        const ramAvailableResult = await this.queryPrometheus(ramAvailableQuery);
        const ramTotal = this.getValue(ramTotalResult);
        const ramAvailable = this.getValue(ramAvailableResult);
        const ramUsed = ramTotal !== '--' && ramAvailable !== '--' ? ramTotal - ramAvailable : '--';
        
        if (ramUsed !== '--' && ramTotal !== '--') {
            document.getElementById('memory-ram').textContent = `${this.formatBytes(ramUsed)} / ${this.formatBytes(ramTotal)}`;
            const ramPercent = (ramUsed / ramTotal) * 100;
            document.getElementById('memory-ram-bar').style.width = `${ramPercent}%`;
        } else {
            document.getElementById('memory-ram').textContent = '--';
            document.getElementById('memory-ram-bar').style.width = '0%';
        }

        // SSD (root filesystem)
        const fsSizeQuery = `node_filesystem_size_bytes{hostname="${this.currentHostname}",mountpoint="/",fstype!="rootfs"}`;
        const fsAvailQuery = `node_filesystem_avail_bytes{hostname="${this.currentHostname}",mountpoint="/",fstype!="rootfs"}`;
        const fsSizeResult = await this.queryPrometheus(fsSizeQuery);
        const fsAvailResult = await this.queryPrometheus(fsAvailQuery);
        const fsSize = this.getValue(fsSizeResult);
        const fsAvail = this.getValue(fsAvailResult);
        const fsUsed = fsSize !== '--' && fsAvail !== '--' ? fsSize - fsAvail : '--';

        if (fsUsed !== '--' && fsSize !== '--') {
            document.getElementById('memory-ssd').textContent = `${this.formatBytes(fsUsed)} / ${this.formatBytes(fsSize)}`;
            const fsPercent = (fsUsed / fsSize) * 100;
            document.getElementById('memory-ssd-bar').style.width = `${fsPercent}%`;
        } else {
            document.getElementById('memory-ssd').textContent = '--';
            document.getElementById('memory-ssd-bar').style.width = '0%';
        }

        // Disk I/O
        const diskReadQuery = `sum(rate(node_disk_read_bytes_total{hostname="${this.currentHostname}",device!~"dm-.*|loop.*"}[1m]))`;
        const diskWriteQuery = `sum(rate(node_disk_written_bytes_total{hostname="${this.currentHostname}",device!~"dm-.*|loop.*"}[1m]))`;
        const diskReadResult = await this.queryPrometheus(diskReadQuery);
        const diskWriteResult = await this.queryPrometheus(diskWriteQuery);
        const diskRead = this.getValue(diskReadResult);
        const diskWrite = this.getValue(diskWriteResult);
        
        if (diskRead !== '--' && diskWrite !== '--') {
            document.getElementById('memory-disk-io').textContent = `R: ${this.formatBytes(diskRead)}/s W: ${this.formatBytes(diskWrite)}/s`;
        } else {
            document.getElementById('memory-disk-io').textContent = '--';
        }
    },

    async updateNetworkCard() {
        if (!this.primaryNetworkDevice) {
            await this.detectPrimaryNetworkDevice();
        }

        if (!this.primaryNetworkDevice) {
            document.getElementById('network-ip').textContent = '--';
            document.getElementById('network-down').textContent = '--';
            document.getElementById('network-up').textContent = '--';
            return;
        }

        // IP Address (prefer primary IPv4 metric; it's derived from default route on the host)
        const ipQuery = `node_textfile_primary_ipv4{hostname="${this.currentHostname}"}`;
        const ipResult = await this.queryPrometheus(ipQuery);
        if (ipResult.length > 0 && ipResult[0].metric.address) {
            document.getElementById('network-ip').textContent = ipResult[0].metric.address;
            // If we have an authoritative primary interface from the metric, prefer it.
            if (ipResult[0].metric.device) {
                this.primaryNetworkDevice = ipResult[0].metric.device;
            }
        } else {
            document.getElementById('network-ip').textContent = this.primaryNetworkDevice;
        }

        // Prefer host-derived primary interface throughput (works even when node_exporter sees only container eth0).
        const downRateQ = `node_textfile_primary_network_receive_bps{hostname="${this.currentHostname}"}`;
        const upRateQ = `node_textfile_primary_network_transmit_bps{hostname="${this.currentHostname}"}`;
        const downTotalQ = `node_textfile_primary_network_receive_bytes_total{hostname="${this.currentHostname}"}`;
        const upTotalQ = `node_textfile_primary_network_transmit_bytes_total{hostname="${this.currentHostname}"}`;

        const [downRateR, upRateR, downTotalR, upTotalR] = await Promise.all([
            this.queryPrometheus(downRateQ),
            this.queryPrometheus(upRateQ),
            this.queryPrometheus(downTotalQ),
            this.queryPrometheus(upTotalQ),
        ]);

        const downRate = this.getValue(downRateR);
        const upRate = this.getValue(upRateR);
        const downTotal = this.getValue(downTotalR);
        const upTotal = this.getValue(upTotalR);

        if (downRate !== '--') {
            const totalStr = downTotal !== '--' ? ` (${this.formatBytes(downTotal)})` : '';
            document.getElementById('network-down').textContent = `${this.formatBytes(downRate)}/s${totalStr}`;
        } else {
            // Fallback to node_exporter network series (container iface)
            const fallbackDownQ = `rate(node_network_receive_bytes_total{device="${this.primaryNetworkDevice}",hostname="${this.currentHostname}"}[1m])`;
            const fallbackDownR = await this.queryPrometheus(fallbackDownQ);
            const fallbackDown = this.getValue(fallbackDownR);
            document.getElementById('network-down').textContent = fallbackDown !== '--' ? `${this.formatBytes(fallbackDown)}/s` : '--';
        }

        if (upRate !== '--') {
            const totalStr = upTotal !== '--' ? ` (${this.formatBytes(upTotal)})` : '';
            document.getElementById('network-up').textContent = `${this.formatBytes(upRate)}/s${totalStr}`;
        } else {
            const fallbackUpQ = `rate(node_network_transmit_bytes_total{device="${this.primaryNetworkDevice}",hostname="${this.currentHostname}"}[1m])`;
            const fallbackUpR = await this.queryPrometheus(fallbackUpQ);
            const fallbackUp = this.getValue(fallbackUpR);
            document.getElementById('network-up').textContent = fallbackUp !== '--' ? `${this.formatBytes(fallbackUp)}/s` : '--';
        }
    },

    async updateProcessesCard() {
        const cpuQuery = `node_textfile_top_process_cpu_percent{hostname="${this.currentHostname}"}`;
        const memQuery = `node_textfile_top_process_mem_percent{hostname="${this.currentHostname}"}`;
        const cpuResult = await this.queryPrometheus(cpuQuery);
        const memResult = await this.queryPrometheus(memQuery);

        const processesList = document.getElementById('processes-list');
        if (!processesList) return;

        processesList.innerHTML = '';

        // Combine and sort by CPU (top 5)
        const processes = [];
        cpuResult.forEach(item => {
            processes.push({
                name: item.metric.comm || 'unknown',
                cpu: parseFloat(item.value[1]) || 0,
                mem: 0
            });
        });

        memResult.forEach(item => {
            const existing = processes.find(p => p.name === item.metric.comm);
            if (existing) {
                existing.mem = parseFloat(item.value[1]) || 0;
            }
        });

        processes.sort((a, b) => b.cpu - a.cpu);
        processes.slice(0, 5).forEach(proc => {
            const procDiv = document.createElement('div');
            procDiv.className = 'process-item';
            procDiv.innerHTML = `
                <span class="process-name">${proc.name}</span>
                <span class="process-mem">${proc.mem.toFixed(1)}%</span>
                <span class="process-cpu">${proc.cpu.toFixed(1)}%</span>
            `;
            processesList.appendChild(procDiv);
        });

        if (processes.length === 0) {
            processesList.innerHTML = '<div class="loading">No process data available</div>';
        }
    },

    async updateAllCards() {
        try {
            if (!this.currentHostname) {
                // Keep the UI stable, but show placeholders until we can resolve a host.
                return;
            }
            await Promise.all([
                this.updateStatusCard(),
                this.updateSystemCard(),
                this.updateCpuCard(),
                this.updateGpuCard(),
                this.updateMemoryCard(),
                this.updateNetworkCard(),
                this.updateProcessesCard()
            ]);
        } catch (error) {
            console.error('Error updating cards:', error);
        }
    },

    async updateDetailView(section) {
        const contentEl = document.getElementById(`detail-${section}-content`);
        if (!contentEl) return;

        contentEl.innerHTML = '<div class="loading">Loading...</div>';

        const end = Math.floor(Date.now() / 1000);
        const start = end - 3600; // 1 hour window
        const step = '30s';

        try {
            switch (section) {
                case 'status':
                    await this.renderStatusDetail(contentEl, start, end, step);
                    break;
                case 'system':
                    await this.renderSystemDetail(contentEl);
                    break;
                case 'cpu':
                    await this.renderCpuDetail(contentEl, start, end, step);
                    break;
                case 'gpu':
                    await this.renderGpuDetail(contentEl, start, end, step);
                    break;
                case 'memory':
                    await this.renderMemoryDetail(contentEl, start, end, step);
                    break;
                case 'network':
                    await this.renderNetworkDetail(contentEl, start, end, step);
                    break;
                case 'processes':
                    await this.renderProcessesDetail(contentEl);
                    break;
            }
        } catch (error) {
            console.error(`Error rendering ${section} detail:`, error);
            contentEl.innerHTML = `<div class="error">Error loading data: ${error.message}</div>`;
        }
    },

    async renderStatusDetail(container, start, end, step) {
        const html = `
            <div class="detail-section">
                <h3>System Status Over Time</h3>
                <div class="detail-graph" id="status-graph"></div>
            </div>
        `;
        container.innerHTML = html;
        // TODO: Add graph rendering
    },

    async renderSystemDetail(container) {
        const html = `
            <div class="detail-section">
                <h3>System Information</h3>
                <div class="detail-stats">
                    <div class="detail-stat">
                        <span class="detail-stat-label">Hostname</span>
                        <span class="detail-stat-value">${this.currentHostname}</span>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML = html;
    },

    async renderCpuDetail(container, start, end, step) {
        const html = `
            <div class="detail-section">
                <h3>CPU Usage</h3>
                <div class="detail-graph" id="cpu-graph"></div>
            </div>
        `;
        container.innerHTML = html;
        // TODO: Add graph rendering
    },

    async renderGpuDetail(container, start, end, step) {
        const html = `
            <div class="detail-section">
                <h3>GPU Metrics</h3>
                <div class="detail-graph" id="gpu-graph"></div>
            </div>
        `;
        container.innerHTML = html;
        // TODO: Add graph rendering
    },

    async renderMemoryDetail(container, start, end, step) {
        const html = `
            <div class="detail-section">
                <h3>Memory Usage</h3>
                <div class="detail-graph" id="memory-graph"></div>
            </div>
        `;
        container.innerHTML = html;
        // TODO: Add graph rendering
    },

    async renderNetworkDetail(container, start, end, step) {
        const html = `
            <div class="detail-section">
                <h3>Network Traffic</h3>
                <div class="detail-graph" id="network-graph"></div>
            </div>
        `;
        container.innerHTML = html;
        // TODO: Add graph rendering
    },

    async renderProcessesDetail(container) {
        const html = `
            <div class="detail-section">
                <h3>Top Processes</h3>
                <div class="detail-stats">
                    <div class="detail-stat">
                        <span class="detail-stat-label">Processes</span>
                        <span class="detail-stat-value">See overview card</span>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML = html;
    },

    startUpdates() {
        this.updateAllCards();
        this.updateTimer = setInterval(() => {
            this.updateAllCards();
        }, this.UPDATE_INTERVAL);
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});


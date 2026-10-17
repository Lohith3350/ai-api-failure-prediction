import React, { useState, useMemo, useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import "./style.css";

// ============================================================================
// Service Inventory & Metrics Data
// ============================================================================
const services = [
  {
    name: "API Gateway",
    status: "Healthy",
    latency: 42,
    error: "0.2%",
    errorValue: 0.2,
    uptime: "99.98%",
    requests: "1,240/min",
    requestValue: 1240,
    type: "Edge Ingress",
    description: "Reverse proxy, SSL termination, and rate limiting for incoming traffic.",
  },
  {
    name: "Order Service",
    status: "Warning",
    latency: 186,
    error: "2.8%",
    errorValue: 2.8,
    uptime: "99.82%",
    requests: "820/min",
    requestValue: 820,
    type: "Business Logic",
    description: "Checkout workflows, order fulfillment, and cart orchestration.",
  },
  {
    name: "Payment Service",
    status: "Critical",
    latency: 420,
    error: "8.4%",
    errorValue: 8.4,
    uptime: "98.91%",
    requests: "410/min",
    requestValue: 410,
    type: "Financial Core",
    description: "Payment tokenization, third-party gateway dispatch, and ledger records.",
  },
  {
    name: "Database",
    status: "Healthy",
    latency: 28,
    error: "0.1%",
    errorValue: 0.1,
    uptime: "99.99%",
    requests: "2,140/min",
    requestValue: 2140,
    type: "Data Persistence",
    description: "PostgreSQL read-replica cluster and primary transactional connection pool.",
  },
];

// ============================================================================
// Telemetry Multi-Range & Multi-Service Datasets
// ============================================================================
const telemetryDatasets = {
  "Last 45 minutes": {
    "All Services": [
      { time: "09:00", latency: 48, requests: 3600, errors: 4 },
      { time: "09:05", latency: 52, requests: 3850, errors: 6 },
      { time: "09:10", latency: 47, requests: 3720, errors: 5 },
      { time: "09:15", latency: 76, requests: 4100, errors: 12 },
      { time: "09:20", latency: 95, requests: 4250, errors: 16 },
      { time: "09:25", latency: 140, requests: 4420, errors: 24 },
      { time: "09:30", latency: 186, requests: 4580, errors: 38 },
      { time: "09:35", latency: 168, requests: 4490, errors: 31 },
      { time: "09:40", latency: 210, requests: 4610, errors: 45 },
    ],
    "Payment Service": [
      { time: "09:00", latency: 110, requests: 320, errors: 2 },
      { time: "09:05", latency: 125, requests: 340, errors: 3 },
      { time: "09:10", latency: 140, requests: 330, errors: 4 },
      { time: "09:15", latency: 195, requests: 360, errors: 8 },
      { time: "09:20", latency: 260, requests: 375, errors: 14 },
      { time: "09:25", latency: 320, requests: 390, errors: 20 },
      { time: "09:30", latency: 380, requests: 405, errors: 28 },
      { time: "09:35", latency: 405, requests: 398, errors: 31 },
      { time: "09:40", latency: 420, requests: 410, errors: 34 },
    ],
    "Order Service": [
      { time: "09:00", latency: 65, requests: 680, errors: 1 },
      { time: "09:05", latency: 70, requests: 710, errors: 2 },
      { time: "09:10", latency: 68, requests: 690, errors: 1 },
      { time: "09:15", latency: 92, requests: 750, errors: 3 },
      { time: "09:20", latency: 115, requests: 780, errors: 5 },
      { time: "09:25", latency: 145, requests: 795, errors: 9 },
      { time: "09:30", latency: 172, requests: 810, errors: 15 },
      { time: "09:35", latency: 164, requests: 805, errors: 14 },
      { time: "09:40", latency: 186, requests: 820, errors: 23 },
    ],
    "API Gateway": [
      { time: "09:00", latency: 28, requests: 980, errors: 1 },
      { time: "09:05", latency: 30, requests: 1040, errors: 1 },
      { time: "09:10", latency: 29, requests: 1010, errors: 0 },
      { time: "09:15", latency: 33, requests: 1120, errors: 1 },
      { time: "09:20", latency: 36, requests: 1160, errors: 1 },
      { time: "09:25", latency: 39, requests: 1200, errors: 2 },
      { time: "09:30", latency: 41, requests: 1225, errors: 2 },
      { time: "09:35", latency: 40, requests: 1210, errors: 2 },
      { time: "09:40", latency: 42, requests: 1240, errors: 2 },
    ],
    Database: [
      { time: "09:00", latency: 22, requests: 1620, errors: 0 },
      { time: "09:05", latency: 23, requests: 1760, errors: 0 },
      { time: "09:10", latency: 21, requests: 1690, errors: 0 },
      { time: "09:15", latency: 24, requests: 1870, errors: 0 },
      { time: "09:20", latency: 26, requests: 1950, errors: 1 },
      { time: "09:25", latency: 27, requests: 2035, errors: 1 },
      { time: "09:30", latency: 28, requests: 2140, errors: 1 },
      { time: "09:35", latency: 27, requests: 2085, errors: 1 },
      { time: "09:40", latency: 28, requests: 2140, errors: 2 },
    ],
  },
  "Last 1 hour": {
    "All Services": [
      { time: "08:45", latency: 45, requests: 3450, errors: 3 },
      { time: "08:50", latency: 46, requests: 3500, errors: 3 },
      { time: "08:55", latency: 47, requests: 3550, errors: 4 },
      { time: "09:00", latency: 48, requests: 3600, errors: 4 },
      { time: "09:05", latency: 52, requests: 3850, errors: 6 },
      { time: "09:10", latency: 47, requests: 3720, errors: 5 },
      { time: "09:15", latency: 76, requests: 4100, errors: 12 },
      { time: "09:20", latency: 95, requests: 4250, errors: 16 },
      { time: "09:25", latency: 140, requests: 4420, errors: 24 },
      { time: "09:30", latency: 186, requests: 4580, errors: 38 },
      { time: "09:35", latency: 168, requests: 4490, errors: 31 },
      { time: "09:40", latency: 210, requests: 4610, errors: 45 },
    ],
    "Payment Service": [
      { time: "08:45", latency: 95, requests: 290, errors: 1 },
      { time: "08:50", latency: 100, requests: 305, errors: 1 },
      { time: "08:55", latency: 105, requests: 315, errors: 2 },
      { time: "09:00", latency: 110, requests: 320, errors: 2 },
      { time: "09:05", latency: 125, requests: 340, errors: 3 },
      { time: "09:10", latency: 140, requests: 330, errors: 4 },
      { time: "09:15", latency: 195, requests: 360, errors: 8 },
      { time: "09:20", latency: 260, requests: 375, errors: 14 },
      { time: "09:25", latency: 320, requests: 390, errors: 20 },
      { time: "09:30", latency: 380, requests: 405, errors: 28 },
      { time: "09:35", latency: 405, requests: 398, errors: 31 },
      { time: "09:40", latency: 420, requests: 410, errors: 34 },
    ],
    "Order Service": [
      { time: "08:45", latency: 58, requests: 620, errors: 1 },
      { time: "08:50", latency: 60, requests: 640, errors: 1 },
      { time: "08:55", latency: 62, requests: 660, errors: 1 },
      { time: "09:00", latency: 65, requests: 680, errors: 1 },
      { time: "09:05", latency: 70, requests: 710, errors: 2 },
      { time: "09:10", latency: 68, requests: 690, errors: 1 },
      { time: "09:15", latency: 92, requests: 750, errors: 3 },
      { time: "09:20", latency: 115, requests: 780, errors: 5 },
      { time: "09:25", latency: 145, requests: 795, errors: 9 },
      { time: "09:30", latency: 172, requests: 810, errors: 15 },
      { time: "09:35", latency: 164, requests: 805, errors: 14 },
      { time: "09:40", latency: 186, requests: 820, errors: 23 },
    ],
    "API Gateway": [
      { time: "08:45", latency: 25, requests: 920, errors: 0 },
      { time: "08:50", latency: 26, requests: 940, errors: 0 },
      { time: "08:55", latency: 27, requests: 960, errors: 1 },
      { time: "09:00", latency: 28, requests: 980, errors: 1 },
      { time: "09:05", latency: 30, requests: 1040, errors: 1 },
      { time: "09:10", latency: 29, requests: 1010, errors: 0 },
      { time: "09:15", latency: 33, requests: 1120, errors: 1 },
      { time: "09:20", latency: 36, requests: 1160, errors: 1 },
      { time: "09:25", latency: 39, requests: 1200, errors: 2 },
      { time: "09:30", latency: 41, requests: 1225, errors: 2 },
      { time: "09:35", latency: 40, requests: 1210, errors: 2 },
      { time: "09:40", latency: 42, requests: 1240, errors: 2 },
    ],
    Database: [
      { time: "08:45", latency: 20, requests: 1510, errors: 0 },
      { time: "08:50", latency: 21, requests: 1550, errors: 0 },
      { time: "08:55", latency: 21, requests: 1580, errors: 0 },
      { time: "09:00", latency: 22, requests: 1620, errors: 0 },
      { time: "09:05", latency: 23, requests: 1760, errors: 0 },
      { time: "09:10", latency: 21, requests: 1690, errors: 0 },
      { time: "09:15", latency: 24, requests: 1870, errors: 0 },
      { time: "09:20", latency: 26, requests: 1950, errors: 1 },
      { time: "09:25", latency: 27, requests: 2035, errors: 1 },
      { time: "09:30", latency: 28, requests: 2140, errors: 1 },
      { time: "09:35", latency: 27, requests: 2085, errors: 1 },
      { time: "09:40", latency: 28, requests: 2140, errors: 2 },
    ],
  },
  "Last 24 hours": {
    "All Services": [
      { time: "10:00", latency: 42, requests: 3100, errors: 3 },
      { time: "12:00", latency: 45, requests: 3500, errors: 4 },
      { time: "14:00", latency: 50, requests: 3800, errors: 5 },
      { time: "16:00", latency: 55, requests: 4100, errors: 7 },
      { time: "18:00", latency: 48, requests: 3900, errors: 4 },
      { time: "20:00", latency: 44, requests: 3200, errors: 2 },
      { time: "22:00", latency: 39, requests: 2400, errors: 1 },
      { time: "00:00", latency: 36, requests: 1800, errors: 1 },
      { time: "02:00", latency: 35, requests: 1500, errors: 1 },
      { time: "04:00", latency: 37, requests: 1650, errors: 1 },
      { time: "06:00", latency: 41, requests: 2300, errors: 2 },
      { time: "08:00", latency: 68, requests: 3600, errors: 8 },
      { time: "09:40", latency: 210, requests: 4610, errors: 45 },
    ],
    "Payment Service": [
      { time: "10:00", latency: 85, requests: 280, errors: 1 },
      { time: "12:00", latency: 95, requests: 320, errors: 2 },
      { time: "14:00", latency: 105, requests: 350, errors: 2 },
      { time: "16:00", latency: 120, requests: 380, errors: 4 },
      { time: "18:00", latency: 100, requests: 340, errors: 2 },
      { time: "20:00", latency: 88, requests: 270, errors: 1 },
      { time: "22:00", latency: 75, requests: 200, errors: 0 },
      { time: "00:00", latency: 70, requests: 150, errors: 0 },
      { time: "02:00", latency: 68, requests: 130, errors: 0 },
      { time: "04:00", latency: 72, requests: 140, errors: 0 },
      { time: "06:00", latency: 82, requests: 210, errors: 1 },
      { time: "08:00", latency: 160, requests: 330, errors: 6 },
      { time: "09:40", latency: 420, requests: 410, errors: 34 },
    ],
    "Order Service": [
      { time: "10:00", latency: 52, requests: 590, errors: 1 },
      { time: "12:00", latency: 58, requests: 650, errors: 1 },
      { time: "14:00", latency: 65, requests: 720, errors: 2 },
      { time: "16:00", latency: 75, requests: 780, errors: 2 },
      { time: "18:00", latency: 62, requests: 710, errors: 1 },
      { time: "20:00", latency: 55, requests: 600, errors: 1 },
      { time: "22:00", latency: 48, requests: 440, errors: 0 },
      { time: "00:00", latency: 45, requests: 320, errors: 0 },
      { time: "02:00", latency: 43, requests: 270, errors: 0 },
      { time: "04:00", latency: 46, requests: 290, errors: 0 },
      { time: "06:00", latency: 50, requests: 420, errors: 1 },
      { time: "08:00", latency: 85, requests: 680, errors: 3 },
      { time: "09:40", latency: 186, requests: 820, errors: 23 },
    ],
    "API Gateway": [
      { time: "10:00", latency: 24, requests: 880, errors: 0 },
      { time: "12:00", latency: 26, requests: 980, errors: 0 },
      { time: "14:00", latency: 28, requests: 1080, errors: 0 },
      { time: "16:00", latency: 31, requests: 1180, errors: 1 },
      { time: "18:00", latency: 27, requests: 1100, errors: 0 },
      { time: "20:00", latency: 25, requests: 920, errors: 0 },
      { time: "22:00", latency: 23, requests: 700, errors: 0 },
      { time: "00:00", latency: 21, requests: 520, errors: 0 },
      { time: "02:00", latency: 20, requests: 430, errors: 0 },
      { time: "04:00", latency: 21, requests: 470, errors: 0 },
      { time: "06:00", latency: 24, requests: 660, errors: 0 },
      { time: "08:00", latency: 34, requests: 1040, errors: 1 },
      { time: "09:40", latency: 42, requests: 1240, errors: 2 },
    ],
    Database: [
      { time: "10:00", latency: 19, requests: 1450, errors: 0 },
      { time: "12:00", latency: 21, requests: 1620, errors: 0 },
      { time: "14:00", latency: 23, requests: 1780, errors: 0 },
      { time: "16:00", latency: 25, requests: 1940, errors: 0 },
      { time: "18:00", latency: 22, requests: 1810, errors: 0 },
      { time: "20:00", latency: 20, requests: 1500, errors: 0 },
      { time: "22:00", latency: 18, requests: 1120, errors: 0 },
      { time: "00:00", latency: 17, requests: 850, errors: 0 },
      { time: "02:00", latency: 16, requests: 710, errors: 0 },
      { time: "04:00", latency: 17, requests: 770, errors: 0 },
      { time: "06:00", latency: 19, requests: 1080, errors: 0 },
      { time: "08:00", latency: 25, requests: 1690, errors: 0 },
      { time: "09:40", latency: 28, requests: 2140, errors: 2 },
    ],
  },
};

// ============================================================================
// Initial Incidents Data
// ============================================================================
const initialIncidents = [
  {
    id: "INC-1042",
    service: "Payment Service",
    issue: "High response latency & degradation",
    risk: "Critical",
    time: "2 min ago",
    timestamp: "09:38:12",
    details: "Latency reached 420ms (threshold: 250ms) and error rate climbed to 8.4%. Downstream DB connection pool exhaustion suspected.",
    remediation: "Scale worker replica pool, inspect slow queries on Postgres, and enable connection pooling backoff.",
  },
  {
    id: "INC-1041",
    service: "Order Service",
    issue: "Elevated HTTP 5xx error rate",
    risk: "High",
    time: "5 min ago",
    timestamp: "09:35:00",
    details: "HTTP 502/504 errors increased to 2.8% over the past 3 intervals. Downstream Payment Service call timeouts detected.",
    remediation: "Trigger circuit breaker fallback for checkout retry queue and isolate failing payment endpoint.",
  },
  {
    id: "INC-1040",
    service: "API Gateway",
    issue: "Traffic spike above baseline threshold",
    risk: "Medium",
    time: "12 min ago",
    timestamp: "09:28:45",
    details: "Request volume reached 1,240 req/min (+45% above 30-day baseline). TLS handshake latency increased slightly to 42ms.",
    remediation: "Verify edge rate limiting quotas and monitor ingress worker memory pressure.",
  },
];

// ============================================================================
// Prevention Knowledge Base & Checklist Data
// ============================================================================
const preventionData = {
  "Payment Service": {
    score: 87,
    status: "Critical",
    severity: "High risk",
    color: "#e55369",
    advice: "Review database connection pool saturation, inspect recent payment worker 504 gateway timeouts, and verify autoscaling group headroom before peak traffic.",
    reasons: [
      "p99 latency (420ms) is 3.5x higher than normal baseline (120ms)",
      "Error rate (8.4%) is significantly above the 1.0% SLO threshold",
      "Cascading risk: Order Service is already experiencing 504 timeouts due to Payment dependency",
    ],
    checklist: [
      "Inspect connection pool saturation on downstream Database cluster",
      "Audit recent payment worker timeouts and HTTP 504 gateway responses",
      "Verify payment gateway third-party webhook retry backoff",
      "Confirm worker autoscaling group headroom and replica availability",
    ],
  },
  "Order Service": {
    score: 63,
    status: "Warning",
    severity: "Needs review",
    color: "#d99a2b",
    advice: "Inspect recent 5xx responses, verify downstream Payment Service dependency circuit breaker, and review order retry backoff parameters.",
    reasons: [
      "HTTP 5xx error rate climbed to 2.8% (warning threshold: 2.0%)",
      "Average latency elevated to 186ms",
      "Dependent on Payment Service which is currently in Critical state",
    ],
    checklist: [
      "Inspect HTTP 5xx error distribution across checkout endpoints",
      "Verify circuit breaker trip thresholds for Payment Service dependency",
      "Inspect message queue consumer lag and dead-letter queues",
      "Audit database read-replica replication lag and cache hit ratio",
    ],
  },
  "API Gateway": {
    score: 24,
    status: "Healthy",
    severity: "Lower risk",
    color: "#1ca878",
    advice: "Continue monitoring request volume spikes and keep edge rate limits aligned with cluster throughput capacity.",
    reasons: [
      "Response latency (42ms) remains well within SLA target (<60ms)",
      "Error rate is 0.2%, below the 0.5% caution threshold",
      "Traffic spike handled without edge CPU starvation",
    ],
    checklist: [
      "Verify client rate-limiting policies and quota thresholds",
      "Inspect TLS/SSL handshake latency percentiles (p99)",
      "Review ingress route load balancing across upstream service clusters",
      "Confirm health check probe intervals and timeout windows",
    ],
  },
  Database: {
    score: 18,
    status: "Healthy",
    severity: "Lower risk",
    color: "#1ca878",
    advice: "Monitor connection pool utilization, query latency, and maintain ample buffer pool headroom.",
    reasons: [
      "Query latency (28ms) is stable within normal limits",
      "Error rate is nominal at 0.1%",
      "Uptime is 99.99% with all read replicas in sync",
    ],
    checklist: [
      "Inspect slow query logs for unindexed joins",
      "Audit active connection count vs max_connections allocation",
      "Monitor buffer pool hit ratio and disk I/O wait times",
      "Verify automated failover replica health and WAL replication",
    ],
  },
};

const navItems = [
  { id: "overview", label: "Overview", icon: "▦" },
  { id: "services", label: "Services", icon: "◇" },
  { id: "telemetry", label: "Telemetry", icon: "⌁" },
  { id: "incidents", label: "Incidents", icon: "⚑" },
  { id: "prevention", label: "Prevention", icon: "✧" },
];

// ============================================================================
// Helper Components
// ============================================================================
function Badge({ children }) {
  const text = String(children || "");
  const className = `badge ${text.toLowerCase().replace(/\s+/g, "-")}`;
  return <span className={className}>{children}</span>;
}

function PageTitle({
  eyebrow = "REAL-TIME AI FOR CRITICAL DECISIONS",
  title,
  subtitle,
  children,
}) {
  return (
    <section className="page-title">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="subtitle">{subtitle}</p>
      </div>
      {children && <div className="page-title-actions">{children}</div>}
    </section>
  );
}

function CustomChartTooltip({ active, payload, label, unit = "" }) {
  if (active && payload && payload.length) {
    return (
      <div className="custom-tooltip">
        <p className="tooltip-time">Time: {label}</p>
        {payload.map((entry, index) => (
          <p
            key={`item-${index}`}
            className="tooltip-value"
            style={{ color: entry.color || entry.stroke || entry.fill }}
          >
            <span
              className="tooltip-dot"
              style={{ background: entry.color || entry.stroke || entry.fill }}
            />
            <span>
              {entry.name}: <strong>{entry.value}{unit ? ` ${unit}` : ""}</strong>
            </span>
          </p>
        ))}
      </div>
    );
  }
  return null;
}

function ServiceCards({ items, onInspect }) {
  if (!items || items.length === 0) {
    return <p className="empty">No services match the selected filter.</p>;
  }

  return (
    <div className="service-grid">
      {items.map((service) => (
        <article className="service-card" key={service.name}>
          <div className="service-top">
            <div className="service-symbol">◇</div>
            <Badge>{service.status}</Badge>
          </div>

          <h3>{service.name}</h3>
          <p className="service-type-tag">{service.type}</p>

          <div className="latency">
            {service.latency}
            <span> ms</span>
          </div>

          <p className="muted small">Average response latency</p>

          <div className="service-divider" />

          <div className="service-stats">
            <div>
              <span>Error rate</span>
              <strong>{service.error}</strong>
            </div>
            <div>
              <span>Uptime</span>
              <strong>{service.uptime}</strong>
            </div>
          </div>

          <div className="request-info">
            <span>Request volume</span>
            <strong>{service.requests}</strong>
          </div>

          {onInspect && (
            <button
              className="card-action-btn"
              onClick={() => onInspect(service.name)}
              title={`Inspect ${service.name} telemetry`}
            >
              Inspect telemetry →
            </button>
          )}
        </article>
      ))}
    </div>
  );
}

function LatencyChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <article className="panel">
        <div className="section-heading">
          <h2>Response time</h2>
        </div>
        <p className="empty">No telemetry data available.</p>
      </article>
    );
  }

  return (
    <article className="panel">
      <div className="section-heading">
        <div>
          <h2>Response time</h2>
          <p>Latency trend · milliseconds</p>
        </div>
        <span className="legend">
          <i /> Latency
        </span>
      </div>

      <div className="chart">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 10, right: 12, left: -16, bottom: 0 }}
          >
            <defs>
              <linearGradient id="latencyFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6478f6" stopOpacity={0.28} />
                <stop offset="100%" stopColor="#6478f6" stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid
              stroke="#edf0f6"
              strokeDasharray="4 4"
              vertical={false}
            />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: "#7e8ab1" }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#7e8ab1" }}
              tickLine={false}
              axisLine={false}
              unit="ms"
            />
            <Tooltip content={<CustomChartTooltip unit="ms" />} />
            <Area
              type="monotone"
              dataKey="latency"
              name="Response time"
              stroke="#6478f6"
              strokeWidth={2.5}
              fill="url(#latencyFill)"
              dot={{ r: 2.5, fill: "#6478f6" }}
              activeDot={{ r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function RequestsChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <article className="panel">
        <div className="section-heading">
          <h2>Incoming requests</h2>
        </div>
        <p className="empty">No telemetry data available.</p>
      </article>
    );
  }

  return (
    <article className="panel">
      <div className="section-heading">
        <div>
          <h2>Incoming requests</h2>
          <p>Request volume by interval</p>
        </div>
        <span className="legend purple">
          <i /> Requests
        </span>
      </div>

      <div className="chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 10, right: 10, left: -14, bottom: 0 }}
          >
            <CartesianGrid
              stroke="#edf0f6"
              strokeDasharray="4 4"
              vertical={false}
            />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: "#7e8ab1" }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#7e8ab1" }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomChartTooltip unit="req" />} />
            <Bar
              dataKey="requests"
              name="Request volume"
              fill="#9980ed"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function IncidentList({
  incidents,
  onDismiss,
  onReset,
  notice,
  onDismissNotice,
  showFullControls = false,
}) {
  const [serviceFilter, setServiceFilter] = useState("All services");
  const [severityFilter, setSeverityFilter] = useState("All severities");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedId, setExpandedId] = useState(null);

  const filtered = useMemo(() => {
    return incidents.filter((item) => {
      const matchService =
        serviceFilter === "All services" || item.service === serviceFilter;
      const matchSeverity =
        severityFilter === "All severities" || item.risk === severityFilter;
      const matchSearch =
        !searchQuery ||
        item.issue.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.service.toLowerCase().includes(searchQuery.toLowerCase());
      return matchService && matchSeverity && matchSearch;
    });
  }, [incidents, serviceFilter, severityFilter, searchQuery]);

  return (
    <article className="panel">
      <div className="section-heading">
        <div>
          <h2>{showFullControls ? "Incident management" : "Active incident feed"}</h2>
          <p>Recent service events and anomalies · demo session</p>
        </div>

        <div className="heading-actions">
          {showFullControls && (
            <>
              <input
                type="text"
                placeholder="Search incidents..."
                className="table-search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search incidents"
              />
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                aria-label="Filter by severity"
              >
                <option>All severities</option>
                <option>Critical</option>
                <option>High</option>
                <option>Medium</option>
              </select>
              <select
                value={serviceFilter}
                onChange={(e) => setServiceFilter(e.target.value)}
                aria-label="Filter incidents by service"
              >
                <option>All services</option>
                {services.map((service) => (
                  <option key={service.name}>{service.name}</option>
                ))}
              </select>
            </>
          )}

          <span className="count">
            {filtered.length} {showFullControls && filtered.length !== incidents.length ? `of ${incidents.length}` : ""} open
          </span>

          {onReset && incidents.length < initialIncidents.length && (
            <button
              className="text-action-btn"
              onClick={onReset}
              title="Reset all demo incidents to initial state"
            >
              ↺ Reset demo items
            </button>
          )}
        </div>
      </div>

      {notice && (
        <div className="inline-notice" role="status">
          <span>{notice}</span>
          {onDismissNotice && (
            <button
              className="notice-close-btn"
              onClick={onDismissNotice}
              aria-label="Close notice"
            >
              ×
            </button>
          )}
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="empty-state-box">
          <p className="empty">
            {incidents.length === 0
              ? "All demo incidents have been dismissed for this session."
              : "No incidents match the selected filter criteria."}
          </p>
          {onReset && incidents.length === 0 && (
            <button className="secondary-button" onClick={onReset}>
              ↺ Restore initial demo incidents
            </button>
          )}
        </div>
      ) : (
        <div className="incident-list">
          {filtered.map((incident) => {
            const isExpanded = expandedId === incident.id;
            return (
              <div className="incident" key={incident.id}>
                <div className={`incident-mark ${incident.risk.toLowerCase()}`}>
                  !
                </div>

                <div className="incident-info">
                  <strong>{incident.issue}</strong>
                  <span>
                    {incident.service} · {incident.id}
                  </span>
                  <small>Detected {incident.time} ({incident.timestamp})</small>

                  <p className="incident-details">{incident.details}</p>

                  {showFullControls && (
                    <div className="incident-remediation-box">
                      <span className="remediation-title">Suggested response:</span>
                      <span>{incident.remediation}</span>
                    </div>
                  )}
                </div>

                <div className="incident-end">
                  <Badge>{incident.risk}</Badge>
                  <button
                    className="dismiss-btn"
                    onClick={() => onDismiss(incident.id)}
                    title="Dismiss incident from session view"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </article>
  );
}

function PreventionPage({ selectedService, onServiceChange }) {
  const currentService = selectedService || "Payment Service";
  const [reviewedByService, setReviewedByService] = useState({
    "Payment Service": [],
    "Order Service": [],
    "API Gateway": [],
    Database: [],
  });

  const activePrevention = preventionData[currentService] || preventionData["Payment Service"];
  const risk = activePrevention.score;
  const riskLabel = activePrevention.status;
  const actions = activePrevention.checklist;
  const reviewed = reviewedByService[currentService] || [];

  function toggleCheck(action) {
    setReviewedByService((prev) => {
      const currentList = prev[currentService] || [];
      const updated = currentList.includes(action)
        ? currentList.filter((item) => item !== action)
        : [...currentList, action];
      return { ...prev, [currentService]: updated };
    });
  }

  function selectAll() {
    setReviewedByService((prev) => ({
      ...prev,
      [currentService]: [...actions],
    }));
  }

  function clearAll() {
    setReviewedByService((prev) => ({
      ...prev,
      [currentService]: [],
    }));
  }

  // Determine progress bar gradient based on score
  const progressGradient =
    risk >= 80
      ? "linear-gradient(90deg, #f2994a, #e55369)"
      : risk >= 55
      ? "linear-gradient(90deg, #f2b64c, #e09228)"
      : "linear-gradient(90deg, #20a779, #34d399)";

  return (
    <>
      <PageTitle
        eyebrow="RISK & PREVENTIVE INTELLIGENCE"
        title="Preventive insights"
        subtitle="Review illustrative service risk scores, probable degradation factors, and recommended checks."
      />

      <div className="notice">
        <span className="notice-icon">ⓘ</span>
        <div>
          <strong>Illustrative risk assessment</strong>
          <p>
            These scores and recommendations are static demonstration examples,
            distinguished from genuine ML predictions produced by Namith's
            model service.
          </p>
        </div>
      </div>

      <section className="prevention-layout">
        <article className="panel">
          <div className="section-heading">
            <div>
              <h2>Service risk assessment</h2>
              <p>Select a service to inspect its demo risk score and telemetry signals.</p>
            </div>
          </div>

          <label className="field-label" htmlFor="risk-service">
            Target service:
          </label>

          <select
            id="risk-service"
            className="wide-select"
            value={currentService}
            onChange={(e) => onServiceChange(e.target.value)}
          >
            {services.map((service) => (
              <option key={service.name}>{service.name}</option>
            ))}
          </select>

          <div className="risk-line">
            <div>
              <span>{currentService} risk score</span>
              <strong>
                {risk}
                <span>/100</span>
              </strong>
            </div>
            <Badge>{riskLabel}</Badge>
          </div>

          <div className="progress">
            <span
              style={{
                width: `${risk}%`,
                background: progressGradient,
              }}
            />
          </div>

          <div className="risk-reasons-box">
            <strong>Key contributing factors:</strong>
            <ul>
              {activePrevention.reasons.map((reason, idx) => (
                <li key={idx}>{reason}</li>
              ))}
            </ul>
          </div>

          <p className="insight">{activePrevention.advice}</p>
        </article>

        <article className="panel">
          <div className="section-heading">
            <div>
              <h2>Prevention checklist</h2>
              <p>Track mitigation checks for {currentService} in this session.</p>
            </div>
            <div className="heading-actions">
              <span className="count">
                {reviewed.length}/{actions.length} completed
              </span>
              <button className="text-action-btn" onClick={selectAll}>
                Check all
              </button>
              <button className="text-action-btn" onClick={clearAll}>
                Clear
              </button>
            </div>
          </div>

          <div className="checklist">
            {actions.map((action) => (
              <label className="check-row" key={action}>
                <input
                  type="checkbox"
                  checked={reviewed.includes(action)}
                  onChange={() => toggleCheck(action)}
                />
                <span>{action}</span>
              </label>
            ))}
          </div>

          <div className="recommendation">
            <strong>✦ Recommended operational action</strong>
            <p>{activePrevention.advice}</p>
          </div>

          <p className="disclaimer">
            Checklist selections are preserved in this browser session only.
            No automated changes are triggered on backend infrastructure.
          </p>
        </article>
      </section>

      <section className="panel prevention-notes">
        <h2>Risk score interpretation guide</h2>
        <div className="risk-guide">
          <span>
            <i className="risk-dot healthy-dot" /> 0–54 · Lower risk (Healthy / Standard tolerance)
          </span>
          <span>
            <i className="risk-dot warning-dot" /> 55–79 · Needs review (Warning / Latency elevation)
          </span>
          <span>
            <i className="risk-dot critical-dot" /> 80–100 · High risk (Critical / Potential failure)
          </span>
        </div>
      </section>
    </>
  );
}

// ============================================================================
// Main Application Component
// ============================================================================
function App() {
  const [page, setPage] = useState(
    () => window.location.hash.replace("#", "") || "overview"
  );
  const [serviceFilter, setServiceFilter] = useState("All services");
  const [statusFilter, setStatusFilter] = useState("All statuses");
  const [serviceSearch, setServiceSearch] = useState("");
  const [range, setRange] = useState("Last 45 minutes");
  const [telemetryService, setTelemetryService] = useState("All Services");
  const [preventionService, setPreventionService] = useState("Payment Service");
  const [incidents, setIncidents] = useState(initialIncidents);
  const [notice, setNotice] = useState("");
  const [backendStatus, setBackendStatus] = useState({
    checked: false,
    online: false,
    message: "Checking backend...",
  });

  // Verify backend health endpoint non-invasively
  useEffect(() => {
    let isMounted = true;
    async function checkHealth() {
      try {
        const response = await fetch("/health", { signal: AbortSignal.timeout(2500) });
        if (response.ok) {
          const data = await response.json();
          if (isMounted) {
            setBackendStatus({
              checked: true,
              online: true,
              message: `FastAPI Online (${data.status})`,
            });
          }
        } else {
          if (isMounted) {
            setBackendStatus({
              checked: true,
              online: false,
              message: `HTTP ${response.status}`,
            });
          }
        }
      } catch (err) {
        if (isMounted) {
          setBackendStatus({
            checked: true,
            online: false,
            message: "Standalone Demo Mode (Backend Offline)",
          });
        }
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 20000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Listen for hash changes for seamless browser navigation
  useEffect(() => {
    function handleHash() {
      const hash = window.location.hash.replace("#", "");
      if (hash && ["overview", "services", "telemetry", "incidents", "prevention"].includes(hash)) {
        setPage(hash);
      }
    }
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, []);

  // Filtered services for Services tab and Overview tab
  const visibleServices = useMemo(() => {
    return services.filter((service) => {
      const matchName =
        serviceFilter === "All services" || service.name === serviceFilter;
      const matchStatus =
        statusFilter === "All statuses" || service.status === statusFilter;
      const matchSearch =
        !serviceSearch ||
        service.name.toLowerCase().includes(serviceSearch.toLowerCase()) ||
        service.type.toLowerCase().includes(serviceSearch.toLowerCase());
      return matchName && matchStatus && matchSearch;
    });
  }, [serviceFilter, statusFilter, serviceSearch]);

  const healthyCount = services.filter((s) => s.status === "Healthy").length;
  const warningCount = services.filter((s) => s.status === "Warning").length;
  const criticalCount = services.filter((s) => s.status === "Critical").length;

  // Active telemetry data based on selected range and service
  const currentTelemetry = useMemo(() => {
    const rangeData = telemetryDatasets[range] || telemetryDatasets["Last 45 minutes"];
    return rangeData[telemetryService] || rangeData["All Services"] || [];
  }, [range, telemetryService]);

  const latestTelemetryPoint = useMemo(() => {
    if (!currentTelemetry || currentTelemetry.length === 0) {
      return { latency: 0, requests: 0, errors: 0 };
    }
    return currentTelemetry[currentTelemetry.length - 1];
  }, [currentTelemetry]);

  function navigate(nextPage) {
    setPage(nextPage);
    window.location.hash = nextPage;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleInspectService(serviceName) {
    setTelemetryService(serviceName);
    navigate("telemetry");
  }

  function dismissIncident(id) {
    setIncidents((current) => current.filter((incident) => incident.id !== id));
    setNotice(`Incident ${id} dismissed from this demo view.`);
  }

  function resetIncidents() {
    setIncidents(initialIncidents);
    setNotice("Restored initial demo incidents.");
  }

  const pageMeta = {
    overview: ["Workspace", "Overview"],
    services: ["Workspace", "Services"],
    telemetry: ["Workspace", "Telemetry"],
    incidents: ["Workspace", "Incidents"],
    prevention: ["Workspace", "Prevention"],
  };

  const breadcrumb = pageMeta[page] || pageMeta.overview;

  return (
    <div className="app">
      <aside className="sidebar">
        <button
          className="brand brand-button"
          onClick={() => navigate("overview")}
          aria-label="APIGuard overview"
        >
          <span className="brand-icon">A</span>
          <span>
            <strong>APIGuard</strong>
            <small>RELIABILITY INTELLIGENCE</small>
          </span>
        </button>

        <p className="nav-heading">WORKSPACE</p>

        <nav className="nav-menu" aria-label="Main navigation">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`nav-link ${page === item.id ? "active" : ""}`}
              onClick={() => navigate(item.id)}
              aria-current={page === item.id ? "page" : undefined}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
              {item.id === "incidents" && incidents.length > 0 && (
                <b>{incidents.length}</b>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="backend-indicator" title={backendStatus.message}>
            <i className={`status-dot ${backendStatus.online ? "online" : "offline"}`} />
            <span>{backendStatus.online ? "BACKEND CONNECTED" : "DEMO / OFFLINE MODE"}</span>
          </div>
          <div className="profile">
            <div className="avatar">AI</div>
            <div>
              <strong>Platform Team</strong>
              <small>Reliability workspace</small>
            </div>
          </div>
        </div>
      </aside>

      <main className="content">
        <header className="topbar">
          <div className="breadcrumb-nav">
            <span>Workspace</span>
            <span className="muted"> / </span>
            <span className="current-crumb">{breadcrumb[1]}</span>
          </div>

          <div className="topbar-right">
            <span
              className={`backend-pill ${backendStatus.online ? "pill-online" : "pill-offline"}`}
              title="FastAPI backend status check via /health"
            >
              <i />
              {backendStatus.online ? "FastAPI Connected" : "Standalone Demo"}
            </span>
            <span className="demo-label">
              <i /> DEMO DATA
            </span>
          </div>
        </header>

        {/* ================================================================= */}
        {/* OVERVIEW SECTION */}
        {/* ================================================================= */}
        {page === "overview" && (
          <>
            <PageTitle
              title="API Failure Prediction"
              subtitle="Predict API degradation before outages, explain probable causes, and recommend preventive actions."
            >
              <select
                value={range}
                onChange={(e) => setRange(e.target.value)}
                aria-label="Time range selector"
              >
                <option>Last 45 minutes</option>
                <option>Last 1 hour</option>
                <option>Last 24 hours</option>
              </select>
            </PageTitle>

            <div className="notice">
              <span className="notice-icon">ⓘ</span>
              <div>
                <strong>Demonstration mode active</strong>
                <p>
                  Metrics, incident queues, and risk scores represent sample
                  data for the Meghana dashboard demonstration. Start the backend
                  to test live API contract endpoints.
                </p>
              </div>
            </div>

            <section className="metric-grid">
              <article className="metric-card">
                <span>Services monitored</span>
                <strong>{services.length}</strong>
                <small>Core ecosystem services</small>
                <div className="metric-symbol blue">◇</div>
              </article>

              <article className="metric-card">
                <span>Healthy services</span>
                <strong>{healthyCount}</strong>
                <small className="green-text">
                  {Math.round((healthyCount / services.length) * 100)}% operational
                </small>
                <div className="metric-symbol green">✓</div>
              </article>

              <article className="metric-card">
                <span>Warnings</span>
                <strong>{warningCount}</strong>
                <small className="amber-text">Elevated latency / 5xx</small>
                <div className="metric-symbol amber">△</div>
              </article>

              <article className="metric-card">
                <span>Critical services</span>
                <strong>{criticalCount}</strong>
                <small className="red-text">Requires immediate check</small>
                <div className="metric-symbol red">!</div>
              </article>
            </section>

            <section className="section">
              <div className="section-heading">
                <div>
                  <h2>Service health overview</h2>
                  <p>Operational status, latencies, and error rates across all tiers</p>
                </div>
                <div className="heading-actions">
                  <select
                    value={serviceFilter}
                    onChange={(e) => setServiceFilter(e.target.value)}
                    aria-label="Filter service cards"
                  >
                    <option>All services</option>
                    {services.map((s) => (
                      <option key={s.name}>{s.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <ServiceCards
                items={visibleServices}
                onInspect={handleInspectService}
              />
            </section>

            <section className="chart-grid">
              <LatencyChart data={currentTelemetry} />
              <RequestsChart data={currentTelemetry} />
            </section>

            <section className="bottom-grid">
              <IncidentList
                incidents={incidents}
                onDismiss={dismissIncident}
                onReset={resetIncidents}
                notice={notice}
                onDismissNotice={() => setNotice("")}
              />

              <article className="panel">
                <div className="section-heading">
                  <div>
                    <h2>Preventive insight</h2>
                    <p>Highest-risk service analysis</p>
                  </div>
                  <span className="sparkle">✧</span>
                </div>

                <div className="risk-line">
                  <div>
                    <span>Payment Service risk score</span>
                    <strong>
                      87<span>/100</span>
                    </strong>
                  </div>
                  <Badge>Critical</Badge>
                </div>

                <div className="progress">
                  <span
                    style={{
                      width: "87%",
                      background: "linear-gradient(90deg, #f2994a, #e55369)",
                    }}
                  />
                </div>

                <p className="insight">
                  Latency (420ms) and error rates (8.4%) are elevated in this demo.
                  Probable root cause: PostgreSQL database connection pool saturation.
                </p>

                <div className="recommendation">
                  <strong>✦ Recommended operational action</strong>
                  <p>
                    Review database saturation, inspect slow queries, and evaluate
                    payment worker autoscale headroom before peak traffic.
                  </p>
                </div>

                <button
                  className="secondary-button"
                  onClick={() => {
                    setPreventionService("Payment Service");
                    navigate("prevention");
                  }}
                >
                  Open prevention intelligence →
                </button>
              </article>
            </section>
          </>
        )}

        {/* ================================================================= */}
        {/* SERVICES SECTION */}
        {/* ================================================================= */}
        {page === "services" && (
          <>
            <PageTitle
              eyebrow="SERVICE MONITORING & INVENTORY"
              title="Services"
              subtitle="Inspect service health, response latency, error budgets, and compare key performance indicators."
            />

            <div className="notice">
              <span className="notice-icon">ⓘ</span>
              <div>
                <strong>Service inventory overview</strong>
                <p>
                  Comparing {services.length} core microservices across Edge Ingress,
                  Business Logic, Financial Core, and Data Persistence tiers.
                </p>
              </div>
            </div>

            <section className="metric-grid compact-metrics">
              <article className="metric-card">
                <span>Total services</span>
                <strong>{services.length}</strong>
                <small>Monitored endpoints</small>
              </article>
              <article className="metric-card">
                <span>Healthy</span>
                <strong>{healthyCount}</strong>
                <small className="green-text">Normal operation</small>
              </article>
              <article className="metric-card">
                <span>Warnings</span>
                <strong>{warningCount}</strong>
                <small className="amber-text">Needs attention</small>
              </article>
              <article className="metric-card">
                <span>Critical</span>
                <strong>{criticalCount}</strong>
                <small className="red-text">Degradation detected</small>
              </article>
            </section>

            <section className="section">
              <div className="section-heading">
                <div>
                  <h2>Service inventory</h2>
                  <p>Filter or search to inspect individual service metrics.</p>
                </div>

                <div className="heading-actions">
                  <input
                    type="text"
                    placeholder="Search by name or tier..."
                    className="table-search"
                    value={serviceSearch}
                    onChange={(e) => setServiceSearch(e.target.value)}
                    aria-label="Search services"
                  />
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    aria-label="Filter services by status"
                  >
                    <option>All statuses</option>
                    <option>Healthy</option>
                    <option>Warning</option>
                    <option>Critical</option>
                  </select>
                  <select
                    value={serviceFilter}
                    onChange={(e) => setServiceFilter(e.target.value)}
                    aria-label="Filter by service name"
                  >
                    <option>All services</option>
                    {services.map((service) => (
                      <option key={service.name}>{service.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <ServiceCards
                items={visibleServices}
                onInspect={handleInspectService}
              />
            </section>

            <section className="panel table-panel">
              <div className="section-heading">
                <div>
                  <h2>Service comparison table</h2>
                  <p>Side-by-side reliability and throughput metrics</p>
                </div>
                {(serviceFilter !== "All services" ||
                  statusFilter !== "All statuses" ||
                  serviceSearch) && (
                  <button
                    className="text-action-btn"
                    onClick={() => {
                      setServiceFilter("All services");
                      setStatusFilter("All statuses");
                      setServiceSearch("");
                    }}
                  >
                    Clear all filters
                  </button>
                )}
              </div>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Service</th>
                      <th>Tier</th>
                      <th>Status</th>
                      <th>Latency</th>
                      <th>Error rate</th>
                      <th>Uptime</th>
                      <th>Request volume</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleServices.length === 0 ? (
                      <tr>
                        <td colSpan="8" className="empty-table-cell">
                          No services match the current filter criteria.
                        </td>
                      </tr>
                    ) : (
                      visibleServices.map((service) => (
                        <tr key={service.name}>
                          <td>
                            <strong>{service.name}</strong>
                          </td>
                          <td>
                            <span className="tier-tag">{service.type}</span>
                          </td>
                          <td>
                            <Badge>{service.status}</Badge>
                          </td>
                          <td>
                            <strong>{service.latency} ms</strong>
                          </td>
                          <td
                            className={
                              service.errorValue > 5
                                ? "red-text"
                                : service.errorValue > 1
                                ? "amber-text"
                                : "green-text"
                            }
                          >
                            {service.error}
                          </td>
                          <td>{service.uptime}</td>
                          <td>{service.requests}</td>
                          <td>
                            <button
                              className="table-action-link"
                              onClick={() => handleInspectService(service.name)}
                            >
                              Inspect telemetry →
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}

        {/* ================================================================= */}
        {/* TELEMETRY SECTION */}
        {/* ================================================================= */}
        {page === "telemetry" && (
          <>
            <PageTitle
              eyebrow="METRICS & TELEMETRY INVESTIGATION"
              title="Telemetry"
              subtitle="Inspect historical latency curves, request throughput, and error trends over selected time windows."
            >
              <div className="telemetry-controls">
                <select
                  value={telemetryService}
                  onChange={(e) => setTelemetryService(e.target.value)}
                  aria-label="Select service for telemetry"
                >
                  <option>All Services</option>
                  {services.map((s) => (
                    <option key={s.name}>{s.name}</option>
                  ))}
                </select>

                <select
                  value={range}
                  onChange={(e) => setRange(e.target.value)}
                  aria-label="Telemetry time range selector"
                >
                  <option>Last 45 minutes</option>
                  <option>Last 1 hour</option>
                  <option>Last 24 hours</option>
                </select>
              </div>
            </PageTitle>

            <div className="notice">
              <span className="notice-icon">ⓘ</span>
              <div>
                <strong>Active telemetry scope: {telemetryService} · {range}</strong>
                <p>
                  Telemetry charts are dynamically mapped to both the selected
                  time interval ({range}) and the selected service ({telemetryService}).
                  Values align mathematically with the service status table.
                </p>
              </div>
            </div>

            <section className="metric-grid compact-metrics">
              <article className="metric-card">
                <span>Latest latency</span>
                <strong>
                  {latestTelemetryPoint.latency}
                  <small> ms</small>
                </strong>
                <small>Interval average</small>
              </article>
              <article className="metric-card">
                <span>Latest requests</span>
                <strong>
                  {latestTelemetryPoint.requests.toLocaleString()}
                </strong>
                <small>Requests in last bucket</small>
              </article>
              <article className="metric-card">
                <span>Latest errors</span>
                <strong>{latestTelemetryPoint.errors}</strong>
                <small className="red-text">Errors in last bucket</small>
              </article>
              <article className="metric-card">
                <span>Active scope</span>
                <strong className="range-value">{telemetryService}</strong>
                <small>{range}</small>
              </article>
            </section>

            <section className="chart-grid">
              <LatencyChart data={currentTelemetry} />
              <RequestsChart data={currentTelemetry} />
            </section>

            <section className="panel telemetry-errors">
              <div className="section-heading">
                <div>
                  <h2>Error trend analysis</h2>
                  <p>
                    HTTP 5xx and timeout distribution for {telemetryService} over {range}
                  </p>
                </div>
                <span className="legend red-legend">
                  <i /> Errors
                </span>
              </div>

              <div className="chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={currentTelemetry}
                    margin={{ top: 10, right: 12, left: -16, bottom: 0 }}
                  >
                    <CartesianGrid
                      stroke="#edf0f6"
                      strokeDasharray="4 4"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="time"
                      tick={{ fontSize: 10, fill: "#7e8ab1" }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: "#7e8ab1" }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip content={<CustomChartTooltip unit="errors" />} />
                    <Line
                      type="monotone"
                      dataKey="errors"
                      name="Errors"
                      stroke="#e56a7c"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: "#e56a7c" }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          </>
        )}

        {/* ================================================================= */}
        {/* INCIDENTS SECTION */}
        {/* ================================================================= */}
        {page === "incidents" && (
          <>
            <PageTitle
              eyebrow="OPERATIONS & INCIDENT RESPONSE"
              title="Incidents"
              subtitle="Review active operational incidents, diagnostic summaries, and manage incident dismissals."
            />

            <div className="notice">
              <span className="notice-icon">ⓘ</span>
              <div>
                <strong>Incident management session</strong>
                <p>
                  Dismissing an incident removes it from this local session display
                  and updates all summary counters synchronously. It does not
                  delete or alter records on the backend.
                </p>
              </div>
            </div>

            <section className="metric-grid compact-metrics">
              <article className="metric-card">
                <span>Open incidents</span>
                <strong>{incidents.length}</strong>
                <small>In current demo session</small>
              </article>
              <article className="metric-card">
                <span>Critical</span>
                <strong>
                  {incidents.filter((item) => item.risk === "Critical").length}
                </strong>
                <small className="red-text">Highest severity</small>
              </article>
              <article className="metric-card">
                <span>High</span>
                <strong>
                  {incidents.filter((item) => item.risk === "High").length}
                </strong>
                <small className="amber-text">Requires attention</small>
              </article>
              <article className="metric-card">
                <span>Medium</span>
                <strong>
                  {incidents.filter((item) => item.risk === "Medium").length}
                </strong>
                <small>Monitor trend</small>
              </article>
            </section>

            <section className="section">
              <IncidentList
                incidents={incidents}
                onDismiss={dismissIncident}
                onReset={resetIncidents}
                notice={notice}
                onDismissNotice={() => setNotice("")}
                showFullControls
              />
            </section>
          </>
        )}

        {/* ================================================================= */}
        {/* PREVENTION SECTION */}
        {/* ================================================================= */}
        {page === "prevention" && (
          <PreventionPage
            selectedService={preventionService}
            onServiceChange={setPreventionService}
          />
        )}

        <footer>
          <span>APIGuard · AI-Powered API Failure Prediction & Reliability Intelligence</span>
          <span>
            Branch: feature/meghana-dashboard · Range: {range} · Backend:{" "}
            {backendStatus.online ? "Connected" : "Standalone"}
          </span>
        </footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
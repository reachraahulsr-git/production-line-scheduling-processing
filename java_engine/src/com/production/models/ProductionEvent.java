package com.production.models;

import java.time.Instant;

/**
 * Event model capturing real-time simulation progress and lock transitions.
 */
public class ProductionEvent {
    private final String timestamp;
    private final String eventType;
    private final int jobId;
    private final int machineId;
    private final String message;
    private final String threadName;

    public ProductionEvent(String eventType, int jobId, int machineId, String message, String threadName) {
        this.timestamp = Instant.now().toString();
        this.eventType = eventType;
        this.jobId = jobId;
        this.machineId = machineId;
        this.message = message;
        this.threadName = threadName;
    }

    public String getTimestamp() { return timestamp; }
    public String getEventType() { return eventType; }
    public int getJobId() { return jobId; }
    public int getMachineId() { return machineId; }
    public String getMessage() { return message; }
    public String getThreadName() { return threadName; }

    public String toJson() {
        return String.format(
            "{\"timestamp\":\"%s\",\"eventType\":\"%s\",\"jobId\":%d,\"machineId\":%d,\"message\":\"%s\",\"threadName\":\"%s\"}",
            timestamp, eventType, jobId, machineId,
            message.replace("\"", "\\\"").replace("\n", " "),
            threadName
        );
    }
}

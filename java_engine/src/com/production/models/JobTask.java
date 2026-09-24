package com.production.models;

import java.time.Instant;

/**
 * Encapsulates a production job scheduled for multithreaded processing.
 */
public class JobTask implements Comparable<JobTask> {
    public enum Status {
        QUEUED,
        ACQUIRING_RESOURCES,
        PROCESSING,
        PAUSED,
        COMPLETED,
        FAILED,
        INTERRUPTED
    }

    private final int id;
    private final String jobNumber;
    private final String title;
    private final int machineId;
    private final int workerId;
    private final int durationSeconds; // Simulation duration
    private final String priority; // Critical, High, Medium, Low
    private volatile Status status;
    private volatile int progressPercentage;
    private volatile long startTimeMillis;
    private volatile long endTimeMillis;
    private String errorMessage;

    public JobTask(int id, String jobNumber, String title, int machineId, int workerId, int durationSeconds, String priority) {
        this.id = id;
        this.jobNumber = jobNumber;
        this.title = title;
        this.machineId = machineId;
        this.workerId = workerId;
        this.durationSeconds = Math.max(2, durationSeconds);
        this.priority = priority != null ? priority : "Medium";
        this.status = Status.QUEUED;
        this.progressPercentage = 0;
    }

    public int getId() { return id; }
    public String getJobNumber() { return jobNumber; }
    public String getTitle() { return title; }
    public int getMachineId() { return machineId; }
    public int getWorkerId() { return workerId; }
    public int getDurationSeconds() { return durationSeconds; }
    public String getPriority() { return priority; }
    public Status getStatus() { return status; }
    public synchronized void setStatus(Status status) { this.status = status; }
    public int getProgressPercentage() { return progressPercentage; }
    public synchronized void setProgressPercentage(int progressPercentage) {
        this.progressPercentage = Math.min(100, Math.max(0, progressPercentage));
    }
    public long getStartTimeMillis() { return startTimeMillis; }
    public void setStartTimeMillis(long startTimeMillis) { this.startTimeMillis = startTimeMillis; }
    public long getEndTimeMillis() { return endTimeMillis; }
    public void setEndTimeMillis(long endTimeMillis) { this.endTimeMillis = endTimeMillis; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }

    public int getPriorityWeight() {
        switch (priority.toUpperCase()) {
            case "CRITICAL": return 4;
            case "HIGH": return 3;
            case "MEDIUM": return 2;
            case "LOW": return 1;
            default: return 2;
        }
    }

    @Override
    public int compareTo(JobTask o) {
        // Higher priority first
        int cmp = Integer.compare(o.getPriorityWeight(), this.getPriorityWeight());
        if (cmp != 0) return cmp;
        return Integer.compare(this.id, o.id);
    }

    public String toJson() {
        return String.format(
            "{\"id\":%d,\"jobNumber\":\"%s\",\"title\":\"%s\",\"machineId\":%d,\"workerId\":%d,\"durationSeconds\":%d,\"priority\":\"%s\",\"status\":\"%s\",\"progress\":%d,\"errorMessage\":%s}",
            id,
            escapeJson(jobNumber),
            escapeJson(title),
            machineId,
            workerId,
            durationSeconds,
            priority,
            status.name(),
            progressPercentage,
            errorMessage == null ? "null" : "\"" + escapeJson(errorMessage) + "\""
        );
    }

    private static String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "");
    }
}

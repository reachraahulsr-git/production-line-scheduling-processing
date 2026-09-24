package com.production.ipc;

import com.production.engine.ProductionEngine;
import com.production.models.JobTask;
import com.production.models.MachineUnit;
import com.production.models.WorkerAssignment;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Parses and dispatches JSON protocol messages between Python and Java.
 * Self-contained parser without external JSON library dependencies to ensure pure zero-dependency compilation.
 */
public class ProtocolHandler {
    private final ProductionEngine engine;

    public ProtocolHandler(ProductionEngine engine) {
        this.engine = engine;
    }

    public String handleCommand(String rawCommand) {
        if (rawCommand == null || rawCommand.trim().isEmpty()) {
            return "{\"error\":\"Empty command\"}";
        }

        String trimmed = rawCommand.trim();

        // Extract command name
        String command = extractStringField(trimmed, "command");
        if (command == null || command.isEmpty()) {
            if (trimmed.equalsIgnoreCase("PING")) command = "PING";
            else if (trimmed.equalsIgnoreCase("GET_STATUS")) command = "GET_STATUS";
            else if (trimmed.equalsIgnoreCase("PAUSE")) command = "PAUSE";
            else if (trimmed.equalsIgnoreCase("RESUME")) command = "RESUME";
            else if (trimmed.equalsIgnoreCase("STOP")) command = "STOP";
        }

        switch (command.toUpperCase()) {
            case "PING":
                return "{\"status\":\"PONG\",\"timestamp\":" + System.currentTimeMillis() + "}";

            case "INIT_RESOURCES":
                return handleInitResources(trimmed);

            case "SUBMIT_JOB":
                return handleSubmitJob(trimmed);

            case "SUBMIT_BATCH":
                return handleSubmitBatch(trimmed);

            case "PAUSE":
                engine.pauseAll();
                return "{\"status\":\"PAUSED\",\"success\":true}";

            case "RESUME":
                engine.resumeAll();
                return "{\"status\":\"RESUMED\",\"success\":true}";

            case "STOP":
                engine.stopAllThreads();
                return "{\"status\":\"STOPPED\",\"success\":true}";

            case "GET_STATUS":
                return engine.getStatusJson();

            default:
                return "{\"error\":\"Unknown command: " + escape(command) + "\"}";
        }
    }

    private String handleInitResources(String json) {
        try {
            List<MachineUnit> machines = parseMachines(json);
            List<WorkerAssignment> workers = parseWorkers(json);
            engine.initializeResources(machines, workers);
            return "{\"success\":true,\"message\":\"Resources initialized\",\"machines\":" + machines.size() + ",\"workers\":" + workers.size() + "}";
        } catch (Exception e) {
            return "{\"success\":false,\"error\":\"Init failed: " + escape(e.getMessage()) + "\"}";
        }
    }

    private String handleSubmitJob(String json) {
        try {
            int id = extractIntField(json, "id", 0);
            String number = extractStringField(json, "jobNumber");
            String title = extractStringField(json, "title");
            int machineId = extractIntField(json, "machineId", 1);
            int workerId = extractIntField(json, "workerId", 1);
            int duration = extractIntField(json, "durationSeconds", 5);
            String priority = extractStringField(json, "priority");

            JobTask task = new JobTask(id, number != null ? number : "JOB-" + id, title != null ? title : "Production Task",
                    machineId, workerId, duration, priority != null ? priority : "Medium");
            engine.submitJob(task);
            return "{\"success\":true,\"message\":\"Job queued\",\"jobId\":" + id + "}";
        } catch (Exception e) {
            return "{\"success\":false,\"error\":\"Submit failed: " + escape(e.getMessage()) + "\"}";
        }
    }

    private String handleSubmitBatch(String json) {
        try {
            List<JobTask> tasks = parseJobTasks(json);
            engine.submitBatch(tasks);
            return "{\"success\":true,\"message\":\"Batch queued\",\"batchSize\":" + tasks.size() + "}";
        } catch (Exception e) {
            return "{\"success\":false,\"error\":\"Batch failed: " + escape(e.getMessage()) + "\"}";
        }
    }

    // Light regex-based JSON parser utilities
    private List<MachineUnit> parseMachines(String json) {
        List<MachineUnit> list = new ArrayList<>();
        Pattern arrayPattern = Pattern.compile("\"machines\"\\s*:\\s*\\[([^\\]]*)\\]");
        Matcher m = arrayPattern.matcher(json);
        if (m.find()) {
            String items = m.group(1);
            Pattern objPattern = Pattern.compile("\\{([^\\}]+)\\}");
            Matcher objM = objPattern.matcher(items);
            while (objM.find()) {
                String obj = objM.group(1);
                int id = extractIntField("{" + obj + "}", "id", 0);
                String code = extractStringField("{" + obj + "}", "code");
                String name = extractStringField("{" + obj + "}", "name");
                String type = extractStringField("{" + obj + "}", "type");
                String stateStr = extractStringField("{" + obj + "}", "state");
                MachineUnit.State state = MachineUnit.State.IDLE;
                if ("RUNNING".equalsIgnoreCase(stateStr)) state = MachineUnit.State.BUSY;
                else if ("MAINTENANCE".equalsIgnoreCase(stateStr)) state = MachineUnit.State.MAINTENANCE;
                else if ("ERROR".equalsIgnoreCase(stateStr)) state = MachineUnit.State.ERROR;

                list.add(new MachineUnit(id, code != null ? code : "M-" + id, name != null ? name : "Machine " + id,
                        type != null ? type : "General", state));
            }
        }
        return list;
    }

    private List<WorkerAssignment> parseWorkers(String json) {
        List<WorkerAssignment> list = new ArrayList<>();
        Pattern arrayPattern = Pattern.compile("\"workers\"\\s*:\\s*\\[([^\\]]*)\\]");
        Matcher m = arrayPattern.matcher(json);
        if (m.find()) {
            String items = m.group(1);
            Pattern objPattern = Pattern.compile("\\{([^\\}]+)\\}");
            Matcher objM = objPattern.matcher(items);
            while (objM.find()) {
                String obj = objM.group(1);
                int id = extractIntField("{" + obj + "}", "id", 0);
                String code = extractStringField("{" + obj + "}", "code");
                String name = extractStringField("{" + obj + "}", "name");
                String skill = extractStringField("{" + obj + "}", "skill");
                list.add(new WorkerAssignment(id, code != null ? code : "W-" + id, name != null ? name : "Worker " + id,
                        skill != null ? skill : "Mid-Level"));
            }
        }
        return list;
    }

    private List<JobTask> parseJobTasks(String json) {
        List<JobTask> list = new ArrayList<>();
        Pattern arrayPattern = Pattern.compile("\"jobs\"\\s*:\\s*\\[([^\\]]*)\\]");
        Matcher m = arrayPattern.matcher(json);
        if (m.find()) {
            String items = m.group(1);
            Pattern objPattern = Pattern.compile("\\{([^\\}]+)\\}");
            Matcher objM = objPattern.matcher(items);
            while (objM.find()) {
                String obj = "{" + objM.group(1) + "}";
                int id = extractIntField(obj, "id", 0);
                String number = extractStringField(obj, "jobNumber");
                String title = extractStringField(obj, "title");
                int machineId = extractIntField(obj, "machineId", 1);
                int workerId = extractIntField(obj, "workerId", 1);
                int duration = extractIntField(obj, "durationSeconds", 5);
                String priority = extractStringField(obj, "priority");

                list.add(new JobTask(id, number != null ? number : "JOB-" + id, title != null ? title : "Task",
                        machineId, workerId, duration, priority != null ? priority : "Medium"));
            }
        }
        return list;
    }

    private String extractStringField(String json, String fieldName) {
        Pattern p = Pattern.compile("\"" + fieldName + "\"\\s*:\\s*\"([^\"]*)\"");
        Matcher m = p.matcher(json);
        if (m.find()) return m.group(1);
        return null;
    }

    private int extractIntField(String json, String fieldName, int defaultValue) {
        Pattern p = Pattern.compile("\"" + fieldName + "\"\\s*:\\s*([0-9]+)");
        Matcher m = p.matcher(json);
        if (m.find()) {
            try { return Integer.parseInt(m.group(1)); } catch (NumberFormatException ignored) {}
        }
        return defaultValue;
    }

    private String escape(String s) {
        if (s == null) return "";
        return s.replace("\"", "\\\"").replace("\n", " ");
    }
}

package com.production.engine;

import com.production.models.JobTask;
import com.production.models.MachineUnit;
import com.production.models.ProductionEvent;
import com.production.models.WorkerAssignment;
import com.production.interfaces.IEventListener;
import com.production.sync.SafeJobQueue;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * Master multithreaded production controller.
 * Orchestrates machine threads, receives job batches, and dispatches to machine queues.
 */
public class ProductionEngine implements IEventListener {
    private final Map<Integer, MachineUnit> machines = new ConcurrentHashMap<>();
    private final Map<Integer, WorkerAssignment> workers = new ConcurrentHashMap<>();
    private final Map<Integer, MachineWorkerThread> threadPool = new ConcurrentHashMap<>();
    private final Map<Integer, JobTask> taskRegistry = new ConcurrentHashMap<>();
    private final ConcurrentLinkedQueue<ProductionEvent> eventBuffer = new ConcurrentLinkedQueue<>();
    private final SafeJobQueue globalDispatchQueue = new SafeJobQueue(100);

    private volatile boolean isRunning = false;
    private volatile boolean isPaused = false;
    private static final int MAX_EVENTS = 200;

    public ProductionEngine() {
        // Ready
    }

    public synchronized void initializeResources(List<MachineUnit> machineList, List<WorkerAssignment> workerList) {
        stopAllThreads();
        machines.clear();
        workers.clear();
        threadPool.clear();

        for (MachineUnit m : machineList) {
            machines.put(m.getId(), m);
        }
        for (WorkerAssignment w : workerList) {
            workers.put(w.getId(), w);
        }

        // Spawn one dedicated worker thread per physical machine
        for (MachineUnit m : machines.values()) {
            MachineWorkerThread thread = new MachineWorkerThread(m, workers, this);
            threadPool.put(m.getId(), thread);
            thread.start();
        }
        isRunning = true;
        isPaused = false;

        onEvent(new ProductionEvent("INFO", -1, -1,
                "Java Production Engine initialized with " + machines.size() + " machine threads and " + workers.size() + " worker resources.",
                "ProductionEngine"));
    }

    public void submitJob(JobTask task) {
        taskRegistry.put(task.getId(), task);
        MachineWorkerThread targetThread = threadPool.get(task.getMachineId());
        if (targetThread != null && targetThread.isAlive()) {
            targetThread.assignJob(task);
        } else {
            globalDispatchQueue.enqueue(task);
            onEvent(new ProductionEvent("WARNING", task.getId(), task.getMachineId(),
                    "No active thread found for machine " + task.getMachineId() + ". Job held in dispatch queue.",
                    "ProductionEngine"));
        }
    }

    public void submitBatch(List<JobTask> tasks) {
        for (JobTask t : tasks) {
            submitJob(t);
        }
        onEvent(new ProductionEvent("INFO", -1, -1,
                "Batch of " + tasks.size() + " jobs submitted to multithreaded engine.",
                "ProductionEngine"));
    }

    public void pauseAll() {
        isPaused = true;
        for (MachineWorkerThread thread : threadPool.values()) {
            thread.pauseProcessing();
        }
        onEvent(new ProductionEvent("WARNING", -1, -1, "All machine threads PAUSED.", "ProductionEngine"));
    }

    public void resumeAll() {
        isPaused = false;
        for (MachineWorkerThread thread : threadPool.values()) {
            thread.resumeProcessing();
        }
        onEvent(new ProductionEvent("INFO", -1, -1, "All machine threads RESUMED.", "ProductionEngine"));
    }

    public void stopAllThreads() {
        isRunning = false;
        for (MachineWorkerThread thread : threadPool.values()) {
            thread.stopProcessing();
        }
    }

    @Override
    public void onEvent(ProductionEvent event) {
        eventBuffer.offer(event);
        while (eventBuffer.size() > MAX_EVENTS) {
            eventBuffer.poll();
        }
    }

    public List<ProductionEvent> getRecentEvents(int limit) {
        List<ProductionEvent> list = new ArrayList<>(eventBuffer);
        int fromIndex = Math.max(0, list.size() - limit);
        List<ProductionEvent> sub = list.subList(fromIndex, list.size());
        Collections.reverse(sub);
        return sub;
    }

    public String getStatusJson() {
        StringBuilder sb = new StringBuilder();
        sb.append("{");
        sb.append("\"isRunning\":").append(isRunning).append(",");
        sb.append("\"isPaused\":").append(isPaused).append(",");
        sb.append("\"activeMachineThreads\":").append(threadPool.size()).append(",");

        // Machines
        sb.append("\"threads\":[");
        int count = 0;
        for (MachineWorkerThread t : threadPool.values()) {
            if (count > 0) sb.append(",");
            sb.append(t.toJson());
            count++;
        }
        sb.append("],");

        // Tasks
        sb.append("\"tasks\":[");
        int tCount = 0;
        for (JobTask t : taskRegistry.values()) {
            if (tCount > 0) sb.append(",");
            sb.append(t.toJson());
            tCount++;
        }
        sb.append("],");

        // Events
        List<ProductionEvent> recent = getRecentEvents(30);
        sb.append("\"events\":[");
        for (int i = 0; i < recent.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append(recent.get(i).toJson());
        }
        sb.append("]");

        sb.append("}");
        return sb.toString();
    }
}

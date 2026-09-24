package com.production.engine;

import com.production.models.JobTask;
import com.production.models.MachineUnit;
import com.production.models.ProductionEvent;
import com.production.models.WorkerAssignment;
import com.production.interfaces.IProcessor;
import com.production.interfaces.IEventListener;
import com.production.exceptions.ProductionHaltException;
import com.production.exceptions.ResourceConflictException;
import com.production.sync.ResourceLockManager;

import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.Map;

/**
 * Dedicated worker thread for a single physical machine.
 * Processes jobs assigned to this machine sequentially while running concurrently with other machines.
 */
public class MachineWorkerThread extends Thread implements IProcessor {
    private final MachineUnit machine;
    private final Map<Integer, WorkerAssignment> workerRegistry;
    private final BlockingQueue<JobTask> machineQueue;
    private final IEventListener eventListener;
    private volatile boolean running = true;
    private volatile boolean paused = false;
    private final Object pauseLock = new Object();
    private volatile JobTask activeTask = null;

    public MachineWorkerThread(MachineUnit machine, Map<Integer, WorkerAssignment> workerRegistry, IEventListener eventListener) {
        super("MachineThread-" + machine.getCode());
        this.machine = machine;
        this.workerRegistry = workerRegistry;
        this.eventListener = eventListener;
        this.machineQueue = new LinkedBlockingQueue<>();
    }

    public void assignJob(JobTask task) {
        machineQueue.offer(task);
        fireEvent("QUEUED", task.getId(), "Job " + task.getJobNumber() + " queued for processing on " + machine.getName());
    }

    public int getQueueDepth() {
        return machineQueue.size();
    }

    public JobTask getActiveTask() {
        return activeTask;
    }

    public MachineUnit getMachine() {
        return machine;
    }

    @Override
    public void run() {
        fireEvent("INFO", -1, "Worker thread started for " + machine.getName() + " [" + machine.getCode() + "]");

        while (running) {
            try {
                // Wait for an assigned job (polls every 500ms to check running flag)
                JobTask task = machineQueue.poll(500, TimeUnit.MILLISECONDS);
                if (task == null) {
                    continue;
                }

                // Check machine operational state
                if (machine.getState() == MachineUnit.State.MAINTENANCE || machine.getState() == MachineUnit.State.ERROR) {
                    task.setStatus(JobTask.Status.FAILED);
                    task.setErrorMessage("Machine " + machine.getCode() + " is in " + machine.getState().name() + " mode.");
                    fireEvent("ERROR", task.getId(), "Job " + task.getJobNumber() + " rejected: machine offline.");
                    continue;
                }

                activeTask = task;
                processJob(task);
                activeTask = null;

            } catch (InterruptedException e) {
                if (!running) break;
            } catch (Exception e) {
                fireEvent("ERROR", activeTask != null ? activeTask.getId() : -1, "Unexpected thread exception: " + e.getMessage());
            }
        }

        fireEvent("INFO", -1, "Worker thread terminated for " + machine.getName());
    }

    @Override
    public void processJob(JobTask task) {
        WorkerAssignment worker = workerRegistry.get(task.getWorkerId());
        String requester = getName() + "-Job-" + task.getJobNumber();

        task.setStatus(JobTask.Status.ACQUIRING_RESOURCES);
        fireEvent("LOCK_ACQUIRED", task.getId(), "Attempting resource lock on " + machine.getCode() + " & Worker ID " + task.getWorkerId());

        try {
            // Lock machine and worker
            ResourceLockManager.acquirePair(machine, worker, requester, 5000);
            machine.setCurrentJobId(task.getId());

            task.setStatus(JobTask.Status.PROCESSING);
            task.setStartTimeMillis(System.currentTimeMillis());
            fireEvent("START", task.getId(), "Production cycle initiated for " + task.getTitle() + " (Priority: " + task.getPriority() + ")");

            int totalDurationSec = task.getDurationSeconds();
            int steps = 10;
            long stepSleepMillis = (long) ((totalDurationSec * 1000.0) / steps);

            for (int step = 1; step <= steps; step++) {
                if (!running) {
                    task.setStatus(JobTask.Status.INTERRUPTED);
                    throw new ProductionHaltException("Engine stopped during job processing");
                }

                // Handle pause/resume
                synchronized (pauseLock) {
                    while (paused && running) {
                        task.setStatus(JobTask.Status.PAUSED);
                        fireEvent("INFO", task.getId(), "Job paused on machine " + machine.getCode());
                        pauseLock.wait();
                        if (running) {
                            task.setStatus(JobTask.Status.PROCESSING);
                            fireEvent("INFO", task.getId(), "Job resumed on machine " + machine.getCode());
                        }
                    }
                }

                Thread.sleep(stepSleepMillis);
                int progress = step * 10;
                task.setProgressPercentage(progress);

                if (step % 2 == 0 || step == steps) {
                    fireEvent("PROGRESS", task.getId(), "Processing " + task.getJobNumber() + ": " + progress + "% complete");
                }
            }

            task.setStatus(JobTask.Status.COMPLETED);
            task.setEndTimeMillis(System.currentTimeMillis());
            task.setProgressPercentage(100);
            fireEvent("COMPLETION", task.getId(), "Production finished successfully for " + task.getTitle() + " in " + totalDurationSec + "s");

        } catch (ResourceConflictException e) {
            task.setStatus(JobTask.Status.FAILED);
            task.setErrorMessage(e.getMessage());
            fireEvent("ERROR", task.getId(), "Resource Conflict: " + e.getMessage());
        } catch (ProductionHaltException e) {
            task.setStatus(JobTask.Status.INTERRUPTED);
            task.setErrorMessage(e.getMessage());
            fireEvent("WARNING", task.getId(), "Halt exception: " + e.getMessage());
        } catch (InterruptedException e) {
            task.setStatus(JobTask.Status.INTERRUPTED);
            task.setErrorMessage("Processing interrupted by shutdown signal.");
            fireEvent("WARNING", task.getId(), "Job interrupted.");
        } finally {
            ResourceLockManager.releasePair(machine, worker, requester);
            machine.setCurrentJobId(-1);
        }
    }

    @Override
    public void pauseProcessing() {
        synchronized (pauseLock) {
            paused = true;
        }
    }

    @Override
    public void resumeProcessing() {
        synchronized (pauseLock) {
            paused = false;
            pauseLock.notifyAll();
        }
    }

    @Override
    public void stopProcessing() {
        running = false;
        resumeProcessing();
        interrupt();
    }

    @Override
    public boolean isRunning() {
        return running;
    }

    private void fireEvent(String eventType, int jobId, String message) {
        if (eventListener != null) {
            eventListener.onEvent(new ProductionEvent(eventType, jobId, machine.getId(), message, getName()));
        }
    }

    public String toJson() {
        return String.format(
            "{\"threadName\":\"%s\",\"machine\":%s,\"queueDepth\":%d,\"activeJob\":%s,\"isPaused\":%b,\"isAlive\":%b}",
            getName(),
            machine.toJson(),
            machineQueue.size(),
            activeTask != null ? activeTask.toJson() : "null",
            paused,
            isAlive()
        );
    }
}

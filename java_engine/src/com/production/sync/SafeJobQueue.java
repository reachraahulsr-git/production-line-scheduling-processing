package com.production.sync;

import com.production.models.JobTask;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.PriorityBlockingQueue;
import java.util.concurrent.TimeUnit;

/**
 * Thread-safe Priority Queue prioritizing Critical and High priority production tasks.
 */
public class SafeJobQueue {
    private final PriorityBlockingQueue<JobTask> queue;

    public SafeJobQueue(int initialCapacity) {
        this.queue = new PriorityBlockingQueue<>(initialCapacity);
    }

    public void enqueue(JobTask task) {
        queue.put(task);
    }

    public JobTask poll(long timeoutMillis) throws InterruptedException {
        return queue.poll(timeoutMillis, TimeUnit.MILLISECONDS);
    }

    public JobTask peek() {
        return queue.peek();
    }

    public int size() {
        return queue.size();
    }

    public boolean isEmpty() {
        return queue.isEmpty();
    }

    public void clear() {
        queue.clear();
    }

    public List<JobTask> snapshot() {
        return new ArrayList<>(queue);
    }
}

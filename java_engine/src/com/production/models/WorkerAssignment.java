package com.production.models;

import com.production.interfaces.ILockableResource;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Thread-safe representation of an assigned technician/worker resource.
 */
public class WorkerAssignment implements ILockableResource {
    private final int id;
    private final String employeeCode;
    private final String name;
    private final String skillLevel;
    private final ReentrantLock lock;
    private volatile String lockedBy;

    public WorkerAssignment(int id, String employeeCode, String name, String skillLevel) {
        this.id = id;
        this.employeeCode = employeeCode;
        this.name = name;
        this.skillLevel = skillLevel;
        this.lock = new ReentrantLock(true);
        this.lockedBy = null;
    }

    public int getId() { return id; }
    public String getEmployeeCode() { return employeeCode; }
    public String getName() { return name; }
    public String getSkillLevel() { return skillLevel; }

    @Override
    public boolean tryAcquireLock(String requesterId, long timeoutMillis) throws InterruptedException {
        boolean acquired = lock.tryLock(timeoutMillis, TimeUnit.MILLISECONDS);
        if (acquired) {
            this.lockedBy = requesterId;
        }
        return acquired;
    }

    @Override
    public void releaseLock(String requesterId) {
        if (lock.isHeldByCurrentThread()) {
            this.lockedBy = null;
            lock.unlock();
        }
    }

    @Override
    public boolean isLocked() {
        return lock.isLocked();
    }

    @Override
    public String getLockedBy() {
        return lockedBy;
    }

    @Override
    public String getResourceId() {
        return "WORKER-" + id + "(" + employeeCode + ")";
    }

    public String toJson() {
        return String.format(
            "{\"id\":%d,\"employeeCode\":\"%s\",\"name\":\"%s\",\"skill\":\"%s\",\"isLocked\":%b,\"lockedBy\":%s}",
            id, employeeCode, name, skillLevel, isLocked(),
            lockedBy == null ? "null" : "\"" + lockedBy + "\""
        );
    }
}

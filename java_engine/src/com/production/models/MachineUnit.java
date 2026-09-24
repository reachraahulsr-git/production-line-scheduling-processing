package com.production.models;

import com.production.interfaces.ILockableResource;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Thread-safe representation of a physical machine on the production line.
 */
public class MachineUnit implements ILockableResource {
    public enum State {
        IDLE,
        BUSY,
        MAINTENANCE,
        ERROR
    }

    private final int id;
    private final String code;
    private final String name;
    private final String machineType;
    private volatile State state;
    private final ReentrantLock lock;
    private volatile String lockedBy;
    private volatile int currentJobId;

    public MachineUnit(int id, String code, String name, String machineType, State initialState) {
        this.id = id;
        this.code = code;
        this.name = name;
        this.machineType = machineType;
        this.state = initialState != null ? initialState : State.IDLE;
        this.lock = new ReentrantLock(true); // Fair lock
        this.lockedBy = null;
        this.currentJobId = -1;
    }

    public int getId() { return id; }
    public String getCode() { return code; }
    public String getName() { return name; }
    public String getMachineType() { return machineType; }
    public State getState() { return state; }
    public void setState(State state) { this.state = state; }
    public int getCurrentJobId() { return currentJobId; }
    public void setCurrentJobId(int currentJobId) { this.currentJobId = currentJobId; }

    @Override
    public boolean tryAcquireLock(String requesterId, long timeoutMillis) throws InterruptedException {
        boolean acquired = lock.tryLock(timeoutMillis, TimeUnit.MILLISECONDS);
        if (acquired) {
            this.lockedBy = requesterId;
            this.state = State.BUSY;
        }
        return acquired;
    }

    @Override
    public void releaseLock(String requesterId) {
        if (lock.isHeldByCurrentThread()) {
            this.lockedBy = null;
            if (this.state == State.BUSY) {
                this.state = State.IDLE;
            }
            this.currentJobId = -1;
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
        return "MACHINE-" + id + "(" + code + ")";
    }

    public String toJson() {
        return String.format(
            "{\"id\":%d,\"code\":\"%s\",\"name\":\"%s\",\"type\":\"%s\",\"state\":\"%s\",\"isLocked\":%b,\"lockedBy\":%s,\"currentJobId\":%d}",
            id, code, name, machineType, state.name(), isLocked(),
            lockedBy == null ? "null" : "\"" + lockedBy + "\"",
            currentJobId
        );
    }
}

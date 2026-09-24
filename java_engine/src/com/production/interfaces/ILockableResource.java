package com.production.interfaces;

import com.production.exceptions.ResourceConflictException;

/**
 * Interface for thread-safe lockable resources (Machines, Workers).
 */
public interface ILockableResource {
    boolean tryAcquireLock(String requesterId, long timeoutMillis) throws InterruptedException;
    void releaseLock(String requesterId);
    boolean isLocked();
    String getLockedBy();
    String getResourceId();
}

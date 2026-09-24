package com.production.sync;

import com.production.interfaces.ILockableResource;
import com.production.exceptions.ResourceConflictException;
import java.util.Arrays;
import java.util.Comparator;

/**
 * Coordinates multi-resource locking with strict ordering to prevent circular wait deadlocks.
 */
public class ResourceLockManager {

    /**
     * Atomically acquires both machine and worker locks within timeoutMillis.
     * Enforces lexicographical order of resource IDs to prevent deadlock.
     */
    public static void acquirePair(ILockableResource res1, ILockableResource res2, String requesterId, long timeoutMillis)
            throws ResourceConflictException, InterruptedException {

        if (res1 == null && res2 == null) return;
        if (res1 == null) {
            if (!res2.tryAcquireLock(requesterId, timeoutMillis)) {
                throw new ResourceConflictException(res2.getResourceId(), requesterId,
                        "Timeout acquiring single resource: " + res2.getResourceId());
            }
            return;
        }
        if (res2 == null) {
            if (!res1.tryAcquireLock(requesterId, timeoutMillis)) {
                throw new ResourceConflictException(res1.getResourceId(), requesterId,
                        "Timeout acquiring single resource: " + res1.getResourceId());
            }
            return;
        }

        // Deterministic ordering prevents deadlocks
        ILockableResource first = res1;
        ILockableResource second = res2;
        if (res1.getResourceId().compareTo(res2.getResourceId()) > 0) {
            first = res2;
            second = res1;
        }

        long deadline = System.currentTimeMillis() + timeoutMillis;

        if (!first.tryAcquireLock(requesterId, timeoutMillis / 2)) {
            throw new ResourceConflictException(first.getResourceId(), requesterId,
                    "Resource busy: failed to lock " + first.getResourceId());
        }

        long remaining = Math.max(10, deadline - System.currentTimeMillis());
        boolean secondAcquired = false;
        try {
            secondAcquired = second.tryAcquireLock(requesterId, remaining);
            if (!secondAcquired) {
                throw new ResourceConflictException(second.getResourceId(), requesterId,
                        "Secondary resource busy: failed to lock " + second.getResourceId());
            }
        } finally {
            if (!secondAcquired) {
                first.releaseLock(requesterId); // Rollback first lock if second failed
            }
        }
    }

    public static void releasePair(ILockableResource res1, ILockableResource res2, String requesterId) {
        if (res2 != null) {
            try { res2.releaseLock(requesterId); } catch (Exception ignored) {}
        }
        if (res1 != null) {
            try { res1.releaseLock(requesterId); } catch (Exception ignored) {}
        }
    }
}

package com.production.exceptions;

/**
 * Thrown when two threads attempt to seize the same machine or worker simultaneously.
 */
public class ResourceConflictException extends Exception {
    private final String resourceId;
    private final String requesterId;

    public ResourceConflictException(String resourceId, String requesterId, String message) {
        super(message);
        this.resourceId = resourceId;
        this.requesterId = requesterId;
    }

    public String getResourceId() {
        return resourceId;
    }

    public String getRequesterId() {
        return requesterId;
    }
}

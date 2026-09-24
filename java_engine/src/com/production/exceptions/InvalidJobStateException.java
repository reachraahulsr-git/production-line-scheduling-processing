package com.production.exceptions;

/**
 * Thrown on improper state transitions in the JobTask state machine.
 */
public class InvalidJobStateException extends RuntimeException {
    public InvalidJobStateException(String message) {
        super(message);
    }
}

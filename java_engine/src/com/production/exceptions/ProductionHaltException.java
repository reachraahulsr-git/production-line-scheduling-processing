package com.production.exceptions;

/**
 * Thrown when an emergency stop or fatal hardware exception interrupts processing.
 */
public class ProductionHaltException extends Exception {
    private final String reason;

    public ProductionHaltException(String reason) {
        super("Production halted: " + reason);
        this.reason = reason;
    }

    public String getReason() {
        return reason;
    }
}

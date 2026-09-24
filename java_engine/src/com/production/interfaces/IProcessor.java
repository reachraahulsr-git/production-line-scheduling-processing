package com.production.interfaces;

import com.production.models.JobTask;
import com.production.exceptions.ProductionHaltException;
import com.production.exceptions.ResourceConflictException;

/**
 * Interface defining the execution lifecycle of a production processor.
 */
public interface IProcessor {
    void processJob(JobTask task) throws ProductionHaltException, ResourceConflictException;
    void pauseProcessing();
    void resumeProcessing();
    void stopProcessing();
    boolean isRunning();
}

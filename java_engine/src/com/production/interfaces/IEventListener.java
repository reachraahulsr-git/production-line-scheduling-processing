package com.production.interfaces;

import com.production.models.ProductionEvent;

/**
 * Listener interface for real-time thread simulation events.
 */
public interface IEventListener {
    void onEvent(ProductionEvent event);
}

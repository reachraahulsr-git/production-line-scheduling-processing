package com.production.ipc;

import com.production.engine.ProductionEngine;

/**
 * Main application entry point for the Java Multithreaded Production-Processing Engine.
 */
public class Main {
    public static void main(String[] args) {
        int port = 5050;
        if (args.length > 0) {
            try {
                port = Integer.parseInt(args[0]);
            } catch (NumberFormatException ignored) {}
        }

        System.out.println("==========================================================");
        System.out.println("  Production Line Resource Scheduling System - Java Engine");
        System.out.println("  Architecture: CSE Multithreaded Real-time Processing");
        System.out.println("==========================================================");

        ProductionEngine engine = new ProductionEngine();
        ProtocolHandler handler = new ProtocolHandler(engine);
        SocketServer server = new SocketServer(port, handler);

        // Register shutdown hook
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("\n[JAVA ENGINE] Shutting down multithreaded processing engine...");
            engine.stopAllThreads();
            server.stopServer();
            System.out.println("[JAVA ENGINE] Clean shutdown complete.");
        }));

        server.start();

        try {
            server.join();
        } catch (InterruptedException e) {
            System.out.println("[JAVA ENGINE] Main thread interrupted.");
        }
    }
}

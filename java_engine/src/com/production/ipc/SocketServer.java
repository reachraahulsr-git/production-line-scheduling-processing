package com.production.ipc;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketException;
import java.nio.charset.StandardCharsets;

/**
 * High-performance multi-threaded TCP Socket Server for Python-Java IPC.
 */
public class SocketServer extends Thread {
    private final int port;
    private final ProtocolHandler handler;
    private volatile boolean running = true;
    private ServerSocket serverSocket;

    public SocketServer(int port, ProtocolHandler handler) {
        super("JavaSocketServer-Port" + port);
        this.port = port;
        this.handler = handler;
    }

    @Override
    public void run() {
        try {
            serverSocket = new ServerSocket(port);
            System.out.println("[JAVA SERVER] Listening for Python IPC on 127.0.0.1:" + port);

            while (running) {
                try {
                    Socket clientSocket = serverSocket.accept();
                    new ClientHandler(clientSocket, handler).start();
                } catch (SocketException se) {
                    if (!running) break;
                }
            }
        } catch (Exception e) {
            System.err.println("[JAVA SERVER ERROR] ServerSocket failure: " + e.getMessage());
        } finally {
            closeSocket();
        }
    }

    public void stopServer() {
        running = false;
        closeSocket();
    }

    private void closeSocket() {
        if (serverSocket != null && !serverSocket.isClosed()) {
            try { serverSocket.close(); } catch (Exception ignored) {}
        }
    }

    private static class ClientHandler extends Thread {
        private final Socket socket;
        private final ProtocolHandler handler;

        public ClientHandler(Socket socket, ProtocolHandler handler) {
            this.socket = socket;
            this.handler = handler;
        }

        @Override
        public void run() {
            try (
                BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
                PrintWriter writer = new PrintWriter(socket.getOutputStream(), true, StandardCharsets.UTF_8)
            ) {
                String line;
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (line.isEmpty()) continue;
                    String response = handler.handleCommand(line);
                    writer.println(response);
                    writer.flush();
                }
            } catch (Exception ignored) {
                // Client disconnected
            } finally {
                try { socket.close(); } catch (Exception ignored) {}
            }
        }
    }
}

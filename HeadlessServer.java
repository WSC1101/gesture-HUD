package org.example;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;

public class HeadlessServer {

    private static final int WEBSOCKET_PORT = 8884;
    private static final int HTTP_PORT = 8000; // 브라우저 접속용 포트

    public static void main(String[] args) {
        System.out.println("GestureHUD Headless Server");

        try {
            // 1. Mapbox를 서빙할 HTTP 서버 시작
            startLocalWebServer(HTTP_PORT);
        } catch (IOException e) {
            System.err.println("HTTP 서버 시작 실패: " + e.getMessage());
            return;
        }

        // 2. Python과 브라우저를 중계할 WebSocket 서버 시작
        startWebsocketServer(WEBSOCKET_PORT);

        System.out.println("=======================================================");
        System.out.println("✓ 서버가 성공적으로 시작되었습니다.");
        System.out.println("  1. Python 클라이언트를 실행하세요.");
        System.out.println("  2. Chrome/Edge 브라우저에서 http://localhost:" + HTTP_PORT + " 로 접속하세요.");
        System.out.println("=======================================================");

        // 메인 스레드가 종료되지 않도록 대기
        try {
            Thread.currentThread().join();
        } catch (InterruptedException e) {
            System.out.println("서버 중지됨.");
        }
    }

    private static void startLocalWebServer(int port) throws IOException {
        HttpServer localwebserver = HttpServer.create(new InetSocketAddress(port), 0);
        localwebserver.createContext("/", new HttpHandler() {
            @Override
            public void handle(HttpExchange exchange) throws IOException {
                // (GestureHUDApp.java에 있던 로직과 동일)
                // 리소스 경로 확인! (resources 폴더 최상단에 index.html)
                InputStream is = HeadlessServer.class.getResourceAsStream("/index.html");
                if (is == null) {
                    System.err.println("[HTTP] /index.html 파일을 찾을 수 없습니다.");
                    String response = "404 (Not Found) - index.html missing";
                    exchange.sendResponseHeaders(404, response.length());
                    try (OutputStream os = exchange.getResponseBody()) {
                        os.write(response.getBytes());
                    }
                    return;
                }

                byte[] htmlBytes = is.readAllBytes();
                is.close();

                exchange.getResponseHeaders().set("Content-Type", "text/html; charset=utf-8");
                exchange.sendResponseHeaders(200, htmlBytes.length);
                try (OutputStream os = exchange.getResponseBody()) {
                    os.write(htmlBytes);
                }
            }
        });
        localwebserver.setExecutor(null); // 기본 Executor 사용
        localwebserver.start();
        System.out.println("[HTTP 서버] http://localhost:" + port + " 에서 대기 중...");
    }

    private static void startWebsocketServer(int port) {
        GestureRouter gestureRouter = new GestureRouter();
        MainServer server = new MainServer(port, gestureRouter);

        // ★ 중요: MainServer 인스턴스를 핸들러에 주입
        // 핸들러가 서버의 broadcast() 기능을 사용해야 함
        PinchHandler pinchHandler = new PinchHandler(server);
        DragHandler dragHandler = new DragHandler(server);
        ZoomHandler zoomHandler = new ZoomHandler(server);

        // 모든 제스처 핸들러 등록
        gestureRouter.registerHandler("drag", dragHandler);
        gestureRouter.registerHandler("pinch", pinchHandler);
        gestureRouter.registerHandler("pinch_zoom", zoomHandler);


        Thread serverThread = new Thread(server); // Runnable이므로 바로 Thread에 넘김
        serverThread.setDaemon(true); // 메인 스레드 종료 시 함께 종료
        serverThread.start();

        System.out.println("[WebSocket 서버] ws://localhost:" + port + " 에서 대기 중...");
    }
}

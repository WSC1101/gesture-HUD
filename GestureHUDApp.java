package org.example;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.scene.Scene;
import javafx.scene.control.Label;
import javafx.scene.layout.Pane;
import javafx.scene.paint.Color;
import javafx.scene.shape.Circle;
import javafx.stage.Stage;

public class GestureHUDApp extends Application implements GestureListener {
    private MainServer server;
    private static final int PORT = 8885;
    private static final int SCREEN_WIDTH = 800;
    private static final int SCREEN_HEIGHT = 600;

    private Circle pointer;
    private Label coordinatesLabel;

    public static void main(String[] args) {
        launch(args);
    }

    @Override
    public void start(Stage primaryStage) {
        pointer = new Circle(15, Color.BLUE);
        coordinatesLabel = new Label("X: 0.00 , Y: 0.00");
        coordinatesLabel.setStyle("-fx-font-size: 16px; -fx-text-fill: white; -fx-background-color: rgba(0, 0, 0, 0.5); -fx-padding: 5;");
        coordinatesLabel.setLayoutX(10);
        coordinatesLabel.setLayoutY(10);

        Pane root = new Pane();
        root.setStyle("-fx-background-color: #333;");
        root.getChildren().addAll(pointer, coordinatesLabel);

        Scene scene = new Scene(root, SCREEN_WIDTH, SCREEN_HEIGHT);
        primaryStage.setTitle("Gesture HUD");
        primaryStage.setScene(scene);
        primaryStage.show();

        startWebsocketServer();

    }

    @Override
    public void onHandMoved(double x, double y) {

        Platform.runLater(() -> {
            double newX = x * SCREEN_WIDTH;
            double newY = y * SCREEN_HEIGHT;
            pointer.setCenterX(newX);
            pointer.setCenterY(newY);
            coordinatesLabel.setText(String.format("X: %.2f , Y: %.2f", x, y));

        });
    }

    public void startWebsocketServer(){
        GestureRouter gestureRouter = new GestureRouter();

        LandmarkHandler landmarkHandler =new LandmarkHandler(this);
        PinchHandler pinchHandler = new PinchHandler();
        DragHandler dragHandler = new DragHandler();
        ZoomHandler zoomHandler = new ZoomHandler();

        gestureRouter.handlerMap.put("drag",  dragHandler);
        gestureRouter.handlerMap.put("HAND_LANDMARKS", landmarkHandler);
        gestureRouter.handlerMap.put("pinch", pinchHandler);
        gestureRouter.handlerMap.put("pinch_zoom", zoomHandler);


        server = new MainServer(PORT, gestureRouter);
        new Thread(() -> server.start()).start();
        System.out.println("Started websocket server on the background");
    }

    @Override
    public void stop() throws Exception {
        if (server != null) {
            server.stop();
            System.out.println("Stopped server on the background");
        }
        super.stop();
    }





}

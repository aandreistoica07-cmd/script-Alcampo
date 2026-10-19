package com.alcampo.scraper;

import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class GitHubManager {

    private static final String OWNER = "hugh0ah";
    private static final String REPO = "alcampo";
    private static final ExecutorService executor = Executors.newSingleThreadExecutor();
    private static final Handler mainHandler = new Handler(Looper.getMainLooper());

    public interface Callback {
        void onSuccess(String message);
        void onError(String error);
    }

    public static void dispatchWorkflow(String token, String workflowFile, int accountsPerVm, int threads, Callback callback) {
        executor.execute(() -> {
            try {
                String endpoint = String.format("https://api.github.com/repos/%s/%s/actions/workflows/%s/dispatches", OWNER, REPO, workflowFile);
                URL url = new URL(endpoint);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Authorization", "Bearer " + token.trim());
                conn.setRequestProperty("Accept", "application/vnd.github.v3+json");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                conn.setConnectTimeout(15000);
                conn.setReadTimeout(15000);

                JSONObject body = new JSONObject();
                body.put("ref", "main");
                JSONObject inputs = new JSONObject();
                if ("alcampo_2pass_matrix.yml".equals(workflowFile)) {
                    inputs.put("accounts_per_vm", String.valueOf(accountsPerVm));
                } else {
                    inputs.put("threads", String.valueOf(threads));
                }
                body.put("inputs", inputs);

                try (OutputStream os = conn.getOutputStream()) {
                    os.write(body.toString().getBytes(StandardCharsets.UTF_8));
                }

                int responseCode = conn.getResponseCode();
                if (responseCode == 204 || responseCode == 200) {
                    mainHandler.post(() -> callback.onSuccess("¡Workflow '" + workflowFile + "' iniciado con éxito en GitHub Actions!"));
                } else {
                    StringBuilder errBuilder = new StringBuilder();
                    try (BufferedReader br = new BufferedReader(new InputStreamReader(conn.getErrorStream(), StandardCharsets.UTF_8))) {
                        String line;
                        while ((line = br.readLine()) != null) {
                            errBuilder.append(line);
                        }
                    }
                    String err = "HTTP " + responseCode + ": " + errBuilder.toString();
                    mainHandler.post(() -> callback.onError(err));
                }
            } catch (Exception e) {
                mainHandler.post(() -> callback.onError("Error de conexión: " + e.getMessage()));
            }
        });
    }
}
